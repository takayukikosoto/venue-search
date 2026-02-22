"""venues.json から venuePageUrl を読み取り crawl_urls にシード投入"""

from __future__ import annotations

import json
import logging
from urllib.parse import urlparse

from .config import CrawlConfig, config as default_config
from .db import CrawlDB
from .models import CrawlStatus, CrawlUrl, UrlType

logger = logging.getLogger(__name__)


def seed_from_venues(
    cfg: CrawlConfig | None = None,
    db: CrawlDB | None = None,
) -> int:
    """venues.json の venuePageUrl → crawl_urls にシード投入。投入件数を返す。"""
    cfg = cfg or default_config
    db = db or CrawlDB(cfg)
    db.init_db()

    with open(cfg.venues_json, encoding="utf-8") as f:
        venues = json.load(f)

    urls_to_add: list[CrawlUrl] = []

    for venue in venues:
        hotel_id = venue.get("id", "")
        practical = venue.get("practicalInfo", {})
        venue_page_url = practical.get("venuePageUrl") or venue.get("venuePageUrl")
        floor_plan_url = practical.get("floorPlanUrl") or venue.get("floorPlanUrl")

        if venue_page_url:
            domain = urlparse(venue_page_url).netloc
            urls_to_add.append(
                CrawlUrl(
                    url=venue_page_url,
                    hotel_id=hotel_id,
                    domain=domain,
                    depth=0,
                    url_type=cfg.classify_url_type(venue_page_url),
                    status=CrawlStatus.PENDING,
                )
            )

        if floor_plan_url:
            domain = urlparse(floor_plan_url).netloc
            urls_to_add.append(
                CrawlUrl(
                    url=floor_plan_url,
                    hotel_id=hotel_id,
                    domain=domain,
                    depth=0,
                    url_type=cfg.classify_url_type(floor_plan_url),
                    status=CrawlStatus.PENDING,
                )
            )

    added = db.add_urls(urls_to_add)
    logger.info("Seeded %d URLs (from %d candidates)", added, len(urls_to_add))
    return added
