#!/usr/bin/env python3
"""
notify_issue.py — emit a Markdown body for the weekly review GitHub Issue.
Prints to stdout; the workflow pipes it into `gh issue create`.
"""
import json, datetime
from pathlib import Path
ROOT=Path(__file__).resolve().parent.parent
pend=json.loads((ROOT/"pending"/"candidates.json").read_text())
cands=[c for c in pend.get("candidates",[]) if c.get("status")=="pending"]
today=datetime.date.today().isoformat()
print(f"# F4F weekly review — {today}\n")
print(f"**{len(cands)}** candidates in the queue (target {pend.get('review_target',25)}). "
      f"New this run: **{pend.get('new_this_run',0)}**. "
      f"Expired dropped: {pend.get('expired_dropped',0)}. "
      f"Overflow held: {pend.get('overflow_count',0)}.\n")
print(f"Approve up to **{pend.get('approve_cap',10)}** by editing `pending/candidates.json` "
      f"(set `\"status\": \"approved\"`), then run `python scripts/approve_candidates.py`.\n")
print("| # | Candidate | Source | Deadline | Link |")
print("|---|-----------|--------|----------|------|")
for i,c in enumerate(cands,1):
    r=c.get("record",{})
    dl=r.get("deadline","") or "—"
    title=(r.get("fellowship") or c.get("candidate_title",""))[:80].replace("|","/")
    print(f"| {i} | {title} | {c.get('source','')} | {dl} | {c.get('url','')} |")
print("\n_Ranked most time-sensitive first. Nothing publishes until you approve._")
