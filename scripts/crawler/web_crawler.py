"""Webクローラー: httpx + BeautifulSoup によるHTML取得・リンク発見"""

from __future__ import annotations

import hashlib
import json
import logging
from urllib.parse import urljoin, urlparse

import httpx
from bs4 import BeautifulSoup

from .config import CrawlConfig, config as default_config
from .db import CrawlDB
from .models import CrawlPage, CrawlStatus, CrawlUrl, UrlType

logger = logging.getLogger(__name__)


class WebCrawler:
    """HTML取得 + リンク発見"""

    def __init__(self, cfg: CrawlConfig | None = None):
        self.cfg = cfg or default_config
        self._client: httpx.AsyncClient | None = None

    async def get_client(self) -> httpx.AsyncClient:
        if self._client is None:
            self._client = httpx.AsyncClient(
                timeout=self.cfg.request_timeout,
                follow_redirects=True,
                headers={"User-Agent": self.cfg.user_agent},
            )
        return self._client

    async def close(self):
        if self._client:
            await self._client.aclose()
            self._client = None

    async def fetch_page(
        self, crawl_url: CrawlUrl, db: CrawlDB
    ) -> tuple[CrawlPage | None, list[CrawlUrl]]:
        """ページを取得し、HTMLとリンクを返す。ETag差分チェック付き。

        Returns:
            (CrawlPage, 発見したURL一覧) or (None, []) on error/not-modified
        """
        client = await self.get_client()

        headers: dict[str, str] = {}
        if crawl_url.etag:
            headers["If-None-Match"] = crawl_url.etag

        try:
            resp = await client.get(crawl_url.url, headers=headers)

            # Not Modified
            if resp.status_code == 304:
                db.update_url_status(crawl_url.id, CrawlStatus.DONE)  # type: ignore
                logger.info("304 Not Modified: %s", crawl_url.url)
                return None, []

            resp.raise_for_status()

        except httpx.HTTPStatusError as e:
            logger.warning("HTTP %d: %s", e.response.status_code, crawl_url.url)
            db.update_url_status(crawl_url.id, CrawlStatus.ERROR)  # type: ignore
            return None, []
        except httpx.RequestError as e:
            logger.warning("Request error: %s - %s", crawl_url.url, e)
            db.update_url_status(crawl_url.id, CrawlStatus.ERROR)  # type: ignore
            return None, []

        # Content-Typeチェック
        content_type = resp.headers.get("content-type", "")
        if "text/html" not in content_type and "application/xhtml" not in content_type:
            logger.debug("Non-HTML content-type: %s for %s", content_type, crawl_url.url)
            db.update_url_status(crawl_url.id, CrawlStatus.DONE)  # type: ignore
            return None, []

        html = resp.text
        content_hash = hashlib.sha256(html.encode()).hexdigest()[:16]
        etag = resp.headers.get("etag")

        # 内容が前回と同じなら更新不要
        if crawl_url.content_hash and crawl_url.content_hash == content_hash:
            db.update_url_status(crawl_url.id, CrawlStatus.DONE, etag=etag)  # type: ignore
            logger.info("Content unchanged: %s", crawl_url.url)
            return None, []

        # HTMLパース
        soup = BeautifulSoup(html, "html.parser")
        title = soup.title.string.strip() if soup.title and soup.title.string else ""
        text_content = soup.get_text(separator="\n", strip=True)

        # リンク発見
        discovered = self._discover_links(
            soup, crawl_url, db
        )
        links_json = json.dumps(
            [u.url for u in discovered], ensure_ascii=False
        )

        page = CrawlPage(
            url_id=crawl_url.id,  # type: ignore
            html=html,
            text_content=text_content,
            title=title,
            links_json=links_json,
        )

        # DB保存
        db.save_page(page)
        db.update_url_status(
            crawl_url.id,  # type: ignore
            CrawlStatus.DONE,
            etag=etag,
            content_hash=content_hash,
        )

        return page, discovered

    def _discover_links(
        self,
        soup: BeautifulSoup,
        parent: CrawlUrl,
        db: CrawlDB,
    ) -> list[CrawlUrl]:
        """ページ内リンクからクロール対象URLを発見"""
        if parent.depth >= self.cfg.max_depth:
            return []

        discovered: list[CrawlUrl] = []
        base_url = parent.url

        for tag in soup.find_all("a", href=True):
            href = tag["href"].strip()
            if not href or href.startswith(("#", "mailto:", "tel:", "javascript:")):
                continue

            abs_url = urljoin(base_url, href)
            parsed = urlparse(abs_url)

            # フラグメント除去、スキーム制限
            clean_url = parsed._replace(fragment="").geturl()
            if parsed.scheme not in ("http", "https"):
                continue

            # 同一ドメイン制限
            if parsed.netloc != parent.domain:
                continue

            # 拡張子チェック
            from pathlib import PurePosixPath

            ext = PurePosixPath(parsed.path).suffix.lower()
            if ext in self.cfg.skip_extensions:
                continue

            # パスパターンフィルタ（PDF/画像は常に許可、ページはパターン一致必須）
            url_type = self.cfg.classify_url_type(clean_url)
            if url_type == "page" and not self.cfg.url_matches_allowed_path(parsed.path):
                continue

            # ドメインページ上限チェック
            if db.get_domain_page_count(parent.domain) >= self.cfg.max_pages_per_domain:
                continue

            discovered.append(
                CrawlUrl(
                    url=clean_url,
                    hotel_id=parent.hotel_id,
                    domain=parsed.netloc,
                    depth=parent.depth + 1,
                    url_type=UrlType(url_type),
                    status=CrawlStatus.PENDING,
                    parent_url_id=parent.id,
                )
            )

        return discovered

    async def download_asset(
        self, url: str, local_path: str
    ) -> tuple[bytes, dict[str, str]]:
        """PDF/画像のバイナリダウンロード"""
        from pathlib import Path

        client = await self.get_client()
        resp = await client.get(url)
        resp.raise_for_status()

        Path(local_path).parent.mkdir(parents=True, exist_ok=True)
        Path(local_path).write_bytes(resp.content)

        return resp.content, dict(resp.headers)
