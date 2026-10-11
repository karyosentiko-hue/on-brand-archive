#!/usr/bin/env python3
"""Replace retired Fudgie media URLs with validated original Anchor enclosures."""

from __future__ import annotations

import json
import re
import time
import urllib.request
import xml.etree.ElementTree as ET
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from email.utils import format_datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent
FEED_PATH = ROOT / "feed.xml"
RECOVERED_PATH = ROOT / "recovered_enclosures.json"
USER_AGENT = "PodcastFeedVerifier/1.0"
ET.register_namespace("atom", "http://www.w3.org/2005/Atom")
ET.register_namespace("itunes", "http://www.itunes.com/dtds/podcast-1.0.dtd")


def verify_audio(url: str) -> int:
    for attempt in range(4):
        try:
            request = urllib.request.Request(
                url,
                headers={"User-Agent": USER_AGENT, "Range": "bytes=0-0"},
            )
            with urllib.request.urlopen(request, timeout=60) as response:
                if response.status not in (200, 206):
                    raise ValueError(f"HTTP {response.status}")
                content_type = response.headers.get_content_type()
                if not (content_type.startswith("audio/") or content_type == "application/octet-stream"):
                    raise ValueError(f"Unexpected content type {content_type}")
                content_range = response.headers.get("Content-Range", "")
                range_match = re.search(r"/(\d+)$", content_range)
                length = int(range_match.group(1)) if range_match else int(
                    response.headers.get("Content-Length", "0")
                )
                if length <= 0:
                    raise ValueError("Missing media length")
                return length
        except (OSError, ValueError):
            if attempt == 3:
                raise
            time.sleep(2**attempt)
    raise AssertionError("unreachable")


def main() -> None:
    recovered = json.loads(RECOVERED_PATH.read_text(encoding="utf-8"))
    tree = ET.parse(FEED_PATH)
    channel = tree.getroot().find("channel")
    if channel is None:
        raise ValueError("RSS channel not found")
    items = channel.findall("item")
    if len(items) != 98 or len(recovered) != 98:
        raise ValueError(f"Expected 98 items and mappings; got {len(items)} and {len(recovered)}")

    titles = [item.findtext("title", default="") for item in items]
    urls = [recovered[title]["audio_url"] for title in titles]
    with ThreadPoolExecutor(max_workers=6) as executor:
        lengths = list(executor.map(verify_audio, urls))

    description = channel.find("description")
    if description is not None:
        description.text = (
            "Unofficial personal archive feed for On Brand episodes 1–98, hosted by "
            "Al Worth and Lauren B. Audio streams from the podcast's original public "
            "Spotify/Anchor media hosting. This feed is not affiliated with or endorsed "
            "by the podcast's creators."
        )
    last_build = channel.find("lastBuildDate")
    if last_build is not None:
        last_build.text = format_datetime(datetime.now(timezone.utc), usegmt=True)

    for item, title, url, length in zip(items, titles, urls, lengths):
        record = recovered[title]
        link = item.find("link")
        enclosure = item.find("enclosure")
        item_description = item.find("description")
        if link is None or enclosure is None:
            raise ValueError(f"Missing link or enclosure for {title}")
        link.text = record["page_url"]
        enclosure.set("url", url)
        enclosure.set("length", str(length))
        enclosure.set("type", "audio/mpeg")
        if item_description is not None:
            number_match = re.search(r"OB\s*#(\d+)", title, flags=re.IGNORECASE)
            number = number_match.group(1) if number_match else ""
            item_description.text = (
                f"Archived On Brand episode {number}. Audio streams from the original "
                "public Spotify/Anchor media file; the episode link opens a cached "
                "directory page."
            )

    ET.indent(tree, space="  ")
    tree.write(FEED_PATH, encoding="utf-8", xml_declaration=True)
    print(f"Updated and validated {len(items)} episode enclosures.")


if __name__ == "__main__":
    main()
