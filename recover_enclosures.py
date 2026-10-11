#!/usr/bin/env python3
"""Recover deleted On Brand enclosure URLs from podcast.app's public cache."""

from __future__ import annotations

import html
import json
import re
import time
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

BASE = "https://podcast.app"
SHOW = BASE + "/on-brand-p6022094?page={}"
USER_AGENT = "Mozilla/5.0 (compatible; on-brand-archive-recovery/1.0)"
ROOT = Path(__file__).resolve().parent
TITLE_OVERRIDES = {
    "OB #91 - Steven Crowder w/Louder Than Crowder": "/steven-crowder-wlouder-than-crowder-e367553856",
    "OB #76 - Yes, Matt Walsh Is In Fact Racist. w/Where There's Woke": "/yes-matt-walsh-is-in-fact-racist-wwhere-theres-woke-e361397334",
    "OB #62 - Alex Jones w/Knowledge Fight": "/alex-jones-wknowledge-fight-e355661175",
    "OB #45 - 'Brandemic' w/Eli Bosnick & Jordan Holmes": "/brandemic-weli-bosnick-jordan-holmes-e347811949",
    "OB #16 - Russell Brand Primer Part 1: The Man": "/ob-16-russell-brand-primer-the-man-e338311322",
}


def fetch(url: str) -> str:
    for attempt in range(4):
        try:
            request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
            with urllib.request.urlopen(request, timeout=45) as response:
                return response.read().decode("utf-8", errors="replace")
        except OSError:
            if attempt == 3:
                raise
            time.sleep(2**attempt)
    raise AssertionError("unreachable")


def normalized_title(value: str) -> str:
    value = html.unescape(value).replace("’", "'").replace("–", "-").replace("—", "-")
    return re.sub(r"[^a-z0-9]+", " ", value.lower()).strip()


def episode_links() -> list[str]:
    links: set[str] = set()
    for page in range(1, 15):
        body = fetch(SHOW.format(page))
        links.update(
            BASE + path
            for path in re.findall(r'href="(/[^"]+-e\d+)"', body)
            if not path.startswith("/on-brand-p")
        )
    return sorted(links)


def episode_record(url: str) -> dict[str, str] | None:
    body = fetch(url)
    audio_match = re.search(r'"audio_url":"([^"]+)"', body)
    title_match = re.search(r'<h1[^>]*>(.*?)</h1>', body, flags=re.DOTALL)
    if not audio_match or not title_match:
        return None
    title = re.sub(r"<[^>]+>", "", title_match.group(1))
    return {
        "title": html.unescape(title).strip(),
        "page_url": url,
        "audio_url": html.unescape(audio_match.group(1)),
    }


def main() -> None:
    links = episode_links()
    records: list[dict[str, str]] = []
    with ThreadPoolExecutor(max_workers=6) as executor:
        futures = {executor.submit(episode_record, url): url for url in links}
        for future in as_completed(futures):
            record = future.result()
            if record:
                records.append(record)

    by_title = {normalized_title(record["title"]): record for record in records}
    by_path = {urllib.parse.urlparse(record["page_url"]).path: record for record in records}
    feed_root = ET.parse(ROOT / "feed.xml").getroot()
    feed_items = feed_root.findall("./channel/item")
    recovered: dict[str, dict[str, str]] = {}
    missing: list[str] = []
    for item in feed_items:
        title = item.findtext("title", default="")
        record = by_title.get(normalized_title(title))
        if not record and title in TITLE_OVERRIDES:
            record = by_path.get(TITLE_OVERRIDES[title])
        if record:
            recovered[title] = record
        else:
            missing.append(title)

    (ROOT / "recovered_enclosures.json").write_text(
        json.dumps(recovered, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    print(f"Directory links: {len(links)}")
    print(f"Audio records: {len(records)}")
    print(f"Feed matches: {len(recovered)}/{len(feed_items)}")
    if missing:
        print("Missing titles:")
        for title in missing:
            print(f"  {title}")


if __name__ == "__main__":
    main()
