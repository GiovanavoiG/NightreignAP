"""
Static game data for Elden Ring: Nightreign (base game + The Forsaken Hollows DLC, Dec 2025).

Nightreign is a roguelite: nothing persists between expeditions except *meta* progression, so this
world randomizes meta progression only. Checks are "first time you do X" events that the game
already tracks with event flags (Nightlord kills, night-boss kills, Remembrance chapters, vessel
purchases, character unlocks, Shifting Earth clears). Items are the meta unlocks that gate those
events (Nightfarers, expedition access, Shifting Earths, Remembrance progress, vessels) plus Murk,
relics and traps.

Event-flag ids (`flag`) are placeholders (0) until reversed with the Hexinton CE table / Smithbox.
"""
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple

GAME_NAME = "Elden Ring Nightreign"
BASE_ID = 2_622_380_000  # Steam AppID 2622380 * 1000


# --------------------------------------------------------------------------------------
# Nightlords / expeditions
# --------------------------------------------------------------------------------------
@dataclass(frozen=True)
class Nightlord:
    expedition: str
    boss: str
    dlc: bool = False
    final: bool = False
    defeat_flag: int = 0     # NightBossMenuParam.defeat_event_flag (regulation 1.03.x) - confirmed
    unlock_flag: int = 0     # NightBossMenuParam.unlock_event_flag (vanilla gate)


# Flags read from NightBossMenuParam rows 0-9 (see research/nightreign_signatures.md §5.1). Row order ==
# menu order; the boss-name mapping per row is inferred from menu order and should be confirmed via
# the Menu FMG ids 131050-131059.
NIGHTLORDS: List[Nightlord] = [
    Nightlord("Tricephalos", "Gladius, Beast of Night", defeat_flag=150, unlock_flag=0),
    Nightlord("Gaping Jaw", "Adel, Baron of Night", defeat_flag=151, unlock_flag=110),
    Nightlord("Sentient Pest", "Gnoster, Wisdom of Night", defeat_flag=152, unlock_flag=110),
    Nightlord("Augur", "Maris, Fathom of Night", defeat_flag=153, unlock_flag=110),
    Nightlord("Equilibrious Beast", "Libra, Creature of Night", defeat_flag=154, unlock_flag=110),
    Nightlord("Darkdrift Knight", "Fulghor, Champion of Nightglow", defeat_flag=155, unlock_flag=110),
    Nightlord("Fissure in the Fog", "Caligo, Miasma of Night", defeat_flag=156, unlock_flag=110),
    Nightlord("Night Aspect", "Heolstor the Nightlord", final=True, defeat_flag=160, unlock_flag=115),
    Nightlord("Balancers", "Weapon-Bequeathed Harmonia", dlc=True, defeat_flag=161, unlock_flag=135),
    Nightlord("Dreglord", "Traitorous Straghess", dlc=True, defeat_flag=162, unlock_flag=136),
]
DEEP_OF_NIGHT_UNLOCK_FLAG = 130   # NightBossMenuParam row 100
BASE_NIGHTLORDS = [n for n in NIGHTLORDS if not n.dlc and not n.final]  # the 7 required for Night Aspect

# --------------------------------------------------------------------------------------
# Nightfarers
# --------------------------------------------------------------------------------------
@dataclass(frozen=True)
class Nightfarer:
    name: str
    remembrance_chapters: int
    hero_type: int                      # HeroParam heroType (1..10)
    dlc: bool = False
    unlock_note: str = ""
    unlock_flag: int = 0                # HeroParam.character_unlock_flag (0 = always unlocked) - confirmed
    remembrance_flags: Tuple[int, int] = (0, 0)   # PersonalScenarioParam objective_flag_id range - inferred per hero


# Hero order matches HeroParam heroType. Vessel unlock flags follow AntiqueStandParam:
#   60000 + 50*(heroType-1) + {10,20,30,40} and 60600 + 20*(heroType-1) + {0,10}.
NIGHTFARERS: List[Nightfarer] = [
    Nightfarer("Wylder", 9, 1, remembrance_flags=(1009101, 1009124)),
    Nightfarer("Guardian", 10, 2, remembrance_flags=(1009400, 1009430)),
    Nightfarer("Ironeye", 8, 3, remembrance_flags=(1009501, 1009526)),
    Nightfarer("Duchess", 9, 4, unlock_note="Old Pocketwatch after Gladius -> Priestess", unlock_flag=6031,
               remembrance_flags=(1009801, 1009817)),
    Nightfarer("Raider", 8, 5, remembrance_flags=(1009701, 1009722)),
    Nightfarer("Revenant", 8, 6, unlock_note="Besmirched Frame from the Bazaar -> phantom fight", unlock_flag=6037,
               remembrance_flags=(1009301, 1009317)),
    Nightfarer("Recluse", 8, 7, remembrance_flags=(1009201, 1009229)),
    Nightfarer("Executor", 7, 8, remembrance_flags=(1009600, 1009616)),
    Nightfarer("Scholar", 8, 9, dlc=True, unlock_note="Tricephalos + Iron Menial (DLC)", unlock_flag=6038,
               remembrance_flags=(1029900, 1029926)),
    Nightfarer("Undertaker", 7, 10, dlc=True, unlock_note="Tricephalos + Iron Menial (DLC)", unlock_flag=6039,
               remembrance_flags=(0, 0)),
]


def vessel_unlock_flags(hero_type: int) -> List[int]:
    base = 60000 + 50 * (hero_type - 1)
    extra = 60600 + 20 * (hero_type - 1)
    return [base + 10, base + 20, base + 30, base + 40, extra, extra + 10]


# Per-run challenge checks (option per_run_checks). Tracked mod-side via in-expedition flags
# (8061/8062 encounter start/finish, 7511/7512 night-boss death) plus the run summary.
PER_RUN_CHALLENGES: List[str] = [
    "Survive Night 1", "Survive Night 2", "Defeat a Nightlord",
]
GLOBAL_RUN_CHALLENGES: List[str] = [
    "Collect a Grand Relic in a Run", "Reach Level 15 in a Run", "Upgrade a Weapon to Legendary",
    "Defeat an Evergaol Boss", "Clear a Great Church", "Clear a Fort", "Open a Great Chest",
    "Defeat a Night Boss with 2+ Minutes Remaining", "Finish a Run Without Dying",
]
assert sum(n.remembrance_chapters for n in NIGHTFARERS) == 82
STARTING_NIGHTFARER_CHOICES = ["Wylder", "Guardian", "Ironeye", "Raider", "Recluse", "Executor"]

# --------------------------------------------------------------------------------------
# Shifting Earth
# --------------------------------------------------------------------------------------
SHIFTING_EARTH: List[Tuple[str, bool]] = [
    ("The Crater", False),
    ("The Mountaintop", False),
    ("The Rotted Woods", False),
    ("Noklateo, the Shrouded City", False),
    ("The Great Hollow", True),
]

# --------------------------------------------------------------------------------------
# Night bosses (Night 1 / Night 2 pools). First-kill checks.
# --------------------------------------------------------------------------------------
NIGHT1_BOSSES: List[str] = [
    "Bell Bearing Hunter", "Demi-Human Queen", "Battlefield Commander", "Centipede Demon", "Gaping Dragon",
    "Grafted Monarch", "Night's Cavalry", "Royal Revenant", "Smelter Demon", "Tibia Mariner", "Duke's Dear Freja",
    "Ulcerated Tree Spirit", "Valiant Gargoyle", "Wormface", "Death Knights",
]
NIGHT2_BOSSES: List[str] = [
    "Fell Omen", "Tree Sentinel", "Ancient Dragon", "Crucible Knight", "Dancer of the Boreal Valley",
    "Death Rite Bird", "Draconic Tree Sentinel", "Full-Grown Fallingstar Beast", "Godskin Duo", "Great Wyrm",
    "Nameless King", "Nox Dragonkin Soldier", "Outland Commander", "Knight Artorias", "Demon Prince",
    "Divine Beast Dancing Lion", "Mohg, Lord of Blood",
]
NIGHT_BOSSES_DLC: List[str] = [
    "Demon in Pain & Demon from Below", "Curseblade & Divine Beast Warrior", "Great Red Bear",
]

# Field / POI bosses (subset; first-kill checks). TODO: complete from the in-game Trophy Wall list.
FIELD_BOSSES: List[str] = [
    "Erdtree Avatar", "Black Knife Assassin", "Grave Warden Duelist", "Omenkiller", "Leonine Misbegotten",
    "Crystalian Trio", "Flying Dragon", "Royal Carian Knight", "Magma Wyrm", "Ancient Hero of Zamor",
    "Beastman of Farum Azula", "Banished Knight", "Golden Hippopotamus", "Red Wolf of Radagon",
    "Demi-Human Chief", "Stonedigger Troll", "Mad Pumpkin Head", "Fire Prelate", "Bloodhound Knight",
    "Godskin Apostle", "Cemetery Shade", "Putrid Avatar", "Elder Lion", "Sanguine Noble", "Miranda Blossom",
    "Onyx Lord", "Erdtree Burial Watchdog", "Black Blade Kindred", "Ancestor Spirit", "Dragonkin Soldier",
    "Guardian Golem", "Astel, Naturalborn of the Void", "Tree Sentinel Duo", "Deathbird", "Wandering Nobles Cluster",
]

# --------------------------------------------------------------------------------------
# Vessels (Relic Rites)
# --------------------------------------------------------------------------------------
GRAILS: List[Tuple[str, str]] = [  # (name, requirement description)
    ("Spirit Shelter Grail", "4 Nightlords defeated"),
    ("Giant's Cradle Grail", "7 Nightlords defeated"),
    ("Sacred Erdtree Grail", "Heolstor defeated"),
]

# --------------------------------------------------------------------------------------
# Deep of Night depth milestones
# --------------------------------------------------------------------------------------
DEEP_OF_NIGHT_DEPTHS = 5

# --------------------------------------------------------------------------------------
# Relic colours (filler relic items)
# --------------------------------------------------------------------------------------
RELIC_COLOURS = ["Burning Scene", "Tranquil Scene", "Luminous Scene", "Drizzly Scene"]  # red/blue/yellow/green
