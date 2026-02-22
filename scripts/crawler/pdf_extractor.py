"""PDF抽出モジュール: pymupdf4llm でPDFからテキスト・テーブル・画像を抽出"""

from __future__ import annotations

import json
import logging
from pathlib import Path

from .config import CrawlConfig, config as default_config
from .db import CrawlDB
from .models import AssetType, CrawlAsset, CrawlStatus, CrawlUrl, ExtractedData
from .text_parser import parse_table_text, parse_venue_text

logger = logging.getLogger(__name__)


class PdfExtractor:
    """PDF → テキスト・テーブル・画像抽出"""

    def __init__(self, cfg: CrawlConfig | None = None):
        self.cfg = cfg or default_config

    def extract(
        self,
        crawl_url: CrawlUrl,
        local_path: str,
        db: CrawlDB,
    ) -> list[ExtractedData]:
        """PDFからテキストとテーブルを抽出し、ExtractedDataを返す"""
        import pymupdf4llm
        import pymupdf

        results: list[ExtractedData] = []

        try:
            # Markdown形式でテキスト抽出
            md_text = pymupdf4llm.to_markdown(local_path)

            # テーブル抽出
            doc = pymupdf.open(local_path)
            tables = self._extract_tables(doc)
            # 画像抽出
            image_paths = self._extract_images(doc, local_path)
            doc.close()

        except Exception as e:
            logger.error("PDF extraction failed: %s - %s", local_path, e)
            db.update_url_status(crawl_url.id, CrawlStatus.ERROR)  # type: ignore
            return []

        # アセットDB保存
        db.save_asset(
            CrawlAsset(
                url_id=crawl_url.id,  # type: ignore
                asset_type=AssetType.PDF,
                local_path=local_path,
                extracted_text=md_text[:50000],  # 50KB上限
            )
        )

        # テキストから情報抽出
        text_results = parse_venue_text(
            md_text,
            hotel_id=crawl_url.hotel_id,
            source_url=crawl_url.url,
            source_url_id=crawl_url.id,
        )
        results.extend(text_results)

        # テーブルから情報抽出
        for table in tables:
            table_results = parse_table_text(
                table,
                hotel_id=crawl_url.hotel_id,
                source_url_id=crawl_url.id,
            )
            results.extend(table_results)

        # 抽出データDB保存
        if results:
            db.save_extracted_batch(results)

        db.update_url_status(crawl_url.id, CrawlStatus.DONE)  # type: ignore
        logger.info(
            "PDF extracted: %s → %d data points", local_path, len(results)
        )

        return results

    def _extract_tables(self, doc) -> list[list[list[str]]]:
        """PyMuPDF のテーブル検出"""
        tables: list[list[list[str]]] = []
        for page in doc:
            try:
                tab_finder = page.find_tables()
                for table in tab_finder.tables:
                    rows = table.extract()
                    # ヘッダ+データ行が2行以上ある場合のみ
                    if len(rows) >= 2:
                        # None を空文字列に置換
                        clean_rows = [
                            [cell if cell else "" for cell in row]
                            for row in rows
                        ]
                        tables.append(clean_rows)
            except Exception as e:
                logger.debug("Table extraction failed on page: %s", e)
        return tables

    def _extract_images(self, doc, pdf_path: str) -> list[str]:
        """PDFから埋め込み画像を抽出して保存"""
        image_dir = self.cfg.assets_dir / "images"
        image_dir.mkdir(parents=True, exist_ok=True)
        saved: list[str] = []

        for page_num, page in enumerate(doc):
            for img_idx, img in enumerate(page.get_images(full=True)):
                xref = img[0]
                try:
                    pix = pymupdf_get_pixmap(doc, xref)
                    if pix.width < 100 or pix.height < 100:
                        continue  # アイコンなどをスキップ

                    stem = Path(pdf_path).stem
                    fname = f"{stem}_p{page_num}_i{img_idx}.png"
                    out_path = str(image_dir / fname)
                    pix.save(out_path)
                    saved.append(out_path)
                except Exception as e:
                    logger.debug("Image extraction failed: xref=%d - %s", xref, e)

        return saved


def pymupdf_get_pixmap(doc, xref: int):
    """PyMuPDF で xref から Pixmap を取得"""
    import pymupdf

    return pymupdf.Pixmap(doc, xref)
