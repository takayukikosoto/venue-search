"""Pydantic モデル定義"""

from __future__ import annotations

from enum import Enum
from typing import Any, List, Optional

from pydantic import BaseModel, Field


# --- Enum ---


class UrlType(str, Enum):
    PAGE = "page"
    PDF = "pdf"
    IMAGE = "image"


class CrawlStatus(str, Enum):
    PENDING = "pending"
    FETCHING = "fetching"
    DONE = "done"
    ERROR = "error"


class AssetType(str, Enum):
    PDF = "pdf"
    IMAGE = "image"


class ImageClass(str, Enum):
    FLOOR_PLAN = "floor_plan"
    ROOM_PHOTO = "room_photo"
    OTHER = "other"


class ExtractionMethod(str, Enum):
    REGEX = "regex"
    TABLE = "table"
    GEMINI = "gemini"


# --- CrawlUrl ---


class CrawlUrl(BaseModel):
    """クロール対象URL"""

    id: Optional[int] = None
    url: str
    hotel_id: str
    domain: str
    depth: int = 0
    url_type: UrlType = UrlType.PAGE
    status: CrawlStatus = CrawlStatus.PENDING
    etag: Optional[str] = None
    content_hash: Optional[str] = None
    parent_url_id: Optional[int] = None


# --- CrawlPage ---


class CrawlPage(BaseModel):
    """取得済みHTMLページ"""

    url_id: int
    html: str = ""
    text_content: str = ""
    title: str = ""
    links_json: str = "[]"


# --- CrawlAsset ---


class CrawlAsset(BaseModel):
    """PDF/画像アセット"""

    url_id: int
    asset_type: AssetType
    local_path: str = ""
    extracted_text: str = ""
    image_class: Optional[ImageClass] = None
    classification_confidence: Optional[float] = None


# --- ExtractedData ---


class ExtractedData(BaseModel):
    """構造化抽出結果（1フィールド=1行）"""

    id: Optional[int] = None
    hotel_id: str
    room_id: Optional[str] = None
    room_name: Optional[str] = None
    data_type: str  # "room" / "venue"
    field_name: str  # "capacity_theater", "area_sqm", "ceiling_height_m", etc.
    value_json: str  # JSON文字列
    confidence: float = Field(ge=0.0, le=1.0)
    extraction_method: ExtractionMethod
    source_url_id: Optional[int] = None
    verified: bool = False


# --- RoomData (パーサー出力用) ---


class RoomData(BaseModel):
    """テキストパーサーが出力する部屋情報"""

    name: Optional[str] = None
    area_sqm: Optional[float] = None
    ceiling_height_m: Optional[float] = None
    capacity_theater: Optional[int] = None
    capacity_school: Optional[int] = None
    capacity_banquet: Optional[int] = None
    capacity_standing: Optional[int] = None
    equipment: Optional[str] = None
    phone: Optional[str] = None
    floor_plan_url: Optional[str] = None
    divisions: List[dict] = Field(default_factory=list)


# --- VenuePageData (パーサー出力用) ---


class VenuePageData(BaseModel):
    """1ページ分の宴会場情報抽出結果"""

    hotel_id: str
    source_url: str = ""
    rooms: List[RoomData] = Field(default_factory=list)
    phone: Optional[str] = None
    floor_plan_urls: List[str] = Field(default_factory=list)


# --- ImageClassification ---


class ImageClassification(BaseModel):
    """Gemini画像分類結果"""

    image_class: ImageClass
    confidence: float = Field(ge=0.0, le=1.0)
    description: str = ""
    extracted_text: str = ""
