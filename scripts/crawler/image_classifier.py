"""Gemini Flash による画像分類 + OCR"""

from __future__ import annotations

import json
import logging
from pathlib import Path

from .config import CrawlConfig, config as default_config
from .db import CrawlDB
from .models import (
    AssetType,
    CrawlAsset,
    CrawlStatus,
    CrawlUrl,
    ExtractedData,
    ExtractionMethod,
    ImageClass,
    ImageClassification,
)

logger = logging.getLogger(__name__)

CLASSIFICATION_PROMPT = """\
この画像を分析して、以下のJSON形式で回答してください。

1. 画像の分類: floor_plan（フロアプラン・間取り図・レイアウト図）, room_photo（宴会場・会議室の写真）, other（その他）
2. 信頼度: 0.0〜1.0
3. 画像の説明（日本語、1-2文）
4. 画像内のテキスト（OCR結果。部屋名、面積、収容人数などがあれば抽出）

JSON形式:
{
  "image_class": "floor_plan" | "room_photo" | "other",
  "confidence": 0.0-1.0,
  "description": "...",
  "extracted_text": "..."
}

JSONのみ回答してください。
"""


class ImageClassifier:
    """Gemini Flash を使った画像分類"""

    def __init__(self, cfg: CrawlConfig | None = None):
        self.cfg = cfg or default_config
        self._client = None

    def _get_client(self):
        if self._client is None:
            from google import genai

            api_key = self.cfg.gemini_api_key
            if not api_key:
                raise ValueError(
                    "GEMINI_API_KEY が設定されていません。"
                    "環境変数 GEMINI_API_KEY を設定してください。"
                )
            self._client = genai.Client(api_key=api_key)
        return self._client

    def classify(
        self,
        crawl_url: CrawlUrl,
        local_path: str,
        db: CrawlDB,
    ) -> ImageClassification | None:
        """画像を分類してDB保存"""
        from google.genai import types

        client = self._get_client()

        try:
            image_bytes = Path(local_path).read_bytes()
            mime = _guess_mime(local_path)

            response = client.models.generate_content(
                model=self.cfg.gemini_model,
                contents=[
                    types.Part.from_bytes(data=image_bytes, mime_type=mime),
                    CLASSIFICATION_PROMPT,
                ],
                config=types.GenerateContentConfig(
                    max_output_tokens=self.cfg.gemini_max_tokens,
                ),
            )

            text = response.text or ""
            classification = _parse_classification(text)

        except Exception as e:
            logger.error("Image classification failed: %s - %s", local_path, e)
            db.update_url_status(crawl_url.id, CrawlStatus.ERROR)  # type: ignore
            return None

        # アセットDB保存
        db.save_asset(
            CrawlAsset(
                url_id=crawl_url.id,  # type: ignore
                asset_type=AssetType.IMAGE,
                local_path=local_path,
                extracted_text=classification.extracted_text,
                image_class=classification.image_class,
                classification_confidence=classification.confidence,
            )
        )

        # フロアプランURLとして記録
        if classification.image_class == ImageClass.FLOOR_PLAN:
            db.save_extracted(
                ExtractedData(
                    hotel_id=crawl_url.hotel_id,
                    data_type="venue",
                    field_name="floor_plan_url",
                    value_json=json.dumps(crawl_url.url),
                    confidence=classification.confidence,
                    extraction_method=ExtractionMethod.GEMINI,
                    source_url_id=crawl_url.id,
                )
            )

        # OCRテキストから部屋情報抽出を試みる
        if classification.extracted_text:
            from .text_parser import parse_venue_text

            ocr_results = parse_venue_text(
                classification.extracted_text,
                hotel_id=crawl_url.hotel_id,
                source_url=crawl_url.url,
                source_url_id=crawl_url.id,
            )
            # Gemini OCR由来なので信頼度を少し下げる
            for r in ocr_results:
                r.confidence = min(r.confidence, 0.6)
                r.extraction_method = ExtractionMethod.GEMINI
            if ocr_results:
                db.save_extracted_batch(ocr_results)

        db.update_url_status(crawl_url.id, CrawlStatus.DONE)  # type: ignore
        logger.info(
            "Image classified: %s → %s (%.2f)",
            local_path,
            classification.image_class.value,
            classification.confidence,
        )

        return classification


def _parse_classification(text: str) -> ImageClassification:
    """Geminiの応答JSONをパース"""
    # JSONブロックを抽出
    text = text.strip()
    if text.startswith("```"):
        lines = text.split("\n")
        text = "\n".join(lines[1:-1]) if len(lines) > 2 else text

    try:
        data = json.loads(text)
        return ImageClassification(
            image_class=ImageClass(data.get("image_class", "other")),
            confidence=float(data.get("confidence", 0.5)),
            description=data.get("description", ""),
            extracted_text=data.get("extracted_text", ""),
        )
    except (json.JSONDecodeError, ValueError) as e:
        logger.warning("Failed to parse classification JSON: %s", e)
        return ImageClassification(
            image_class=ImageClass.OTHER,
            confidence=0.0,
            description="",
            extracted_text="",
        )


def _guess_mime(path: str) -> str:
    """ファイルパスからMIMEタイプを推定"""
    ext = Path(path).suffix.lower()
    return {
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".png": "image/png",
        ".webp": "image/webp",
        ".gif": "image/gif",
    }.get(ext, "image/png")
