# Fellowships For Free (F4F)

> **This project is being consolidated onto jonathanlindavis.com/f4f.** The
> fellowship4free.com domain is being retired; the live site, dataset, and all future
> maintenance now happen at [jonathanlindavis.com/f4f](https://jonathanlindavis.com/f4f)
> instead. This repo is kept for historical reference only — see the `Jonathanlindavis
> General` folder for what replaced it.

**Because finding money shouldn't cost you money.**

A free, public, open-data index of graduate and early-career fellowships — a no-paywall
alternative to membership-gated databases.

*A Project by Jonathan Lin Davis.*

- **Live site** (`index.html`): loads `data/fellowships.json`, with search, filtering,
  sort, and one-click CSV/JSON export — all in the browser, no backend.
- **Open data:** `data/fellowships.{json,csv}` — CC-BY-4.0. Code is MIT.

The weekly RSS-import pipeline described in earlier versions of this README
(`scripts/fetch_candidates.py`, `approve_candidates.py`, etc.) has been removed — those
scripts were already broken (stale against a schema change from a prior redesign) and
are superseded by the jonathanlindavis.com/f4f consolidation.

## Sourcing policy (historical)

F4F never scraped websites — it read only published RSS/Atom feeds and APIs, and honored
`robots.txt`. This principle carries forward wherever F4F's data collection continues.

## Data schema (as last deployed here)

Bare JSON array, one object per fellowship:
`id, organization, name, url, opens, deadline, amount, other_benefits, eligibility, area, flags, notes`

## Licenses
Code: MIT (`LICENSE`). Data: CC-BY-4.0 (`LICENSE-DATA`).
