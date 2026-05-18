"""
INFO 628 - Steam Game Database Builder v2
Kelsey Kiantor, Spring 2026

Sources:
  - steam_games_2026.csv      : 1000 Steam games
  - steam_tags_flare.json     : SteamDB tag taxonomy (canonical names + weights)
  - Publisher_V02.csv         : 204 cleaned publishers (Gamalytics)

TAG_TYPE  : 34 SteamDB sub-categories
GENRE     : Tags from genre-type SteamDB categories (Core Genres, Sub-Genres, etc.)
TAG       : All remaining non-genre tags
PUBLISHER : From publisher CSV
GAME      : From game CSV
GAME_GENRE / GAME_TAG : Re-linked with spelling normalization map
"""

import sqlite3, csv, json, os, re, shutil

# ── PATHS ──────────────────────────────────────────────────────────────────────
UP   = "/sessions/cool-clever-wozniak/mnt/uploads"
WS   = "/sessions/cool-clever-wozniak/mnt/Data Librarianship and Management Class Assistant"
GAMES_CSV = f"{UP}/1c0d01d1-57ad-44b0-a9df-9e2922ed4694-1778328663255_steam_games_2026.csv"
TAGS_JSON = f"{UP}/08d4b614-703a-462b-8a2c-446837a102e3-1778328747288_steam_tags_flare.json"
PUB_CSV   = f"{UP}/3ac1fbc0-38b0-49ae-b5dc-2c50e42bf2fb-1778328992557_628-Publisher_Data Management_Base - 02_Publisher_V02.csv"
DB_TMP    = "/tmp/steam_games_v2.db"
DB_OUT    = f"{WS}/steam_games.db"

if os.path.exists(DB_TMP):
    os.remove(DB_TMP)

conn = sqlite3.connect(DB_TMP)
conn.execute("PRAGMA foreign_keys = ON")
cur = conn.cursor()

# ── CREATE TABLES ──────────────────────────────────────────────────────────────
cur.executescript("""
CREATE TABLE PUBLISHER (
    pub_id            INTEGER PRIMARY KEY AUTOINCREMENT,
    pub_name          TEXT    NOT NULL UNIQUE,
    country           TEXT,
    multinational     INTEGER CHECK(multinational IN (0,1)),
    secondary_country TEXT,
    operational_stat  TEXT    CHECK(operational_stat IN ('Active','Inactive','Bankrupt')),
    business_maturity TEXT    CHECK(business_maturity IN ('Startup','Established','Legacy')),
    service           TEXT,
    steam_followers   INTEGER,
    game_published_qty INTEGER,
    p_class_qty       TEXT,
    p_class_rev       TEXT,
    lifetime_rev_usd  REAL,
    avg_rev_usd       REAL,
    active_years      INTEGER,
    fd_game_release   TEXT,
    ld_game_release   TEXT,
    note              TEXT
);

CREATE TABLE TAG_TYPE (
    tag_type_id   INTEGER PRIMARY KEY AUTOINCREMENT,
    tag_type_name TEXT    NOT NULL UNIQUE
);

CREATE TABLE GENRE (
    genre_id        INTEGER PRIMARY KEY AUTOINCREMENT,
    genre_name      TEXT    NOT NULL UNIQUE,
    genre_level     TEXT    CHECK(genre_level IN ('Super-Genre','Genre','Sub-Genre')),
    genre_parent_id INTEGER REFERENCES GENRE(genre_id),
    super_genre     TEXT,
    trend_value     TEXT    CHECK(trend_value IN ('High','Medium','Low',''))
);

CREATE TABLE TAG (
    tag_id        INTEGER PRIMARY KEY AUTOINCREMENT,
    tag_name      TEXT    NOT NULL UNIQUE,
    tag_type_id   INTEGER REFERENCES TAG_TYPE(tag_type_id),
    tag_weight    INTEGER,
    trend_value   TEXT    CHECK(trend_value IN ('High','Medium','Low',''))
);

CREATE TABLE GAME (
    game_id           INTEGER PRIMARY KEY,
    game_name         TEXT    NOT NULL,
    release_date      TEXT,
    price_usd         REAL,
    review_score      INTEGER,
    total_reviews     INTEGER,
    estimated_owners  INTEGER,
    peak_players_24h  INTEGER,
    publisher_id      INTEGER REFERENCES PUBLISHER(pub_id),
    data_quality_note TEXT
);

CREATE TABLE GAME_GENRE (
    game_id  INTEGER REFERENCES GAME(game_id),
    genre_id INTEGER REFERENCES GENRE(genre_id),
    PRIMARY KEY (game_id, genre_id)
);

CREATE TABLE GAME_TAG (
    game_id INTEGER REFERENCES GAME(game_id),
    tag_id  INTEGER REFERENCES TAG(tag_id),
    PRIMARY KEY (game_id, tag_id)
);
""")
conn.commit()
print("Tables created")

# ── PARSE STEAMDB JSON ─────────────────────────────────────────────────────────
with open(TAGS_JSON, encoding="utf-8") as f:
    flare = json.load(f)

# JSON name cleanups (encoding artifacts in source file)
NAME_FIX = {
    "3Match 3": "Match 3",
    "44 Player Local": "4 Player Local",
    "2Sequel": "Sequel",
}

# Which SteamDB sub-categories produce GENRE rows vs TAG rows
GENRE_CATS = {
    "Core Genres":          "Genre",
    "Sub-Genres & Mechanics": "Sub-Genre",
    "Role-Playing":         "Sub-Genre",
    "Sports":               "Sub-Genre",
    "Card & Board":         "Sub-Genre",
}
# A few tags inside mixed categories that are genuinely genres
GENRE_FROM_MIXED = {"Fighting", "2D Fighter", "3D Fighter", "Musou"}

# Flatten JSON into structured list
# Each entry: {name, top_level, category, value, is_genre, genre_level}
all_entries = []

def flatten(node, top="", cat=""):
    name = NAME_FIX.get(node.get("name", ""), node.get("name", ""))
    children = node.get("children", [])
    value = node.get("value")
    if value is not None:
        # Leaf node = actual tag
        is_genre = (cat in GENRE_CATS) or (name in GENRE_FROM_MIXED)
        genre_level = GENRE_CATS.get(cat, "Sub-Genre") if is_genre else None
        all_entries.append({
            "name": name, "top": top, "category": cat,
            "value": value, "is_genre": is_genre, "genre_level": genre_level
        })
    else:
        for child in children:
            new_top = name if not top else top
            new_cat = name if top else ""
            flatten(child, new_top if not top else top, name if top else "")

for child in flare.get("children", []):
    flatten(child, child["name"], "")

genre_entries = [e for e in all_entries if e["is_genre"]]
tag_entries   = [e for e in all_entries if not e["is_genre"]]
print(f"JSON parsed: {len(genre_entries)} genre entries, {len(tag_entries)} tag entries")

# ── POPULATE TAG_TYPE (34 SteamDB sub-categories) ─────────────────────────────
categories = sorted(set(e["category"] for e in tag_entries if e["category"]))
for c in categories:
    cur.execute("INSERT OR IGNORE INTO TAG_TYPE (tag_type_name) VALUES (?)", (c,))
conn.commit()
tag_type_map = {r[1]: r[0] for r in cur.execute("SELECT tag_type_id, tag_type_name FROM TAG_TYPE")}
print(f"TAG_TYPE: {len(categories)} categories")

# ── POPULATE GENRE ─────────────────────────────────────────────────────────────
for e in genre_entries:
    cur.execute(
        "INSERT OR IGNORE INTO GENRE (genre_name, genre_level, super_genre) VALUES (?,?,?)",
        (e["name"], e["genre_level"], e["category"])
    )
conn.commit()
genre_name_map = {r[1]: r[0] for r in cur.execute("SELECT genre_id, genre_name FROM GENRE")}
print(f"GENRE: {len(genre_entries)} entries")

# ── POPULATE TAG ───────────────────────────────────────────────────────────────
for e in tag_entries:
    tt_id = tag_type_map.get(e["category"])
    # Assign trend_value based on tag weight
    w = e["value"]
    trend = "High" if w >= 10000 else ("Medium" if w >= 2000 else "Low")
    cur.execute(
        "INSERT OR IGNORE INTO TAG (tag_name, tag_type_id, tag_weight, trend_value) VALUES (?,?,?,?)",
        (e["name"], tt_id, w, trend)
    )
conn.commit()
tag_name_map = {r[1]: r[0] for r in cur.execute("SELECT tag_id, tag_name FROM TAG")}
print(f"TAG: {len(tag_entries)} entries")

# ── POPULATE PUBLISHER ─────────────────────────────────────────────────────────
def clean_num(s):
    if not s or not s.strip():
        return None
    try:
        return float(re.sub(r"[^\d.]", "", s))
    except:
        return None

def clean_int(s):
    v = clean_num(s)
    return int(v) if v is not None else None

def clean_date(s):
    # Remove non-breaking spaces, strip
    return s.replace("\xa0", " ").strip() if s else None

# Map Budget type → operational_stat + business_maturity + service
BUDGET_MAP = {
    "High":       ("Active",   "Established", None),
    "Middle":     ("Active",   "Established", None),
    "Low":        ("Active",   "Startup",     None),
    "Startups":   ("Active",   "Startup",     None),
    "Bankrupt":   ("Bankrupt", "Legacy",      None),
    "Sub-service":("Active",   "Established", "Sub-Service"),
}

# Normalize Class column
def norm_class(s):
    s = s.strip()
    if s in ("AAA",): return "AAA"
    if s in ("AA", "AA - Indie", "AA - indie", "Indie - AA"): return "AA"
    if s in ("Indie",): return "Indie"
    if s in ("Hobbyist",): return "Hobbyist"
    return None

pub_count = 0
with open(PUB_CSV, encoding="utf-8-sig") as f:
    reader = csv.reader(f)
    header = next(reader)
    for row in reader:
        if not row or not row[1].strip():
            continue
        budget   = row[0].strip()
        name     = row[1].strip()
        country  = row[2].strip() or None
        followers= clean_int(row[4])
        games_pub= clean_int(row[5])
        fd_rel   = clean_date(row[6]) or None
        ld_rel   = clean_date(row[7]) or None
        life_rev = clean_num(row[8])
        avg_rev  = clean_num(row[9])
        p_class  = norm_class(row[11]) if len(row) > 11 else None

        op_stat, biz_mat, service = BUDGET_MAP.get(budget, ("Active", "Established", None))

        cur.execute("""
            INSERT OR IGNORE INTO PUBLISHER
            (pub_name, country, operational_stat, business_maturity, service,
             steam_followers, game_published_qty, p_class_rev,
             lifetime_rev_usd, avg_rev_usd, fd_game_release, ld_game_release)
            VALUES (?,?,?,?,?,?,?,?,?,?,?,?)
        """, (name, country, op_stat, biz_mat, service,
              followers, games_pub, p_class,
              life_rev, avg_rev, fd_rel, ld_rel))
        pub_count += 1

conn.commit()
pub_name_map = {r[1]: r[0] for r in cur.execute("SELECT pub_id, pub_name FROM PUBLISHER")}
print(f"PUBLISHER: {pub_count} rows attempted, {len(pub_name_map)} inserted")

# ── SPELLING NORMALIZATION MAP ─────────────────────────────────────────────────
# Map game CSV tag spellings -> SteamDB canonical names
NORM = {
    # Hyphenation fixes
    "Co-op":                    "Co-op",
    "Co op":                    "Co-op",
    "Online Co-Op":             "Online Co-Op",
    "Online Co-op":             "Online Co-Op",
    "Online Co Op":             "Online Co-Op",
    "Local Co-Op":              "Local Co-Op",
    "Local Co-op":              "Local Co-Op",
    "Local Co Op":              "Local Co-Op",
    "Co-op Campaign":           "Co-op Campaign",
    "Co op Campaign":           "Co-op Campaign",
    "Fast-Paced":               "Fast-Paced",
    "Fast Paced":               "Fast-Paced",
    "First-Person":             "First-Person",
    "First Person":             "First-Person",
    "Hand-drawn":               "Hand-drawn",
    "Hand drawn":               "Hand-drawn",
    "Top-Down":                 "Top-Down",
    "Top Down":                 "Top-Down",
    "Top-Down Shooter":         "Top-Down Shooter",
    "Top Down Shooter":         "Top-Down Shooter",
    "Grid-Based Movement":      "Grid-Based Movement",
    "Grid Based Movement":      "Grid-Based Movement",
    "Quick-Time Events":        "Quick-Time Events",
    "Quick Time Events":        "Quick-Time Events",
    "Lore-Rich":                "Lore-Rich",
    "Lore Rich":                "Lore-Rich",
    "Post-apocalyptic":         "Post-apocalyptic",
    "Post apocalyptic":         "Post-apocalyptic",
    "Class-Based":              "Class-Based",
    "Class Based":              "Class-Based",
    "Party-Based RPG":          "Party-Based RPG",
    "Party Based RPG":          "Party-Based RPG",
    "Sci-fi":                   "Sci-fi",
    "Sci fi":                   "Sci-fi",
    "8-bit Music":              "8-bit Music",
    "8 bit Music":              "8-bit Music",
    "Music-Based Procedural Generation": "Music-Based Procedural Generation",
    "Music Based Procedural Generation": "Music-Based Procedural Generation",
    "On-Rails Shooter":         "On-Rails Shooter",
    "On Rails Shooter":         "On-Rails Shooter",
    "Real-Time":                "Real-Time",
    "Real Time":                "Real-Time",
    "Real-Time with Pause":     "Real-Time with Pause",
    "Real Time with Pause":     "Real-Time with Pause",
    "Action-Adventure":         "Action-Adventure",
    "Action Adventure":         "Action-Adventure",
    "Souls-like":               "Souls-like",
    "Souls like":               "Souls-like",
    "Action Roguelike":         "Action Roguelike",
    # Apostrophe fixes
    "Beat em up":               "Beat ‘em up",
    "Beat Em Up":               "Beat ‘em up",
    "Shoot Em Up":              "Shoot ‘Em Up",
    # Old spellings in game CSV that differ
    "1990s":                    "1990’s",
    "1990's":                   "1990’s",
}

def resolve(tag):
    """Return canonical SteamDB tag name, or None if unresolvable."""
    tag = tag.strip()
    # Normalise curly/smart apostrophes -> straight apostrophe
    tag = tag.replace("’", "'").replace("‘", "'")
    return NORM.get(tag, tag)

# ── POPULATE GAME + JUNCTIONS ──────────────────────────────────────────────────
with open(GAMES_CSV, encoding="utf-8-sig") as f:
    game_rows = list(csv.DictReader(f))

matched_genre = matched_tag = 0
unmatched_set = set()

for row in game_rows:
    app_id   = int(row["AppID"])
    name     = row["Name"].strip()
    raw_date = row["Release_Date"].strip()
    note = None
    if raw_date == "April 2026":
        raw_date = "2026-04-01"
        note = "Release date estimated as 2026-04-01 (originally 'April 2026')"

    try:    price  = float(row["Price_USD"])
    except: price  = None
    try:    review = int(row["Review_Score_Pct"])
    except: review = None
    try:    total  = int(row["Total_Reviews"])
    except: total  = None
    try:    owners = int(re.sub(r"[^\d]", "", row["Estimated_Owners"].split("-")[0]))
    except: owners = None
    try:    peak   = int(row["24h_Peak_Players"])
    except: peak   = None

    if not row["All_Tags"].strip():
        note = (note or "") + " | No tags — excluded from tag analysis"

    cur.execute(
        "INSERT OR IGNORE INTO GAME "
        "(game_id,game_name,release_date,price_usd,review_score,total_reviews,"
        " estimated_owners,peak_players_24h,data_quality_note) "
        "VALUES (?,?,?,?,?,?,?,?,?)",
        (app_id, name, raw_date, price, review, total, owners, peak, note)
    )

    if not row["All_Tags"].strip():
        continue

    for raw_tag in row["All_Tags"].split(";"):
        tag = resolve(raw_tag)
        if not tag:
            continue
        if tag in genre_name_map:
            cur.execute("INSERT OR IGNORE INTO GAME_GENRE (game_id,genre_id) VALUES (?,?)",
                        (app_id, genre_name_map[tag]))
            matched_genre += 1
        elif tag in tag_name_map:
            cur.execute("INSERT OR IGNORE INTO GAME_TAG (game_id,tag_id) VALUES (?,?)",
                        (app_id, tag_name_map[tag]))
            matched_tag += 1
        else:
            unmatched_set.add(tag)

conn.commit()

# ── SUMMARY ────────────────────────────────────────────────────────────────────
print(f"\nGAME: {len(game_rows)} games imported")
print(f"GAME_GENRE: {matched_genre} links")
print(f"GAME_TAG:   {matched_tag} links")
print(f"Unmatched tags: {len(unmatched_set)} unique")
if unmatched_set:
    print(f"  Sample: {sorted(unmatched_set)[:15]}")

print("\n── Table row counts ──────────────────────────────────────")
for t in ["PUBLISHER","TAG_TYPE","GENRE","TAG","GAME","GAME_GENRE","GAME_TAG"]:
    n = cur.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0]
    print(f"  {t:<12} {n:>6} rows")

conn.close()

# Copy to workspace
shutil.copy(DB_TMP, DB_OUT)
print(f"\nSaved to: {DB_OUT}")
