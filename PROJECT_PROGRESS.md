# COMP4010 Project 2 Progress Tracker

## Project

- Project name: `Mekong FloodLens`
- Course: `COMP4010`
- Team: `Group 3`
- Repository: `COMP4010-Project-2`
- Last updated: `2026-05-18`

## Current Goal

Build a rainfall-focused MVP for the Vietnamese Mekong Delta using cleaned province-level rainfall data, then extend it into an interactive dashboard.

## Overall Status

| Area | Status | Notes |
|---|---|---|
| Repository setup | Done | Base repo structure is in place |
| Raw data collection | Done | Rainfall CSVs and boundary GeoJSON are present |
| Rainfall cleaning | Done | `scripts/02_clean_rainfall.py` generates processed output |
| Processed dataset | Done | `data/processed/province_month_rainfall.csv` exists |
| Earth Engine test | Done | `test.py` exports `precipitation_map.html` |
| Dashboard app | Not started | `mvp.py` is currently empty |
| Dependency management | Not started | No `requirements.txt` yet |
| Documentation | In progress | `README.md` updated to reflect current repo state |

## Milestones

| Milestone | Status | Target | Notes |
|---|---|---|---|
| Confirm project scope | Done | May 2026 | Rainfall-first MVP confirmed |
| Collect and store raw rainfall data | Done | May 2026 | 2020-2024 and 2000-2024 files available |
| Clean rainfall data | Done | May 2026 | Anomaly and z-score fields generated |
| Validate Earth Engine access | Done | May 2026 | Basic CHIRPS test completed |
| Build first dashboard prototype | Not started | TBD | Start from `mvp.py` or new app entry file |
| Add install instructions and dependencies | Not started | TBD | Create `requirements.txt` |
| Add charts and interactions | Not started | TBD | Use processed rainfall table |
| Final polish and submission assets | Not started | TBD | README, slides, report, demo |

## Completed Work

### Data

- Added Mekong Delta province boundary file:
  - `data/raw/mekong_provinces_boundary.geojson`
- Added raw monthly rainfall datasets:
  - `data/raw/mekong_province_month_rainfall_2020_2024.csv`
  - `data/raw/mekong_province_month_rainfall_2000_2024.csv`
- Generated cleaned rainfall dataset:
  - `data/processed/province_month_rainfall.csv`

### Code

- Implemented rainfall cleaning pipeline in `scripts/02_clean_rainfall.py`
- Added Earth Engine smoke test in `test.py`
- Exported sample map to `precipitation_map.html`

### Documentation

- Added team Git workflow notes in `github.md`
- Updated `README.md` to match the current repository contents

## In Progress

- Keep this section limited to tasks actively being worked on.

| Task | Owner | Started | Status | Notes |
|---|---|---|---|---|
| Update documentation to match actual repo status | Team | 2026-05-18 | In progress | Continue refining setup and usage notes |

## Next Tasks

| Priority | Task | Owner | Notes |
|---|---|---|---|
| High | Create dashboard app entry point | Unassigned | Replace empty `mvp.py` or add a proper app file |
| High | Add `requirements.txt` | Unassigned | Capture the actual Python dependencies |
| High | Decide dashboard framework structure | Unassigned | Confirm Shiny or another stack before coding UI |
| Medium | Add first rainfall charts | Unassigned | Start with trend, ranking, and heatmap views |
| Medium | Document raw data extraction workflow | Unassigned | Explain how the raw CSV files were created |
| Low | Remove unused placeholders | Unassigned | Clean up files that are no longer needed |

## Risks and Blockers

| Item | Type | Status | Notes |
|---|---|---|---|
| No dashboard code yet | Risk | Open | The project currently stops at data prep |
| No dependency file | Risk | Open | Setup is not yet reproducible in one step |
| Earth Engine project access may vary by teammate | Blocker | Open | `test.py` depends on authentication and project permissions |

## Decisions Log

| Date | Decision | Reason |
|---|---|---|
| 2026-05-18 | Keep current scope documented as rainfall MVP | Matches the actual repo contents |
| 2026-05-18 | Track progress in a dedicated Markdown file | Easier to update during development |

## Useful Commands

### Rebuild processed rainfall data

```bash
cd scripts
python 02_clean_rainfall.py
```

### Run Earth Engine test

```bash
python test.py
```

## Update Template

Use this block when adding a new weekly or milestone update:

```md
### Update - YYYY-MM-DD

- What was completed:
- What is in progress:
- What is blocked:
- Next action:
```

## Activity Log

### Update - 2026-05-18

- What was completed: README updated to match the current repository contents.
- What is in progress: Project tracking and documentation cleanup.
- What is blocked: Dashboard implementation has not started yet.
- Next action: Add dependency file and start the MVP dashboard structure.
