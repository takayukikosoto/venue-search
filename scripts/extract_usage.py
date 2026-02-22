#!/usr/bin/env python3
"""
sharepoint_pptx.db から運営マニュアルの利用実績データを抽出し、
usage-records.json を生成するスクリプト。

Usage:
    python scripts/extract_usage.py
"""

import json
import os
import re
import sqlite3
import hashlib
from pathlib import Path

# --- 設定 ---
DB_PATH = os.path.expanduser("~/K_Kyosai/cosponsor-automation/sharepoint_pptx.db")
VENUES_JSON = os.path.join(os.path.dirname(__file__), "..", "public", "data", "venues.json")
OUTPUT_PATH = os.path.join(os.path.dirname(__file__), "..", "public", "data", "usage-records.json")

# --- ホテル名正規化辞書 ---
# venues.json のホテル名 → DB中で使われる表記の揺れ対応
HOTEL_ALIASES = {
    "ホテルニューオータニ東京": ["ニューオータニ東京", "ホテルニューオータニ　東京", "Hotel New Otani Tokyo"],
    "帝国ホテル東京": ["帝国ホテル 東京", "Imperial Hotel Tokyo", "帝国ホテル　東京"],
    "ホテルオークラ東京": ["オークラ東京", "The Okura Tokyo", "ホテルオークラ 東京"],
    "パレスホテル東京": ["パレスホテル 東京", "Palace Hotel Tokyo"],
    "ザ・プリンス パークタワー東京": ["プリンス パークタワー東京", "プリンスパークタワー東京", "ザ・プリンスパークタワー東京", "Prince Park Tower"],
    "東京マリオットホテル": ["東京マリオット", "Tokyo Marriott"],
    "グランドプリンスホテル新高輪": ["グランドプリンス新高輪", "Grand Prince Shintakanawa"],
    "品川プリンスホテル": ["品川プリンス", "Shinagawa Prince"],
    "ヒルトン東京": ["Hilton Tokyo", "ヒルトン 東京"],
    "ザ・リッツ・カールトン東京": ["リッツ・カールトン東京", "リッツカールトン東京", "Ritz-Carlton Tokyo"],
    "ANAインターコンチネンタルホテル東京": ["ANAインターコンチ", "ANA InterContinental", "ANAインターコンチネンタル東京"],
    "ホテル椿山荘東京": ["椿山荘", "椿山荘東京", "Hotel Chinzanso"],
    "グランドハイアット東京": ["グランド ハイアット東京", "Grand Hyatt Tokyo"],
    "セルリアンタワー東急ホテル": ["セルリアンタワー", "Cerulean Tower"],
    "京王プラザホテル": ["京王プラザ", "Keio Plaza"],
    "ホテルグランドアーク半蔵門": ["グランドアーク半蔵門", "Grand Arc Hanzomon"],
    "ハイアットリージェンシー東京": ["ハイアット リージェンシー東京", "Hyatt Regency Tokyo"],
    "ウェスティンホテル東京": ["ウェスティン東京", "Westin Tokyo"],
    "シェラトン都ホテル東京": ["シェラトン都", "シェラトン都ホテル", "Sheraton Miyako Tokyo"],
    "ホテルイースト21東京": ["イースト21", "Hotel East 21"],
    "第一ホテル東京": ["第一ホテル 東京", "Dai-ichi Hotel Tokyo"],
    "ヒルトン大阪": ["Hilton Osaka", "ヒルトン 大阪"],
    "リーガロイヤルホテル大阪": ["リーガロイヤル大阪", "リーガロイヤル", "Rihga Royal Osaka"],
    "ホテルニューオータニ大阪": ["ニューオータニ大阪", "New Otani Osaka"],
    "帝国ホテル大阪": ["帝国ホテル 大阪", "Imperial Hotel Osaka"],
    "名古屋マリオットアソシアホテル": ["名古屋マリオット", "マリオットアソシア", "Nagoya Marriott"],
    "ヒルトン名古屋": ["Hilton Nagoya", "ヒルトン 名古屋"],
    "ヒルトン福岡シーホーク": ["ヒルトン福岡", "Hilton Fukuoka", "シーホーク"],
    "ホテルニューオータニ博多": ["ニューオータニ博多", "New Otani Hakata"],
    "グランドプリンスホテル京都(ザ・プリンス京都宝ヶ池)": ["プリンスホテル京都", "プリンス京都宝ヶ池", "ザ・プリンス京都宝ヶ池", "グランドプリンス京都"],
    "ウェスティン都ホテル京都": ["ウェスティン都京都", "都ホテル京都", "Westin Miyako Kyoto"],
    # --- 以下は venues.json にないが DB に頻出する施設 ---
    # ホテル（venues.json 未登録）
    "東京プリンスホテル": ["東京プリンス"],
    "ストリングスホテル東京インターコンチネンタル": ["ストリングスホテル", "ストリングス東京"],
    "ホテルモントレ ルフレール大阪": ["モントレ ルフレール", "モントレルフレール大阪"],
    "ホテルモントレグラスミア大阪": ["モントレグラスミア"],
    "コンラッド東京": ["コンラッド 東京", "Conrad Tokyo"],
    "横浜ベイホテル東急": [],
    "東京ドームホテル": [],
    "横浜ロイヤルパークホテル": ["ロイヤルパークホテル"],
    "横浜桜木町ワシントンホテル": ["桜木町ワシントンホテル"],
    "神戸ポートピアホテル": ["ポートピアホテル", "神戸ポートピアホテル南館", "神戸ポートピアホテル本館"],
    "ヒルトン横浜": [],
    "丸ノ内ホテル": [],
    "札幌プリンスホテル": [],
    "ホテル日航金沢": ["日航金沢"],
    "ホテルオークラ福岡": ["オークラ福岡"],
    "ホテル日航福岡": ["日航福岡"],
    "京王プラザホテル札幌": [],
    "ホテルオークラ神戸": ["オークラ神戸"],
    "唐津シーサイドホテル": [],
    "ホテルメトロポリタン仙台": ["メトロポリタン仙台"],
    "羽田エクセルホテル東急": ["エクセルホテル東急"],
    "秋田キャッスルホテル": [],
    "ANAクラウンプラザホテル神戸": [],
    "ANAクラウンプラザホテル大阪": [],
    "ANAクラウンプラザホテル松山": [],
    "グランドプリンスホテル高輪": ["グランドプリンス高輪"],
    "ザ・リッツ・カールトン大阪": ["リッツ・カールトン大阪", "リッツカールトン大阪"],
    "ウェスティンホテル大阪": ["ウェスティン大阪"],
    "ホテルグランヴィア大阪": ["グランヴィア大阪"],
    # 会議場・ホール・コンファレンス施設
    "パシフィコ横浜": [],
    "日経ホール": ["日経ホール＆カンファレンスルーム", "日経カンファレンスルーム"],
    "ベルサール八重洲": [],
    "ベルサール飯田橋駅前": ["ベルサール飯田橋"],
    "ベルサール半蔵門": [],
    "ベルサール九段": [],
    "ベルサール渋谷ファースト": ["ベルサール渋谷"],
    "ベルサール東京日本橋": [],
    "ベルサール東京": [],
    "東京国際フォーラム": [],
    "ヒューリックホール東京": ["ヒューリックホール"],
    "丸ビルホール": [],
    "日本橋三井ホール": ["三井ホール"],
    "虎ノ門ヒルズフォーラム": [],
    "JPタワーホール＆カンファレンス": ["JPタワーホール"],
    "ステーションコンファレンス東京": [],
    "東京コンファレンスセンター・品川": ["東京コンファレンスセンター品川"],
    "御茶ノ水ソラシティカンファレンスセンター": ["御茶ノ水ソラシティ"],
    "TODA HALL & CONFERENCE TOKYO": ["TODA HALL"],
    "福岡国際会議場": [],
    "神戸国際会議場": [],
    "名古屋国際会議場": [],
    "大阪国際会議場": ["大阪府立国際会議場", "グランキューブ大阪"],
    "仙台国際センター": [],
    "熊本城ホール": [],
    "和歌山城ホール": [],
    "岡山コンベンションセンター": [],
    "コングレコンベンションセンター": [],
    "ナレッジキャピタルコングレコンベンションセンター": ["ナレッジキャピタル"],
    "TKP東京ベイ幕張ホール": [],
    "TKPガーデンシティ仙台": [],
    "TKPガーデンシティ博多": [],
    "TKPガーデンシティPREMIUM大宮": [],
    "TKPガーデンシティPREMIUMみなとみらい": [],
    "TKPガーデンシティPREMIUM仙台西口": [],
    "TKPガーデンシティPREMIUM広島駅前": [],
    "品川インターシティホール": ["品川インターシティ"],
    "秋葉原UDX": [],
    # 追加ホテル・施設
    "KABUTO ONE": ["KABUTO ONE HALL＆CONFERENCE", "KABUTO ONE HALL"],
    "幕張メッセ": [],
    "東京ビッグサイト": [],
    "アカデミーヒルズ": [],
    "オービックホール": [],
    "TKP新横浜カンファレンスセンター": ["TKP 新横浜 カンファレンスセンター", "TKP新横浜"],
    "JRゲートタワーカンファレンス": ["JRゲートタワー"],
    "イイノホール": [],
    "東京ガーデンテラス紀尾井町": ["東京ガーデンテラス"],
    "六本木ヒルズ": [],
    "東京ミッドタウン": ["ミッドタウンカンファレンス", "ミッドタウンタワー"],
    "新宿ファーストタワー": [],
    "江陽グランドホテル": [],
    "山形国際ホテル": [],
    "京都烏丸コンベンションホール": [],
    "ビッグパレットふくしま": [],
    "フクラシア東京ステーション": ["フクラシア"],
    "三重県総合文化センター": [],
    "あわぎんホール": [],
    "金沢市アートホール": [],
    "石川県立音楽堂": [],
}


def load_venues():
    """venues.json を読み込み、ホテル名→(hotel_id, canonical_name)、部屋名→IDのマッピングを構築"""
    with open(VENUES_JSON, encoding="utf-8") as f:
        hotels = json.load(f)

    hotel_map = {}  # alias_or_name -> (hotel_id, canonical_name)
    room_map = {}   # (hotel_id, normalized_room_name) -> room_id

    for h in hotels:
        canonical = h["name"]
        # 正規名
        hotel_map[canonical] = (h["id"], canonical)
        # エイリアス
        for alias in HOTEL_ALIASES.get(canonical, []):
            hotel_map[alias] = (h["id"], canonical)

        for r in h["rooms"]:
            # 部屋名の正規化: 括弧や全角半角を統一
            room_name_normalized = normalize_room_name(r["name"])
            room_map[(h["id"], room_name_normalized)] = r["id"]
            # 分割部屋も登録
            for d in r.get("divisions", []):
                dn = normalize_room_name(d["name"])
                room_map[(h["id"], dn)] = r["id"]

    # venues.json にないホテルのエイリアスも登録
    for canonical, aliases in HOTEL_ALIASES.items():
        if canonical not in [v[1] for v in hotel_map.values()]:
            # venues.json にないホテル → hotel_id なし
            hotel_map[canonical] = (None, canonical)
            for alias in aliases:
                hotel_map[alias] = (None, canonical)

    return hotel_map, room_map


def normalize_room_name(name):
    """部屋名を正規化"""
    # 括弧内の補足を除去: 醍醐(全室) → 醍醐
    name = re.sub(r'[（(][^）)]*[）)]', '', name)
    # 全角スペース→半角
    name = name.replace('　', ' ')
    # 前後の空白除去
    return name.strip()


def match_hotel(text, hotel_map):
    """テキストからホテル名を検出し、(正規ホテル名, hotel_id) を返す"""
    # 長い名前から先にマッチさせる（部分一致の誤検出を防止）
    for name in sorted(hotel_map.keys(), key=len, reverse=True):
        if name in text:
            hotel_id, canonical_name = hotel_map[name]
            return canonical_name, hotel_id
    return None, None


def match_room(room_name_raw, hotel_id, room_map):
    """部屋名からroom_idをマッチ"""
    if not hotel_id or not room_name_raw:
        return None
    normalized = normalize_room_name(room_name_raw)
    # 完全マッチ
    if (hotel_id, normalized) in room_map:
        return room_map[(hotel_id, normalized)]
    # 部分マッチ
    for (hid, rname), rid in room_map.items():
        if hid == hotel_id:
            if normalized in rname or rname in normalized:
                return rid
    return None


def extract_date(text):
    """テキストから開催日を抽出"""
    # パターン1: 2025年7月25日
    m = re.search(r'(20\d{2})\s*年\s*(\d{1,2})\s*月\s*(\d{1,2})\s*日', text)
    if m:
        return f"{m.group(1)}-{int(m.group(2)):02d}-{int(m.group(3)):02d}"
    # パターン2: 2025/7/25 or 2025.7.25
    m = re.search(r'(20\d{2})[./](\d{1,2})[./](\d{1,2})', text)
    if m:
        return f"{m.group(1)}-{int(m.group(2)):02d}-{int(m.group(3)):02d}"
    return None


def extract_year(date_str):
    """日付文字列から年を返す"""
    if date_str:
        m = re.match(r'(\d{4})', date_str)
        if m:
            return int(m.group(1))
    return None


def extract_seminar_name(text, filename):
    """セミナー名を抽出"""
    # スライドテキストからセミナー名らしきものを探す（優先）
    lines = text.split('\n')
    candidates = []
    for line in lines:
        line = line.strip()
        # 定型文を除外
        if any(skip in line for skip in ['運営マニュアル', '個人情報', '機密情報', '本マニュアル',
                                          '署名', '廃棄', 'Ver.', 'Name：', 'Day', 'Venue',
                                          'Operation Manual', 'Time', '来場', '退場',
                                          'CONFIDENTIAL', 'Supported by',
                                          'Facilitate', 'No：', '終了後', '保全',
                                          '最終', '初稿', '第1稿', '第2稿', '第3稿', '第4稿',
                                          '会場', '日時']):
            continue
        # 日付行を除外
        if re.match(r'^\d{4}[./年]', line):
            continue
        if re.match(r'^\d{1,2}\s*:\s*\d{2}', line):
            continue
        if re.match(r'^\d{1,2}月', line):
            continue
        # 短すぎる・長すぎる行を除外
        if len(line) < 4 or len(line) > 100:
            continue
        # ホテル名だけの行を除外
        if re.match(r'^(シェラトン|ヒルトン|ウェスティン|帝国|ニューオータニ|グランド|プリンス|東京|リーガ|ストリングス|ANAインター|コンラッド|京王|セルリアン|ハイアット|パレス|オークラ|マリオット|椿山荘)', line):
            if len(line) < 20:
                continue
        candidates.append(line)

    if candidates:
        # 「ランチョンセミナー」「エキスパートセミナー」等のセッション名があればそれを優先
        for c in candidates:
            if re.search(r'(セミナー|シンポジウム|ワークショップ|フォーラム|カンファレンス|Conference|Summit|Seminar|Forum|Meeting|研究会)', c):
                return c
        return candidates[0]

    # ファイル名からフォールバック
    m = re.search(r'【運営マニュアル】(.+?)(?:_v\d|_ver\.|_最終|\.pptx)', filename)
    if m:
        name = m.group(1).strip()
        # 日付部分を除去
        name = re.sub(r'_?\d{4}$', '', name)
        name = re.sub(r'^[\d_]+', '', name).strip('_').strip()
        if len(name) > 3:
            return name

    return filename.replace('.pptx', '')


def extract_seat_count(text):
    """席数総数を抽出"""
    m = re.search(r'席数総数[：:\s]*(\d+)\s*席', text)
    if m:
        return int(m.group(1))
    # 「座席数：N席」パターン
    m = re.search(r'座席[数総]*[：:\s]*(\d+)\s*席', text)
    if m:
        return int(m.group(1))
    return None


def extract_area(text):
    """面積を抽出"""
    m = re.search(r'(?:広さ|面積)[：:\s]*(\d+(?:\.\d+)?)\s*㎡', text)
    if m:
        return float(m.group(1))
    return None


def extract_ceiling(text):
    """天井高を抽出"""
    m = re.search(r'(?:天[井高]+|天高)[：:\s]*(\d+(?:\.\d+)?)\s*m', text)
    if m:
        return float(m.group(1))
    return None


def extract_room_name_from_layout(text):
    """レイアウトスライドから会場名を抽出"""
    m = re.search(r'会場[名：:\s]*([^\s\n]+)', text)
    if m:
        return m.group(1).strip()
    return None


def extract_equipment(texts_list):
    """機材リストをレイアウト/機材スライドから抽出"""
    equipment = set()
    # 機材テーブルのあるスライドのみ対象（「機材関係」or 「No,」+「名称」を含む）
    for text in texts_list:
        if not ('機材' in text or ('名称' in text and re.search(r'No[.,\s]', text))):
            continue
        lines = text.split('\n')
        for line in lines:
            line = line.strip()
            # 機材テーブルの行: 機材名称を含む行
            if re.match(r'^(有線マイク|ワイヤレスマイク|スクリーン&?プロジェクター|プロジェクター|インターネット回線|モニター|ホワイトボード|レーザーポインター|演台|マイクスタンド|PC\b)', line):
                # 数量部分を除去
                item = re.sub(r'\s+\d+[本式台個セット名].*$', '', line).strip()
                item = re.sub(r'[●○]', '', item).strip()
                if item and len(item) > 1 and len(item) < 30:
                    equipment.add(item)
    # 「■ スクリーン：2面(250inch)」形式を抽出
    for text in texts_list:
        for m in re.finditer(r'スクリーン[：:\s]*(\d+面(?:\([^)]+\))?)', text):
            equipment.add(f"スクリーン {m.group(1)}")
    return sorted(equipment) if equipment else None


def extract_green_rooms(text):
    """控室情報を抽出（会場全体案内テーブルから）"""
    rooms = []
    lines = text.split('\n')

    # テーブル形式: 部屋名 / 用途 / 面積 / 時間
    purpose_keywords = ['講師控室', '主催事務局', '社員聴講', '控室', '託児',
                        '運営事務局', 'ブリーフィング', 'トラベル']
    for i, line in enumerate(lines):
        line = line.strip()
        for kw in purpose_keywords:
            if kw in line:
                room_info = {"purpose": kw}
                # 前後の行から部屋名・面積を探す
                context = '\n'.join(lines[max(0, i-2):min(len(lines), i+3)])
                # 面積
                am = re.search(r'(\d+(?:\.\d+)?)\s*㎡', context)
                if am:
                    room_info["areaSqm"] = float(am.group(1))
                # 部屋名（行の前後で探す）
                for j in range(max(0, i-2), min(len(lines), i+3)):
                    cl = lines[j].strip()
                    if cl and cl != line and len(cl) < 20 and kw not in cl:
                        if not re.match(r'^\d', cl) and '㎡' not in cl and ':' not in cl:
                            room_info["name"] = cl
                            break
                if "name" not in room_info:
                    room_info["name"] = kw
                rooms.append(room_info)
                break

    # 重複除去
    seen = set()
    unique = []
    for r in rooms:
        key = r["name"]
        if key not in seen:
            seen.add(key)
            unique.append(r)
    return unique if unique else None


def extract_usage_hours(text):
    """使用時間帯を抽出"""
    m = re.search(r'手配時間[：:\s]*(\d{1,2}:\d{2}\s*[-~～]\s*\d{1,2}:\d{2})', text)
    if m:
        return m.group(1)
    return None


def extract_attendee_estimate(all_texts):
    """弁当数から参加者推定"""
    for text in all_texts:
        # 「弁当 N個」パターン
        m = re.search(r'(?:弁当|お弁当)[：:\s]*(\d+)\s*(?:個|食|名分)', text)
        if m:
            return int(m.group(1))
        # 「登録者数」や「一般：N名」パターン
        m = re.search(r'一般[：:\s]*(\d+)\s*名', text)
        if m:
            return int(m.group(1))
    return None


def deduplicate_files(files):
    """同一ベース名で最新版のみ残す重複排除"""
    # ベース名の正規化: 稿数・バージョン・日付接尾辞を除去
    def base_name(filename):
        name = filename
        # 先頭の稿数プレフィックスを除去
        name = re.sub(r'^(?:最終稿|最終準備稿|印刷後最終稿|初稿|第\d稿|[\d稿]*※.+?)(?:【|_)', '【', name)
        name = re.sub(r'^(?:大塚製薬用_|お台場スタッフ用|作成中)', '', name)
        # 先頭の日付プレフィックスを除去: 0122藤崎戻し, 0912IQVIA追記, 1009更新, 230705, etc.
        name = re.sub(r'^\d{4,6}(?:[A-Za-z\u3040-\u9FFF]+)?(?:【)', '【', name)
        # 先頭の数字_パターン: 1_【運営マニュアル】
        name = re.sub(r'^\d+_', '', name)
        # バージョン接尾辞を除去: _v0217, _v01301, _ver.0705
        name = re.sub(r'_v\d+(?:\.\d+)?\.pptx$', '.pptx', name)
        name = re.sub(r'_ver\.\d+\.pptx$', '.pptx', name)
        # 日付接尾辞を除去: _0217, _0216 (4桁 at end), _20231213
        name = re.sub(r'_\d{4,8}\.pptx$', '.pptx', name)
        # 日付接尾辞パターン2: _1115 (1) (1).pptx, _1115 (1).pptx
        name = re.sub(r'_\d{4}\s*(?:\(\d+\)\s*)*\.pptx$', '.pptx', name)
        # 「最終」「最終準備稿」等の接尾辞
        name = re.sub(r'_?(?:最終準備稿|最終稿|最終|FIX最終稿)\.pptx$', '.pptx', name)
        # 「-tuskamoto-PC」等の個人名サフィックス
        name = re.sub(r'-\w+-PC\.pptx$', '.pptx', name)
        return name

    groups = {}
    for f in files:
        bn = base_name(f["name"])
        if bn not in groups:
            groups[bn] = []
        groups[bn].append(f)

    # 各グループで最新（extracted_at順）を選択
    result = []
    for bn, group in groups.items():
        # extracted_at が最新のものを選択
        latest = max(group, key=lambda x: x.get("extracted_at", "") or "")
        result.append(latest)

    return result


def process_manual(item_id, filename, slides, hotel_map, room_map):
    """1つの運営マニュアルから UsageRecord を抽出"""
    if not slides:
        return None

    slide_texts = {s["slide_number"]: s["texts"] for s in slides}
    all_texts = [s["texts"] for s in slides]
    all_text_combined = '\n'.join(all_texts)

    # --- スライド1 + 2 + 3 から基本情報抽出 ---
    first_slides_text = '\n'.join(
        slide_texts.get(i, '') for i in range(1, min(6, max(slide_texts.keys()) + 1))
    )

    # ホテル名
    hotel_name, hotel_id = match_hotel(first_slides_text, hotel_map)
    if not hotel_name:
        # 全スライドから探す
        hotel_name, hotel_id = match_hotel(all_text_combined, hotel_map)

    if not hotel_name:
        return None  # ホテルが特定できない場合はスキップ

    # 開催日
    date = extract_date(first_slides_text)

    # セミナー名
    slide1_text = slide_texts.get(1, '')
    seminar_name = extract_seminar_name(slide1_text, filename)

    # --- 会場全体案内スライドから詳細情報 ---
    room_name = None
    floor = None
    area_sqm = None
    ceiling_height = None
    green_rooms = None
    usage_hours = None

    for sn, text in slide_texts.items():
        if '会場全体案内' in text or ('㎡' in text and '会場' in text and '用途' in text):
            # フロア・部屋テーブルパース
            # 「講演会会場」行から部屋名を取得
            m = re.search(r'講演会\s*会場\s*\n?\s*([^\n㎡]+)', text)
            if m:
                candidate = m.group(1).strip()
                if len(candidate) < 30:
                    room_name = candidate
                    # 括弧除去
                    room_name = re.sub(r'[（(].*?[）)]', '', room_name).strip()

            # 控室情報
            green_rooms = extract_green_rooms(text)
            # 使用時間
            usage_hours = extract_usage_hours(text)
            break

    # --- レイアウトスライドから席数・機材 ---
    seat_count = None
    equipment = None

    for sn, text in slide_texts.items():
        if '席数総数' in text or '座席総数' in text:
            seat_count = extract_seat_count(text)
            if not area_sqm:
                area_sqm = extract_area(text)
            if not ceiling_height:
                ceiling_height = extract_ceiling(text)
            if not room_name:
                room_name = extract_room_name_from_layout(text)
            break

    # 機材は全スライドから抽出
    equipment = extract_equipment(all_texts)

    # スライド1のテキストからも部屋名候補を抽出
    if not room_name:
        # 「N階「部屋名」」パターン
        m = re.search(r'(\d+)\s*階\s*[「『]([^」』]+)[」』]', first_slides_text)
        if m:
            floor = f"{m.group(1)}F"
            room_name = m.group(2)
        else:
            # 「NF 部屋名」パターン
            m = re.search(r'(\d+)\s*F\s+(\S+)', first_slides_text)
            if m:
                floor = f"{m.group(1)}F"
                room_name = m.group(2)

    # スケジュールスライドから部屋名候補
    if not room_name:
        for sn, text in slide_texts.items():
            if 'スケジュール' in text and '講演会会場' in text:
                # 「NF 部屋名」パターン
                m = re.search(r'(\d+)F\s+(\S+)', text)
                if m:
                    floor = f"{m.group(1)}F"
                    room_name = m.group(2)
                    break

    if not room_name:
        room_name = "不明"

    # room_id マッチ
    room_id = match_room(room_name, hotel_id, room_map)

    # 参加者推定
    attendee_estimate = extract_attendee_estimate(all_texts)

    # ID生成
    record_id = hashlib.md5(f"{item_id}:{hotel_name}:{room_name}".encode()).hexdigest()[:12]

    record = {
        "id": record_id,
        "hotelName": hotel_name,
        "roomName": room_name,
        "seminarName": seminar_name,
        "sourceFile": filename,
    }

    if hotel_id:
        record["hotelId"] = hotel_id
    if room_id:
        record["roomId"] = room_id
    if floor:
        record["floor"] = floor
    if date:
        record["date"] = date
        year = extract_year(date)
        if year:
            record["year"] = year
    if seat_count:
        record["seatCount"] = seat_count
    if area_sqm:
        record["areaSqm"] = area_sqm
    if ceiling_height:
        record["ceilingHeightM"] = ceiling_height
    if green_rooms:
        record["greenRooms"] = green_rooms
    if equipment:
        record["equipment"] = equipment
    if usage_hours:
        record["usageHours"] = usage_hours
    if attendee_estimate:
        record["attendeeEstimate"] = attendee_estimate

    return record


def main():
    print(f"DB: {DB_PATH}")
    print(f"Output: {OUTPUT_PATH}")

    # venues.json 読み込み
    hotel_map, room_map = load_venues()
    print(f"venues.json: {len(hotel_map)} hotel aliases, {len(room_map)} room entries")

    # DB接続
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row

    # 運営マニュアルファイル取得
    cursor = conn.execute("""
        SELECT item_id, name, extracted_at
        FROM files
        WHERE name LIKE '%運営マニュアル%'
        ORDER BY name
    """)
    files = [dict(row) for row in cursor.fetchall()]
    print(f"運営マニュアル総数: {len(files)}")

    # 重複排除
    files = deduplicate_files(files)
    print(f"重複排除後: {len(files)}")

    # 各ファイルを処理
    records = []
    skipped = 0
    for i, f in enumerate(files):
        if (i + 1) % 100 == 0:
            print(f"  処理中: {i + 1}/{len(files)} (抽出: {len(records)})")

        # スライド取得
        cursor = conn.execute("""
            SELECT slide_number, texts
            FROM slides
            WHERE item_id = ?
            ORDER BY slide_number
        """, (f["item_id"],))
        slides = [dict(row) for row in cursor.fetchall()]

        record = process_manual(f["item_id"], f["name"], slides, hotel_map, room_map)
        if record:
            records.append(record)
        else:
            skipped += 1

    conn.close()

    # 日付順ソート（新しい順）
    records.sort(key=lambda r: r.get("date", "0000-00-00"), reverse=True)

    # 出力
    os.makedirs(os.path.dirname(OUTPUT_PATH), exist_ok=True)
    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        json.dump(records, f, ensure_ascii=False, indent=2)

    print(f"\n=== 結果 ===")
    print(f"抽出レコード数: {len(records)}")
    print(f"スキップ（ホテル特定不可）: {skipped}")

    # ホテル別集計
    hotel_counts = {}
    for r in records:
        name = r["hotelName"]
        hotel_counts[name] = hotel_counts.get(name, 0) + 1

    print(f"\nホテル別件数（上位20）:")
    for name, count in sorted(hotel_counts.items(), key=lambda x: -x[1])[:20]:
        matched = "✓" if any(r.get("hotelId") for r in records if r["hotelName"] == name) else "✗"
        print(f"  {matched} {name}: {count}件")

    print(f"\n出力: {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
