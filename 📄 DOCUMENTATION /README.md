# Making Community Data FAIR: Steam Tag Taxonomy Pipeline

**Kelsey Kiantoro · INFO628 Data Librarianship & Management · Prof. Vicky Steeves · Pratt School of Information · May 2026**


## Research Question

> *Can community-curated tags be restructured into a FAIR-compliant taxonomy for data librarianship?*

Steam allows any player to apply any label to any game — producing hundreds of flat, unstructured tags with no hierarchy and no controlled vocabulary. This project transforms that folksonomy into a FAIR-compliant relational database, then compares it against MobyGames' controlled vocabulary to show what is gained (and lost) in that translation.


## Project Deliverables

| Document | Description |
|----------|-------------|
| [Analysis Write-Up](analysis_writeup.pdf) | Methodology and findings (3 pages) |
| [Data Management Plan](data_management_plan.pdf) | DMP + plan vs. actual addendum |
| [Research Poster](research_poster.pdf) | Visual summary of the full pipeline |


## The Project in Three Steps

### 1. Clean the Data
Two datasets were cleaned and normalized:
- **Steam game dataset** (Waddah Ali, Kaggle, 2026) — 1,000 games, community tags extracted from semicolon-delimited cells, 370 unique tags identified
- **Publisher dataset** (Gamalytics, 205 publishers) — name normalization via OpenRefine (e.g. "EA" / "Electronic Arts" / "EA Games" → canonical form), market-tier classification

### 2. Build the Database
The cleaned data was restructured into a 7-table SQLite database normalized to 3NF, with SKOS properties applied to the schema:

| Table | Rows | Description |
|-------|------|-------------|
| PUBLISHER | 205 | Gamalytics data, cleaned & normalized |
| GAME | 1,000 | Steam 2026 top games |
| TAG_TYPE | 29 | SteamDB sub-categories (Grelier dimension labels) |
| TAG | 308 | Non-genre tags with Grelier dimension labels |
| GENRE | 142 | Full genre hierarchy (adjacency list) |
| GAME_GENRE | 3,162 | Game ↔ Genre junction |
| GAME_TAG | 6,324 | Game ↔ Tag junction |

SKOS properties used:
- `skos:broader` — encodes the 3-level genre hierarchy in the GENRE table (Sub-Genre → Genre → Super-Genre, a mereological / part-whole relationship)
- `skos:inScheme` — assigns each non-genre tag in the TAG table to its Grelier dimension

### 3. Compare: SteamDB Folksonomy vs. MobyGames Taxonomy
With the database built, the analysis asks: how well does Steam's community vocabulary map onto a library-standard controlled vocabulary?

**Finding:** Of 370 Steam tags and 230 MobyGames genre terms, only **54 terms are shared**.

- Steam carries **316 tags** with no MobyGames equivalent — experiential terms like *Cozy, Soulslike, Wholesome, Boomer Shooter*
- MobyGames carries **176 terms** absent from Steam — structural metadata like *Perspective, Pacing, Visual Presentation*

Neither system is wrong. They answer different questions. Steam describes how a game *feels*; MobyGames describes how a game *works*. SKOS (`skos:broader`, `skos:inScheme`) holds both in one schema without forcing them to merge.

---

## Key Files

```
📓 CODE
├── steam_fair_pipeline_v2.ipynb     ← Full pipeline notebook (Google Colab)
├── build_db_v2.py                   ← SQLite database builder
└── analysis_pipeline.py             ← Standalone reproducible script

📄 DOCUMENTATION
├── README.md                        ← This file
├── analysis_writeup.pdf             ← Methodology and findings (3 pages)
├── data_management_plan.pdf         ← DMP + plan vs. actual addendum
├── research_poster.pdf              ← Visual summary of the full pipeline
├── DATA_CREDITS.md                  ← Full attribution for all data sources
├── Genre_ERD_ASCII.md               ← Entity-relationship diagram + schema SQL
└── GENRE_TAXONOMY_DATA_FLOW.md      ← Classification decisions and methodology

📊 DATA
├── steam_games_2026.csv             ← Primary dataset (Waddah Ali, CC BY-NC-SA 4.0)
├── steam_tags_full_taxonomy.csv     ← All 370 tags with Grelier dimension labels
└── Genre/Genre StudyCase/           ← MobyGames vs SteamDB crosswalk CSVs

🗄️ DATABASE
└── steam_games.db                   ← SQLite database (7 tables, ~11,170 rows)
```

---

## How to Run

Open `steam_fair_pipeline_v2.ipynb` in **Google Colab**. Upload `steam_games_2026.csv` when prompted. Run cells top to bottom.

For the standalone reproducible script: `python analysis_pipeline.py`

---

## Data Management

| Decision | Choice | Rationale |
|----------|--------|-----------|
| File format | CSV (UTF-8-sig) | Open, tool-agnostic |
| File naming | ISO 8601 (YYYY-MM-DD_name_stage_version) | Sortable, reproducible |
| License | ODC-By (Open Data Commons Attribution) | Designed for databases |
| Metadata | DataCite schema + README | Machine-readable and human-readable |
| Cleaning tool | OpenRefine (publisher clustering) | Documented, reproducible |
| Database | SQLite via DBeaver | Lightweight, portable, open |
| Repository | OSF (Open Science Framework) | DOI assignment, public access |

---

## References

Grelier, N., Kaufmann, S., & Schmalz, M. (2023). Data-driven classifications of video game vocabulary. *arXiv preprint arXiv:2303.07179.* https://arxiv.org/abs/2303.07179

Li, X., & Zhang, B. (2020). A preliminary network analysis on steam game tags: Another way of understanding game genres. *Proceedings of the 23rd International Academic Mindtrek Conference* (pp. 80–88). https://doi.org/10.1145/3377290.3377300

Wilkinson, M. D., et al. (2016). The FAIR Guiding Principles for scientific data management and stewardship. *Scientific Data, 3*(1), 1–9. https://doi.org/10.1038/sdata.2016.18

Windleharth, T. W., Jett, J., Schmalz, M., & Lee, J. H. (2016). Full steam ahead: A conceptual analysis of user-supplied tags on Steam. *Cataloging & Classification Quarterly, 54*(7), 418–441. https://doi.org/10.1080/01639374.2016.1190951

---

*Attribution: Code scaffolding assisted by Claude (Anthropic, 2026). All analytical decisions, classification rules, taxonomy design, database structure, and interpretations are the author's own.*
