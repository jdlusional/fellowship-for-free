#!/usr/bin/env python3
"""
approve_candidates.py — promote reviewed candidates into the live F4F dataset.

Enforces the APPROVE_CAP (10) per run.

Maintainer workflow:
  1. Open pending/candidates.json (up to 25 candidates, ranked most-time-sensitive).
  2. For each one to publish: fill in the record fields (organization, area, type,
     deadline as 'Mon D', etc.) and set "status": "approved".
     Mark junk "rejected".
  3. Run this script. Up to 10 approved candidates move into data/fellowships.json,
     the CSV is rebuilt, and resolved items leave the queue.
     If you approve more than 10, it promotes the 10 most time-sensitive and tells you.
"""
import json, datetime, re, csv
from pathlib import Path

ROOT=Path(__file__).resolve().parent.parent
LIVE=ROOT/"data"/"fellowships.json"; CSV=ROOT/"data"/"fellowships.csv"; PENDING=ROOT/"pending"/"candidates.json"
APPROVE_CAP=10
FIELDS=["id","organization","fellowship","url","area","type","funded","duration_months",
        "opens","deadline","next_cohort","flag","description","terms","contact","notes","added","source"]
MONTHS={m:i for i,m in enumerate(["jan","feb","mar","apr","may","jun","jul","aug","sep","oct","nov","dec"],start=1)}

def parse_md(s):
    if not s: return (99,99)
    m=re.search(r"\b(jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[a-z]*\.?\s+(\d{1,2})",s.lower())
    return (MONTHS[m.group(1)],int(m.group(2))) if m else (99,99)
def slugid(rec,n):
    base=(rec.get("organization","")[:20]+"-"+rec.get("fellowship","")[:30]).lower()
    return "-".join(filter(None,re.sub(r"\W","-",base).split("-")))+f"-{n:03d}"

def main():
    live=json.loads(LIVE.read_text()); pend=json.loads(PENDING.read_text()) if PENDING.exists() else {"candidates":[]}
    approved=[c for c in pend["candidates"] if c.get("status")=="approved"]
    # rank approved by soonest deadline, enforce cap
    approved.sort(key=lambda c: parse_md(c.get("record",{}).get("deadline","")))
    over=[]
    if len(approved)>APPROVE_CAP:
        over=approved[APPROVE_CAP:]; approved=approved[:APPROVE_CAP]
        print(f"[cap] {len(over)+APPROVE_CAP} approved; promoting the {APPROVE_CAP} most time-sensitive. "
              f"{len(over)} will stay pending for next week.")

    today=datetime.date.today().isoformat(); n=len(live["fellowships"]); promoted=0
    promoted_ids=set()
    for c in approved:
        rec=c.get("record",{})
        if not rec.get("organization") or not rec.get("fellowship"):
            print(f"[skip] {c['id']} approved but missing org/name; fill it in."); continue
        rec["id"]=slugid(rec,n); n+=1; rec["added"]=today; rec["source"]="reviewed"
        live["fellowships"].append(rec); promoted+=1; promoted_ids.add(c["id"])

    # keep: still-pending + capped-overflow approved (revert those to pending). drop: rejected + promoted.
    new_q=[]
    for c in pend["candidates"]:
        if c["id"] in promoted_ids: continue
        if c.get("status")=="rejected": continue
        if c in over: c["status"]="pending"
        new_q.append(c)
    pend["candidates"]=new_q; pend["pending_count"]=sum(1 for c in new_q if c["status"]=="pending")

    live["count"]=len(live["fellowships"])
    live["generated"]=datetime.datetime.now(datetime.UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
    LIVE.write_text(json.dumps(live,indent=2)); PENDING.write_text(json.dumps(pend,indent=2))
    with CSV.open("w",newline="") as f:
        w=csv.DictWriter(f,fieldnames=FIELDS); w.writeheader()
        for r in live["fellowships"]: w.writerow({k:r.get(k,"") for k in FIELDS})
    print(f"Promoted {promoted}. Live total: {live['count']}. Remaining pending: {pend['pending_count']}")

if __name__=="__main__": main()
