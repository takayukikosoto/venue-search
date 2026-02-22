"""オーケストレーター: asyncioワーカー管理・ドメインレート制限・URL振り分け"""

from __future__ import annotations

import asyncio
import logging
import time
from pathlib import Path
from urllib.parse import urlparse

from .config import CrawlConfig, config as default_config
from .db import CrawlDB
from .models import CrawlStatus, CrawlUrl, UrlType
from .web_crawler import WebCrawler
from .pdf_extractor import PdfExtractor
from .text_parser import parse_venue_text
from .image_classifier import ImageClassifier

logger = logging.getLogger(__name__)


class DomainRateLimiter:
    """ドメインごとのリクエスト間隔を制御"""

    def __init__(self, delay: float):
        self.delay = delay
        self._last_request: dict[str, float] = {}
        self._lock = asyncio.Lock()

    async def wait(self, domain: str):
        """ドメインのレート制限を待つ"""
        async with self._lock:
            last = self._last_request.get(domain, 0)
            elapsed = time.monotonic() - last
            if elapsed < self.delay:
                await asyncio.sleep(self.delay - elapsed)
            self._last_request[domain] = time.monotonic()


class Orchestrator:
    """クロール全体を管理するオーケストレーター"""

    def __init__(self, cfg: CrawlConfig | None = None):
        self.cfg = cfg or default_config
        self.db = CrawlDB(self.cfg)
        self.rate_limiter = DomainRateLimiter(self.cfg.request_delay)
        self.web_crawler = WebCrawler(self.cfg)
        self.pdf_extractor = PdfExtractor(self.cfg)
        self.image_classifier = ImageClassifier(self.cfg)
        self._run_id: str = ""
        self._stop_event = asyncio.Event()

    async def run(
        self,
        hotel_id: str | None = None,
        max_urls: int | None = None,
    ):
        """クロール実行

        Args:
            hotel_id: 特定ホテルのみクロール（Noneで全ホテル）
            max_urls: 最大処理URL数（Noneで無制限）
        """
        self.db.init_db()
        self._reset_stale_fetching()
        self._run_id = CrawlDB.new_run_id()
        self.db.log_event(self._run_id, "start", f"hotel_id={hotel_id}")
        logger.info("Crawl started: run_id=%s, hotel_id=%s", self._run_id, hotel_id)

        sem = asyncio.Semaphore(self.cfg.max_concurrency)
        processed = 0
        tasks: set[asyncio.Task] = set()

        try:
            while not self._stop_event.is_set():
                if max_urls and processed >= max_urls:
                    break

                # 次のURLを取得
                crawl_url = self.db.claim_next_url(hotel_id=hotel_id)
                if crawl_url is None:
                    # 実行中のタスクがあれば待つ
                    if tasks:
                        done, tasks = await asyncio.wait(
                            tasks, return_when=asyncio.FIRST_COMPLETED
                        )
                        for t in done:
                            if t.exception():
                                logger.error("Worker error: %s", t.exception())
                        continue
                    else:
                        break  # 全URL処理完了

                processed += 1
                task = asyncio.create_task(
                    self._process_url(crawl_url, sem)
                )
                tasks.add(task)
                task.add_done_callback(tasks.discard)

            # 残りのタスクを待つ
            if tasks:
                await asyncio.gather(*tasks, return_exceptions=True)

        finally:
            await self.web_crawler.close()
            self.db.log_event(
                self._run_id, "end", f"processed={processed}"
            )
            logger.info("Crawl finished: processed=%d URLs", processed)

    async def _process_url(self, crawl_url: CrawlUrl, sem: asyncio.Semaphore):
        """URL種類に応じた処理ディスパッチ"""
        async with sem:
            # ドメインレート制限
            await self.rate_limiter.wait(crawl_url.domain)

            self.db.log_event(
                self._run_id, "fetch", crawl_url.url, url_id=crawl_url.id
            )

            try:
                if crawl_url.url_type == UrlType.PAGE:
                    await self._process_page(crawl_url)
                elif crawl_url.url_type == UrlType.PDF:
                    await self._process_pdf(crawl_url)
                elif crawl_url.url_type == UrlType.IMAGE:
                    await self._process_image(crawl_url)
            except Exception as e:
                logger.error("Error processing %s: %s", crawl_url.url, e)
                self.db.update_url_status(crawl_url.id, CrawlStatus.ERROR)  # type: ignore
                self.db.log_event(
                    self._run_id, "error", str(e), url_id=crawl_url.id
                )

    async def _process_page(self, crawl_url: CrawlUrl):
        """HTMLページの処理: 取得→パース→リンク発見→データ抽出"""
        page, discovered = await self.web_crawler.fetch_page(crawl_url, self.db)

        if discovered:
            added = self.db.add_urls(discovered)
            logger.info(
                "Discovered %d new URLs from %s", added, crawl_url.url
            )

        if page and page.text_content:
            # テキストから宴会場情報を抽出
            results = parse_venue_text(
                page.text_content,
                hotel_id=crawl_url.hotel_id,
                source_url=crawl_url.url,
                source_url_id=crawl_url.id,
            )
            if results:
                self.db.save_extracted_batch(results)
                logger.info(
                    "Extracted %d data points from %s",
                    len(results),
                    crawl_url.url,
                )

    async def _process_pdf(self, crawl_url: CrawlUrl):
        """PDFの処理: ダウンロード→テキスト/テーブル/画像抽出"""
        # ダウンロード先
        self.cfg.assets_dir.mkdir(parents=True, exist_ok=True)
        parsed = urlparse(crawl_url.url)
        filename = Path(parsed.path).name or "document.pdf"
        local_path = str(
            self.cfg.assets_dir / "pdfs" / crawl_url.hotel_id / filename
        )
        Path(local_path).parent.mkdir(parents=True, exist_ok=True)

        try:
            await self.web_crawler.download_asset(crawl_url.url, local_path)
        except Exception as e:
            logger.error("PDF download failed: %s - %s", crawl_url.url, e)
            self.db.update_url_status(crawl_url.id, CrawlStatus.ERROR)  # type: ignore
            return

        # PDF抽出（同期処理をスレッドプールで実行）
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(
            None,
            self.pdf_extractor.extract,
            crawl_url,
            local_path,
            self.db,
        )

    async def _process_image(self, crawl_url: CrawlUrl):
        """画像の処理: ダウンロード→Gemini分類"""
        if not self.cfg.gemini_api_key:
            logger.warning("GEMINI_API_KEY not set, skipping image: %s", crawl_url.url)
            self.db.update_url_status(crawl_url.id, CrawlStatus.ERROR)  # type: ignore
            return

        # ダウンロード先
        self.cfg.assets_dir.mkdir(parents=True, exist_ok=True)
        parsed = urlparse(crawl_url.url)
        filename = Path(parsed.path).name or "image.png"
        local_path = str(
            self.cfg.assets_dir / "images" / crawl_url.hotel_id / filename
        )
        Path(local_path).parent.mkdir(parents=True, exist_ok=True)

        try:
            await self.web_crawler.download_asset(crawl_url.url, local_path)
        except Exception as e:
            logger.error("Image download failed: %s - %s", crawl_url.url, e)
            self.db.update_url_status(crawl_url.id, CrawlStatus.ERROR)  # type: ignore
            return

        # Gemini分類（同期処理をスレッドプールで実行）
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(
            None,
            self.image_classifier.classify,
            crawl_url,
            local_path,
            self.db,
        )

    def _reset_stale_fetching(self):
        """前回中断で fetching のまま残ったURLを pending に戻す"""
        conn = self.db.connect()
        cur = conn.execute(
            "UPDATE crawl_urls SET status = 'pending', updated_at = datetime('now') WHERE status = 'fetching'"
        )
        if cur.rowcount > 0:
            logger.info("Reset %d stale fetching URLs to pending", cur.rowcount)

    def stop(self):
        """クロール停止"""
        self._stop_event.set()
