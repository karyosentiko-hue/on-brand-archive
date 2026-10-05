#!/usr/bin/env python3
"""Build the static On Brand archive podcast feed from Fudgie's public API."""

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

API = "https://fight.fudgie.org/search/api/shows/ob/episodes/?limit=100&offset={}"
AUDIO = "https://fight.fudgie.org/static/sites/1/ob/audio/{}.mp3"
EPISODE_PAGE = "https://fight.fudgie.org/search/show/ob/episode/{}"
SITE = "https://karyosentiko-hue.github.io/on-brand-archive/"
FEED = SITE + "feed.xml"
CUTOFF = "2025-02-12"
EXPECTED_EPISODES = 98
USER_AGENT = "on-brand-archive-feed/1.0"

ITUNES = "http://www.itunes.com/dtds/podcast-1.0.dtd"
ATOM = "http://www.w3.org/2005/Atom"
ET.register_namespace("itunes", ITUNES)
ET.register_namespace("atom", ATOM)


def request_json(url: str) -> dict:
    for attempt in range(4):
        try:
            request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
            with urllib.request.urlopen(request, timeout=60) as response:
                return json.load(response)
        except (OSError, ValueError):
            if attempt == 3:
                raise
            time.sleep(2 ** attempt)
    raise AssertionError("unreachable")


def audio_length(episode_id: str) -> int:
    for attempt in range(4):
        try:
            request = urllib.request.Request(
                AUDIO.format(episode_id), method="HEAD", headers={"User-Agent": USER_AGENT}
            )
            with urllib.request.urlopen(request, timeout=60) as response:
                length = int(response.headers.get("Content-Length", "0"))
                if length <= 0:
                    raise ValueError(f"No Content-Length returned for {episode_id}")
                return length
        except (OSError, ValueError):
            if attempt == 3:
                raise
            time.sleep(2 ** attempt)
    raise AssertionError("unreachable")


def episode_number(title: str) -> int:
    match = re.search(r"\bOB\s*#(\d+)\b", title, flags=re.IGNORECASE)
    if not match:
        raise ValueError(f"Could not find an episode number in: {title!r}")
    return int(match.group(1))


def duration_text(seconds: int) -> str:
    hours, remainder = divmod(seconds, 3600)
    minutes, seconds = divmod(remainder, 60)
    return f"{hours}:{minutes:02d}:{seconds:02d}"


def build_feed() -> None:
    episodes = []
    for offset in (0, 100):
        episodes.extend(request_json(API.format(offset))["results"])

    episodes = [episode for episode in episodes if episode["aired_date"] < CUTOFF]
    episodes.sort(key=lambda episode: episode_number(episode["title"]), reverse=True)

    numbers = [episode_number(episode["title"]) for episode in episodes]
    expected_numbers = list(range(EXPECTED_EPISODES, 0, -1))
    if numbers != expected_numbers:
        raise ValueError(f"Expected episodes 1-{EXPECTED_EPISODES}; received {numbers}")

    with ThreadPoolExecutor(max_workers=4) as executor:
        lengths = dict(
            zip(
                (episode["id"] for episode in episodes),
                executor.map(audio_length, (episode["id"] for episode in episodes)),
            )
        )

    rss = ET.Element("rss", {"version": "2.0"})
    channel = ET.SubElement(rss, "channel")
    ET.SubElement(channel, "title").text = "On Brand — Archived Episodes"
    ET.SubElement(channel, "link").text = SITE
    ET.SubElement(channel, "description").text = (
        "Unofficial personal archive feed for On Brand episodes 1–98, hosted by "
        "Al Worth and Lauren B. Audio streams from the public Fudgie archive. "
        "This feed is not affiliated with or endorsed by the podcast's creators."
    )
    ET.SubElement(channel, "language").text = "en-gb"
    ET.SubElement(channel, "lastBuildDate").text = format_datetime(
        datetime.now(timezone.utc), usegmt=True
    )
    ET.SubElement(channel, ET.QName(ATOM, "link"), {
        "href": FEED,
        "rel": "self",
        "type": "application/rss+xml",
    })
    ET.SubElement(channel, ET.QName(ITUNES, "author")).text = "On Brand"
    ET.SubElement(channel, ET.QName(ITUNES, "explicit")).text = "false"
    ET.SubElement(channel, ET.QName(ITUNES, "type")).text = "episodic"

    for episode in episodes:
        number = episode_number(episode["title"])
        episode_url = EPISODE_PAGE.format(episode["id"])
        audio_url = AUDIO.format(episode["id"])
        published = datetime.strptime(episode["aired_date"], "%Y-%m-%d").replace(
            tzinfo=timezone.utc
        )

        item = ET.SubElement(channel, "item")
        ET.SubElement(item, "title").text = episode["title"]
        ET.SubElement(item, "link").text = episode_url
        ET.SubElement(item, "description").text = (
            f"Archived On Brand episode {number}. Audio is streamed from Fudgie; "
            "follow the episode link for the archive page and transcript."
        )
        guid = ET.SubElement(item, "guid", {"isPermaLink": "false"})
        guid.text = f"on-brand-archive:{episode['id']}"
        ET.SubElement(item, "pubDate").text = format_datetime(published, usegmt=True)
        ET.SubElement(item, "enclosure", {
            "url": audio_url,
            "length": str(lengths[episode["id"]]),
            "type": "audio/mpeg",
        })
        ET.SubElement(item, ET.QName(ITUNES, "episode")).text = str(number)
        ET.SubElement(item, ET.QName(ITUNES, "episodeType")).text = "full"
        ET.SubElement(item, ET.QName(ITUNES, "duration")).text = duration_text(
            int(episode["duration"])
        )
        ET.SubElement(item, ET.QName(ITUNES, "explicit")).text = "false"

    tree = ET.ElementTree(rss)
    ET.indent(tree, space="  ")
    tree.write(Path(__file__).with_name("feed.xml"), encoding="utf-8", xml_declaration=True)
    print(f"Created feed.xml with {len(episodes)} episodes (OB #1–#{EXPECTED_EPISODES}).")


if __name__ == "__main__":
    build_feed()
