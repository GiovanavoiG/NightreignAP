from dataclasses import dataclass

from Options import (Choice, DeathLinkMixin, DefaultOnToggle, OptionGroup, PerGameCommonOptions, Range,
                     StartInventoryPool, Toggle)


class Goal(Choice):
    """
    heolstor: defeat Heolstor the Nightlord (Night Aspect).
    all_base_nightlords: defeat all 8 base-game Nightlords.
    all_nightlords: defeat every Nightlord including DLC (requires the DLC option).
    """
    display_name = "Goal"
    option_heolstor = 0
    option_all_base_nightlords = 1
    option_all_nightlords = 2
    default = 0


class DlcForsakenHollows(Toggle):
    """
    The Forsaken Hollows (Dec 2025): adds Scholar and Undertaker, the Balancers and Dreglord expeditions,
    The Great Hollow Shifting Earth and three DLC night bosses. Requires owning the DLC.
    """
    display_name = "DLC: The Forsaken Hollows"


class ExpeditionLocks(DefaultOnToggle):
    """
    Expeditions are locked until the matching "Expedition Access" item is received. Tricephalos is
    always available from the start. Off: vanilla unlock order (defeat Gladius to open the rest).
    """
    display_name = "Expedition Locks"


class NightfarerShuffle(DefaultOnToggle):
    """
    Nightfarers are items. You start with one (see Starting Nightfarer) and unlock the rest from the
    multiworld. Off: the six base Nightfarers are usable from the start (Duchess/Revenant via their quests).
    """
    display_name = "Shuffle Nightfarers"


class StartingNightfarer(Choice):
    """Which Nightfarer you begin with when Nightfarers are shuffled."""
    display_name = "Starting Nightfarer"
    option_random_nightfarer = 0
    option_wylder = 1
    option_guardian = 2
    option_ironeye = 3
    option_raider = 4
    option_recluse = 5
    option_executor = 6
    default = 0


class RemembranceLocks(Choice):
    """
    How Remembrance chapters (82 locations) are gated.
    none: only the Nightfarer is needed.
    key: one "Remembrance Key: <Nightfarer>" item unlocks all of that Nightfarer's chapters (10 items).
    progressive: each chapter needs one more "Progressive Remembrance: <Nightfarer>" (82 items).
    """
    display_name = "Remembrance Locks"
    option_none = 0
    option_key = 1
    option_progressive = 2
    default = 1


class ShiftingEarthLocks(DefaultOnToggle):
    """Shifting Earth events only appear once the matching item is received; clearing each one is a location."""
    display_name = "Shifting Earth Locks"


class NightBossChecks(DefaultOnToggle):
    """First kill of each Night 1 / Night 2 boss is a location."""
    display_name = "Night Boss Checks"


class FieldBossChecks(DefaultOnToggle):
    """First kill of each field / evergaol / POI boss is a location."""
    display_name = "Field Boss Checks"


class VesselChecks(DefaultOnToggle):
    """Buying each Goblet and Grail at the Small Jar Bazaar is a location; vessels become items."""
    display_name = "Vessel Checks"


class PerRunChecks(Toggle):
    """
    Adds per-run challenge locations: survive Night 1 / Night 2 / defeat a Nightlord with each Nightfarer,
    plus nine general run challenges (Grand relic, level 15, legendary upgrade, evergaol, ...).
    """
    display_name = "Per-Run Challenge Checks"


class RunChallengePool(Choice):
    """
    Which per-run challenge locations are used when Per-Run Challenge Checks is on.
    basic: 3 per Nightfarer + 9 general (39). extended: adds 3 more per Nightfarer + 20 general (89 total).
    """
    display_name = "Run Challenge Pool"
    option_basic = 0
    option_extended = 1
    default = 0


class DeepOfNightChecks(Toggle):
    """Reaching each Deep of Night depth is a location; a Deep of Night Access item is added."""
    display_name = "Deep of Night Checks"


class SeamlessCoop(Toggle):
    """
    Play expeditions through Seamless Co-op. The host's mod is authoritative: kills and progress in the
    host's session send the host's checks. Guests do not need the Archipelago mod. (Solo is the primary
    supported mode; treat this as experimental.)
    """
    display_name = "Seamless Co-op"


class TrapPercentage(Range):
    """Percentage of filler replaced by traps."""
    display_name = "Trap Percentage"
    range_start = 0
    range_end = 100
    default = 10


@dataclass
class NightreignOptions(PerGameCommonOptions, DeathLinkMixin):
    goal: Goal
    dlc_forsaken_hollows: DlcForsakenHollows
    expedition_locks: ExpeditionLocks
    nightfarer_shuffle: NightfarerShuffle
    starting_nightfarer: StartingNightfarer
    remembrance_locks: RemembranceLocks
    shifting_earth_locks: ShiftingEarthLocks
    night_boss_checks: NightBossChecks
    field_boss_checks: FieldBossChecks
    vessel_checks: VesselChecks
    per_run_checks: PerRunChecks
    run_challenge_pool: RunChallengePool
    deep_of_night_checks: DeepOfNightChecks
    seamless_coop: SeamlessCoop
    trap_percentage: TrapPercentage
    start_inventory_from_pool: StartInventoryPool


option_groups = [
    OptionGroup("Goal & DLC", [Goal, DlcForsakenHollows]),
    OptionGroup("Structure", [ExpeditionLocks, NightfarerShuffle, StartingNightfarer, RemembranceLocks,
                              ShiftingEarthLocks]),
    OptionGroup("Location Pools", [NightBossChecks, FieldBossChecks, VesselChecks, PerRunChecks, RunChallengePool,
                                   DeepOfNightChecks]),
    OptionGroup("Item Pool & Play", [TrapPercentage, SeamlessCoop]),
]
