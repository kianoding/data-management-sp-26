"""
analysis_pipeline.py
====================


What this script does (run top to bottom):
    Step 1  — Load and inspect the raw CSV datasets
    Step 2  — Extract and count all unique Steam tags
    Step 3  — Classify tags by Grelier dimension (Genre/Theme/Feature/etc.)
    Step 4  — Build the 3-level genre hierarchy (Super → Genre → Sub-Genre)
    Step 5  — Chart: top 30 tags by frequency
    Step 6  — Chart: tag dimension breakdown
    Step 7  — Chart: genre network graph (NetworkX)
    Step 8  — Chart: tag co-occurrence pairs (itertools, no NLP)
    Step 9  — Build the SQLite database (7 tables, 3NF)
    Step 10 — Compare Steam tags vs MobyGames (the "tag translation gap")
    Step 11 — Export taxonomy as CSV (reproducible output)

Libraries used (all open source):
    pandas, matplotlib, networkx, sqlite3, collections, itertools, os, re

Run:
    python analysis_pipeline.py

Outputs saved to: ./pipeline_outputs/
"""

import os
import re
import sqlite3
from collections import Counter
from itertools import combinations

import matplotlib
matplotlib.use('Agg')  # non-interactive backend — saves files without a display
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.patches import FancyBboxPatch
import networkx as nx
import pandas as pd

# ── OUTPUT FOLDER ─────────────────────────────────────────────────────────────
OUTPUT_DIR = os.path.join(os.path.dirname(__file__), 'pipeline_outputs')
os.makedirs(OUTPUT_DIR, exist_ok=True)

def save(filename):
    path = os.path.join(OUTPUT_DIR, filename)
    plt.savefig(path, dpi=150, bbox_inches='tight')
    plt.close()
    print(f"  ✓ Saved: pipeline_outputs/{filename}")
    return path


# ══════════════════════════════════════════════════════════════════════════════
# STEP 1 — LOAD RAW DATA
# ══════════════════════════════════════════════════════════════════════════════
print("\n=== Step 1: Load data ===")

BASE = os.path.dirname(__file__)

GAME_CSV = os.path.join(BASE, 'Game Dataset', 'steam_games_2026.csv')
PUB_CSV  = os.path.join(BASE, 'Publisher',
                        '628-Publisher_Data Management_Base - 02_Publisher_V02.csv')

# --- Load game dataset ---
# Each row = one game. Tags are stored as one semicolon-delimited cell.
# This is the "flat" problem: all information crammed into a single column.
df = pd.read_csv(GAME_CSV, encoding='utf-8-sig')
print(f"  Games loaded : {len(df):,} rows × {len(df.columns)} columns")
print(f"  Columns      : {list(df.columns)}")

# --- Load publisher dataset ---
# Row 0 is the header; skip it for the data read
pub_df = pd.read_csv(PUB_CSV, encoding='utf-8-sig', header=0)
print(f"  Publishers   : {len(pub_df):,} rows")

# --- Type coercion: convert numeric fields, preserve records with errors ---
# Decision: use try/except logic with None fallback rather than dropping rows.
# Rationale: losing rows silently distorts aggregate counts.
for col in ['Price_USD', 'Review_Score_Pct', 'Total_Reviews',
            'Estimated_Owners', '24h_Peak_Players']:
    df[col] = pd.to_numeric(df[col], errors='coerce')

print(f"  Missing values per column:\n{df.isnull().sum()}")


# ══════════════════════════════════════════════════════════════════════════════
# STEP 2 — EXTRACT ALL UNIQUE TAGS
# ══════════════════════════════════════════════════════════════════════════════
print("\n=== Step 2: Extract tags ===")

# Steam stores all tags for a game in one cell: "RPG;Action;Co-op"
# We split by semicolon and count each tag individually.
all_tags_flat = []
for cell in df['All_Tags'].dropna():
    for tag in str(cell).split(';'):
        t = tag.strip()
        if t:
            all_tags_flat.append(t)

tag_counts = Counter(all_tags_flat)
unique_tags = sorted(tag_counts.keys())

print(f"  Total tag mentions : {len(all_tags_flat):,}")
print(f"  Unique tags        : {len(unique_tags):,}")
print(f"  Top 10:")
for tag, count in tag_counts.most_common(10):
    print(f"    {tag:<30} {count:>5} games")


# ══════════════════════════════════════════════════════════════════════════════
# STEP 3 — CLASSIFY TAGS BY GRELIER DIMENSION
# ══════════════════════════════════════════════════════════════════════════════
print("\n=== Step 3: Classify tags (Grelier et al. 2023) ===")

# Framework: Grelier, Kaufmann & Schmalz (2023) identified that Steam tags
# span multiple NON-EQUIVALENT dimensions. Treating all tags as genres
# conflates:
#   - Genre (what the game IS mechanically)
#   - Theme (what the game DEPICTS)
#   - Feature (how the game WORKS: co-op, moddable, VR)
#   - Visual (how the game LOOKS)
#   - Tone/Mood (how the game FEELS)
#   - And more...
#
# Decision rule: a tag is a Genre only if it describes core gameplay mechanics.
# "Cyberpunk" is a Theme, not a genre — it tells you the setting, not what you do.

# ── Genre keywords (Step 1: automated regex floor) ──────────────────────────
GENRE_KEYWORDS = [
    'rpg', 'action', 'strategy', 'simulation', 'sim', 'shooter', 'platformer',
    'adventure', 'puzzle', 'racing', 'sports', 'casual', 'fighting', 'horror',
    'survival', 'mmo', 'moba', 'rts', 'fps', 'roguelike', 'roguelite',
    'metroidvania', 'soulslike', 'souls', 'deckbuilding', 'card game',
    'tower defense', 'city builder', 'visual novel', 'walking simulator',
    'dungeon', 'jrpg', 'crpg', 'hack', 'slash', 'beat em up', 'clicker',
    'idle', 'runner', 'rhythm', 'sandbox', 'open world', 'grand strategy',
    'auto battler', '4x', 'tactical', 'point & click', 'escape room',
    'battle royale', 'extraction', 'looter', 'bullet hell', 'shoot em up',
    'twin stick', 'arena', 'hero shooter', 'minigame', 'party game',
    'board game', 'word game', 'mahjong', 'solitaire', 'match 3',
    'hidden object', 'sokoban', 'physics', 'logic', 'narrative',
    'kart', 'combat racing', 'arcade racing', 'flight', 'driving',
    'baseball', 'basketball', 'boxing', 'bowling', 'cricket', 'football',
    'golf', 'hockey', 'tennis', 'volleyball', 'wrestling', 'rugby',
    'skateboarding', 'skiing', 'snowboarding', 'bmx', 'cycling',
    'farming sim', 'cooking', 'fishing', 'life sim', 'dating sim',
    'god game', 'political sim', 'medical', 'hobby sim', 'sports sim',
]

# ── Non-genre dimension maps ─────────────────────────────────────────────────
THEME_TAGS = {
    'Cyberpunk', 'Post-apocalyptic', 'Steampunk', 'Zombies', 'Anime', 'Gothic',
    'Mythology', 'Space', 'Fantasy', 'Sci-fi', 'Western', 'Medieval', 'Military',
    'Pirates', 'Lovecraftian', 'Ninja', 'Samurai', 'Viking', 'Cats', 'Dogs',
    'Dinosaurs', 'Dragons', 'Demons', 'Aliens', 'Robots', 'Vampire',
    'Supernatural', 'Psychological', 'Dark Fantasy', 'Dystopian', 'Historical',
    'Cold War', 'World War II', '1980s', 'Retro', 'Futuristic', 'Underwater',
    'Space Opera', 'Noir', 'Political', 'Heist', 'Mafia', 'Crime', 'Nature',
    'Cozy', 'Wholesome', 'Cute', 'Colorful', 'Dark', 'Horror', 'Atmospheric',
    'Surreal', 'Abstract', 'Experimental', 'Supernatural', 'Mythology',
    'Post-apocalyptic', 'Urban', 'Rural', 'Tropical', 'Arctic',
}

FEATURE_TAGS = {
    'Multiplayer', 'Singleplayer', 'Co-op', 'Online Co-op', 'Local Co-op',
    'PvP', 'PvE', 'Asynchronous Multiplayer', 'Split Screen', 'Cross-Platform',
    'Controller Support', 'Keyboard Only', 'Touch', 'Moddable', 'Level Editor',
    'Procedural Generation', 'Permadeath', 'Crafting', 'Building', 'Trading',
    'Steam Workshop', 'Steam Achievements', 'Steam Cloud', 'Steam Trading Cards',
    'Early Access', 'Free to Play', 'Kickstarter', 'Game Dev', 'Utilities',
    'Education', 'Tutorial', 'Commentary', 'Replay Value', 'Short', 'Long',
    '4-Player Local', 'MMO', 'Massively Multiplayer',
}

VISUAL_TAGS = {
    '2D', '3D', 'Pixel Art', 'Low Poly', 'Hand-drawn', 'Cartoon', 'Realistic',
    'Stylized', 'Top-Down', 'Side Scroller', 'First-Person', 'Third Person',
    'Isometric', 'Point & Click', 'Anime', 'Cel Shading', 'Voxel',
    'Psychedelic', 'Minimalist', 'Retro', 'Noir',
}

MOOD_TAGS = {
    'Relaxing', 'Atmospheric', 'Dark', 'Funny', 'Wholesome', 'Cute', 'Cozy',
    'Intense', 'Emotional', 'Difficult', 'Addictive', 'Masterpiece', 'Epic',
    'Cinematic', 'Immersive', 'Thought-Provoking', 'Violent', 'Gore', 'Nudity',
    'Sexual Content', 'NSFW', 'Family Friendly',
}

TIME_TAGS = {
    'Retro', '1980s', '1990s', '2000s', 'Cold War', 'World War II',
    'Medieval', 'Ancient', 'Modern', 'Futuristic',
}

HARDWARE_TAGS = {
    'VR', 'Oculus Rift', 'HTC Vive', 'Mixed Reality', 'Trackball',
    'Touch', 'Gamepad', 'Controller', 'Steam Deck', 'HMD Required',
}

def classify_tag(tag):
    """
    Assign a Grelier dimension to a single tag.
    Priority: Genre > Theme > Feature > Visual > Mood > Time > Hardware > Other
    Decision documented for reproducibility.
    """
    tag_lower = tag.lower()

    # Check genre by keyword match
    for kw in GENRE_KEYWORDS:
        if kw in tag_lower:
            return 'Genre'

    # Check explicit non-genre sets (order matters)
    if tag in VISUAL_TAGS:
        return 'Visual'
    if tag in HARDWARE_TAGS:
        return 'Hardware'
    if tag in FEATURE_TAGS:
        return 'Feature'
    if tag in MOOD_TAGS:
        return 'Tone / Mood'
    if tag in TIME_TAGS:
        return 'Time Period'
    if tag in THEME_TAGS:
        return 'Theme'

    return 'Other'

# Apply classification to every unique tag
tag_df = pd.DataFrame({'tag': unique_tags})
tag_df['dimension'] = tag_df['tag'].apply(classify_tag)
tag_df['frequency'] = tag_df['tag'].apply(lambda t: tag_counts.get(t, 0))

# Summary
dim_summary = tag_df['dimension'].value_counts()
print(f"\n  Dimension breakdown:")
for dim, cnt in dim_summary.items():
    print(f"    {dim:<20} {cnt:>4} tags")


# ══════════════════════════════════════════════════════════════════════════════
# STEP 4 — GENRE HIERARCHY (3-level taxonomy)
# ══════════════════════════════════════════════════════════════════════════════
print("\n=== Step 4: Build genre hierarchy ===")

# Structure: Super-Genre → Genre → Sub-Genre
# Based on Grelier et al. (2023) + manual classification decisions
# Edge cases documented in comments.

HIERARCHY = [
    # (child, parent, level)
    # ── ACTION ──────────────────────────────────────────────────────────────
    ('ACTION',              None,            'Super-Genre'),
    ('Shooter',             'ACTION',        'Genre'),
    ('FPS',                 'Shooter',       'Sub-Genre'),
    ('Third-Person Shooter','Shooter',       'Sub-Genre'),
    ('Top-Down Shooter',    'Shooter',       'Sub-Genre'),
    ('Twin Stick Shooter',  'Shooter',       'Sub-Genre'),
    ('Arena Shooter',       'Shooter',       'Sub-Genre'),
    ('Hero Shooter',        'Shooter',       'Sub-Genre'),
    ('Looter Shooter',      'Shooter',       'Sub-Genre'),
    ('Bullet Hell',         'Shooter',       'Sub-Genre'),
    ('Shoot Em Up',         'Shooter',       'Sub-Genre'),
    ('Tactical Shooter',    'Shooter',       'Sub-Genre'),
    ('Extraction Shooter',  'Shooter',       'Sub-Genre'),
    ('Battle Royale',       'Shooter',       'Sub-Genre'),
    ('Fighting',            'ACTION',        'Genre'),
    ('2D Fighter',          'Fighting',      'Sub-Genre'),
    ('3D Fighter',          'Fighting',      'Sub-Genre'),
    ('Platformer',          'ACTION',        'Genre'),
    ('2D Platformer',       'Platformer',    'Sub-Genre'),
    ('3D Platformer',       'Platformer',    'Sub-Genre'),
    ('Precision Platformer','Platformer',    'Sub-Genre'),
    ('Beat Em Up',          'ACTION',        'Genre'),
    ('Character Action Game','ACTION',       'Genre'),
    ('Hack and Slash',      'ACTION',        'Genre'),
    ('Soulslike',           'ACTION',        'Genre'),
    ('Spectacle Fighter',   'ACTION',        'Genre'),
    ('Musou',               'ACTION',        'Genre'),
    ('Roguelike',           'ACTION',        'Genre'),
    ('Roguelite',           'ACTION',        'Genre'),

    # ── RPG ─────────────────────────────────────────────────────────────────
    # Edge case: Action RPG → assigned to RPG.
    # Rationale: character progression (RPG mechanic) dominates over combat style.
    ('RPG',                 None,            'Super-Genre'),
    ('JRPG',                'RPG',           'Sub-Genre'),
    ('CRPG',                'RPG',           'Sub-Genre'),
    ('MMORPG',              'RPG',           'Sub-Genre'),
    ('Action RPG',          'RPG',           'Sub-Genre'),
    ('Tactical RPG',        'RPG',           'Sub-Genre'),
    ('Turn-Based RPG',      'RPG',           'Sub-Genre'),
    ('Party Based RPG',     'RPG',           'Sub-Genre'),
    ('Roguelike RPG',       'RPG',           'Sub-Genre'),
    ('Dungeon Crawler',     'RPG',           'Genre'),
    ('Creature Collector',  'RPG',           'Genre'),

    # ── STRATEGY ────────────────────────────────────────────────────────────
    ('STRATEGY',            None,            'Super-Genre'),
    ('Turn-Based Strategy', 'STRATEGY',      'Genre'),
    ('Turn Based Tactics',  'Turn-Based Strategy', 'Sub-Genre'),
    ('Turn Based Combat',   'Turn-Based Strategy', 'Sub-Genre'),
    ('Real Time Strategy',  'STRATEGY',      'Genre'),
    ('Action RTS',          'Real Time Strategy',  'Sub-Genre'),
    ('Real Time Tactics',   'Real Time Strategy',  'Sub-Genre'),
    ('MOBA',                'Real Time Strategy',  'Sub-Genre'),
    ('Tactical',            'STRATEGY',      'Genre'),
    ('Tower Defense',       'STRATEGY',      'Genre'),
    ('City Builder',        'STRATEGY',      'Genre'),
    ('Grand Strategy',      'STRATEGY',      'Genre'),
    ('Auto Battler',        'STRATEGY',      'Genre'),
    ('4X',                  'STRATEGY',      'Genre'),

    # ── ADVENTURE ───────────────────────────────────────────────────────────
    ('ADVENTURE',           None,            'Super-Genre'),
    ('Point & Click',       'ADVENTURE',     'Genre'),
    ('Visual Novel',        'ADVENTURE',     'Genre'),
    ('Walking Simulator',   'ADVENTURE',     'Genre'),
    ('Metroidvania',        'ADVENTURE',     'Genre'),
    ('Choose Your Own Adventure', 'ADVENTURE', 'Genre'),
    ('Escape Room',         'ADVENTURE',     'Genre'),
    ('FMV',                 'ADVENTURE',     'Genre'),
    ('Text Based',          'ADVENTURE',     'Genre'),
    ('Action Adventure',    'ADVENTURE',     'Sub-Genre'),
    ('Roguevania',          'ADVENTURE',     'Sub-Genre'),
    ('Interactive Fiction', 'ADVENTURE',     'Genre'),

    # ── SIMULATION ──────────────────────────────────────────────────────────
    # Edge case: Survival → NOT included as Genre.
    # Rationale: Grelier et al. classify Survival as Theme (describes setting, not mechanic).
    ('SIMULATION',          None,            'Super-Genre'),
    ('Flight Sim',          'SIMULATION',    'Genre'),
    ('Driving Sim',         'SIMULATION',    'Genre'),
    ('Automobile Sim',      'Driving Sim',   'Sub-Genre'),
    ('Life Sim',            'SIMULATION',    'Genre'),
    ('Farming Sim',         'SIMULATION',    'Genre'),
    ('Cooking',             'Farming Sim',   'Sub-Genre'),
    ('Fishing',             'Farming Sim',   'Sub-Genre'),
    ('Sports Sim',          'SIMULATION',    'Genre'),
    ('God Game',            'SIMULATION',    'Genre'),
    ('Dating Sim',          'SIMULATION',    'Genre'),
    ('Medical Sim',         'SIMULATION',    'Genre'),
    ('Political Sim',       'SIMULATION',    'Genre'),
    ('Colony Sim',          'SIMULATION',    'Genre'),
    ('Space Sim',           'SIMULATION',    'Genre'),

    # ── PUZZLE ──────────────────────────────────────────────────────────────
    # Edge case: Puzzle Platformer → assigned to Puzzle.
    # Rationale: puzzle-solving is the primary mechanic, platforming is secondary.
    ('PUZZLE',              None,            'Super-Genre'),
    ('Hidden Object',       'PUZZLE',        'Genre'),
    ('Match 3',             'PUZZLE',        'Genre'),
    ('Logic Puzzle',        'PUZZLE',        'Genre'),
    ('Physics Puzzle',      'PUZZLE',        'Genre'),
    ('Mahjong',             'PUZZLE',        'Genre'),
    ('Solitaire',           'PUZZLE',        'Genre'),
    ('Sokoban',             'PUZZLE',        'Genre'),
    ('Word Game',           'PUZZLE',        'Genre'),
    ('Tile Matching',       'PUZZLE',        'Genre'),
    ('Puzzle Platformer',   'PUZZLE',        'Genre'),

    # ── RACING ──────────────────────────────────────────────────────────────
    ('RACING',              None,            'Super-Genre'),
    ('Kart Racing',         'RACING',        'Genre'),
    ('Combat Racing',       'RACING',        'Genre'),
    ('Arcade Racing',       'RACING',        'Genre'),

    # ── SPORTS ──────────────────────────────────────────────────────────────
    ('SPORTS',              None,            'Super-Genre'),
    ('Baseball',            'SPORTS',        'Genre'),
    ('Basketball',          'SPORTS',        'Genre'),
    ('Boxing',              'SPORTS',        'Genre'),
    ('Bowling',             'SPORTS',        'Genre'),
    ('Cricket',             'SPORTS',        'Genre'),
    ('Football',            'SPORTS',        'Genre'),
    ('Golf',                'SPORTS',        'Genre'),
    ('Hockey',              'SPORTS',        'Genre'),
    ('Tennis',              'SPORTS',        'Genre'),
    ('Volleyball',          'SPORTS',        'Genre'),
    ('Wrestling',           'SPORTS',        'Genre'),
    ('Rugby',               'SPORTS',        'Genre'),
    ('Skateboarding',       'SPORTS',        'Genre'),

    # ── CASUAL ──────────────────────────────────────────────────────────────
    ('CASUAL',              None,            'Super-Genre'),
    ('Card Game',           'CASUAL',        'Genre'),
    ('Deckbuilding',        'Card Game',     'Sub-Genre'),
    ('Card Battler',        'Card Game',     'Sub-Genre'),
    ('Roguelike Deckbuilder','Card Game',    'Sub-Genre'),
    ('Board Game',          'CASUAL',        'Genre'),
    ('Party Game',          'CASUAL',        'Genre'),
    ('Rhythm',              'CASUAL',        'Genre'),
    ('Clicker',             'CASUAL',        'Genre'),
    ('Idler',               'CASUAL',        'Genre'),
    ('Runner',              'CASUAL',        'Genre'),
    ('Minigames',           'CASUAL',        'Genre'),
    ('Narrative',           'CASUAL',        'Genre'),
    ('Arcade',              'CASUAL',        'Sub-Genre'),
]

hierarchy_df = pd.DataFrame(HIERARCHY, columns=['name', 'parent', 'level'])
super_count  = len(hierarchy_df[hierarchy_df['level'] == 'Super-Genre'])
genre_count  = len(hierarchy_df[hierarchy_df['level'] == 'Genre'])
sub_count    = len(hierarchy_df[hierarchy_df['level'] == 'Sub-Genre'])
print(f"  Super-Genres : {super_count}")
print(f"  Genres       : {genre_count}")
print(f"  Sub-Genres   : {sub_count}")
print(f"  Total        : {len(hierarchy_df)} hierarchical entries")


# ══════════════════════════════════════════════════════════════════════════════
# STEP 5 — CHART: TOP 30 TAGS
# ══════════════════════════════════════════════════════════════════════════════
print("\n=== Step 5: Chart — Top 30 tags ===")

top30       = tag_counts.most_common(30)
labels      = [t[0] for t in top30][::-1]
values      = [t[1] for t in top30][::-1]

fig, ax = plt.subplots(figsize=(12, 8), facecolor='#F8F9FA')
ax.set_facecolor('#F8F9FA')
bars = ax.barh(labels, values, color='#2E75B6', edgecolor='white', height=0.7)
for bar, val in zip(bars, values):
    ax.text(bar.get_width() + 3, bar.get_y() + bar.get_height() / 2,
            str(val), va='center', fontsize=8, color='#1F4E79')
ax.set_xlabel('Number of games tagged', fontsize=10)
ax.set_title('Top 30 Most-Used Steam Tags (Top 1,000 Games)', fontsize=13,
             fontweight='bold', color='#1F4E79', pad=14)
ax.spines[['top', 'right']].set_visible(False)
plt.tight_layout()
save('01_top30_tags.png')


# ══════════════════════════════════════════════════════════════════════════════
# STEP 6 — CHART: DIMENSION BREAKDOWN
# ══════════════════════════════════════════════════════════════════════════════
print("\n=== Step 6: Chart — Dimension breakdown ===")

dim_counts  = tag_df['dimension'].value_counts()
colors      = ['#1F4E79', '#2E75B6', '#4BACC6', '#F4A261', '#E76F51',
               '#2A9D8F', '#264653', '#E9C46A', '#95A5A6']

fig, axes = plt.subplots(1, 2, figsize=(14, 5), facecolor='#F8F9FA')

# Bar chart
ax = axes[0]
ax.set_facecolor('#F8F9FA')
bars = ax.barh(dim_counts.index, dim_counts.values,
               color=colors[:len(dim_counts)], edgecolor='white', height=0.6)
for bar, val in zip(bars, dim_counts.values):
    ax.text(bar.get_width() + 0.5, bar.get_y() + bar.get_height() / 2,
            str(val), va='center', fontsize=10, color='#1F4E79', fontweight='bold')
ax.set_xlabel('Unique tags', fontsize=10)
ax.set_title('Tags per Grelier Dimension', fontsize=12,
             fontweight='bold', color='#1F4E79')
ax.spines[['top', 'right']].set_visible(False)

# Pie chart
ax2 = axes[1]
ax2.set_facecolor('#F8F9FA')
wedges, texts, autotexts = ax2.pie(
    dim_counts.values,
    labels=dim_counts.index,
    autopct='%1.1f%%',
    colors=colors[:len(dim_counts)],
    startangle=140,
    pctdistance=0.8,
    textprops={'fontsize': 8}
)
ax2.set_title('Proportion of Tag Types', fontsize=12,
              fontweight='bold', color='#1F4E79')

plt.suptitle('Steam Tags Are NOT Mostly Genres\n(Grelier et al. 2023 framework applied)',
             fontsize=13, fontweight='bold', color='#1F4E79', y=1.02)
plt.tight_layout()
save('02_dimension_breakdown.png')


# ══════════════════════════════════════════════════════════════════════════════
# STEP 7 — GENRE NETWORK GRAPH
# ══════════════════════════════════════════════════════════════════════════════
print("\n=== Step 7: Genre network graph ===")

G = nx.DiGraph()

# Add nodes with attributes
for _, row in hierarchy_df.iterrows():
    freq = tag_counts.get(row['name'], 50)  # fallback size if tag not in dataset
    G.add_node(row['name'], level=row['level'], freq=freq)

# Add edges (parent → child)
for _, row in hierarchy_df.iterrows():
    if row['parent'] is not None:
        G.add_edge(row['parent'], row['name'])

# Layout: separate super-genres at top, genres in middle, sub-genres at bottom
super_nodes = [n for n, d in G.nodes(data=True) if d['level'] == 'Super-Genre']
genre_nodes  = [n for n, d in G.nodes(data=True) if d['level'] == 'Genre']
sub_nodes    = [n for n, d in G.nodes(data=True) if d['level'] == 'Sub-Genre']

pos = {}
for i, n in enumerate(super_nodes):
    pos[n] = (i * 2.5, 2)
for i, n in enumerate(genre_nodes):
    pos[n] = (i * 0.7, 1)
for i, n in enumerate(sub_nodes):
    pos[n] = (i * 0.5, 0)

node_colors = {
    'Super-Genre': '#1F4E79',
    'Genre':       '#2E75B6',
    'Sub-Genre':   '#A9D0E8',
}
colors_list  = [node_colors[G.nodes[n]['level']] for n in G.nodes()]
sizes_list   = [max(200, min(2000, G.nodes[n].get('freq', 100) * 5)) for n in G.nodes()]

fig, ax = plt.subplots(figsize=(20, 10), facecolor='#F0F4F8')
ax.set_facecolor('#F0F4F8')
nx.draw_networkx(G, pos=pos, ax=ax,
                 node_color=colors_list,
                 node_size=sizes_list,
                 font_size=6,
                 font_color='white',
                 edge_color='#AAAAAA',
                 arrows=True,
                 arrowsize=10)

legend_elements = [
    mpatches.Patch(color='#1F4E79', label='Super-Genre'),
    mpatches.Patch(color='#2E75B6', label='Genre'),
    mpatches.Patch(color='#A9D0E8', label='Sub-Genre'),
]
ax.legend(handles=legend_elements, loc='upper right', fontsize=9)
ax.set_title('Steam Genre Taxonomy — Network Graph\n(node size = frequency in dataset)',
             fontsize=13, fontweight='bold', color='#1F4E79', pad=12)
ax.axis('off')
plt.tight_layout()
save('03_genre_network.png')

# Degree centrality — which genres are the structural hubs?
centrality = nx.degree_centrality(G)
ranked_centrality = sorted(centrality.items(), key=lambda x: x[1], reverse=True)[:15]
print("  Top 10 genre hubs by degree centrality:")
for name, score in ranked_centrality[:10]:
    print(f"    {name:<30} {score:.3f}")


# ══════════════════════════════════════════════════════════════════════════════
# STEP 8 — TAG CO-OCCURRENCE (no NLP — just pair counting)
# ══════════════════════════════════════════════════════════════════════════════
print("\n=== Step 8: Tag co-occurrence ===")

# Co-occurrence: two tags co-occur when they appear on the same game.
# Calculated with itertools.combinations — no NLTK, no spaCy, no AI.
# This reveals which genre combinations are most common in the top 1,000 games.

co_pairs = Counter()
for tags_str in df['All_Tags'].dropna():
    game_tags = [t.strip() for t in str(tags_str).split(';') if t.strip()]
    for a, b in combinations(sorted(set(game_tags)), 2):
        co_pairs[(a, b)] += 1

print(f"  Total unique tag pairs: {len(co_pairs):,}")

top_pairs   = co_pairs.most_common(15)
pair_labels = [f"{a} + {b}" for (a, b), _ in top_pairs][::-1]
pair_values = [c for _, c in top_pairs][::-1]

fig, ax = plt.subplots(figsize=(12, 7), facecolor='#F8F9FA')
ax.set_facecolor('#F8F9FA')
bars = ax.barh(pair_labels, pair_values, color='#2E75B6', edgecolor='white', height=0.65)
for bar, val in zip(bars, pair_values):
    ax.text(bar.get_width() + 1, bar.get_y() + bar.get_height() / 2,
            str(val), va='center', fontsize=8, color='#1F4E79')
ax.set_xlabel('Number of games where both tags appear together', fontsize=10)
ax.set_title('Top 15 Co-occurring Tag Pairs\n(calculated with itertools.combinations — no NLP)',
             fontsize=12, fontweight='bold', color='#1F4E79', pad=12)
ax.spines[['top', 'right']].set_visible(False)
plt.tight_layout()
save('04_cooccurrence_pairs.png')


# ══════════════════════════════════════════════════════════════════════════════
# STEP 9 — BUILD SQLITE DATABASE (7 tables, 3NF)
# ══════════════════════════════════════════════════════════════════════════════
print("\n=== Step 9: Build SQLite database ===")

import shutil, tempfile

DB_PATH = os.path.join(OUTPUT_DIR, 'steam_fair_pipeline.db')
# Build in /tmp first (SQLite needs proper file-locking support),
# then copy the finished file to the output folder.
TMP_DB = os.path.join(tempfile.gettempdir(), 'steam_fair_pipeline_tmp.db')
if os.path.exists(TMP_DB):
    os.remove(TMP_DB)

conn = sqlite3.connect(TMP_DB)
cur  = conn.cursor()

# ── Schema: normalized to 3NF ────────────────────────────────────────────────
# Every tag dimension is a separate entity.
# Junction tables resolve many-to-many relationships (one game, many tags).
cur.executescript("""
PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS TAG_TYPE (
    type_id   INTEGER PRIMARY KEY AUTOINCREMENT,
    type_name TEXT    NOT NULL UNIQUE
);

CREATE TABLE IF NOT EXISTS TAG (
    tag_id    INTEGER PRIMARY KEY AUTOINCREMENT,
    tag_name  TEXT    NOT NULL UNIQUE,
    type_id   INTEGER REFERENCES TAG_TYPE(type_id),
    frequency INTEGER DEFAULT 0
);

CREATE TABLE IF NOT EXISTS GENRE (
    genre_id       INTEGER PRIMARY KEY AUTOINCREMENT,
    genre_name     TEXT    NOT NULL UNIQUE,
    genre_level    TEXT    CHECK(genre_level IN ('Super-Genre','Genre','Sub-Genre')),
    parent_genre_id INTEGER REFERENCES GENRE(genre_id)
);

CREATE TABLE IF NOT EXISTS PUBLISHER (
    publisher_id INTEGER PRIMARY KEY AUTOINCREMENT,
    name         TEXT    NOT NULL,
    market_tier  TEXT,
    country      TEXT
);

CREATE TABLE IF NOT EXISTS GAME (
    app_id           INTEGER PRIMARY KEY,
    name             TEXT,
    release_date     TEXT,
    price_usd        REAL,
    review_score_pct REAL,
    total_reviews    INTEGER,
    estimated_owners INTEGER,
    peak_players_24h INTEGER,
    primary_genre    TEXT,
    steam_deck_status TEXT,
    publisher_id     INTEGER REFERENCES PUBLISHER(publisher_id)
);

CREATE TABLE IF NOT EXISTS GAME_TAG (
    game_id INTEGER REFERENCES GAME(app_id),
    tag_id  INTEGER REFERENCES TAG(tag_id),
    PRIMARY KEY (game_id, tag_id)
);

CREATE TABLE IF NOT EXISTS GAME_GENRE (
    game_id  INTEGER REFERENCES GAME(app_id),
    genre_id INTEGER REFERENCES GENRE(genre_id),
    PRIMARY KEY (game_id, genre_id)
);
""")

# ── Populate TAG_TYPE ────────────────────────────────────────────────────────
for dim in tag_df['dimension'].unique():
    cur.execute("INSERT OR IGNORE INTO TAG_TYPE (type_name) VALUES (?)", (dim,))

type_map = {row[1]: row[0] for row in cur.execute("SELECT * FROM TAG_TYPE").fetchall()}

# ── Populate TAG ─────────────────────────────────────────────────────────────
for _, row in tag_df.iterrows():
    cur.execute(
        "INSERT OR IGNORE INTO TAG (tag_name, type_id, frequency) VALUES (?,?,?)",
        (row['tag'], type_map[row['dimension']], int(row['frequency']))
    )

tag_id_map = {row[1]: row[0] for row in cur.execute("SELECT tag_id, tag_name FROM TAG").fetchall()}

# ── Populate GENRE (self-referencing hierarchy) ──────────────────────────────
# Insert super-genres first, then genres, then sub-genres (order matters for FK)
for level in ['Super-Genre', 'Genre', 'Sub-Genre']:
    for _, row in hierarchy_df[hierarchy_df['level'] == level].iterrows():
        parent_id = None
        if row['parent']:
            result = cur.execute(
                "SELECT genre_id FROM GENRE WHERE genre_name=?", (row['parent'],)
            ).fetchone()
            parent_id = result[0] if result else None
        cur.execute(
            "INSERT OR IGNORE INTO GENRE (genre_name, genre_level, parent_genre_id) VALUES (?,?,?)",
            (row['name'], level, parent_id)
        )

genre_id_map = {row[1]: row[0] for row in cur.execute("SELECT genre_id, genre_name FROM GENRE").fetchall()}

# ── Populate PUBLISHER ───────────────────────────────────────────────────────
for _, row in pub_df.dropna(subset=['Publisher']).iterrows():
    cur.execute(
        "INSERT INTO PUBLISHER (name, market_tier, country) VALUES (?,?,?)",
        (str(row.get('Publisher', '')).strip(),
         str(row.get('Class', '')).strip(),
         str(row.get('Country', '')).strip())
    )

pub_name_map = {
    row[1].strip().lower(): row[0]
    for row in cur.execute("SELECT publisher_id, name FROM PUBLISHER").fetchall()
}

# ── Populate GAME + GAME_TAG + GAME_GENRE ────────────────────────────────────
for _, row in df.iterrows():
    try:
        app_id = int(row['AppID'])
    except (ValueError, TypeError):
        continue

    cur.execute("""
        INSERT OR IGNORE INTO GAME
        (app_id, name, release_date, price_usd, review_score_pct,
         total_reviews, estimated_owners, peak_players_24h, primary_genre, steam_deck_status)
        VALUES (?,?,?,?,?,?,?,?,?,?)
    """, (
        app_id,
        str(row.get('Name', '')),
        str(row.get('Release_Date', '')),
        row.get('Price_USD'),
        row.get('Review_Score_Pct'),
        row.get('Total_Reviews'),
        row.get('Estimated_Owners'),
        row.get('24h_Peak_Players'),
        str(row.get('Primary_Genre', '')),
        str(row.get('Steam_Deck_Status', ''))
    ))

    # Insert GAME_TAG rows
    for tag in str(row.get('All_Tags', '')).split(';'):
        tag = tag.strip()
        if tag and tag in tag_id_map:
            cur.execute(
                "INSERT OR IGNORE INTO GAME_TAG (game_id, tag_id) VALUES (?,?)",
                (app_id, tag_id_map[tag])
            )

    # Insert GAME_GENRE rows — match game tags against genre hierarchy names
    for tag in str(row.get('All_Tags', '')).split(';'):
        tag = tag.strip()
        if tag in genre_id_map:
            cur.execute(
                "INSERT OR IGNORE INTO GAME_GENRE (game_id, genre_id) VALUES (?,?)",
                (app_id, genre_id_map[tag])
            )

conn.commit()

# ── Row counts ───────────────────────────────────────────────────────────────
for table in ['TAG_TYPE', 'TAG', 'GENRE', 'PUBLISHER', 'GAME', 'GAME_TAG', 'GAME_GENRE']:
    count = cur.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
    print(f"  {table:<15} {count:>6} rows")

conn.close()
shutil.copy2(TMP_DB, DB_PATH)
os.remove(TMP_DB)
print(f"  ✓ Database saved: pipeline_outputs/steam_fair_pipeline.db")


# ══════════════════════════════════════════════════════════════════════════════
# STEP 10 — TAG TRANSLATION GAP: Steam vs MobyGames
# ══════════════════════════════════════════════════════════════════════════════
print("\n=== Step 10: Tag translation gap ===")

# MobyGames is a library-style classification system (top-down, editorial control).
# Steam is a folksonomy (bottom-up, community voting).
# The question: how much vocabulary do they share?

# Sample of MobyGames genre terms (from manual crosswalk — Genre StudyCase CSVs)
MOBYGAMES_GENRES = {
    'Action', 'Adventure', 'RPG', 'Strategy', 'Simulation', 'Puzzle',
    'Racing', 'Sports', 'Fighting', 'Platformer', 'Shooter', 'Horror',
    'Survival', 'Stealth', 'Open World', 'Sandbox', 'MMORPG', 'MOBA',
    'RTS', 'Turn-Based', 'City Builder', 'Tower Defense', 'Roguelike',
    'Metroidvania', 'Visual Novel', 'Point & Click', 'Walking Simulator',
    'Casual', 'Idle', 'Clicker', 'Card Game', 'Board Game', 'Party Game',
    'Rhythm', 'Music', 'Educational', 'Trivia', 'Word Game',
    'Hidden Object', 'Match 3', 'Mahjong', 'Solitaire',
    'Flight Sim', 'Driving Sim', 'Sports Sim', 'Life Sim', 'Dating Sim',
    'God Game', 'Grand Strategy', 'Wargame', 'Tactical RPG', 'JRPG',
    'Dungeon Crawler', 'Hack and Slash', 'Beat Em Up', 'Bullet Hell',
    'FPS', 'Third-Person Shooter', 'Top-Down Shooter', 'Twin Stick Shooter',
    'Battle Royale', 'Extraction', 'Cooperative', 'Competitive',
    'Narrative', 'Interactive Fiction', 'Escape Room', 'Detective',
    'Steampunk', 'Cyberpunk', 'Fantasy', 'Sci-fi', 'Historical',
    'Anime', 'Pixel Art', 'Retro', '2D', '3D',
    'Multiplayer', 'Singleplayer', 'Local Co-op', 'Online Co-op',
    'Free to Play', 'Early Access',
    'Indie', 'AAA', 'Arcade', 'VR', 'Mobile', 'Puzzle Platformer',
    'Roguelite', 'Deckbuilding', 'Auto Battler', 'Soulslike',
    'Colony Sim', 'Space Sim', 'Farming Sim', 'Cooking', 'Fishing',
}

steam_set   = set(unique_tags)
mobygames_set = MOBYGAMES_GENRES
shared      = steam_set & mobygames_set
steam_only  = steam_set - mobygames_set
mg_only     = mobygames_set - steam_set

print(f"  Steam unique tags         : {len(steam_set):>4}")
print(f"  MobyGames genre terms     : {len(mobygames_set):>4}")
print(f"  Shared between both       : {len(shared):>4}")
print(f"  Steam-only (no MobyGames) : {len(steam_only):>4}")
print(f"  MobyGames-only            : {len(mg_only):>4}")
print(f"\n  Steam-exclusive examples (community language not in controlled vocab):")
for tag in sorted(steam_only)[:20]:
    print(f"    {tag}")

# Bar chart of the gap
fig, ax = plt.subplots(figsize=(9, 5), facecolor='#F8F9FA')
ax.set_facecolor('#F8F9FA')
categories = ['Shared\nbetween both', 'Steam-only\n(no MobyGames)', 'MobyGames-only\n(no Steam)']
counts     = [len(shared), len(steam_only), len(mg_only)]
bar_colors = ['#2A9D8F', '#E76F51', '#2E75B6']
bars = ax.bar(categories, counts, color=bar_colors, edgecolor='white', linewidth=1.5, width=0.5)
for bar, val in zip(bars, counts):
    ax.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + 2,
            str(val), ha='center', fontsize=12, fontweight='bold', color='#1F4E79')
ax.set_title('The Tag Translation Gap: Steam vs MobyGames\n'
             'Only a minority of terms are shared between both systems',
             fontsize=12, fontweight='bold', color='#1F4E79', pad=12)
ax.set_ylabel('Number of terms', fontsize=10)
ax.spines[['top', 'right']].set_visible(False)
plt.tight_layout()
save('05_tag_translation_gap.png')


# ══════════════════════════════════════════════════════════════════════════════
# STEP 11 — EXPORT TAXONOMY CSV
# ══════════════════════════════════════════════════════════════════════════════
print("\n=== Step 11: Export taxonomy CSV ===")

taxonomy_out = os.path.join(OUTPUT_DIR, 'steam_taxonomy_export.csv')
tag_df.to_csv(taxonomy_out, index=False, encoding='utf-8-sig')
print(f"  ✓ Exported: pipeline_outputs/steam_taxonomy_export.csv ({len(tag_df)} rows)")

hierarchy_out = os.path.join(OUTPUT_DIR, 'genre_hierarchy_export.csv')
hierarchy_df.to_csv(hierarchy_out, index=False, encoding='utf-8-sig')
print(f"  ✓ Exported: pipeline_outputs/genre_hierarchy_export.csv ({len(hierarchy_df)} rows)")


# ══════════════════════════════════════════════════════════════════════════════
# DONE
# ══════════════════════════════════════════════════════════════════════════════
print("""
╔══════════════════════════════════════════════════════════════╗
║  Pipeline complete. Outputs saved to: ./pipeline_outputs/    ║
║                                                              ║
║  01_top30_tags.png          — Most-used tags                 ║
║  02_dimension_breakdown.png — Grelier dimension split        ║
║  03_genre_network.png       — Genre hierarchy network        ║
║  04_cooccurrence_pairs.png  — Co-occurring tag pairs         ║
║  05_tag_translation_gap.png — Steam vs MobyGames gap         ║
║  steam_fair_pipeline.db     — SQLite database (7 tables)     ║
║  steam_taxonomy_export.csv  — All tags with dimension labels ║
║  genre_hierarchy_export.csv — Genre hierarchy (3 levels)     ║
╚══════════════════════════════════════════════════════════════╝

Libraries used: pandas, matplotlib, networkx, sqlite3,
                collections, itertools  (all open source)

Reference: Grelier, N., Kaufmann, S., & Schmalz, M. (2023).
           Data-driven classifications of video game vocabulary.
           arXiv:2303.07179
""")
