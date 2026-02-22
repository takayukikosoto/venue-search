"""CLI エントリポイント: seed / crawl / status / merge / export"""

from __future__ import annotations

import argparse
import asyncio
import json
import logging
import sys

from .config import CrawlConfig, config as default_config
from .db import CrawlDB


def setup_logging(verbose: bool = False):
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%H:%M:%S",
    )


def cmd_seed(args, cfg: CrawlConfig):
    """venues.json → crawl_urls シード投入"""
    from .seed import seed_from_venues

    db = CrawlDB(cfg)
    added = seed_from_venues(cfg, db)
    print(f"Seeded {added} URLs into crawl_urls")
    db.close()


def cmd_crawl(args, cfg: CrawlConfig):
    """クロール実行"""
    from .orchestrator import Orchestrator

    orch = Orchestrator(cfg)
    asyncio.run(
        orch.run(
            hotel_id=args.hotel_id,
            max_urls=args.max_urls,
        )
    )


def cmd_status(args, cfg: CrawlConfig):
    """クロール状態表示"""
    db = CrawlDB(cfg)
    db.init_db()

    print("=== URL Status ===")
    counts = db.get_status_counts()
    total = sum(counts.values())
    for status, cnt in sorted(counts.items()):
        pct = cnt / total * 100 if total else 0
        print(f"  {status:10s}: {cnt:5d} ({pct:.1f}%)")
    print(f"  {'total':10s}: {total:5d}")

    print("\n=== Hotel Summary ===")
    summary = db.get_hotel_summary()
    for row in summary:
        print(
            f"  {row['hotel_id']:40s}  "
            f"done={row['done']:3d}  "
            f"pending={row['pending']:3d}  "
            f"error={row['errors']:3d}  "
            f"total={row['total_urls']:3d}"
        )

    print("\n=== Extracted Data ===")
    data_summary = db.get_extracted_data_summary()
    for field, cnt in data_summary.items():
        print(f"  {field:25s}: {cnt:5d}")

    db.close()


def cmd_merge(args, cfg: CrawlConfig):
    """クロール結果を venues.json にマージ"""
    from .merge_crawled import merge, format_diff

    db = CrawlDB(cfg)
    diff = merge(
        cfg=cfg,
        db=db,
        confidence_threshold=args.threshold,
        dry_run=args.dry_run,
    )

    if diff:
        print(format_diff(diff))
        if args.dry_run:
            print(f"\n[DRY RUN] {len(diff)} hotels would be modified")
        else:
            print(f"\n{len(diff)} hotels updated in venues.json")
    else:
        print("No changes to merge")

    db.close()


def cmd_export(args, cfg: CrawlConfig):
    """extracted_data を JSON でエクスポート"""
    db = CrawlDB(cfg)
    db.init_db()

    conn = db.connect()
    rows = conn.execute(
        "SELECT * FROM extracted_data ORDER BY hotel_id, room_name, field_name"
    ).fetchall()

    data = [dict(r) for r in rows]

    output = args.output or "-"
    if output == "-":
        json.dump(data, sys.stdout, ensure_ascii=False, indent=2)
        print()
    else:
        with open(output, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
            f.write("\n")
        print(f"Exported {len(data)} records to {output}")

    db.close()


def main():
    parser = argparse.ArgumentParser(
        description="Venue Search Crawler",
        prog="python -m scripts.crawler.run",
    )
    parser.add_argument(
        "-v", "--verbose", action="store_true", help="詳細ログ出力"
    )
    parser.add_argument(
        "--db", type=str, default=None, help="DBファイルパス（デフォルト: crawl.db）"
    )

    sub = parser.add_subparsers(dest="command", required=True)

    # seed
    sub.add_parser("seed", help="venues.json → crawl_urls シード投入")

    # crawl
    p_crawl = sub.add_parser("crawl", help="クロール実行")
    p_crawl.add_argument(
        "--hotel-id", type=str, default=None, help="特定ホテルのみクロール"
    )
    p_crawl.add_argument(
        "--max-urls", type=int, default=None, help="最大処理URL数"
    )

    # status
    sub.add_parser("status", help="クロール状態表示")

    # merge
    p_merge = sub.add_parser("merge", help="クロール結果 → venues.json マージ")
    p_merge.add_argument(
        "--dry-run",
        action="store_true",
        help="venues.json を更新せずdiffだけ表示",
    )
    p_merge.add_argument(
        "--threshold",
        type=float,
        default=0.5,
        help="最低 confidence 閾値 (default: 0.5)",
    )

    # export
    p_export = sub.add_parser("export", help="extracted_data をJSON出力")
    p_export.add_argument(
        "-o", "--output", type=str, default=None, help="出力ファイル（- で stdout）"
    )

    args = parser.parse_args()
    setup_logging(args.verbose)

    cfg = CrawlConfig()
    if args.db:
        from pathlib import Path
        cfg.db_path = Path(args.db)

    cmds = {
        "seed": cmd_seed,
        "crawl": cmd_crawl,
        "status": cmd_status,
        "merge": cmd_merge,
        "export": cmd_export,
    }

    cmds[args.command](args, cfg)


if __name__ == "__main__":
    main()
