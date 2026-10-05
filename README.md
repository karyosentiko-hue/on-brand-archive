# On Brand — Archived Episodes

An unofficial personal podcast feed for the original run of *On Brand*: episodes
1–98, ending with “RFK Jr.'s Confirmation Hearing” on 6 February 2025.

The repository contains only the RSS metadata. Episode audio streams directly
from the public Fudgie archive.

Feed URL: <https://karyosentiko-hue.github.io/on-brand-archive/feed.xml>

## Regenerating the feed

Run:

```sh
python3 generate_feed.py
```

The generator reads Fudgie's public API, keeps records dated before 12 February
2025, verifies that episodes 1 through 98 are present, checks each MP3's byte
length, and rewrites `feed.xml`.

This is an unofficial personal archive and is not affiliated with or endorsed
by the podcast's creators.
