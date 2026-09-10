"""
Elden Ring: Nightreign - Archipelago World (prototype 0.2.0)

Meta-progression randomizer: see docs/ and the discovery document.
"""
from typing import Any, ClassVar, Dict, List, Mapping

from BaseClasses import CollectionState, Item, ItemClassification, Region, Tutorial
from worlds.AutoWorld import WebWorld, World
from worlds.generic.Rules import add_rule, set_rule

from .data import BASE_ID, BASE_NIGHTLORDS, GAME_NAME, NIGHTFARERS, NIGHTLORDS, STARTING_NIGHTFARER_CHOICES
from .items import (ALL_ITEMS, DEEP_OF_NIGHT_ITEM, EVENT_ITEMS, EXPEDITION_ITEMS, FILLER_ITEMS, GOBLET_ITEMS,
                    GRAIL_ITEMS, NIGHTFARER_ITEMS, REMEMBRANCE_ITEMS, REMEMBRANCE_KEY_ITEMS, SHIFTING_EARTH_ITEMS,
                    TRAP_ITEMS, ItemData,
                    NightreignItem, item_name_groups, item_name_to_id, item_table)
from .locations import (ALL_LOCATIONS, ANY_EXPEDITION, ROUNDTABLE, LocationData, NightreignLocation,
                        expedition_region, location_name_groups, location_name_to_id, location_table)
from .options import Goal, NightreignOptions, RemembranceLocks, StartingNightfarer, option_groups

from . import components  # noqa: F401


class NightreignWeb(WebWorld):
    theme = "stone"
    bug_report_page = "https://github.com/GiovanavoiG/NightreignAP/issues"
    tutorials = [Tutorial(
        "Multiworld Setup Guide",
        "A guide to setting up Elden Ring Nightreign for Archipelago.",
        "English", "setup_en.md", "setup/en", ["GiovanavoiG"],
    )]
    option_groups = option_groups
    rich_text_options_doc = True


class NightreignWorld(World):
    """
    Elden Ring: Nightreign is a three-day roguelite expedition game. This world randomizes its meta
    progression: Nightfarers, expedition access, Shifting Earth events, Remembrance progress and
    vessels are items, while Nightlord kills, night/field boss first-kills, Remembrance chapters and
    Bazaar purchases are checks.
    """
    game = GAME_NAME
    web = NightreignWeb()
    options_dataclass = NightreignOptions
    options: NightreignOptions
    topology_present = True
    origin_region_name = ROUNDTABLE

    item_name_to_id: ClassVar[Dict[str, int]] = item_name_to_id
    location_name_to_id: ClassVar[Dict[str, int]] = location_name_to_id
    item_name_groups: ClassVar[Dict[str, set]] = item_name_groups
    location_name_groups: ClassVar[Dict[str, set]] = location_name_groups

    # ------------------------------------------------------------------ helpers
    def _dlc(self) -> bool:
        return bool(self.options.dlc_forsaken_hollows)

    def _enabled_locations(self) -> List[LocationData]:
        o = self.options
        out = []
        for loc in ALL_LOCATIONS:
            if loc.dlc and not self._dlc():
                continue
            if loc.category == "Night Boss" and not o.night_boss_checks:
                continue
            if loc.category == "Field Boss" and not o.field_boss_checks:
                continue
            if loc.category == "Vessel" and not o.vessel_checks:
                continue
            if loc.category == "Deep" and not o.deep_of_night_checks:
                continue
            if loc.category == "Run Challenge" and not o.per_run_checks:
                continue
            if loc.category == "Unlock" and not o.nightfarer_shuffle:
                # With vanilla unlocks the quests still happen; keep them as checks.
                pass
            out.append(loc)
        return out

    def _active_nightlords(self):
        return [nl for nl in NIGHTLORDS if self._dlc() or not nl.dlc]

    # ------------------------------------------------------------------ lifecycle
    def generate_early(self) -> None:
        if self.options.goal == Goal.option_all_nightlords and not self._dlc():
            self.options.goal.value = Goal.option_all_base_nightlords

        self.starting_nightfarer = ""
        if self.options.nightfarer_shuffle:
            choice = self.options.starting_nightfarer
            if choice == StartingNightfarer.option_random_nightfarer:
                self.starting_nightfarer = self.random.choice(STARTING_NIGHTFARER_CHOICES)
            else:
                self.starting_nightfarer = choice.current_key.capitalize()
            self.push_precollected(self.create_item(f"Nightfarer: {self.starting_nightfarer}"))
        else:
            for nf in NIGHTFARERS:
                if not nf.dlc or self._dlc():
                    self.push_precollected(self.create_item(f"Nightfarer: {nf.name}"))

        if self.options.expedition_locks:
            self.push_precollected(self.create_item("Expedition Access: Tricephalos"))

    def create_regions(self) -> None:
        regions: Dict[str, Region] = {}

        def region(name: str) -> Region:
            r = Region(name, self.player, self.multiworld)
            regions[name] = r
            return r

        roundtable = region(ROUNDTABLE)
        any_exp = region(ANY_EXPEDITION)
        deep = region("Deep of Night")
        for nl in self._active_nightlords():
            region(expedition_region(nl.expedition))
        self.multiworld.regions.extend(regions.values())

        for loc in self._enabled_locations():
            r = regions[loc.region]
            address = None if loc.offset is None else BASE_ID + loc.offset
            r.locations.append(NightreignLocation(self.player, loc.name, address, r))

        for nl in self._active_nightlords():
            r = regions[expedition_region(nl.expedition)]
            roundtable.connect(r, f"Embark: {nl.expedition}")
            r.connect(any_exp, f"{nl.expedition} -> Any Expedition")
        roundtable.connect(deep, "Enter Deep of Night")

        # Events
        for nl in self._active_nightlords():
            self.get_location(f"Event: {nl.expedition} Cleared").place_locked_item(
                self.create_item(f"{nl.expedition} Cleared"))
        self.get_location("Event: Victory").place_locked_item(self.create_item("Victory"))

    def create_item(self, name: str) -> Item:
        if name in EVENT_ITEMS:
            return NightreignItem(name, ItemClassification.progression, None, self.player)
        d = item_table[name]
        return NightreignItem(name, d.classification, BASE_ID + d.offset, self.player)

    def create_items(self) -> None:
        pool: List[Item] = []
        dlc = self._dlc()

        if self.options.nightfarer_shuffle:
            for it in NIGHTFARER_ITEMS:
                if (dlc or not it.dlc) and it.name != f"Nightfarer: {self.starting_nightfarer}":
                    pool.append(self.create_item(it.name))

        if self.options.expedition_locks:
            for it in EXPEDITION_ITEMS:
                if (dlc or not it.dlc) and it.name != "Expedition Access: Tricephalos":
                    pool.append(self.create_item(it.name))

        if self.options.shifting_earth_locks:
            for it in SHIFTING_EARTH_ITEMS:
                if dlc or not it.dlc:
                    pool.append(self.create_item(it.name))

        if self.options.remembrance_locks == RemembranceLocks.option_progressive:
            for it in REMEMBRANCE_ITEMS:
                if dlc or not it.dlc:
                    for _ in range(it.count):
                        pool.append(self.create_item(it.name))
        elif self.options.remembrance_locks == RemembranceLocks.option_key:
            for it in REMEMBRANCE_KEY_ITEMS:
                if dlc or not it.dlc:
                    pool.append(self.create_item(it.name))

        if self.options.vessel_checks:
            for it in GOBLET_ITEMS + GRAIL_ITEMS:
                if dlc or not it.dlc:
                    pool.append(self.create_item(it.name))

        if self.options.deep_of_night_checks:
            pool.append(self.create_item(DEEP_OF_NIGHT_ITEM.name))

        unfilled = len(self.multiworld.get_unfilled_locations(self.player))
        remaining = unfilled - len(pool)
        if remaining < 0:
            for _ in range(-remaining):
                idx = next((i for i, it in reversed(list(enumerate(pool)))
                            if it.classification == ItemClassification.useful), None)
                if idx is None:
                    break
                pool.pop(idx)
        else:
            traps = int(remaining * self.options.trap_percentage.value / 100)
            for _ in range(traps):
                pool.append(self.create_item(self.random.choice([t.name for t in TRAP_ITEMS])))
            for _ in range(remaining - traps):
                pool.append(self.create_item(self.get_filler_item_name()))
        self.multiworld.itempool.extend(pool)

    def get_filler_item_name(self) -> str:
        names = [i.name for i in FILLER_ITEMS]
        weights = [6 if n.startswith("Murk (500)") else 3 if n.startswith("Murk") else 2 if n.startswith("Polished")
                   else 1 for n in names]
        return self.random.choices(names, weights=weights)[0]

    # ------------------------------------------------------------------ rules
    def _cleared_count(self, state: CollectionState, n: int) -> bool:
        return sum(1 for nl in self._active_nightlords() if state.has(f"{nl.expedition} Cleared", self.player)) >= n

    def set_rules(self) -> None:
        p = self.player
        dlc = self._dlc()

        for nl in self._active_nightlords():
            ent = self.get_entrance(f"Embark: {nl.expedition}")
            reqs: List[str] = []
            if self.options.expedition_locks:
                reqs.append(f"Expedition Access: {nl.expedition}")
            if nl.final:
                needed = [f"{b.expedition} Cleared" for b in BASE_NIGHTLORDS]
                reqs.extend(needed)
            elif nl.dlc:
                # DLC expeditions: vanilla requires Tricephalos + both DLC Nightfarers unlocked
                reqs.append("Tricephalos Cleared")
            if reqs:
                set_rule(ent, lambda state, r=tuple(reqs): state.has_all(r, p))

        # Deep of Night requires Heolstor beaten (+ access item when enabled)
        deep_reqs = ["Night Aspect Cleared"]
        if self.options.deep_of_night_checks:
            deep_reqs.append("Deep of Night Access")
        set_rule(self.get_entrance("Enter Deep of Night"), lambda state, r=tuple(deep_reqs): state.has_all(r, p))

        for loc in self._enabled_locations():
            if loc.offset is None:
                continue
            location = self.get_location(loc.name)
            if loc.requires and not (loc.category == "Shifting Earth" and not self.options.shifting_earth_locks):
                add_rule(location, lambda state, r=loc.requires: state.has_all(r, p))
            if loc.category == "Remembrance":
                if self.options.remembrance_locks == RemembranceLocks.option_progressive:
                    add_rule(location, lambda state, nf=loc.nightfarer, c=loc.chapter:
                             state.has(f"Progressive Remembrance: {nf}", p, c))
                elif self.options.remembrance_locks == RemembranceLocks.option_key:
                    add_rule(location, lambda state, nf=loc.nightfarer: state.has(f"Remembrance Key: {nf}", p))
            if loc.nightlords_cleared:
                add_rule(location, lambda state, n=loc.nightlords_cleared: self._cleared_count(state, n))
            if loc.category == "Deep":
                depth = int(loc.name.rsplit(" ", 1)[1])
                if depth > 1:
                    prev = f"Deep of Night: Reach Depth {depth - 1}"
                    add_rule(location, lambda state, pl=prev: state.can_reach_location(pl, p))

        # Nightlord "Cleared" event mirrors the Nightlord kill location
        for nl in self._active_nightlords():
            ev = self.get_location(f"Event: {nl.expedition} Cleared")
            kill = f"Nightlord: {nl.boss} Defeated"
            set_rule(ev, lambda state, k=kill: state.can_reach_location(k, p))

        goal = self.options.goal
        if goal == Goal.option_heolstor:
            victory_rule = lambda state: state.has("Night Aspect Cleared", p)
        elif goal == Goal.option_all_base_nightlords:
            base = [f"{nl.expedition} Cleared" for nl in NIGHTLORDS if not nl.dlc]
            victory_rule = lambda state, b=tuple(base): state.has_all(b, p)
        else:
            allnl = [f"{nl.expedition} Cleared" for nl in self._active_nightlords()]
            victory_rule = lambda state, a=tuple(allnl): state.has_all(a, p)
        set_rule(self.get_location("Event: Victory"), victory_rule)
        self.multiworld.completion_condition[p] = lambda state: state.has("Victory", p)

    # ------------------------------------------------------------------ output
    def fill_slot_data(self) -> Mapping[str, Any]:
        data = self.options.as_dict("goal", "dlc_forsaken_hollows", "expedition_locks", "nightfarer_shuffle",
                                    "remembrance_locks", "shifting_earth_locks", "night_boss_checks",
                                    "field_boss_checks", "vessel_checks", "per_run_checks", "deep_of_night_checks",
                                    "seamless_coop", "death_link")
        data["starting_nightfarer"] = self.starting_nightfarer
        data["world_version"] = "0.2.0"
        data["location_flags"] = {BASE_ID + l.offset: l.flag for l in ALL_LOCATIONS if l.offset is not None}
        data["nightlord_defeat_flags"] = [nl.defeat_flag for nl in NIGHTLORDS]
        data["nightfarer_unlock_flags"] = [nf.unlock_flag for nf in NIGHTFARERS]
        data["remembrance_flag_ranges"] = {nf.name: list(nf.remembrance_flags) for nf in NIGHTFARERS}
        return data
