"""テキストパーサー: 正規表現でHTML/PDFテキストから宴会場情報を抽出"""

from __future__ import annotations

import json
import logging
import re

from .models import (
    ExtractedData,
    ExtractionMethod,
    RoomData,
    VenuePageData,
)

logger = logging.getLogger(__name__)

# --- 正規表現パターン ---

# 面積: 「1,200㎡」「850 m²」「1200m2」等
RE_AREA = re.compile(
    r"(?:面積|広さ|Size)[：:\s]*"
    r"([\d,]+(?:\.\d+)?)\s*(?:㎡|m²|m2|平米)",
    re.IGNORECASE,
)
# テーブルや一覧中の面積（名前のあとに直接書かれるケース）
RE_AREA_INLINE = re.compile(
    r"([\d,]+(?:\.\d+)?)\s*(?:㎡|m²|m2)(?:\s|$|[）\)])",
)

# 天井高: 「天井高5.7m」「Ceiling: 3.2m」
RE_CEILING = re.compile(
    r"(?:天井高?|天高|Ceiling\s*(?:Height)?)[：:\s]*"
    r"(\d+(?:\.\d+)?)\s*(?:m|ｍ|メートル)",
    re.IGNORECASE,
)

# 収容人数: 「シアター200名」「スクール形式 150名」「Theater: 200」
RE_CAPACITY_THEATER = re.compile(
    r"(?:シアター|Theater|シアタ|立食を除くシアター)[形式ー\s：:]*(\d[\d,]*)\s*(?:名|人|席)?",
    re.IGNORECASE,
)
RE_CAPACITY_SCHOOL = re.compile(
    r"(?:スクール|School|教室)[形式ー\s：:]*(\d[\d,]*)\s*(?:名|人|席)?",
    re.IGNORECASE,
)
RE_CAPACITY_BANQUET = re.compile(
    r"(?:正餐|着席|バンケット|Banquet|ディナー|Dinner)[形式ー\s：:]*(\d[\d,]*)\s*(?:名|人|席)?",
    re.IGNORECASE,
)
RE_CAPACITY_STANDING = re.compile(
    r"(?:立食|スタンディング|Standing|ブッフェ|Buffet|カクテル|Cocktail)[形式ー\s：:]*(\d[\d,]*)\s*(?:名|人|席)?",
    re.IGNORECASE,
)

# 電話番号
RE_PHONE = re.compile(
    r"(?:TEL|電話|Tel|Phone|☎)[：:\s]*"
    r"((?:0\d{1,4}[-\s]?\d{1,4}[-\s]?\d{3,4})|(?:\+81[-\s]?\d{1,4}[-\s]?\d{1,4}[-\s]?\d{3,4}))",
    re.IGNORECASE,
)

# AV機器・設備
RE_EQUIPMENT = re.compile(
    r"(?:設備|備品|機材|Equipment|AV|音響|照明|プロジェクター|スクリーン|マイク|同時通訳)"
    r"[：:\s]*([^\n]{5,200})",
    re.IGNORECASE,
)

# PDFリンク（フロアプラン候補）
RE_PDF_LINK = re.compile(
    r'href=["\']([^"\']+\.pdf)["\']',
    re.IGNORECASE,
)

# 部屋名候補のパターン（テーブルヘッダ等で使用）
RE_ROOM_NAME = re.compile(
    r"(?:の間|ホール|ルーム|Room|Hall|サロン|Salon|ボールルーム|Ballroom)",
)


def _parse_number(s: str) -> float | None:
    """カンマ付き数値文字列をfloatに変換"""
    try:
        return float(s.replace(",", ""))
    except (ValueError, TypeError):
        return None


def _parse_int(s: str) -> int | None:
    """カンマ付き数値文字列をintに変換"""
    try:
        return int(s.replace(",", ""))
    except (ValueError, TypeError):
        return None


def parse_venue_text(
    text: str,
    hotel_id: str,
    source_url: str = "",
    source_url_id: int | None = None,
) -> list[ExtractedData]:
    """テキストから宴会場情報を抽出し、ExtractedDataリストを返す"""
    results: list[ExtractedData] = []

    # --- 施設全体の情報 ---

    # 電話番号
    phone_match = RE_PHONE.search(text)
    if phone_match:
        results.append(
            ExtractedData(
                hotel_id=hotel_id,
                data_type="venue",
                field_name="phone",
                value_json=json.dumps(phone_match.group(1).strip()),
                confidence=0.8,
                extraction_method=ExtractionMethod.REGEX,
                source_url_id=source_url_id,
            )
        )

    # フロアプランPDFリンク
    for pdf_match in RE_PDF_LINK.finditer(text):
        results.append(
            ExtractedData(
                hotel_id=hotel_id,
                data_type="venue",
                field_name="floor_plan_url",
                value_json=json.dumps(pdf_match.group(1)),
                confidence=0.6,
                extraction_method=ExtractionMethod.REGEX,
                source_url_id=source_url_id,
            )
        )

    # --- テキストをセクション分割して部屋単位で抽出を試みる ---
    sections = _split_into_room_sections(text)

    if sections:
        for room_name, section_text in sections:
            _extract_room_fields(
                section_text,
                hotel_id,
                room_name,
                source_url_id,
                results,
            )
    else:
        # セクション分割できない場合は全体から抽出
        _extract_room_fields(
            text,
            hotel_id,
            None,
            source_url_id,
            results,
        )

    return results


def _split_into_room_sections(text: str) -> list[tuple[str, str]]:
    """テキストを部屋名で区切ってセクションに分割。

    Returns:
        [(room_name, section_text), ...]
    """
    # 「◆鶴の間」「■ ボールルーム」「【芙蓉の間】」等のヘッダで分割
    pattern = re.compile(
        r"(?:^|\n)\s*(?:[◆■●▶▸★☆【〈《]|#{1,3}\s)"
        r"\s*([^\n]{2,30}(?:の間|ホール|ルーム|Room|Hall|サロン|Salon|ボールルーム|Ballroom)[^\n]{0,20})"
        r"\s*(?:[】〉》])?",
        re.MULTILINE,
    )

    matches = list(pattern.finditer(text))
    if len(matches) < 2:
        return []

    sections: list[tuple[str, str]] = []
    for i, m in enumerate(matches):
        room_name = m.group(1).strip()
        start = m.end()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
        section_text = text[start:end]
        sections.append((room_name, section_text))

    return sections


def _extract_room_fields(
    text: str,
    hotel_id: str,
    room_name: str | None,
    source_url_id: int | None,
    results: list[ExtractedData],
):
    """テキスト区間から部屋のフィールドを正規表現抽出"""

    field_patterns: list[tuple[str, re.Pattern, bool]] = [
        ("area_sqm", RE_AREA, False),
        ("area_sqm", RE_AREA_INLINE, False),
        ("ceiling_height_m", RE_CEILING, False),
        ("capacity_theater", RE_CAPACITY_THEATER, True),
        ("capacity_school", RE_CAPACITY_SCHOOL, True),
        ("capacity_banquet", RE_CAPACITY_BANQUET, True),
        ("capacity_standing", RE_CAPACITY_STANDING, True),
    ]

    seen_fields: set[str] = set()

    for field_name, pattern, is_int in field_patterns:
        if field_name in seen_fields:
            continue
        match = pattern.search(text)
        if match:
            raw = match.group(1)
            value = _parse_int(raw) if is_int else _parse_number(raw)
            if value is not None and value > 0:
                seen_fields.add(field_name)
                results.append(
                    ExtractedData(
                        hotel_id=hotel_id,
                        room_name=room_name,
                        data_type="room",
                        field_name=field_name,
                        value_json=json.dumps(value),
                        confidence=0.7,
                        extraction_method=ExtractionMethod.REGEX,
                        source_url_id=source_url_id,
                    )
                )

    # 設備
    equip_match = RE_EQUIPMENT.search(text)
    if equip_match:
        results.append(
            ExtractedData(
                hotel_id=hotel_id,
                room_name=room_name,
                data_type="room",
                field_name="equipment",
                value_json=json.dumps(equip_match.group(1).strip()),
                confidence=0.6,
                extraction_method=ExtractionMethod.REGEX,
                source_url_id=source_url_id,
            )
        )


def parse_table_text(
    rows: list[list[str]],
    hotel_id: str,
    source_url_id: int | None = None,
) -> list[ExtractedData]:
    """テーブル形式（行列）から部屋情報を抽出。

    ホテル宴会場ページによくある形式:
    | 会場名 | 面積(㎡) | 天井高(m) | シアター | スクール | 正餐 | 立食 |

    Args:
        rows: [[cell, cell, ...], ...] 形式のテーブルデータ
    """
    if len(rows) < 2:
        return []

    results: list[ExtractedData] = []
    header = [cell.strip().lower() for cell in rows[0]]

    # ヘッダからカラムマッピングを推定
    col_map: dict[str, int] = {}
    for i, h in enumerate(header):
        if any(k in h for k in ["会場", "部屋", "ルーム", "room", "name", "名称"]):
            col_map["name"] = i
        elif any(k in h for k in ["面積", "㎡", "m²", "area"]):
            col_map["area_sqm"] = i
        elif any(k in h for k in ["天井", "ceiling"]):
            col_map["ceiling_height_m"] = i
        elif any(k in h for k in ["シアター", "theater"]):
            col_map["capacity_theater"] = i
        elif any(k in h for k in ["スクール", "school", "教室"]):
            col_map["capacity_school"] = i
        elif any(k in h for k in ["正餐", "着席", "banquet", "ディナー"]):
            col_map["capacity_banquet"] = i
        elif any(k in h for k in ["立食", "standing", "ブッフェ", "buffet", "カクテル"]):
            col_map["capacity_standing"] = i

    if not col_map:
        return []

    # データ行処理
    for row in rows[1:]:
        if len(row) <= max(col_map.values(), default=0):
            continue

        room_name = row[col_map["name"]].strip() if "name" in col_map else None

        for field_name, col_idx in col_map.items():
            if field_name == "name":
                continue
            raw = row[col_idx].strip().replace(",", "").replace("，", "")
            # 数値抽出
            num_match = re.search(r"([\d.]+)", raw)
            if not num_match:
                continue

            is_int = field_name.startswith("capacity_")
            value = _parse_int(num_match.group(1)) if is_int else _parse_number(num_match.group(1))
            if value is None or value <= 0:
                continue

            results.append(
                ExtractedData(
                    hotel_id=hotel_id,
                    room_name=room_name,
                    data_type="room",
                    field_name=field_name,
                    value_json=json.dumps(value),
                    confidence=0.85,  # テーブルは信頼度高め
                    extraction_method=ExtractionMethod.TABLE,
                    source_url_id=source_url_id,
                )
            )

    return results
