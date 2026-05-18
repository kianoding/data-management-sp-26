# Genre ERD — Full ASCII Map
### INFO628 Final Project | Data Librarianship & Management
---

## RELATIONSHIP NOTATION
```
||       = exactly one (mandatory)
o|       = zero or one (optional)
|{       = one or many
o{       = zero or many
```

---

## FULL ERD (7 Tables — Current Implementation)

```
┌─────────────────────────┐          ┌──────────────────────────────────┐
│        PUBLISHER        │          │               GAME               │
├─────────────────────────┤          ├──────────────────────────────────┤
│ PK  publisher_id        │          │ PK  game_id                      │
│     publisher_name      │          │     game_name                    │
│     country             │ ||───o{  │ FK  publisher_id                 │
│     steam_followers     │          │     release_date                 │
│     games_published     │          │     price_usd                    │
│     lifetime_rev        │          │     review_score_pct             │
│     avg_rev             │          │     total_reviews                │
│     publisher_class     │          │     estimated_owners             │
│     operational_status  │          └────────────┬─────────────────────┘
└─────────────────────────┘                       │
                                                  │
                                     ┌────────────┴────────────┐
                                     │                         │
                                     ▼                         ▼
                              ┌─────────────┐          ┌─────────────┐
                              │  GAME_GENRE │          │  GAME_TAG   │
                              │ (junction)  │          │ (junction)  │
                              ├─────────────┤          ├─────────────┤
                              │ FK  game_id │          │ FK  game_id │
                              │ FK  genre_id│          │ FK  tag_id  │
                              └──────┬──────┘          └──────┬──────┘
                                     │                        │
                                     ▼                        ▼
                        ┌────────────────────┐    ┌──────────────────────┐
                        │       GENRE        │    │         TAG          │
                        ├────────────────────┤    ├──────────────────────┤
                        │ PK  genre_id       │    │ PK  tag_id           │
                        │     genre_name     │    │     tag_name         │
                        │     genre_level    │    │ FK  tag_type_id      │
                        │ FK  parent_genre_id│◄─┐ │     trend_value      │
                        └────────────────────┘  │ └──────────┬───────────┘
                          (self-referencing FK)  │            │ o{───||
                          skos:broader ──────────┘            ▼
                                                  ┌──────────────────────┐
                                                  │       TAG_TYPE       │
                                                  ├──────────────────────┤
                                                  │ PK  tag_type_id      │
                                                  │     dimension_name   │
                                                  └──────────────────────┘
                                                       skos:inScheme
```

---

## KEY DESIGN DECISIONS

### GENRE — Single Table, Adjacency List
The genre hierarchy (Super-Genre → Genre → Sub-Genre) is encoded in **one table** using a self-referencing foreign key (`parent_genre_id`). The `genre_level` field (ENUM: Super-Genre / Genre / Sub-Genre) identifies which level each row belongs to. This avoids three separate tables and unnecessary joins.

Maps to `skos:broader` — each genre's parent is its broader concept in the mereological hierarchy.

```sql
GENRE (
  genre_id        INTEGER PRIMARY KEY,
  genre_name      TEXT NOT NULL,
  genre_level     TEXT CHECK(genre_level IN ('Super-Genre','Genre','Sub-Genre')),
  parent_genre_id INTEGER REFERENCES GENRE(genre_id)
)
```

### TAG_TYPE — Grelier Dimension Labels
Non-genre tags are stored in TAG and classified via FK to TAG_TYPE. Each dimension_name maps to one of Grelier et al.'s (2023) non-equivalent tag categories (Theme, Feature, Visual, Tone/Mood, Assessment, etc.).

Maps to `skos:inScheme` — each tag is a member of a controlled dimension scheme without a hierarchy imposed on it.

```sql
TAG_TYPE (
  tag_type_id    INTEGER PRIMARY KEY,
  dimension_name TEXT NOT NULL
)
```

---

## RELATIONSHIP SUMMARY

| From      | To       | Via        | Cardinality | SKOS           | Note |
|-----------|----------|------------|-------------|----------------|------|
| Publisher | Game     | FK         | 1 → many    | —              | One publisher, many games |
| Game      | Genre    | GAME_GENRE | many → many | skos:broader   | Junction table |
| Game      | Tag      | GAME_TAG   | many → many | skos:inScheme  | Junction table |
| Genre     | Genre    | parent_id  | many → 1    | skos:broader   | Self-ref — mereological hierarchy |
| Tag       | Tag_Type | FK         | many → 1    | skos:inScheme  | Many tags per dimension |

---

## TABLE COUNT: 7 TABLES

| Table      | Type     | Rows   | Source |
|------------|----------|--------|--------|
| Publisher  | Entity   | 205    | Gamalytics — cleaned via OpenRefine |
| Game       | Entity   | 1,000  | Waddah Ali / Kaggle (CC BY-NC-SA 4.0) |
| Genre      | Entity   | 142    | Author's taxonomy (adjacency list, 3 levels) |
| Tag        | Entity   | 308    | Author's taxonomy (non-genre tags) |
| Tag_Type   | Entity   | 29     | SteamDB sub-categories / Grelier framework |
| Game_Genre | Junction | 3,162  | Derived from Steam tag data |
| Game_Tag   | Junction | 6,324  | Derived from Steam tag data |

**Total: ~11,170 rows across 7 tables. Schema normalized to 3NF. All FK constraints enforced.**

---

## THEORETICAL FRAMEWORK

### PATH 1 — TAXONOMY (GENRE, adjacency list)
**Justified by: Grelier, Kaufmann & Schmalz (2023)**

> "Steam provides a taxonomy of Steam tags. Tags are divided into several taxa: Genres, Visual
> Properties, Themes & Moods, Features, Players... The taxon Genres is split into three taxa:
> Super-Genre, Genre and Sub-Genre."
> — Grelier et al. (2023, p. 3)

Grelier et al. validated empirically that genre tags form a three-level hierarchy based on how players assign them. Their framework provides the structure for the Super-Genre → Genre → Sub-Genre chain encoded in the single GENRE table via self-referencing FK.

The relationship is **mereological** (part-whole), not strictly taxonomic — Sub-Genres are parts of Genres, not subtypes that inherit properties. `skos:broader` is used because it covers both IS-A and part-whole relationships in SKOS practice (Li & Zhang, 2020).

**Citation:** Grelier, N., Kaufmann, S., & Schmalz, M. (2023). Data-driven classifications of video game vocabulary. *arXiv preprint arXiv:2303.07179.* https://arxiv.org/abs/2303.07179

---

### PATH 2 — FOLKSONOMY (TAG → TAG_TYPE)
**Justified by: Windleharth, Jett, Schmalz & Lee (2016)**

> "This article describes a conceptual analysis of user-generated tags applied to video games
> in the Steam video game distribution system... This analysis allowed the team to identify
> new metadata elements and terms useful to game players."
> — Windleharth et al. (2016, p. 418)

Windleharth et al. found that Steam tags span multiple non-genre dimensions of meaning — gameplay, theme, mood, visual style, features, and more. Treating all tags as equivalent loses important semantic distinctions. This justifies storing tags with a `tag_type_id` FK so each tag retains its dimensional context.

**Citation:** Windleharth, T. W., Jett, J., Schmalz, M., & Lee, J. H. (2016). Full steam ahead: A conceptual analysis of user-supplied tags on Steam. *Cataloging & Classification Quarterly, 54*(7), 418–441. https://doi.org/10.1080/01639374.2016.1190951

---

### WHY TWO PATHS TOGETHER?

The GENRE and TAG tables run in parallel — both connected to GAME through junction tables. This reflects the core finding of both papers: genre classification and community tagging are not the same thing and should not be collapsed into one structure.

Together they satisfy FAIR's **Interoperability** and **Reusability** principles (Wilkinson et al., 2016): the data is queryable through both expert genre vocabulary and community tag vocabulary, with each dimension clearly labeled via SKOS.

- `skos:broader` — genre hierarchy is traversable as a controlled vocabulary
- `skos:inScheme` — non-genre tags belong to a documented scheme without false hierarchy

**Citation:** Wilkinson, M. D., et al. (2016). The FAIR Guiding Principles for scientific data management and stewardship. *Scientific Data, 3*(1), 1–9. https://doi.org/10.1038/sdata.2016.18
