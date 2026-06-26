#!/usr/bin/env python3
"""
fetch_candidates.py — F4F weekly candidate puller (feeds/APIs only; no scraping).

Pipeline per weekly run:
  1. Read RSS/Atom feeds listed in scripts/sources.json (feeds the project is
     permitted to read; robots/ToS respected — we only consume published feeds).
  2. Keyword-filter items to fellowship-like opportunities.
  3. De-duplicate against the live dataset (data/fellowships.json) and the
     existing pending queue.
  4. Expiry sweep: drop PENDING candidates whose hard deadline has already passed.
     (Approved/live fellowships are NEVER auto-dropped — recurring ones recur.)
  5. Rank remaining + new candidates by MOST TIME-SENSITIVE (soonest deadline).
  6. Surface up to REVIEW_TARGET (25) for human review. From those you approve
     up to APPROVE_CAP (10) via approve_candidates.py.

Output: pending/candidates.json  (a review queue; nothing publishes here)
A companion step (notify_issue.py) posts the weekly GitHub Issue.
"""
import json, re, sys, hashlib, datetime, urllib.request, urllib.error
from pathlib import Path
from xml.etree import ElementTree as ET

ROOT = Path(__file__).resolve().parent.parent
LIVE = ROOT / "data" / "fellowships.json"
PENDING = ROOT / "pending" / "candidates.json"
SOURCES = ROOT / "scripts" / "sources.json"

REVIEW_TARGET = 25     # surface up to this many for review each cycle
APPROVE_CAP   = 10     # you approve up to this many (enforced in approve script)
UA = "F4F-Bot/1.0 (Fellowships For Free; weekly fellowship index; contact in repo)"
KEYWORDS = re.compile(r"\b(fellow|fellowship|grant|scholarship|residency|stipend|funding|call for applications|doctoral|postdoctoral|dissertation)\b", re.I)

MONTHS = {m:i for i,m in enumerate(
    ["jan","feb","mar","apr","may","jun","jul","aug","sep","oct","nov","dec"], start=1)}

def norm(s): return re.sub(r"\s+"," ",(s or "")).strip()

def parse_monthday(s):
    """'Nov 1' / 'Nov 1 (assumed...)' -> (month, day) or None. Rolling/blank -> None."""
    if not s: return None
    s = s.lower()
    if "rolling" in s or "annual" in s: return None
    m = re.search(r"\b(jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[a-z]*\.?\s+(\d{1,2})", s)
    if not m: return None
    return (MONTHS[m.group(1)], int(m.group(2)))

def days_until(md, today):
    """Days from today to the next occurrence of (month,day). Always returns >=0
    by rolling to next year if the date this year already passed."""
    if not md: return 10**6  # no concrete deadline -> least time-sensitive
    mo, day = md
    yr = today.year
    try:
        target = datetime.date(yr, mo, min(day, 28 if mo==2 else day))
    except ValueError:
        target = datetime.date(yr, mo, 28)
    if target < today:
        try: target = datetime.date(yr+1, mo, day)
        except ValueError: target = datetime.date(yr+1, mo, 28)
    return (target - today).days

def passed_last_week(md, today):
    """True if (month,day) fell within the 7 days before today (this year)."""
    if not md: return False
    mo, day = md
    try: d = datetime.date(today.year, mo, day)
    except ValueError: return False
    delta = (today - d).days
    return 0 <= delta <= 7

def fetch(url, timeout=25):
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read()

def parse_feed(xml_bytes, source_name):
    out=[]
    try: root=ET.fromstring(xml_bytes)
    except ET.ParseError: return out
    items=root.findall(".//item"); is_atom=False
    if not items:
        ns={"a":"http://www.w3.org/2005/Atom"}; items=root.findall(".//a:entry",ns); is_atom=True
    for it in items:
        if is_atom:
            ns={"a":"http://www.w3.org/2005/Atom"}
            title=norm(it.findtext("a:title",default="",namespaces=ns))
            le=it.find("a:link",ns); link=le.get("href") if le is not None else ""
            summary=norm(it.findtext("a:summary",default="",namespaces=ns) or it.findtext("a:content",default="",namespaces=ns))
        else:
            title=norm(it.findtext("title",default="")); link=norm(it.findtext("link",default="")); summary=norm(it.findtext("description",default=""))
        if not title: continue
        if not KEYWORDS.search(f"{title} {summary}"): continue
        out.append({"candidate_title":title,"url":link,"raw_summary":summary[:600],"source":source_name})
    return out

def load_json(p,default): return json.loads(p.read_text()) if p.exists() else default

def main():
    today = datetime.date.today()
    sources = load_json(SOURCES, {"feeds":[]})
    live = load_json(LIVE, {"fellowships":[]})
    live_urls={norm(f.get("url","")).lower() for f in live["fellowships"] if f.get("url")}
    live_titles={norm(f.get("fellowship","")).lower() for f in live["fellowships"]}

    pend = load_json(PENDING, {"candidates":[]})

    # --- Expiry sweep: drop PENDING candidates whose deadline passed last week ---
    kept=[]
    dropped_expired=0
    for c in pend["candidates"]:
        md = parse_monthday(c.get("record",{}).get("deadline",""))
        if c.get("status")=="pending" and passed_last_week(md, today):
            dropped_expired+=1; continue
        kept.append(c)
    pend["candidates"]=kept
    seen={(c.get("url","").lower(), c.get("candidate_title","").lower()) for c in pend["candidates"]}

    # --- Pull new candidates from feeds ---
    found=[]
    for feed in sources.get("feeds",[]):
        url,name=feed.get("url"),feed.get("name","feed")
        if not url: continue
        try: data=fetch(url)
        except Exception as e:
            print(f"[warn] {name}: {e}", file=sys.stderr); continue
        for cand in parse_feed(data,name):
            u=cand["url"].lower(); t=cand["candidate_title"].lower()
            if u and u in live_urls: continue
            if t in live_titles: continue
            if (u,t) in seen: continue
            cand["id"]="cand-"+hashlib.sha1((u+t).encode()).hexdigest()[:10]
            cand["found"]=today.isoformat(); cand["status"]="pending"
            cand["record"]={"organization":"","fellowship":cand["candidate_title"],"url":cand["url"],
                "funded":"Verify","duration_months":"","type":"","flag":"","area":"",
                "description":cand["raw_summary"][:300],"opens":"","deadline":"","next_cohort":"",
                "contact":"","terms":"","notes":f"Auto-found via {name}; verify all fields before approving."}
            found.append(cand); seen.add((u,t))

    pend["candidates"].extend(found)

    # --- Rank by most time-sensitive; cap review queue at REVIEW_TARGET ---
    def sort_key(c):
        md=parse_monthday(c.get("record",{}).get("deadline",""))
        return days_until(md, today)
    pend["candidates"].sort(key=sort_key)
    if len(pend["candidates"])>REVIEW_TARGET:
        overflow=pend["candidates"][REVIEW_TARGET:]
        pend["candidates"]=pend["candidates"][:REVIEW_TARGET]
        pend["overflow_count"]=len(overflow)
    else:
        pend["overflow_count"]=0

    pend["last_run"]=datetime.datetime.now(datetime.UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
    pend["review_target"]=REVIEW_TARGET; pend["approve_cap"]=APPROVE_CAP
    pend["pending_count"]=sum(1 for c in pend["candidates"] if c["status"]=="pending")
    pend["new_this_run"]=len(found); pend["expired_dropped"]=dropped_expired
    PENDING.parent.mkdir(exist_ok=True)
    PENDING.write_text(json.dumps(pend,indent=2))
    print(f"New: {len(found)} | Expired dropped: {dropped_expired} | "
          f"In review queue: {pend['pending_count']} (target {REVIEW_TARGET}) | "
          f"Overflow held: {pend['overflow_count']} | Approve up to {APPROVE_CAP}")

if __name__=="__main__":
    main()
