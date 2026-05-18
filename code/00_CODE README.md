#Making Community Data FAIR: Steam Tag Taxonomy Pipeline


## Getting Started

All notebooks run in **Google Colab** — no local setup required. The standalone script runs with Python 3.x and open-source libraries only (`pandas`, `matplotlib`, `plotly`, `networkx`).

**Requirements for the script:**
```
pip install pandas matplotlib plotly networkx
```

Upload `steam_games_2026.csv` (download from [Kaggle](https://www.kaggle.com/datasets/waddahali/top-1000-steam-games-20242026/versions/1)) when prompted.


## Notebooks & Scripts

| # | Title | Description | Link |
|---|-------|-------------|------|
| 1 | **Data Pipeline Notebook** | Full pipeline: load CSV → extract tags → classify by Grelier framework → build genre hierarchy → visualize | [![Open In Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/kianoding/data-management-sp-26/blob/main/code/steam_fair_pipeline_v2.ipynb) |
| 2 | **Database Builder** | Reads cleaned CSVs → builds 7-table SQLite database with foreign key constraints, normalized to 3NF | [build_db_v2.py](build_db_v2.py) |
| 3 | **Reproducible Script** | Standalone open-source Python script — runs all steps end to end without Colab or proprietary tools | [analysis_pipeline.py](analysis_pipeline.py) |


## What Each File Does

### 1. `steam_pipeline.ipynb`
The main notebook. Run cells top to bottom in Google Colab.

| Step | What It Does |
|------|-------------|
| 1 | Install packages |
| 2 | Upload and load `steam_games_2026.csv` |
| 3 | Explore: shape, columns, missing values |
| 4 | Extract all unique tags from semicolon-delimited cells |
| 5 | Chart: Top 30 most-used tags |
| 6 | Chart: Primary genre distribution |
| 7 | Classify tags by Grelier dimension (Genre / Theme / Feature / Visual / Mood) |
| 8 | Chart: Dimension breakdown |
| 9 | Draw: ERD — the 7-table relational schema |
| 10 | Draw: Network graph — genre hierarchy |
| 10b | Metric: Degree centrality — most connected genres |
| 10c | Metric: Tag co-occurrence — most common tag pairs |
| 11 | Draw: Sunburst — interactive genre hierarchy |
| 12 | Draw: Swimlane — full curation workflow |

### 2. `build_db_v2.py`
Standalone database builder. Reads the cleaned CSV outputs from the notebook and builds the full 7-table SQLite database (`steam_games.db`).

### 3. `analysis_pipeline.py`
Fully reproducible, open-source script. Runs the complete pipeline — data loading, tag extraction, classification, database build, and chart exports — without requiring Google Colab or any proprietary tools. All outputs saved to `pipeline_outputs/`.

---

*Attribution: Code scaffolding assisted by Claude (Anthropic, 2026). Network graph data and structure (nodes, edges, genre hierarchy) are the author's own. All analytical decisions, classification rules, taxonomy design, and interpretations are the author's own.*
