#!/usr/bin/env python3
"""
discover_feeds.py — find which organizations publish a readable RSS/Atom feed.

Why this exists: an organization in our dataset is only usable as a *source* if it
publishes a machine-readable feed. We do NOT scrape. This helper takes a list of
candidate site URLs (seeded from the organizations already in data/fellowships.json
plus any you add), checks each for a feed at the usual locations, honors robots.txt,
and writes the confirmed feeds into scripts/sources.json under "discovered".

Run locally or in CI:  python scripts/discover_feeds.py
Then review scripts/sources.json and move good "discovered" feeds into "feeds".
"""
import json, re, sys, urllib.request, urllib.error, urllib.robotparser as rp
from pathlib import Path
from urllib.parse import urlparse, urljoin
from xml.etree import ElementTree as ET

ROOT=Path(__file__).resolve().parent.parent
LIVE=ROOT/"data"/"fellowships.json"; SOURCES=ROOT/"scripts"/"sources.json"
UA="F4F-Bot/1.0 (feed discovery; respects robots.txt)"
COMMON_PATHS=["/feed","/feed/","/rss","/rss.xml","/atom.xml","/feed.xml","/blog/feed","/news/feed","/index.xml"]

def host_root(u):
    try:
        p=urlparse(u if u.startswith("http") else "https://"+u)
        if not p.netloc: return None
        return f"{p.scheme}://{p.netloc}"
    except Exception: return None

def robots_ok(root, path):
    try:
        r=rp.RobotFileParser(); r.set_url(urljoin(root,"/robots.txt")); r.read()
        return r.can_fetch(UA, urljoin(root,path))
    except Exception: return True  # if robots can't be read, default permit but be polite

def looks_like_feed(b):
    try:
        root=ET.fromstring(b)
        tag=root.tag.lower()
        return ("rss" in tag) or ("feed" in tag) or (root.find(".//item") is not None)
    except Exception: return False

def try_url(u, timeout=15):
    try:
        req=urllib.request.Request(u, headers={"User-Agent":UA})
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.read()
    except Exception: return None

def discover(root):
    # 1) try common feed paths
    for path in COMMON_PATHS:
        if not robots_ok(root, path): continue
        b=try_url(urljoin(root,path))
        if b and looks_like_feed(b): return urljoin(root,path)
    # 2) parse homepage <link rel=alternate type=rss/atom>
    if robots_ok(root,"/"):
        b=try_url(root)
        if b:
            html=b.decode("utf-8","ignore")
            for m in re.finditer(r'<link[^>]+type=["\'](application/(?:rss|atom)\+xml)["\'][^>]*>', html, re.I):
                href=re.search(r'href=["\']([^"\']+)["\']', m.group(0))
                if href:
                    feed=urljoin(root, href.group(1))
                    fb=try_url(feed)
                    if fb and looks_like_feed(fb): return feed
    return None

def main():
    live=json.loads(LIVE.read_text())
    roots=[]
    for f in live["fellowships"]:
        r=host_root(f.get("url",""))
        if r and r not in roots: roots.append(r)
    extra=[]
    if len(sys.argv)>1:  # allow: python discover_feeds.py extra_sites.txt
        extra=[l.strip() for l in Path(sys.argv[1]).read_text().splitlines() if l.strip()]
    for e in extra:
        r=host_root(e)
        if r and r not in roots: roots.append(r)

    sources=json.loads(SOURCES.read_text()) if SOURCES.exists() else {"feeds":[],"discovered":[]}
    known={f["url"] for f in sources.get("feeds",[])} | {d["url"] for d in sources.get("discovered",[])}
    new=[]
    print(f"Checking {len(roots)} organization sites for feeds…")
    for root in roots:
        feed=discover(root)
        if feed and feed not in known:
            new.append({"name":urlparse(root).netloc, "url":feed})
            known.add(feed); print(f"  FOUND  {feed}")
    sources.setdefault("discovered",[]).extend(new)
    SOURCES.write_text(json.dumps(sources,indent=2))
    print(f"\n{len(new)} new feeds discovered and written to scripts/sources.json under 'discovered'.")
    print("Review them, then move good ones into the 'feeds' array to activate.")

if __name__=="__main__": main()
