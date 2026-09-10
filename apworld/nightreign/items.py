from dataclasses import dataclass
from typing import Dict, List, Optional

from BaseClasses import Item, ItemClassification as IC

from .data import (BASE_ID, GAME_NAME, GRAILS, NIGHTFARERS, NIGHTLORDS, RELIC_COLOURS, SHIFTING_EARTH)


class NightreignItem(Item):
    game = GAME_NAME


@dataclass(frozen=True)
class ItemData:
    name: str
    offset: int
    classification: IC
    category: str
    count: int = 0            # default pool count; the World decides based on options
    dlc: bool = False
    game_id: Optional[str] = None   # goods id / event flag for the mod (TBD)


ALL_ITEMS: List[ItemData] = []


def _add(name: str, offset: int, classification: IC, category: str, count: int = 0, dlc: bool = False,
         game_id: Optional[str] = None) -> ItemData:
    d = ItemData(name, offset, classification, category, count, dlc, game_id)
    ALL_ITEMS.append(d)
    return d


# Nightfarers (offset 1..10)
NIGHTFARER_ITEMS: List[ItemData] = [
    _add(f"Nightfarer: {nf.name}", 1 + i, IC.progression, "Nightfarer", dlc=nf.dlc)
    for i, nf in enumerate(NIGHTFARERS)
]

# Expedition access (offset 20..29)
EXPEDITION_ITEMS: List[ItemData] = [
    _add(f"Expedition Access: {nl.expedition}", 20 + i, IC.progression, "Expedition Access", dlc=nl.dlc)
    for i, nl in enumerate(NIGHTLORDS)
]

# Shifting Earth (offset 40..44)
SHIFTING_EARTH_ITEMS: List[ItemData] = [
    _add(f"Shifting Earth: {name}", 40 + i, IC.progression, "Shifting Earth", dlc=dlc)
    for i, (name, dlc) in enumerate(SHIFTING_EARTH)
]

# Progressive Remembrance per Nightfarer (offset 50..59)
REMEMBRANCE_ITEMS: List[ItemData] = [
    _add(f"Progressive Remembrance: {nf.name}", 50 + i, IC.progression_skip_balancing, "Remembrance",
         count=nf.remembrance_chapters, dlc=nf.dlc)
    for i, nf in enumerate(NIGHTFARERS)
]

# Remembrance Keys - one per Nightfarer, unlocks every chapter (offset 60..69). Default mode.
REMEMBRANCE_KEY_ITEMS: List[ItemData] = [
    _add(f"Remembrance Key: {nf.name}", 60 + i, IC.progression, "Remembrance Key", dlc=nf.dlc)
    for i, nf in enumerate(NIGHTFARERS)
]

# Vessels (offset 70..)
GOBLET_ITEMS: List[ItemData] = [
    _add(f"{nf.name}'s Goblet", 70 + i, IC.useful, "Vessel", dlc=nf.dlc) for i, nf in enumerate(NIGHTFARERS)
]
GRAIL_ITEMS: List[ItemData] = [
    _add(name, 85 + i, IC.useful, "Vessel") for i, (name, _) in enumerate(GRAILS)
]

# Deep of Night access (offset 90)
DEEP_OF_NIGHT_ITEM = _add("Deep of Night Access", 90, IC.progression, "Mode")

# Filler (offset 100..)
FILLER_ITEMS: List[ItemData] = [
    _add("Murk (500)", 100, IC.filler, "Filler"),
    _add("Murk (1500)", 101, IC.filler, "Filler"),
    _add("Scenic Flatstone", 102, IC.filler, "Filler"),
    _add("Grand Scenic Flatstone", 103, IC.useful, "Filler"),
]
for _i, _colour in enumerate(RELIC_COLOURS):
    FILLER_ITEMS.append(_add(f"Polished {_colour} Relic", 110 + _i, IC.filler, "Relic"))
    FILLER_ITEMS.append(_add(f"Grand {_colour} Relic", 120 + _i, IC.useful, "Relic"))

# Traps (offset 140..)
TRAP_ITEMS: List[ItemData] = [
    _add("Cursed Relic Trap", 140, IC.trap, "Trap"),          # a Depths-style negative-effect relic is equipped
    _add("Murk Tax Trap", 141, IC.trap, "Trap"),              # lose Murk
    _add("Night's Cavalry Ambush Trap", 142, IC.trap, "Trap"),  # spawn a night-boss-tier enemy on the player
    _add("Circle Collapse Trap", 143, IC.trap, "Trap"),       # accelerate the current rain circle
]

EVENT_ITEMS = ["Victory"] + [f"{nl.expedition} Cleared" for nl in NIGHTLORDS]

item_table: Dict[str, ItemData] = {i.name: i for i in ALL_ITEMS}
item_name_to_id: Dict[str, int] = {i.name: BASE_ID + i.offset for i in ALL_ITEMS}
item_name_groups: Dict[str, set] = {
    "Nightfarers": {i.name for i in NIGHTFARER_ITEMS},
    "Expedition Access": {i.name for i in EXPEDITION_ITEMS},
    "Shifting Earth": {i.name for i in SHIFTING_EARTH_ITEMS},
    "Remembrances": {i.name for i in REMEMBRANCE_ITEMS},
    "Remembrance Keys": {i.name for i in REMEMBRANCE_KEY_ITEMS},
    "Vessels": {i.name for i in GOBLET_ITEMS + GRAIL_ITEMS},
    "Relics": {i.name for i in FILLER_ITEMS if i.category == "Relic"},
    "Traps": {i.name for i in TRAP_ITEMS},
}

assert len(item_name_to_id) == len(ALL_ITEMS)
assert len(set(item_name_to_id.values())) == len(ALL_ITEMS)
