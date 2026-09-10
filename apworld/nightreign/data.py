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
    Nightfarer("Guardian", 10, 2, remembrance_flags=(1009201, 1009229)),
    Nightfarer("Ironeye", 8, 3, remembrance_flags=(1009301, 1009317)),
    Nightfarer("Duchess", 9, 4, unlock_note="Old Pocketwatch after Gladius -> Priestess", unlock_flag=6031,
               remembrance_flags=(1009400, 1009430)),
    Nightfarer("Raider", 8, 5, remembrance_flags=(1009501, 1009526)),
    Nightfarer("Revenant", 8, 6, unlock_note="Besmirched Frame from the Bazaar -> phantom fight", unlock_flag=6037,
               remembrance_flags=(1009600, 1009616)),
    Nightfarer("Recluse", 8, 7, remembrance_flags=(1009701, 1009722)),
    Nightfarer("Executor", 7, 8, remembrance_flags=(1009801, 1009817)),
    Nightfarer("Scholar", 8, 9, dlc=True, unlock_note="Tricephalos + Iron Menial (DLC)", unlock_flag=6038,
               remembrance_flags=(1029900, 1029926)),
    Nightfarer("Undertaker", 7, 10, dlc=True, unlock_note="Tricephalos + Iron Menial (DLC)", unlock_flag=6039,
               remembrance_flags=(1019200, 1019218)),
]

# PersonalScenarioParam (regulation 1.03.5, row names from Smithbox): flag set when a Remembrance chapter is
# COMPLETED = the objective flag of the next chapter's row (the last chapter uses the block's final flag).
REMEMBRANCE_CHAPTER_FLAGS: Dict[str, Dict[int, int]] = {
    "Wylder": {1: 1009101, 2: 1009102, 3: 1009109, 4: 1009110, 5: 1009114, 6: 1009115, 7: 1009122, 8: 1009124, 9: 1009124},
    "Guardian": {1: 1009201, 2: 1009202, 3: 1009203, 4: 1009209, 5: 1009210, 6: 1009215, 7: 1009221, 8: 1009222, 9: 1009229, 10: 1009229},
    "Ironeye": {1: 1009301, 2: 1009302, 3: 1009303, 4: 1009307, 5: 1009308, 6: 1009315, 7: 1009317, 8: 1009317},
    "Duchess": {1: 1009401, 2: 1009404, 3: 1009413, 4: 1009414, 5: 1009417, 6: 1009422, 7: 1009423, 8: 1009429, 9: 1009430},
    "Raider": {1: 1009501, 2: 1009508, 3: 1009509, 4: 1009514, 5: 1009515, 6: 1009516, 7: 1009523, 8: 1009526},
    "Revenant": {1: 1009605, 2: 1009606, 3: 1009607, 4: 1009608, 5: 1009612, 6: 1009613, 7: 1009616, 8: 1009616},
    "Recluse": {1: 1009701, 2: 1009706, 3: 1009707, 4: 1009711, 5: 1009712, 6: 1009718, 7: 1009722, 8: 1009722},
    "Executor": {1: 1009801, 2: 1009809, 3: 1009810, 4: 1009811, 5: 1009812, 6: 1009817, 7: 1009817},
    "Scholar": {1: 1029901, 2: 1029902, 3: 1029910, 4: 1029911, 5: 1029914, 6: 1029915, 7: 1029916, 8: 1029926},
    # Undertaker: the "Chapter 3" row is unnamed; chapter 2 -> first chapter-3 objective flag (verify in game)
    "Undertaker": {1: 1019201, 2: 1019202, 3: 1019208, 4: 1019209, 5: 1019214, 6: 1019215, 7: 1019218},
}
# Every objective flag in each hero's PersonalScenarioParam block (for progress counting / debugging).
REMEMBRANCE_OBJECTIVE_FLAGS: Dict[str, List[int]] = {
    "Wylder": [1009101, 1009102, 1009103, 1009104, 1009105, 1009106, 1009107, 1009108, 1009109, 1009110, 1009111, 1009112, 1009113, 1009114, 1009115, 1009116, 1009117, 1009118, 1009119, 1009120, 1009121, 1009122, 1009123, 1009124],
    "Guardian": [1009201, 1009202, 1009203, 1009204, 1009206, 1009207, 1009208, 1009209, 1009210, 1009211, 1009212, 1009213, 1009214, 1009215, 1009216, 1009217, 1009218, 1009219, 1009220, 1009221, 1009222, 1009223, 1009224, 1009225, 1009226, 1009227, 1009228, 1009229],
    "Ironeye": [1009301, 1009302, 1009303, 1009304, 1009305, 1009306, 1009307, 1009308, 1009309, 1009310, 1009311, 1009312, 1009313, 1009314, 1009315, 1009316, 1009317],
    "Duchess": [1009400, 1009401, 1009404, 1009405, 1009406, 1009407, 1009408, 1009409, 1009410, 1009411, 1009412, 1009413, 1009414, 1009415, 1009416, 1009417, 1009418, 1009419, 1009420, 1009421, 1009422, 1009423, 1009424, 1009425, 1009426, 1009427, 1009428, 1009429, 1009430],
    "Raider": [1009501, 1009502, 1009503, 1009504, 1009505, 1009506, 1009507, 1009508, 1009509, 1009510, 1009511, 1009512, 1009513, 1009514, 1009515, 1009516, 1009517, 1009518, 1009519, 1009520, 1009521, 1009522, 1009523, 1009525, 1009526],
    "Revenant": [1009600, 1009601, 1009602, 1009603, 1009604, 1009605, 1009606, 1009607, 1009608, 1009609, 1009610, 1009611, 1009612, 1009613, 1009614, 1009615, 1009616],
    "Recluse": [1009701, 1009702, 1009703, 1009704, 1009705, 1009706, 1009707, 1009708, 1009709, 1009710, 1009711, 1009712, 1009713, 1009714, 1009715, 1009716, 1009718, 1009719, 1009720, 1009721, 1009722],
    "Executor": [1009801, 1009802, 1009803, 1009804, 1009805, 1009806, 1009807, 1009808, 1009809, 1009810, 1009811, 1009812, 1009813, 1009814, 1009815, 1009816, 1009817],
    "Scholar": [1029900, 1029901, 1029902, 1029904, 1029905, 1029906, 1029907, 1029908, 1029909, 1029910, 1029911, 1029912, 1029913, 1029914, 1029915, 1029916, 1029918, 1029919, 1029920, 1029921, 1029922, 1029923, 1029924, 1029925, 1029926],
    "Undertaker": [1019200, 1019201, 1019202, 1019203, 1019204, 1019205, 1019206, 1019207, 1019208, 1019209, 1019210, 1019211, 1019212, 1019213, 1019214, 1019215, 1019217, 1019218],
}


# AntiqueStandParam (regulation 1.03.5): per hero_type, the 7 vessel rows as (unlock_flag, EquipParamGoods id).
# Row 0 = Urn (default), row 1 = Goblet (Bazaar), row 2 = Chalice (Remembrance), row 3 = Soot-Covered Urn (97xx),
# row 4 = Sealed Urn (98xx), rows 5-6 = Decrepit / Forgotten Goblets (DLC, 99xx). hero_type 11 holds the shared Grails.
VESSEL_ROWS: Dict[int, List[Tuple[int, int]]] = {
    1: [(0, 9600), (60010, 9601), (60020, 9602), (60030, 9700), (60040, 9800), (60600, 9920), (60610, 9921)],
    2: [(0, 9603), (60060, 9604), (60070, 9605), (60080, 9703), (60090, 9803), (60620, 9925), (60630, 9926)],
    3: [(0, 9606), (60110, 9607), (60120, 9608), (60130, 9706), (60140, 9806), (60640, 9930), (60650, 9931)],
    4: [(0, 9609), (60160, 9610), (60170, 9611), (60180, 9709), (60190, 9809), (60660, 9935), (60670, 9936)],
    5: [(0, 9612), (60210, 9613), (60220, 9614), (60230, 9712), (60240, 9812), (60680, 9940), (60690, 9941)],
    6: [(0, 9615), (60260, 9616), (60270, 9617), (60280, 9715), (60290, 9815), (60700, 9945), (60710, 9946)],
    7: [(0, 9618), (60310, 9619), (60320, 9620), (60330, 9718), (60340, 9818), (60720, 9950), (60730, 9951)],
    8: [(0, 9621), (60360, 9622), (60370, 9623), (60380, 9721), (60390, 9821), (60740, 9955), (60750, 9956)],
    9: [(0, 9900), (60510, 9901), (60520, 9902), (60530, 9903), (60540, 9904), (60760, 9905), (60770, 9906)],
    10: [(0, 9910), (60560, 9911), (60570, 9912), (60580, 9913), (60590, 9914), (60780, 9915), (60790, 9916)],
}
# Shared Grails (hero_type 11), in GRAILS order (Spirit Shelter, Giant's Cradle, Sacred Erdtree) + DLC Scadutree Grail.
GRAIL_ROWS: List[Tuple[int, int]] = [(60410, 9651), (60420, 9652), (60400, 9650)]
GRAIL_ROWS_DLC: List[Tuple[int, int]] = [(60430, 9660)]

# EquipParamAntique ids (GaItem category 0xC0000000) for currency / flatstones / relic scenes.
ANTIQUE_MURK = 10
ANTIQUE_SOVEREIGN_SIGIL = 11
ANTIQUE_SCENIC_FLATSTONE = 20
ANTIQUE_LARGE_SCENIC_FLATSTONE = 30
# Delicate/Polished/Grand per colour: Burning 100-102, Drizzly 109-111, Luminous 118-120, Tranquil (see param) 127-129
ANTIQUE_RELIC_SCENES: Dict[str, Tuple[int, int, int]] = {
    "Burning Scene": (100, 101, 102), "Drizzly Scene": (109, 110, 111), "Luminous Scene": (118, 119, 120),
    "Tranquil Scene": (127, 128, 129),
}
RELIC_COLOURS = ["Burning Scene", "Tranquil Scene", "Luminous Scene", "Drizzly Scene"]  # red / blue / yellow / green
# Nightfarer garb (outfit) goods ids: base outfit, Dawn, Darkness, Remembrance, and two unlockables per hero.
GARB_GOODS_BASE: Dict[str, int] = {"Wylder": 40000, "Guardian": 40100, "Ironeye": 40200, "Duchess": 40300, "Raider": 40400,
                                   "Revenant": 40500, "Recluse": 40600, "Executor": 40700, "Scholar": 40800, "Undertaker": 40900}


def vessel_unlock_flags(hero_type: int) -> List[int]:
    return [flag for flag, _ in VESSEL_ROWS[hero_type] if flag]


# Per-run challenge checks (option per_run_checks). Tracked mod-side via in-expedition flags
# (8061/8062 encounter start/finish, 7511/7512 night-boss death) plus the run summary.
PER_RUN_CHALLENGES: List[str] = [
    "Survive Night 1", "Survive Night 2", "Defeat a Nightlord",
]
PER_RUN_CHALLENGES_EXTENDED: List[str] = [
    "Reach Level 10 by Night 1", "Use the Ultimate Art 10 Times in a Run", "Revive an Ally",
]
GLOBAL_RUN_CHALLENGES: List[str] = [
    "Collect a Grand Relic in a Run", "Reach Level 15 in a Run", "Upgrade a Weapon to Legendary",
    "Defeat an Evergaol Boss", "Clear a Great Church", "Clear a Fort", "Open a Great Chest",
    "Defeat a Night Boss with 2+ Minutes Remaining", "Finish a Run Without Dying",
]
GLOBAL_RUN_CHALLENGES_EXTENDED: List[str] = [
    "Clear a Castle", "Clear a Sorcerer's Rise Puzzle", "Defeat a Field Boss on Day 1 Before the First Circle",
    "Reach Night 3 with 3 Legendary Weapons", "Defeat a Nightlord Without Using a Flask",
    "Defeat a Nightlord in Under 3 Minutes", "Collect 10,000 Runes in a Single Day", "Trigger a Shifting Earth Event",
    "Defeat a Night Boss Within 60 Seconds of It Appearing", "Kill 5 Invading Phantoms in a Run",
    "Open Every Great Chest on a Map", "Complete a Run Using Only Starting Equipment",
    "Finish a Run with Full Relic Slots Equipped", "Defeat the Bell Bearing Hunter at a Merchant",
    "Reach the Nightlord Arena with Under 25% HP and Win", "Win an Expedition with Each Weapon Type (Sword)",
    "Win an Expedition with Each Weapon Type (Greatsword)", "Win an Expedition with Each Weapon Type (Bow)",
    "Win an Expedition with Each Weapon Type (Staff/Seal)", "Win an Expedition with a Dagger Equipped",
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

