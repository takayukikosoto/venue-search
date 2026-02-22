"""クロール結果を venues.json にマージ"""

from __future__ import annotations

import json
import logging
import re
from copy import deepcopy
from pathlib import Path

from .config import CrawlConfig, config as default_config
from .db import CrawlDB

logger = logging.getLogger(__name__)

# venues.json のフィールドと extracted_data の field_name のマッピング
FIELD_MAP = {
    "area_sqm": ("areaSqm", float),
    "ceiling_height_m": ("ceilingHeightM", float),
    "capacity_theater": ("capacity.theater", int),
    "capacity_school": ("capacity.school", int),
    "capacity_banquet": ("capacity.banquet", int),
    "capacity_standing": ("capacity.standing", int),
    "equipment": ("equipment", str),
}

VENUE_FIELD_MAP = {
    "phone": ("phone", str),
    "floor_plan_url": ("floorPlanUrl", str),
}

# 最低 confidence 閾値
DEFAULT_CONFIDENCE_THRESHOLD = 0.5


def merge(
    cfg: CrawlConfig | None = None,
    db: CrawlDB | None = None,
    confidence_threshold: float = DEFAULT_CONFIDENCE_THRESHOLD,
    dry_run: bool = False,
) -> dict:
    """extracted_data → venues.json マージ。

    Args:
        confidence_threshold: この値以上の confidence を持つデータのみマージ
        dry_run: True の場合、venues.json を更新せずdiffだけ返す

    Returns:
        diff情報: {hotel_id: {field: {old, new, confidence, method}}}
    """
    cfg = cfg or default_config
    db = db or CrawlDB(cfg)

    # venues.json 読み込み
    with open(cfg.venues_json, encoding="utf-8") as f:
        venues = json.load(f)

    # ホテルID→インデックスのマップ
    venue_idx = {v["id"]: i for i, v in enumerate(venues)}

    diff: dict[str, dict] = {}

    for hotel_id, idx in venue_idx.items():
        hotel_diff = _merge_hotel(
            venues[idx], hotel_id, db, confidence_threshold
        )
        if hotel_diff:
            diff[hotel_id] = hotel_diff

    if not dry_run and diff:
        # venues.json 書き出し
        with open(cfg.venues_json, "w", encoding="utf-8") as f:
            json.dump(venues, f, ensure_ascii=False, indent=2)
            f.write("\n")
        logger.info("venues.json updated: %d hotels modified", len(diff))
    elif dry_run:
        logger.info("Dry run: %d hotels would be modified", len(diff))

    return diff


def _merge_hotel(
    venue: dict,
    hotel_id: str,
    db: CrawlDB,
    threshold: float,
) -> dict:
    """1ホテルの抽出データをマージ"""
    hotel_diff: dict = {}

    # ホテルレベルのフィールド（phone, floorPlanUrl）
    for ext_field, (json_field, cast) in VENUE_FIELD_MAP.items():
        best = db.get_best_value(hotel_id, None, ext_field)
        if best and best.confidence >= threshold:
            old_val = venue.get(json_field)
            new_val = cast(json.loads(best.value_json))
            if old_val is None or old_val == "":
                venue[json_field] = new_val
                hotel_diff[json_field] = {
                    "old": old_val,
                    "new": new_val,
                    "confidence": best.confidence,
                    "method": best.extraction_method.value,
                }

    # 部屋レベルのフィールド
    rooms = venue.get("rooms", [])
    for room in rooms:
        room_id = room.get("id", "")
        room_name = room.get("name", "")
        room_diff: dict = {}

        for ext_field, (json_path, cast) in FIELD_MAP.items():
            # room_id でまず検索、なければ room_name で
            best = db.get_best_value(hotel_id, room_id, ext_field)
            if not best:
                best = _find_by_room_name(db, hotel_id, room_name, ext_field)
            if not best or best.confidence < threshold:
                continue

            new_val = cast(json.loads(best.value_json))

            # ネストされたパス（capacity.theater 等）の処理
            if "." in json_path:
                parts = json_path.split(".")
                container = room
                for part in parts[:-1]:
                    if part not in container:
                        container[part] = {}
                    container = container[part]
                old_val = container.get(parts[-1])
                if old_val is None:
                    container[parts[-1]] = new_val
                    room_diff[json_path] = {
                        "old": old_val,
                        "new": new_val,
                        "confidence": best.confidence,
                        "method": best.extraction_method.value,
                    }
            else:
                old_val = room.get(json_path)
                if old_val is None:
                    room[json_path] = new_val
                    room_diff[json_path] = {
                        "old": old_val,
                        "new": new_val,
                        "confidence": best.confidence,
                        "method": best.extraction_method.value,
                    }

        if room_diff:
            hotel_diff[f"room:{room_name}"] = room_diff

    return hotel_diff


def _find_by_room_name(
    db: CrawlDB, hotel_id: str, room_name: str, field_name: str
):
    """room_name でファジーマッチングして抽出データを探す"""
    all_data = db.get_extracted_by_hotel(hotel_id)
    normalized = _normalize_room_name(room_name)

    best = None
    for d in all_data:
        if d.field_name != field_name:
            continue
        if d.room_name and _normalize_room_name(d.room_name) == normalized:
            if best is None or d.confidence > best.confidence:
                best = d
    return best


def _normalize_room_name(name: str) -> str:
    """部屋名を正規化（比較用）"""
    # 全角→半角、スペース除去、「の間」統一
    name = name.replace("　", " ").strip()
    name = re.sub(r"\s+", "", name)
    name = name.lower()
    return name


def format_diff(diff: dict) -> str:
    """diff辞書を人間に読みやすい文字列に変換"""
    lines: list[str] = []
    for hotel_id, fields in sorted(diff.items()):
        lines.append(f"\n=== {hotel_id} ===")
        for field_key, change in sorted(fields.items()):
            if isinstance(change, dict) and "old" in change:
                lines.append(
                    f"  {field_key}: {change['old']} → {change['new']}"
                    f"  (confidence={change['confidence']:.2f}, method={change['method']})"
                )
            elif isinstance(change, dict):
                # room レベルのネスト
                for sub_field, sub_change in sorted(change.items()):
                    lines.append(
                        f"  {field_key}.{sub_field}: {sub_change['old']} → {sub_change['new']}"
                        f"  (confidence={sub_change['confidence']:.2f}, method={sub_change['method']})"
                    )
    return "\n".join(lines)
