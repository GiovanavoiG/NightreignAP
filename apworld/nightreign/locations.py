from dataclasses import dataclass
from typing import Callable, Dict, List, Optional, Tuple

from BaseClasses import Location

from .data import (BASE_ID, DEEP_OF_NIGHT_DEPTHS, FIELD_BOSSES, GAME_NAME, GLOBAL_RUN_CHALLENGES,
                   GLOBAL_RUN_CHALLENGES_EXTENDED, GRAIL_ROWS, GRAILS, NIGHT1_BOSSES, NIGHT2_BOSSES, NIGHT_BOSSES_DLC,
                   NIGHTFARERS, NIGHTLORDS, PER_RUN_CHALLENGES, PER_RUN_CHALLENGES_EXTENDED, REMEMBRANCE_CHAPTER_FLAGS,
                   SHIFTING_EARTH, vessel_unlock_flags)


class NightreignLocation(Location):
    game = GAME_NAME


@dataclass(frozen=True)
class LocationData:
    name: str
    offset: Optional[int]
    region: str
    category: str                # Nightlord / Night Boss / Field Boss / Remembrance / Vessel / Unlock / Shifting Earth / Deep / Event
    dlc: bool = False
    requires: Tuple[str, ...] = ()        # item names (all)
    nightfarer: Optional[str] = None      # for Remembrance / Goblet checks
    chapter: int = 0                      # Remembrance chapter number
    nightlords_cleared: int = 0           # minimum number of "<expedition> Cleared" events
    flag: int = 0                         # game event flag (TBD)


ALL_LOCATIONS: List[LocationData] = []


def _add(*args, **kwargs) -> LocationData:
    d = LocationData(*args, **kwargs)
    ALL_LOCATIONS.append(d)
    return d


ANY_EXPEDITION = "Any Expedition"
ROUNDTABLE = "Roundtable Hold"


def expedition_region(expedition: str) -> str:
    return f"Expedition: {expedition}"


# Nightlord kills (offset 1..10)
NIGHTLORD_LOCATIONS = [
    _add(f"Nightlord: {nl.boss} Defeated", 1 + i, expedition_region(nl.expedition), "Nightlord", dlc=nl.dlc,
         flag=nl.defeat_flag)
    for i, nl in enumerate(NIGHTLORDS)
]
# Matching event locations (no id) that hold "<expedition> Cleared"
NIGHTLORD_EVENTS = [
    _add(f"Event: {nl.expedition} Cleared", None, expedition_region(nl.expedition), "Event", dlc=nl.dlc)
    for nl in NIGHTLORDS
]

# Night bosses (offset 100..)
NIGHT_BOSS_LOCATIONS = []
_off = 100
for _b in NIGHT1_BOSSES:
    NIGHT_BOSS_LOCATIONS.append(_add(f"Night 1 Boss: {_b} Defeated", _off, ANY_EXPEDITION, "Night Boss")); _off += 1
for _b in NIGHT2_BOSSES:
    NIGHT_BOSS_LOCATIONS.append(_add(f"Night 2 Boss: {_b} Defeated", _off, ANY_EXPEDITION, "Night Boss")); _off += 1
for _b in NIGHT_BOSSES_DLC:
    NIGHT_BOSS_LOCATIONS.append(_add(f"Night Boss: {_b} Defeated", _off, ANY_EXPEDITION, "Night Boss", dlc=True)); _off += 1

# Field bosses (offset 200..)
FIELD_BOSS_LOCATIONS = [
    _add(f"Field Boss: {b} Defeated", 200 + i, ANY_EXPEDITION, "Field Boss") for i, b in enumerate(FIELD_BOSSES)
]

# Remembrance chapters (offset 300..). Flag = completion flag from PersonalScenarioParam (see data.py).
REMEMBRANCE_LOCATIONS = []
_off = 300
for _nf in NIGHTFARERS:
    for _ch in range(1, _nf.remembrance_chapters + 1):
        REMEMBRANCE_LOCATIONS.append(_add(f"Remembrance: {_nf.name} - Chapter {_ch}", _off, ANY_EXPEDITION,
                                          "Remembrance", dlc=_nf.dlc, nightfarer=_nf.name, chapter=_ch,
                                          requires=(f"Nightfarer: {_nf.name}",),
                                          flag=REMEMBRANCE_CHAPTER_FLAGS[_nf.name].get(_ch, 0)))
        _off += 1

# Vessels (offset 400..). Flag: first Goblet slot of the hero (AntiqueStandParam unlockFlag pattern).
VESSEL_LOCATIONS = []
for _i, _nf in enumerate(NIGHTFARERS):
    VESSEL_LOCATIONS.append(_add(f"Small Jar Bazaar: Buy {_nf.name}'s Goblet", 400 + _i, ROUNDTABLE, "Vessel",
                                 dlc=_nf.dlc, requires=(f"Nightfarer: {_nf.name}",), nightlords_cleared=1,
                                 flag=vessel_unlock_flags(_nf.hero_type)[0]))
_grail_req = {"Spirit Shelter Grail": 4, "Giant's Cradle Grail": 7, "Sacred Erdtree Grail": 8}
for _i, (_g, _) in enumerate(GRAILS):
    VESSEL_LOCATIONS.append(_add(f"Small Jar Bazaar: Buy {_g}", 420 + _i, ROUNDTABLE, "Vessel",
                                 nightlords_cleared=_grail_req[_g], flag=GRAIL_ROWS[_i][0]))

# Character unlock quests (offset 440..)
UNLOCK_LOCATIONS = [
    _add("Unlock Quest: Duchess (Old Pocketwatch)", 440, ROUNDTABLE, "Unlock", nightlords_cleared=1, flag=6031),
    _add("Unlock Quest: Revenant (Besmirched Frame)", 441, ROUNDTABLE, "Unlock", flag=6037),
    _add("Unlock Quest: Scholar (Iron Menial)", 442, ROUNDTABLE, "Unlock", dlc=True, nightlords_cleared=1, flag=6038),
    _add("Unlock Quest: Undertaker (Iron Menial)", 443, ROUNDTABLE, "Unlock", dlc=True, nightlords_cleared=1, flag=6039),
]

# Per-run challenge checks (offset 500..). Option per_run_checks.
PER_RUN_LOCATIONS = []
_off = 500
for _nf in NIGHTFARERS:
    for _c in PER_RUN_CHALLENGES:
        PER_RUN_LOCATIONS.append(_add(f"Run Challenge: {_c} as {_nf.name}", _off, ANY_EXPEDITION, "Run Challenge",
                                      dlc=_nf.dlc, nightfarer=_nf.name, requires=(f"Nightfarer: {_nf.name}",)))
        _off += 1
for _c in GLOBAL_RUN_CHALLENGES:
    PER_RUN_LOCATIONS.append(_add(f"Run Challenge: {_c}", _off, ANY_EXPEDITION, "Run Challenge"))
    _off += 1
# Extended pool (offset 560..): option run_challenge_pool = extended
_off = 560
for _nf in NIGHTFARERS:
    for _c in PER_RUN_CHALLENGES_EXTENDED:
        PER_RUN_LOCATIONS.append(_add(f"Run Challenge: {_c} as {_nf.name}", _off, ANY_EXPEDITION, "Run Challenge Extended",
                                      dlc=_nf.dlc, nightfarer=_nf.name, requires=(f"Nightfarer: {_nf.name}",)))
        _off += 1
for _c in GLOBAL_RUN_CHALLENGES_EXTENDED:
    PER_RUN_LOCATIONS.append(_add(f"Run Challenge: {_c}", _off, ANY_EXPEDITION, "Run Challenge Extended"))
    _off += 1

# Shifting Earth (offset 450..)
SHIFTING_EARTH_LOCATIONS = [
    _add(f"Shifting Earth: {name} - Boss Defeated", 450 + i, ANY_EXPEDITION, "Shifting Earth", dlc=dlc,
         requires=(f"Shifting Earth: {name}",))
    for i, (name, dlc) in enumerate(SHIFTING_EARTH)
]

# Deep of Night (offset 460..)
DEEP_LOCATIONS = [
    _add(f"Deep of Night: Reach Depth {d}", 460 + d - 1, "Deep of Night", "Deep")
    for d in range(1, DEEP_OF_NIGHT_DEPTHS + 1)
]

# Victory event
VICTORY_EVENT = _add("Event: Victory", None, ROUNDTABLE, "Event")

location_table: Dict[str, LocationData] = {l.name: l for l in ALL_LOCATIONS}
location_name_to_id: Dict[str, int] = {l.name: BASE_ID + l.offset for l in ALL_LOCATIONS if l.offset is not None}
location_name_groups: Dict[str, set] = {}
for _l in ALL_LOCATIONS:
    if _l.offset is not None:
        location_name_groups.setdefault(_l.category, set()).add(_l.name)
        if _l.nightfarer:
            location_name_groups.setdefault(_l.nightfarer, set()).add(_l.name)

assert len(location_table) == len(ALL_LOCATIONS)
assert len(set(location_name_to_id.values())) == len(location_name_to_id)
