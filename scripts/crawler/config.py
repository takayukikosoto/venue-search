"""クローラー設定モジュール"""

import os
import re
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class CrawlConfig:
    """クロール設定"""

    # パス
    base_dir: Path = field(
        default_factory=lambda: Path(__file__).resolve().parent
    )
    venues_json: Path = field(
        default_factory=lambda: Path(__file__).resolve().parent.parent.parent
        / "public"
        / "data"
        / "venues.json"
    )
    db_path: Path = field(
        default_factory=lambda: Path(__file__).resolve().parent / "crawl.db"
    )
    assets_dir: Path = field(
        default_factory=lambda: Path(__file__).resolve().parent / "assets"
    )

    # HTTP制限
    max_concurrency: int = 5
    request_delay: float = 2.0  # 同一ドメイン間隔(秒)
    request_timeout: float = 30.0
    max_retries: int = 2

    # クロール範囲
    max_depth: int = 3
    max_pages_per_domain: int = 50

    # 許可パスパターン（宴会場関連ページのみ巡回）
    allowed_path_patterns: list[re.Pattern] = field(default_factory=lambda: [
        re.compile(p) for p in [
            r"/banquet", r"/meeting", r"/event", r"/conference",
            r"/venue", r"/hall", r"/floor", r"/plan", r"/access",
            r"/mice", r"/party", r"/function",
            r"/宴会", r"/会議", r"/イベント", r"/施設",
        ]
    ])

    # 無視するファイル拡張子
    skip_extensions: set[str] = field(default_factory=lambda: {
        ".jpg", ".jpeg", ".png", ".gif", ".svg", ".webp", ".ico",
        ".css", ".js", ".woff", ".woff2", ".ttf", ".eot",
        ".mp4", ".mp3", ".avi", ".mov",
        ".zip", ".tar", ".gz",
    })

    # PDF / 画像 拡張子
    pdf_extensions: set[str] = field(default_factory=lambda: {".pdf"})
    image_extensions: set[str] = field(default_factory=lambda: {
        ".jpg", ".jpeg", ".png", ".webp",
    })

    # Gemini 設定
    gemini_api_key: str = field(
        default_factory=lambda: os.environ.get("GEMINI_API_KEY", "")
    )
    gemini_model: str = "gemini-2.0-flash"
    gemini_max_tokens: int = 1024

    # User-Agent
    user_agent: str = (
        "Mozilla/5.0 (compatible; VenueSearchBot/1.0; "
        "+https://github.com/venue-search)"
    )

    def url_matches_allowed_path(self, path: str) -> bool:
        """URLパスが許可パターンに一致するか"""
        path_lower = path.lower()
        return any(p.search(path_lower) for p in self.allowed_path_patterns)

    def classify_url_type(self, url: str) -> str:
        """URLの種類を判定: page / pdf / image"""
        from urllib.parse import urlparse

        parsed = urlparse(url)
        path_lower = parsed.path.lower()
        ext = Path(path_lower).suffix
        if ext in self.pdf_extensions:
            return "pdf"
        if ext in self.image_extensions:
            return "image"
        return "page"


# シングルトン設定インスタンス
config = CrawlConfig()
