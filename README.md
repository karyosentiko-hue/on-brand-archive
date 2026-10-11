# On Brand — Archived Episodes

An unofficial personal podcast feed for the original run of *On Brand*: episodes
1–98, ending with “RFK Jr.'s Confirmation Hearing” on 6 February 2025.

The repository contains only the RSS metadata. Episode audio streams from the
podcast's original public Spotify/Anchor media hosting.

Feed URL: <https://karyosentiko-hue.github.io/on-brand-archive/feed.xml>

## Regenerating the feed

Run:

```sh
python3 generate_feed.py
```

The generator uses the preserved `recovered_enclosures.json` map, verifies all
98 media URLs with byte-range requests, checks each MP3's byte length, and
rewrites `feed.xml`. `recover_enclosures.py` documents how the enclosure map was
recovered from a public podcast-directory cache after Fudgie retired the files.

`generate_feed_from_fudgie_legacy.py` is retained for provenance, but its source
API no longer contains the original run.

This is an unofficial personal archive and is not affiliated with or endorsed
by the podcast's creators.
