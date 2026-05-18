# Data Credits and Attribution

**Project:** Applying FAIR Principles to Community-Curated Gaming Data  
**Student:** Kelsey Kiantoro | INFO628 Data Librarianship and Management | Pratt School of Information | May 2026

This file documents all external data sources used in this project, including those consulted or partially used but not included in the final analysis. Proper attribution is required under the FAIR Reusable principle and the license terms of each dataset.

---

## 1. Primary Game Dataset (used in all analysis)

**Name:** Top 1000 Steam Games (2024–2026)  
**Creator:** Waddah Ali  
**Platform:** Kaggle  
**Published:** March 2026  
**License:** [CC BY-NC-SA 4.0](https://creativecommons.org/licenses/by-nc-sa/4.0/) — Attribution, NonCommercial, ShareAlike  
**URL:** https://www.kaggle.com/datasets/waddahali/top-1000-steam-games-20242026/versions/1  
**File used:** `steam_games_2026.csv`

**How data was collected by creator:**
- AppID discovery via Steam "Top Sellers" page
- Game metadata via Steam Storefront API
- Community tags via Steam store-page scraping
- 24-hour peak players via SteamSpy API
- Estimated owners via Boxleiter Method (Total Reviews × 30)

**How I used it:**
- Primary dataset for all tag analysis, genre classification, and database construction
- Provided the 1,000 game records and their community-assigned tags (semicolon-delimited `All_Tags` column)
- Extracted 369 unique tags from this dataset for taxonomy classification

**Citation (APA 7):**  
Ali, W. (2026). *Top 1000 Steam Games (2024–2026)* [Dataset]. Kaggle. https://www.kaggle.com/datasets/waddahali/top-1000-steam-games-20242026/versions/1

---

## 2. Publisher Dataset (consulted; not used in final analysis)

**Name:** Publisher Classification Data  
**Creator:** Seyed Nasrollahi (online alias: seyedhn) 
**Platform:** Gamalytics (gamalytic.com) — proprietary analytics platform  
**License:** Not specified; data used for educational/research purposes only  
**URL:** https://docs.google.com/spreadsheets/u/1/d/15AN1I1mB67AJkpMuUUfM5ZUALkQmrvrznnPYO5QbqD0/edit?gid=1783327951#gid=1783327951
**File used:** `Publisher/628-Publisher_Data Management_Base - 02_Publisher_V02.csv`
**Publication/Last Updated Date:** April 7, 2026 (visible at the top of the image)Dataset
**Title:** Publisher & Investor Database for Indie Devs (commonly referred to by the community as the Comprehensive list of indie game publishers)

**What it contains:**
- 205 Steam publishers
- Country of origin, website, Steam followers, games published
- First and last game release dates
- Lifetime, average, and median revenue estimates
- Market-tier classification (AAA / AA / Indie)
- Best-selling titles

**How I used it:**
- Included in the database schema design (PUBLISHER table) as part of the planned relational structure
- Used for data cleaning practice: publisher name normalization (e.g., "EA" / "Electronic Arts" / "EA Games" → canonical form) using OpenRefine
- Revenue and tier data were used to design the market-tier classification field
- **Not used in the final write-up analysis** due to scope change — the project's primary focus shifted to tag taxonomy and the folksonomy/taxonomy comparison. The publisher table remains in the database but was not analyzed.

**Citation (APA 7):**  
Nasrollahi, S. (2026, April 7). Publisher & investor database for indie devs [Data set]. Google Sheets. https://docs.google.com/spreadsheets/d/15AN1I1mB67AJkpMuUUfM5ZUALkQmrvrznnPYO5QbqD0/edit?gid=1783327951#gid=1783327951
---

## 3. Original Steam Tag Vocabulary (tag taxonomy source)

**Name:** Steam Trends 2023  
**Creators:** Barabanov, A. (Sadari) & Kobelev, L. (evlko)  
**Platform:** Google Sheets (publicly shared)  
**License:** Not formally specified; publicly shared dataset  
**URL:** https://docs.google.com/spreadsheets/d/1TGGMEbcCqnxZgDm7AOA4-3iLs2f4ANkxT8nnb-x7mGY

**What it contains:**
- 10,800+ Steam game records scraped from the Steam platform (2023)
- 445 unique community-generated tags across the full catalog

**How I used it:**
- The **445 unique tags** from this dataset formed the initial vocabulary for the taxonomy classification work
- Tag classification decisions (Genre / Theme / Feature / Visual / etc.) were built from this full tag list using Grelier et al.'s (2023) framework
- **The game records themselves were not used** — this dataset was replaced by the 2026 Waddah Ali dataset due to release date formatting issues found during data audit
- The tag vocabulary from this earlier dataset informed the taxonomy, even though the final analysis used a newer game records dataset

**Citation (APA 7):**  
Barabanov, A. (Sadari), & Kobelev, L. (evlko). (2023). *Steam Trends 2023* [Dataset]. Google Sheets. https://docs.google.com/spreadsheets/d/1TGGMEbcCqnxZgDm7AOA4-3iLs2f4ANkxT8nnb-x7mGY

---

## 4. MobyGames Genre Categories (crosswalk comparison)

**Name:** MobyGames Genre and Attribute Classification System  
**Creator:** MobyGames (community-maintained; moderated by MobyGames editorial team)  
**Platform:** MobyGames (www.mobygames.com)  
**License:** MobyGames data is copyrighted. Used here for academic research and comparison purposes only; not redistributed.  
**URL:** https://www.mobygames.com

**What it contains:**
- Controlled genre vocabulary assigned by editors (top-down classification)
- Genre facets including: Basic Genres, Perspective, Visual Presentation, Art Style, Pacing, Gameplay, Interface/Control, Sports Themes, Setting, Narrative Theme/Topic
- Coverage statistics (number of games per genre term)

**How I used it:**
- Manual crosswalk: compared MobyGames genre terms against Steam community tags to identify overlap and gaps
- Produced the "tag translation gap" finding: only ~54 terms shared between both systems
- Illustrated the structural difference between a controlled taxonomy (MobyGames — top-down, editorial) and a folksonomy (Steam — bottom-up, community votes)
- Reference statistics captured in: `Genre/Genre StudyCase/INFO648-DataGenre_StudyCase_MobyGameAndSteamDB - MG_Tag and Genre.csv`

**Citation (APA 7):**  
MobyGames. (2024). *Genre and attribute classification system* [Database]. Blue Flame Labs. https://www.mobygames.com

---

## 5. SteamDB Tag Category Filter (scraped for crosswalk)

**Name:** SteamDB Tag Browser / Category Filter  
**Creator:** SteamDB (third-party Steam analytics tool)  
**Platform:** SteamDB (steamdb.info)  
**License:** SteamDB data reflects Steam platform data. Used here for academic research only; not redistributed.  
**URL:** https://steamdb.info/tags/

**What it contains:**
- Steam tags organized into category groups: Top-Level Genres, Genres, Themes & Moods, Visuals & Viewpoint, Features, and more
- Tag application counts (total number of times each tag has been applied across all Steam games)

**How I used it:**
- Used to understand Steam's own informal grouping of tags (SteamDB applies category labels that Steam itself does not display)
- Compared SteamDB's category structure against Grelier et al.'s (2023) dimensional framework
- Provided tag frequency counts to validate which tags are most widely applied
- Reference data captured in: `Genre/Genre StudyCase/INFO648-DataGenre_StudyCase_MobyGameAndSteamDB - Steam_Tag and Genre.csv`

**Citation (APA 7):**  
SteamDB. (2024). *Steam tag browser* [Database]. https://steamdb.info/tags/

---

## 6. Steam Tag Wizard Documentation (methodology validation)

**Name:** Steam Tags — Steamworks Documentation  
**Creator:** Valve Corporation  
**Platform:** Steamworks Partner Documentation  
**License:** Public developer documentation  
**URL:** https://partner.steamgames.com/doc/store/tags

**What it contains:**
- Official description of Steam's Tag Wizard — the internal tool developers use to tag their games
- Defines the tag structure Steam itself uses: Super-Genre → Genre → Sub-Genre
- Lists the same dimensional categories used in this project: Genres, Visuals & Viewpoints, Themes & Moods, Features, Player Support

**How I used it:**
- Used as methodological validation: confirms that the dimensional classification applied in this project (following Grelier et al., 2023) aligns with Steam's own internal tag organization
- Steam's Tag Wizard uses identical hierarchy levels (Super-Genre → Genre → Sub-Genre) to those built in the GENRE table
- This source was not a dataset — it informed the *design rationale* for the taxonomy, not the data itself

**Citation (APA 7):**  
Valve Corporation. (n.d.). *Steam tags* [Documentation]. Steamworks. https://partner.steamgames.com/doc/store/tags

---

## Underlying Platforms Credited by Dataset Creators

These platforms are the original sources of the data — credited through the datasets above:

| Platform | What It Provided | Credited Via |
|----------|-----------------|-------------|
| Valve Corporation / Steam | Game metadata, community tags, store data | Waddah Ali dataset (Dataset 1) |
| SteamSpy (Sergey Galyonkin) | Peak concurrent player counts | Waddah Ali dataset (Dataset 1) |
| Steam API | AppID, name, price, review data | Waddah Ali dataset (Dataset 1) |

## Summary Table

| # | Source | Creator | Used in Final Analysis? | License |
|---|--------|---------|------------------------|---------|
| 1 | Top 1000 Steam Games (2024–2026) | Waddah Ali (Kaggle) | ✅ Yes — primary dataset | CC BY-NC-SA 4.0 |
| 2 | Publisher Classification Data | Gamalytics | ⚠️ Partial — schema only | Unspecified (educational use) |
| 3 | Steam Trends 2023 (tag vocabulary) | Barabanov & Kobelev | ⚠️ Partial — tag list only | Unspecified (public) |
| 4 | MobyGames Genre Classification | MobyGames editorial team | ✅ Yes — crosswalk comparison | Copyrighted (academic use) |
| 5 | SteamDB Tag Category Filter | SteamDB | ✅ Yes — crosswalk comparison | Copyrighted (academic use) |
| 6 | Steam Tag Wizard Documentation | Valve Corporation | ✅ Yes — methodology validation | Public documentation |

---

*This attribution file was prepared in accordance with the FAIR Reusable principle (Wilkinson et al., 2016), which requires that data use be documented with sufficient provenance and licensing information for future reuse.*
