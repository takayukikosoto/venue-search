"""SQLite データベース操作モジュール

5テーブル: crawl_urls, crawl_pages, crawl_assets, extracted_data, crawl_log
"""

from __future__ import annotations

import json
import logging
import sqlite3
import uuid
from contextlib import contextmanager
from datetime import datetime, timezone

from .config import CrawlConfig, config as default_config
from .models import (
    AssetType,
    CrawlAsset,
    CrawlPage,
    CrawlStatus,
    CrawlUrl,
    ExtractedData,
    ExtractionMethod,
    ImageClass,
    UrlType,
)

logger = logging.getLogger(__name__)

SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS crawl_urls (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    url         TEXT    NOT NULL UNIQUE,
    hotel_id    TEXT    NOT NULL,
    domain      TEXT    NOT NULL,
    depth       INTEGER NOT NULL DEFAULT 0,
    url_type    TEXT    NOT NULL DEFAULT 'page',
    status      TEXT    NOT NULL DEFAULT 'pending',
    etag        TEXT,
    content_hash TEXT,
    parent_url_id INTEGER REFERENCES crawl_urls(id),
    created_at  TEXT    NOT NULL DEFAULT (datetime('now')),
    updated_at  TEXT    NOT NULL DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_crawl_urls_status ON crawl_urls(status);
CREATE INDEX IF NOT EXISTS idx_crawl_urls_hotel  ON crawl_urls(hotel_id);
CREATE INDEX IF NOT EXISTS idx_crawl_urls_domain ON crawl_urls(domain);

CREATE TABLE IF NOT EXISTS crawl_pages (
    url_id       INTEGER PRIMARY KEY REFERENCES crawl_urls(id),
    html         TEXT    NOT NULL DEFAULT '',
    text_content TEXT    NOT NULL DEFAULT '',
    title        TEXT    NOT NULL DEFAULT '',
    links_json   TEXT    NOT NULL DEFAULT '[]',
    created_at   TEXT    NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS crawl_assets (
    url_id                   INTEGER PRIMARY KEY REFERENCES crawl_urls(id),
    asset_type               TEXT    NOT NULL,
    local_path               TEXT    NOT NULL DEFAULT '',
    extracted_text           TEXT    NOT NULL DEFAULT '',
    image_class              TEXT,
    classification_confidence REAL,
    created_at               TEXT    NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS extracted_data (
    id                INTEGER PRIMARY KEY AUTOINCREMENT,
    hotel_id          TEXT    NOT NULL,
    room_id           TEXT,
    room_name         TEXT,
    data_type         TEXT    NOT NULL,
    field_name        TEXT    NOT NULL,
    value_json        TEXT    NOT NULL,
    confidence        REAL    NOT NULL DEFAULT 0.5,
    extraction_method TEXT    NOT NULL DEFAULT 'regex',
    source_url_id     INTEGER REFERENCES crawl_urls(id),
    verified          INTEGER NOT NULL DEFAULT 0,
    created_at        TEXT    NOT NULL DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_extracted_hotel ON extracted_data(hotel_id);
CREATE INDEX IF NOT EXISTS idx_extracted_room  ON extracted_data(hotel_id, room_id);

CREATE TABLE IF NOT EXISTS crawl_log (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    run_id     TEXT    NOT NULL,
    event_type TEXT    NOT NULL,
    url_id     INTEGER,
    message    TEXT    NOT NULL DEFAULT '',
    created_at TEXT    NOT NULL DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_crawl_log_run ON crawl_log(run_id);
"""


class CrawlDB:
    """クロールデータベース操作クラス"""

    def __init__(self, cfg: CrawlConfig | None = None):
        self.cfg = cfg or default_config
        self.db_path = self.cfg.db_path
        self._conn: sqlite3.Connection | None = None

    # --- 接続管理 ---

    def connect(self) -> sqlite3.Connection:
        if self._conn is None:
            self._conn = sqlite3.connect(
                str(self.db_path),
                timeout=30,
                isolation_level=None,  # autocommit; 明示的にBEGINする
                check_same_thread=False,  # run_in_executor で別スレッドからアクセス
            )
            self._conn.row_factory = sqlite3.Row
            self._conn.execute("PRAGMA journal_mode=WAL")
            self._conn.execute("PRAGMA foreign_keys=ON")
        return self._conn

    def close(self):
        if self._conn:
            self._conn.close()
            self._conn = None

    def init_db(self):
        """テーブル作成"""
        conn = self.connect()
        conn.executescript(SCHEMA_SQL)
        logger.info("DB initialized: %s", self.db_path)

    @contextmanager
    def transaction(self):
        """BEGIN IMMEDIATE トランザクション"""
        conn = self.connect()
        conn.execute("BEGIN IMMEDIATE")
        try:
            yield conn
            conn.execute("COMMIT")
        except Exception:
            conn.execute("ROLLBACK")
            raise

    # --- crawl_urls CRUD ---

    def add_url(self, crawl_url: CrawlUrl) -> int:
        """URL追加。重複はINSERT OR IGNOREで無視。挿入されたIDまたは既存のIDを返す。"""
        conn = self.connect()
        cur = conn.execute(
            """INSERT OR IGNORE INTO crawl_urls
               (url, hotel_id, domain, depth, url_type, status, parent_url_id)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (
                crawl_url.url,
                crawl_url.hotel_id,
                crawl_url.domain,
                crawl_url.depth,
                crawl_url.url_type.value,
                crawl_url.status.value,
                crawl_url.parent_url_id,
            ),
        )
        if cur.lastrowid and cur.rowcount > 0:
            return cur.lastrowid
        # 既に存在する場合
        row = conn.execute(
            "SELECT id FROM crawl_urls WHERE url = ?", (crawl_url.url,)
        ).fetchone()
        return row["id"]

    def add_urls(self, urls: list[CrawlUrl]) -> int:
        """複数URL一括追加。追加件数を返す。"""
        conn = self.connect()
        added = 0
        for u in urls:
            cur = conn.execute(
                """INSERT OR IGNORE INTO crawl_urls
                   (url, hotel_id, domain, depth, url_type, status, parent_url_id)
                   VALUES (?, ?, ?, ?, ?, ?, ?)""",
                (
                    u.url,
                    u.hotel_id,
                    u.domain,
                    u.depth,
                    u.url_type.value,
                    u.status.value,
                    u.parent_url_id,
                ),
            )
            if cur.rowcount > 0:
                added += 1
        return added

    def claim_next_url(
        self,
        hotel_id: str | None = None,
        url_type: UrlType | None = None,
    ) -> CrawlUrl | None:
        """次のpending URLを取得し、statusをfetchingに更新（アトミック）"""
        conn = self.connect()
        conn.execute("BEGIN IMMEDIATE")
        try:
            conditions = ["status = 'pending'"]
            params: list = []
            if hotel_id:
                conditions.append("hotel_id = ?")
                params.append(hotel_id)
            if url_type:
                conditions.append("url_type = ?")
                params.append(url_type.value)
            where = " AND ".join(conditions)

            row = conn.execute(
                f"SELECT * FROM crawl_urls WHERE {where} ORDER BY depth, id LIMIT 1",
                params,
            ).fetchone()
            if not row:
                conn.execute("COMMIT")
                return None

            conn.execute(
                "UPDATE crawl_urls SET status = 'fetching', updated_at = datetime('now') WHERE id = ?",
                (row["id"],),
            )
            conn.execute("COMMIT")

            return CrawlUrl(
                id=row["id"],
                url=row["url"],
                hotel_id=row["hotel_id"],
                domain=row["domain"],
                depth=row["depth"],
                url_type=UrlType(row["url_type"]),
                status=CrawlStatus.FETCHING,
                etag=row["etag"],
                content_hash=row["content_hash"],
                parent_url_id=row["parent_url_id"],
            )
        except Exception:
            conn.execute("ROLLBACK")
            raise

    def update_url_status(
        self,
        url_id: int,
        status: CrawlStatus,
        etag: str | None = None,
        content_hash: str | None = None,
    ):
        """URL状態更新"""
        conn = self.connect()
        conn.execute(
            """UPDATE crawl_urls
               SET status = ?, etag = COALESCE(?, etag),
                   content_hash = COALESCE(?, content_hash),
                   updated_at = datetime('now')
               WHERE id = ?""",
            (status.value, etag, content_hash, url_id),
        )

    def get_domain_page_count(self, domain: str) -> int:
        """ドメインごとの取得済み+取得中ページ数"""
        conn = self.connect()
        row = conn.execute(
            "SELECT COUNT(*) as cnt FROM crawl_urls WHERE domain = ? AND status IN ('done', 'fetching')",
            (domain,),
        ).fetchone()
        return row["cnt"]

    def get_urls_by_hotel(self, hotel_id: str) -> list[CrawlUrl]:
        """ホテルIDでURL一覧取得"""
        conn = self.connect()
        rows = conn.execute(
            "SELECT * FROM crawl_urls WHERE hotel_id = ? ORDER BY depth, id",
            (hotel_id,),
        ).fetchall()
        return [
            CrawlUrl(
                id=r["id"],
                url=r["url"],
                hotel_id=r["hotel_id"],
                domain=r["domain"],
                depth=r["depth"],
                url_type=UrlType(r["url_type"]),
                status=CrawlStatus(r["status"]),
                etag=r["etag"],
                content_hash=r["content_hash"],
                parent_url_id=r["parent_url_id"],
            )
            for r in rows
        ]

    # --- crawl_pages CRUD ---

    def save_page(self, page: CrawlPage):
        """ページHTML保存"""
        conn = self.connect()
        conn.execute(
            """INSERT OR REPLACE INTO crawl_pages
               (url_id, html, text_content, title, links_json)
               VALUES (?, ?, ?, ?, ?)""",
            (
                page.url_id,
                page.html,
                page.text_content,
                page.title,
                page.links_json,
            ),
        )

    def get_page(self, url_id: int) -> CrawlPage | None:
        """ページ取得"""
        conn = self.connect()
        row = conn.execute(
            "SELECT * FROM crawl_pages WHERE url_id = ?", (url_id,)
        ).fetchone()
        if not row:
            return None
        return CrawlPage(
            url_id=row["url_id"],
            html=row["html"],
            text_content=row["text_content"],
            title=row["title"],
            links_json=row["links_json"],
        )

    # --- crawl_assets CRUD ---

    def save_asset(self, asset: CrawlAsset):
        """アセットメタデータ保存"""
        conn = self.connect()
        conn.execute(
            """INSERT OR REPLACE INTO crawl_assets
               (url_id, asset_type, local_path, extracted_text,
                image_class, classification_confidence)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (
                asset.url_id,
                asset.asset_type.value,
                asset.local_path,
                asset.extracted_text,
                asset.image_class.value if asset.image_class else None,
                asset.classification_confidence,
            ),
        )

    # --- extracted_data CRUD ---

    def save_extracted(self, data: ExtractedData) -> int:
        """抽出データ保存"""
        conn = self.connect()
        cur = conn.execute(
            """INSERT INTO extracted_data
               (hotel_id, room_id, room_name, data_type, field_name,
                value_json, confidence, extraction_method, source_url_id, verified)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                data.hotel_id,
                data.room_id,
                data.room_name,
                data.data_type,
                data.field_name,
                data.value_json,
                data.confidence,
                data.extraction_method.value,
                data.source_url_id,
                int(data.verified),
            ),
        )
        return cur.lastrowid  # type: ignore

    def save_extracted_batch(self, items: list[ExtractedData]):
        """抽出データ一括保存"""
        conn = self.connect()
        conn.executemany(
            """INSERT INTO extracted_data
               (hotel_id, room_id, room_name, data_type, field_name,
                value_json, confidence, extraction_method, source_url_id, verified)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            [
                (
                    d.hotel_id,
                    d.room_id,
                    d.room_name,
                    d.data_type,
                    d.field_name,
                    d.value_json,
                    d.confidence,
                    d.extraction_method.value,
                    d.source_url_id,
                    int(d.verified),
                )
                for d in items
            ],
        )

    def get_extracted_by_hotel(self, hotel_id: str) -> list[ExtractedData]:
        """ホテルIDで抽出データ一覧取得"""
        conn = self.connect()
        rows = conn.execute(
            """SELECT * FROM extracted_data
               WHERE hotel_id = ?
               ORDER BY confidence DESC, id""",
            (hotel_id,),
        ).fetchall()
        return [
            ExtractedData(
                id=r["id"],
                hotel_id=r["hotel_id"],
                room_id=r["room_id"],
                room_name=r["room_name"],
                data_type=r["data_type"],
                field_name=r["field_name"],
                value_json=r["value_json"],
                confidence=r["confidence"],
                extraction_method=ExtractionMethod(r["extraction_method"]),
                source_url_id=r["source_url_id"],
                verified=bool(r["verified"]),
            )
            for r in rows
        ]

    def get_best_value(
        self, hotel_id: str, room_id: str | None, field_name: str
    ) -> ExtractedData | None:
        """最高confidence の抽出値を返す"""
        conn = self.connect()
        if room_id:
            row = conn.execute(
                """SELECT * FROM extracted_data
                   WHERE hotel_id = ? AND room_id = ? AND field_name = ?
                   ORDER BY confidence DESC LIMIT 1""",
                (hotel_id, room_id, field_name),
            ).fetchone()
        else:
            row = conn.execute(
                """SELECT * FROM extracted_data
                   WHERE hotel_id = ? AND room_id IS NULL AND field_name = ?
                   ORDER BY confidence DESC LIMIT 1""",
                (hotel_id, field_name),
            ).fetchone()
        if not row:
            return None
        return ExtractedData(
            id=row["id"],
            hotel_id=row["hotel_id"],
            room_id=row["room_id"],
            room_name=row["room_name"],
            data_type=row["data_type"],
            field_name=row["field_name"],
            value_json=row["value_json"],
            confidence=row["confidence"],
            extraction_method=ExtractionMethod(row["extraction_method"]),
            source_url_id=row["source_url_id"],
            verified=bool(row["verified"]),
        )

    # --- crawl_log ---

    def log_event(
        self,
        run_id: str,
        event_type: str,
        message: str = "",
        url_id: int | None = None,
    ):
        """ログ記録"""
        conn = self.connect()
        conn.execute(
            "INSERT INTO crawl_log (run_id, event_type, url_id, message) VALUES (?, ?, ?, ?)",
            (run_id, event_type, url_id, message),
        )

    # --- 統計 ---

    def get_status_counts(self) -> dict[str, int]:
        """URL状態別件数"""
        conn = self.connect()
        rows = conn.execute(
            "SELECT status, COUNT(*) as cnt FROM crawl_urls GROUP BY status"
        ).fetchall()
        return {r["status"]: r["cnt"] for r in rows}

    def get_hotel_summary(self) -> list[dict]:
        """ホテルごとの進捗サマリ"""
        conn = self.connect()
        rows = conn.execute(
            """SELECT hotel_id,
                      COUNT(*) as total_urls,
                      SUM(CASE WHEN status='done' THEN 1 ELSE 0 END) as done,
                      SUM(CASE WHEN status='error' THEN 1 ELSE 0 END) as errors,
                      SUM(CASE WHEN status='pending' THEN 1 ELSE 0 END) as pending
               FROM crawl_urls GROUP BY hotel_id ORDER BY hotel_id"""
        ).fetchall()
        return [dict(r) for r in rows]

    def get_extracted_data_summary(self) -> dict[str, int]:
        """抽出データの field_name 別件数"""
        conn = self.connect()
        rows = conn.execute(
            "SELECT field_name, COUNT(*) as cnt FROM extracted_data GROUP BY field_name ORDER BY cnt DESC"
        ).fetchall()
        return {r["field_name"]: r["cnt"] for r in rows}

    @staticmethod
    def new_run_id() -> str:
        """新しい run_id を生成"""
        return datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S_") + uuid.uuid4().hex[:6]
