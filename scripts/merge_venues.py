#!/usr/bin/env python3
"""
全データソースを統合して venues.json を生成するスクリプト。

データソース:
1. public/data/venues.json (既存33施設)
2. /tmp/new_hotels_crawl.json (新規ホテル17施設)
3. /tmp/new_venues_crawl.json (新規会議場28施設)
4. /tmp/db_room_enrichment.json (DB由来の部屋補完)
5. /tmp/venue_links.json (PDF/ブロシュア/会場ページURL)
"""

import json
import sys
import os
import re

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_DIR = os.path.dirname(SCRIPT_DIR)
VENUES_PATH = os.path.join(PROJECT_DIR, 'public', 'data', 'venues.json')

NEW_HOTELS_PATH = '/tmp/new_hotels_crawl.json'
NEW_VENUES_PATH = '/tmp/new_venues_crawl.json'
DB_ENRICHMENT_PATH = '/tmp/db_room_enrichment.json'
VENUE_LINKS_PATH = '/tmp/venue_links.json'


def load_json(path):
    if not os.path.exists(path):
        print(f"  警告: {path} が存在しません。スキップ。", file=sys.stderr)
        return None
    with open(path, 'r', encoding='utf-8') as f:
        return json.load(f)


def normalize_divisions(divisions):
    """divisions配列を正規化: 文字列→Division objectに変換"""
    result = []
    for d in divisions:
        if isinstance(d, str):
            # "ホール1 (196㎡)" → {name: "ホール1", areaSqm: 196}
            m = re.match(r'^(.+?)\s*[（(](\d+)㎡[）)]$', d)
            if m:
                result.append({
                    'name': m.group(1).strip(),
                    'areaSqm': int(m.group(2)),
                    'capacity': {}
                })
            else:
                result.append({
                    'name': d,
                    'capacity': {}
                })
        elif isinstance(d, dict):
            if 'capacity' not in d:
                d['capacity'] = {}
            result.append(d)
    return result


def normalize_capacity(cap):
    """capacity objectを正規化: buffet→standing"""
    if not cap:
        return {}
    result = {}
    for k, v in cap.items():
        if k == 'buffet':
            # buffet → standing (if standing not already set)
            if 'standing' not in cap or cap['standing'] is None:
                result['standing'] = v
        else:
            result[k] = v
    return result


def normalize_room(room):
    """Room objectを正規化"""
    room['capacity'] = normalize_capacity(room.get('capacity', {}))
    room['divisions'] = normalize_divisions(room.get('divisions', []))
    # equipmentが空文字列ならキー自体を削除
    if room.get('equipment') == '':
        del room['equipment']
    return room


def build_name_to_id_map(venues):
    """施設名→IDマッピング"""
    m = {}
    for v in venues:
        m[v['name']] = v['id']
    return m


def main():
    print("=== venues.json マージ開始 ===", file=sys.stderr)

    # 1. 既存venues読み込み
    existing = load_json(VENUES_PATH) or []
    existing_ids = {v['id'] for v in existing}
    print(f"  既存施設: {len(existing)}件", file=sys.stderr)

    # 2. 新規ホテル追加
    new_hotels = load_json(NEW_HOTELS_PATH) or []
    added_hotels = 0
    for hotel in new_hotels:
        if hotel['id'] not in existing_ids:
            for room in hotel.get('rooms', []):
                normalize_room(room)
            existing.append(hotel)
            existing_ids.add(hotel['id'])
            added_hotels += 1
    print(f"  新規ホテル追加: {added_hotels}件", file=sys.stderr)

    # 3. 新規会議場追加
    new_venues = load_json(NEW_VENUES_PATH) or []
    added_venues = 0
    for venue in new_venues:
        if venue['id'] not in existing_ids:
            for room in venue.get('rooms', []):
                normalize_room(room)
            existing.append(venue)
            existing_ids.add(venue['id'])
            added_venues += 1
    print(f"  新規会議場追加: {added_venues}件", file=sys.stderr)

    # 4. DB由来の部屋補完
    db_enrichment = load_json(DB_ENRICHMENT_PATH)
    if db_enrichment:
        hotel_map = {v['id']: v for v in existing}
        enriched_count = 0
        missing_added = 0

        for hotel_id, data in db_enrichment.items():
            hotel = hotel_map.get(hotel_id)
            if not hotel:
                continue

            # enrichments: 既存部屋のフィールド補完
            for room_id, enrich in data.get('enrichments', {}).items():
                for room in hotel.get('rooms', []):
                    if room['id'] == room_id:
                        for k, v in enrich.items():
                            if v is not None and room.get(k) is None:
                                room[k] = v
                                enriched_count += 1
                        break

            # missing_rooms: DB由来の追加部屋（控室等）
            existing_room_names = set()
            for r in hotel.get('rooms', []):
                existing_room_names.add(r['name'])
                clean = re.sub(r'[（(].+?[）)]', '', r['name']).strip()
                if clean:
                    existing_room_names.add(clean)
                for d in r.get('divisions', []):
                    existing_room_names.add(d.get('name', ''))

            for mr in data.get('missing_rooms', []):
                name = mr['name']
                # 重複チェック
                is_dup = False
                for en in existing_room_names:
                    if name == en or (len(name) >= 3 and len(en) >= 3 and (name in en or en in name)):
                        is_dup = True
                        break
                # 全スパン/分割バリエーションは既存のdivisionとして扱うべき
                if '全スパン' in name or re.match(r'.+\s*[東西南北]$', name):
                    is_dup = True

                if not is_dup:
                    room_id_slug = re.sub(r'[^a-zA-Z0-9]', '-',
                                          name.encode('ascii', 'ignore').decode() or
                                          f"db-room-{missing_added}")
                    new_room = {
                        'id': f"{hotel_id}-db-{room_id_slug}".lower(),
                        'name': name,
                        'areaSqm': mr.get('areaSqm'),
                        'ceilingHeightM': mr.get('ceilingHeightM'),
                        'capacity': {},
                        'divisions': [],
                    }
                    if mr.get('purpose'):
                        new_room['features'] = mr['purpose']
                    hotel['rooms'].append(new_room)
                    existing_room_names.add(name)
                    missing_added += 1

        print(f"  DB補完: フィールド補完={enriched_count}, 部屋追加={missing_added}", file=sys.stderr)

    # 5. URL情報追加
    venue_links = load_json(VENUE_LINKS_PATH)
    if venue_links:
        name_to_hotel = {v['name']: v for v in existing}
        links_applied = 0
        for name, links in venue_links.items():
            hotel = name_to_hotel.get(name)
            if not hotel:
                continue
            if 'practicalInfo' not in hotel or hotel['practicalInfo'] is None:
                hotel['practicalInfo'] = {}
            pi = hotel['practicalInfo']
            for key in ['venuePageUrl', 'floorPlanUrl', 'brochureUrl']:
                val = links.get(key)
                if val and not pi.get(key):
                    pi[key] = val
                    links_applied += 1
        print(f"  URL追加: {links_applied}件", file=sys.stderr)

    # 6. 最終統計
    total_rooms = sum(len(v.get('rooms', [])) for v in existing)
    regions = set(v.get('region', '?') for v in existing)
    print(f"\n  === 最終結果 ===", file=sys.stderr)
    print(f"  総施設数: {len(existing)}", file=sys.stderr)
    print(f"  総部屋数: {total_rooms}", file=sys.stderr)
    print(f"  地域: {', '.join(sorted(regions))}", file=sys.stderr)

    # 7. 書き出し
    with open(VENUES_PATH, 'w', encoding='utf-8') as f:
        json.dump(existing, f, ensure_ascii=False, indent=2)
    print(f"\n  {VENUES_PATH} に書き出し完了。", file=sys.stderr)


if __name__ == '__main__':
    main()
