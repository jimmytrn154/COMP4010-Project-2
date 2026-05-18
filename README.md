# COMP4010-Project-2 | Mekong FloodLens

## Overview

This repository contains the current working materials for **Mekong FloodLens**, a COMP4010 project focused on rainfall and climate-risk exploration in the Vietnamese Mekong Delta.

At this stage, the repo is centered on:

- project documentation and planning
- rainfall data files and a cleaning script
- proposal and design reference assets
- progress tracking for ongoing work

## Start Here

The most important project documents in this repository are:

- [Proposal write-up](COMP4010_Project2_Team3_proposal_writeup.pdf): the main project proposal, scope, motivation, and planned direction.
- [Wireframe](wireframe.png): the current dashboard wireframe and UI reference.
- [Project progress log](PROJECT_PROGRESS.md): the ongoing status tracker for completed work, current work, risks, and next tasks.

If you are new to the repo, read those three files first.

## Repository Contents

```text
COMP4010-Project-2/
|-- data/
|   |-- raw/
|   |   |-- mekong_province_month_rainfall_2000_2024.csv
|   |   |-- mekong_province_month_rainfall_2020_2024.csv
|   |   `-- mekong_provinces_boundary.geojson
|   `-- processed/
|       `-- province_month_rainfall.csv
|-- scripts/
|   `-- 02_clean_rainfall.py
|-- COMP4010_Project2_Team3.pdf
|-- wireframe.png
|-- PROJECT_PROGRESS.md
|-- github.md
|-- precipitation_map.html
`-- README.md
```

## Key Documentation

### Proposal write-up

[COMP4010_Project2_Team3.pdf](COMP4010_Project2_Team3_proposal_writeup.pdf) is the primary proposal document for the project. It should be treated as the main reference for:

- project problem statement
- goals and scope
- planned dashboard direction
- expected data and visualization approach

### Wireframe

[wireframe.png](wireframe.png) is the current visual reference for the intended dashboard layout. Use it when aligning implementation decisions with the planned interface and user flow.

### Progress tracking

[PROJECT_PROGRESS.md](PROJECT_PROGRESS.md) is the live project log. It records:

- current status by work area
- completed milestones
- in-progress tasks
- blockers and risks
- next actions

This file should be updated as development continues.

## Data Files

The repository already includes the core rainfall and boundary datasets needed for the current MVP work.

### Raw data

Files in `data/raw/`:

- `mekong_province_month_rainfall_2000_2024.csv`
  Historical monthly rainfall table for Mekong Delta provinces covering 2000 to 2024.
- `mekong_province_month_rainfall_2020_2024.csv`
  Shorter rainfall table used for the current cleaning workflow.
- `mekong_provinces_boundary.geojson`
  Province boundary file for the Mekong Delta study area.

### Processed data

Files in `data/processed/`:

- `province_month_rainfall.csv`
  Cleaned rainfall dataset generated from the raw rainfall input. The file includes:
  - `province_name`
  - `year`
  - `month`
  - `date`
  - `rainfall_mm`
  - `monthly_mean`
  - `rainfall_anomaly`
  - `rainfall_zscore`

## Data-Cleaning Script

The main data-processing script in the repo is [scripts/02_clean_rainfall.py](scripts/02_clean_rainfall.py).

What it does:

- reads `data/raw/mekong_province_month_rainfall_2020_2024.csv`
- standardizes the rainfall column name when needed
- converts date and time fields to usable types
- computes monthly climatology by province
- calculates rainfall anomaly and rainfall z-score
- writes the cleaned output to `data/processed/province_month_rainfall.csv`

Run it from the repository root with:

```bash
python scripts/02_clean_rainfall.py
```

## Other Files

- [github.md](github.md): team Git and collaboration notes.
- [precipitation_map.html](precipitation_map.html): exported map artifact from earlier rainfall or Earth Engine testing.

## Current Repo Status

Based on the current repository contents:

- rainfall data collection and cleaning artifacts are present
- the cleaned rainfall dataset already exists
- proposal and wireframe assets are included
- progress tracking is maintained in a dedicated Markdown file
- dashboard implementation files are not yet established in the root repository structure

## Recommended Reading Order

1. [COMP4010_Project2_Team3_proposal_writeup.pdf](COMP4010_Project2_Team3_proposal_writeup.pdf)
2. [wireframe.png](wireframe.png)
3. [PROJECT_PROGRESS.md](PROJECT_PROGRESS.md)
4. [scripts/02_clean_rainfall.py](scripts/02_clean_rainfall.py)
5. `data/raw/` and `data/processed/`

## Notes

- The repository currently documents a rainfall-focused MVP more clearly than a finished dashboard application.
- `PROJECT_PROGRESS.md` should be treated as the source of truth for active project status.
- The proposal PDF and wireframe should stay visible and easy to access because they define the project direction and intended interface.
