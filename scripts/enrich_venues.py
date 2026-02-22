#!/usr/bin/env python3
"""
usage-records.json を元に venues.json の各ホテル・部屋に
利用実績サマリー（usageCount, typicalSeatCount, typicalUse）を追加するスクリプト。

Usage:
    python scripts/enrich_venues.py
"""

import json
import os
from collections import Counter
from statistics import median

VENUES_JSON = os.path.join(os.path.dirname(__file__), "..", "public", "data", "venues.json")
USAGE_JSON = os.path.join(os.path.dirname(__file__), "..", "public", "data", "usage-records.json")


def main():
    # 読み込み
    with open(VENUES_JSON, encoding="utf-8") as f:
        hotels = json.load(f)
    with open(USAGE_JSON, encoding="utf-8") as f:
        records = json.load(f)

    print(f"venues.json: {len(hotels)} hotels")
    print(f"usage-records.json: {len(records)} records")

    # ホテル別・部屋別に集計
    hotel_records = {}  # hotel_id -> list of records
    room_records = {}   # room_id -> list of records

    for r in records:
        hid = r.get("hotelId")
        rid = r.get("roomId")
        if hid:
            hotel_records.setdefault(hid, []).append(r)
        if rid:
            room_records.setdefault(rid, []).append(r)

    # venues.json を更新
    for hotel in hotels:
        hid = hotel["id"]
        h_records = hotel_records.get(hid, [])
        hotel["usageCount"] = len(h_records)

        for room in hotel["rooms"]:
            rid = room["id"]
            r_records = room_records.get(rid, [])
            room["usageCount"] = len(r_records)

            if r_records:
                # 典型的な座席数（中央値）
                seat_counts = [r["seatCount"] for r in r_records if r.get("seatCount")]
                if seat_counts:
                    room["typicalSeatCount"] = int(median(seat_counts))

                # 主な用途（セミナー名から推定）
                use_types = []
                for r in r_records:
                    name = r.get("seminarName", "")
                    if "ランチョン" in name:
                        use_types.append("ランチョンセミナー")
                    elif "エキスパート" in name:
                        use_types.append("エキスパートセミナー")
                    elif any(w in name for w in ["講演会", "講演"]):
                        use_types.append("講演会")
                    elif any(w in name for w in ["Summit", "Conference", "Forum", "カンファレンス", "フォーラム"]):
                        use_types.append("カンファレンス")
                    elif any(w in name for w in ["研究会"]):
                        use_types.append("研究会")
                    elif any(w in name for w in ["シンポジウム"]):
                        use_types.append("シンポジウム")
                    elif any(w in name for w in ["セミナー", "Seminar"]):
                        use_types.append("セミナー")
                    elif any(w in name for w in ["Meeting", "会議"]):
                        use_types.append("会議")
                    else:
                        use_types.append("セミナー")

                if use_types:
                    counter = Counter(use_types)
                    room["typicalUse"] = counter.most_common(1)[0][0]

    # 書き出し
    with open(VENUES_JSON, "w", encoding="utf-8") as f:
        json.dump(hotels, f, ensure_ascii=False, indent=2)
        f.write("\n")

    print(f"\n=== 結果 ===")
    enriched_hotels = sum(1 for h in hotels if h.get("usageCount", 0) > 0)
    enriched_rooms = sum(
        1 for h in hotels for r in h["rooms"] if r.get("usageCount", 0) > 0
    )
    print(f"実績ありホテル: {enriched_hotels}/{len(hotels)}")
    print(f"実績あり部屋: {enriched_rooms}")

    print(f"\nホテル別 usageCount:")
    for h in sorted(hotels, key=lambda x: x.get("usageCount", 0), reverse=True):
        if h.get("usageCount", 0) > 0:
            room_info = ", ".join(
                f"{r['name']}({r.get('usageCount', 0)})"
                for r in h["rooms"] if r.get("usageCount", 0) > 0
            )
            print(f"  {h['name']}: {h['usageCount']}件 [{room_info}]")

    print(f"\n出力: {VENUES_JSON}")


if __name__ == "__main__":
    main()
