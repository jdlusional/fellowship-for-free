# Fellowships For Free (F4F)

**Because finding money shouldn't cost you money.**

A free, public, open-data index of graduate and early-career fellowships — a no-paywall
alternative to membership-gated databases. The whole dataset is downloadable as CSV or
JSON, and the code and data live in public.

*A Project by Jonathan Lin Davis.*

- **Live site** (`index.html`): loads `data/fellowships.json`, with search, filtering,
  sort, and one-click CSV/JSON export — all in the browser, no backend.
- **Weekly refresh:** a GitHub Action reads permitted RSS/Atom feeds, queues up to 25
  candidates ranked most-time-sensitive, sweeps expired pending items, and opens a
  GitHub Issue for review. You approve up to 10 per week. Nothing publishes automatically.
- **Open data:** `data/fellowships.{json,csv}` — CC-BY-4.0. Code is MIT.

Seeded with 93 fellowships across AI policy, public policy, nonprofit governance,
education, data analysis, and more.

---

## Sourcing policy (important)

F4F **does not scrape** websites. It reads only **published RSS/Atom feeds and APIs** —
content sites publish specifically for machine consumption — and it **honors
`robots.txt`**. We never read paywalled databases (e.g. a membership database), only
public feeds. This keeps F4F's data clean, its uptime stable, and its "open and honest"
positioning intact. To add a high-value source that has no feed, request permission or
an API key from that organization rather than scraping it.

---

## How the weekly pipeline works

```
Monday cron
  └─ scripts/fetch_candidates.py
       • read feeds in scripts/sources.json  (feeds/APIs only, robots respected)
       • keyword-filter to fellowship-like items, de-dupe against live + queue
       • EXPIRY SWEEP: drop PENDING candidates whose hard deadline passed last week
         (approved/live fellowships are NEVER auto-dropped — recurring ones recur)
       • RANK most-time-sensitive (soonest deadline first); keep up to 25 for review
  └─ commit pending/candidates.json
  └─ scripts/notify_issue.py  ->  weekly GitHub Issue listing the 25

You review the Issue / edit pending/candidates.json:
  • fill each record's fields, set "status":"approved" (or "rejected")
  └─ scripts/approve_candidates.py
       • promote up to 10 most-time-sensitive approved -> data/fellowships.json + .csv
       • leftovers stay pending for next week
  └─ push to main -> Pages redeploys the site
```

**The numbers you set:** review up to **25** candidates weekly, approve up to **10**.
Change `REVIEW_TARGET` / `APPROVE_CAP` at the top of `scripts/fetch_candidates.py` and
`approve_candidates.py`.

---

## Deploy (one time, ~10 minutes)

1. Create a **public GitHub repo** and upload these files (keep the structure):
   ```
   index.html
   assets/            (logo + favicon)
   data/fellowships.json   data/fellowships.csv
   scripts/fetch_candidates.py  scripts/approve_candidates.py
   scripts/notify_issue.py      scripts/discover_feeds.py  scripts/sources.json
   pending/candidates.json
   .github/workflows/weekly-import.yml  .github/workflows/deploy-pages.yml
   README.md  LICENSE  LICENSE-DATA
   ```
2. **Pages:** Settings → Pages → Source → **GitHub Actions**.
3. **Actions permissions:** Settings → Actions → General → Workflow permissions →
   **Read and write**. (The weekly job needs this to commit the queue and open Issues.)
4. **Create a label** named `review-queue` (Issues → Labels) so the weekly Issue is
   tagged. (Or remove `--label "review-queue"` from `weekly-import.yml`.)
5. Edit `index.html`: set the `★ Source` link (`id="repo-link"`) to your repo URL.
6. Push to `main`. Site goes live at `https://<you>.github.io/<repo>/`.

> GitHub disables scheduled workflows after 60 days of repo inactivity; any commit
> re-arms them. Cron times are UTC.

---

## Expanding sources

`scripts/sources.json` holds the active `feeds`. To grow coverage from the
organizations already in your dataset:

```bash
python scripts/discover_feeds.py            # checks each org site for a real feed
```

It writes confirmed feeds under `"discovered"` (honoring robots.txt). Review them and
move good ones into the `"feeds"` array to activate. You can also pass a text file of
extra site URLs: `python scripts/discover_feeds.py extra_sites.txt`.

---

## Adding fellowships manually

Edit `data/fellowships.json` (add an object to `fellowships`), then run
`python scripts/approve_candidates.py` to rebuild the CSV, or edit both data files and
push. Dates are month/day only (no year); use `(assumed from last cycle)` in `notes`
where a next-cycle date is projected.

## Data schema

`id, organization, fellowship, url, area, type, funded, duration_months, opens,
deadline, next_cohort, flag, description, terms, contact, notes, added, source`

## Email digest (later)

The subscribe form is inert until wired. To enable **Mailchimp**: create an audience +
embedded form, copy its `action` URL into the `<form id="subform">` in `index.html`,
set `method="post"`, rename the input to `name="EMAIL"`, and remove
`onsubmit="return false;"`. A future enhancement can emit a `new-this-week` feed for a
Mailchimp RSS campaign.

## Licenses
Code: MIT (`LICENSE`). Data: CC-BY-4.0 (`LICENSE-DATA`).
