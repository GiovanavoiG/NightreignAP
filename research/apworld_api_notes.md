# Archipelago APWorld API — practical reference

Source of truth: `/home/claude/Archipelago`, `main` @ `1e1efa3f5c8fd0a63df0d0f95ec6c824e413318a`
(2026-08-31, "Wargroove: actually import Items (#6422)"), `Utils.__version__ = "0.6.8"`.
Everything below was verified against that checkout (docs/, `worlds/AutoWorld.py`, `BaseClasses.py`,
`Options.py`, `CommonClient.py`, `worlds/apquest`, `worlds/dark_souls_3`, `worlds/kh1`, `worlds/kh2/ClientStuff/Client.py`).

## Environment notes (this sandbox)

- PyPI and apt mirrors are blocked by the egress policy; `pip install -r requirements.txt` fails. Installed manually:
  `schema` (0.7.7) and `websockets` (13.1) copied from GitHub source into site-packages, `bsdiff4` built from source
  with `setup.py build_ext --inplace`. Missing (non-essential for generation): `jellyfish`, `orjson`, `cython`/`cymem`
  (`_speedups` falls back to pure Python), `kivy` (no GUI), `pymem`.
- Always run with `SKIP_REQUIREMENTS_UPDATE=1` so `ModuleUpdate.py` does not try to pip-install (and block on `input()`).
- Verified: `python Generate.py --help` works; a full APQuest generation succeeds; `AP_TEST_WORLDS=apquest python -m unittest discover -s worlds/apquest/test -t .` passes 40 tests.
- `worlds/clique` no longer exists on main; **`worlds/apquest`** is the official reference/tutorial world (read its `!READ_FIRST!.txt`).

## Package layout

```
worlds/<name>/
  archipelago.json      # REQUIRED manifest: {"game": "...", "minimum_ap_version": "0.6.8", "world_version": "1.0.0", "authors": [...]}
  __init__.py           # must expose the World subclass (AP only imports __init__.py)
  world.py / items.py / locations.py / regions.py / rules.py / options.py / web_world.py   # convention (APQuest)
  components.py         # optional: registers a Launcher Component (client)
  client/               # optional: your CommonClient-based client
  docs/en_<Game Name>.md   # game info page (required)
  docs/setup_en.md         # tutorial referenced by WebWorld.tutorials (required)
  test/__init__.py / test/bases.py / test/test_*.py   # WorldTestBase tests
  requirements.txt      # optional extra pip deps (e.g. Pymem)
  .apignore             # optional gitignore-style excludes for packaging
```
Rules: relative imports inside the package (`from .options import X`), absolute imports for core
(`from Options import Toggle`, `from worlds.AutoWorld import World`). Every subfolder with `.py` needs an `__init__.py`.

**Packaging**: an `.apworld` is a zip, all-lowercase name, containing exactly one top-level folder with the same name
(`mygame.apworld` → `mygame/__init__.py`). Build with the Launcher component: `python Launcher.py "Build APWorlds" -- "Game Name"`
→ output in `build/apworlds/`; it injects `version`/`compatible_version` (APContainer version) into `archipelago.json`.
Users drop it into `custom_worlds/` (source install) or `lib/worlds/` (frozen); `worlds/__init__.py` loads `*.apworld` from both.

## World subclass (`worlds/AutoWorld.py`)

```python
from worlds.AutoWorld import World, WebWorld
from BaseClasses import Region, Location, Entrance, Item, ItemClassification, LocationProgressType, Tutorial, MultiWorld, CollectionState
from Options import PerGameCommonOptions, OptionGroup
from worlds.generic.Rules import set_rule, add_rule, forbid_item, add_item_rule

class MyGameItem(Item):       game = "My Game"
class MyGameLocation(Location): game = "My Game"

class MyGameWeb(WebWorld):
    theme = "stone"                    # dirt|grass|grassFlowers|ice|jungle|ocean|partyTime|stone
    bug_report_page = "https://..."
    tutorials = [Tutorial("Multiworld Setup Guide", "desc", "English", "setup_en.md", "setup/en", ["author"])]
    option_groups = [OptionGroup("Gameplay", [HardMode, ...])]
    options_presets = {"preset name": {"hard_mode": True, ...}}
    rich_text_options_doc = True
    item_descriptions / location_descriptions = {...}  # optional

class MyGameWorld(World):
    """Docstring = game description on WebHost."""
    game = "My Game"                                  # ClassVar[str], must be unique
    web = MyGameWeb()
    options_dataclass = MyGameOptions                 # ClassVar[type[PerGameCommonOptions]]
    options: MyGameOptions                            # type hint only (colon!)
    item_name_to_id: ClassVar[dict[str, int]] = {...} # ids 1..2**53-1, recommend < 2**31; 0/negative reserved
    location_name_to_id: ClassVar[dict[str, int]] = {...}
    item_name_groups: ClassVar[dict[str, set[str]]] = {"Weapons": {...}}   # usable by !hint and state.has_group
    location_name_groups: ClassVar[dict[str, set[str]]] = {}
    topology_present = False          # True -> spoiler shows region paths
    origin_region_name = "Menu"       # start region; player is assumed able to return here at any time
    explicit_indirect_conditions = True
    required_client_version = (0, 1, 6); required_server_version = (0, 5, 0)
    hidden = False                    # hide from WebHost
    settings: ClassVar[MyGameSettings]  # optional host.yaml settings group (settings.Group)
    # provided at runtime: self.multiworld, self.player, self.random (seeded Random), self.settings,
    # cls.item_id_to_name / location_id_to_name / item_names / location_names, self.player_name
```

### Lifecycle (called in this order by `Main.py`; each also has an optional `stage_<name>(cls, multiworld, ...)` classmethod)

| Method | Purpose |
|---|---|
| `stage_assert_generate(cls, multiworld)` | classmethod; check prerequisite files |
| `generate_early(self)` | read options into instance attrs; options + RNG available; last chance to touch local/non_local items |
| `create_regions(self)` | build Regions, Locations (incl. events), connect entrances; add to `self.multiworld.regions` |
| `create_items(self)` | append to `self.multiworld.itempool`; count must equal unfilled locations. After this no items/locations/regions can be added/removed |
| `set_rules(self)` | access rules / item rules; set `completion_condition` |
| `connect_entrances(self)` | entrance randomization; all entrances must be connected by the end |
| `generate_basic(self)` | non-logic randomization |
| `pre_fill(self)` / `fill_hook(...)` / `post_fill(self)` | manipulate placement around fill; `get_pre_fill_items()` returns items you place yourself |
| `generate_output(self, output_directory)` | write ROM/mod; `self.multiworld.get_filled_locations(self.player)` |
| `fill_slot_data(self) -> Mapping[str, Any]` | JSON-able dict sent to client on Connect; usually `self.options.as_dict("a", "b")` |
| `modify_multidata(self, multidata)`, `extend_hint_information(...)`, `write_spoiler*(...)` | rarely needed |
| `create_item(self, name) -> Item` | **required**; may be called with no multiworld (MultiServer) |
| `get_filler_item_name(self) -> str` | **required in practice**; must return an infinitely repeatable item |
| `collect(state, item)` / `remove(state, item)` | override for LogicMixin-style derived state |

Helpers on `World`: `self.get_region(name)`, `get_location(name)`, `get_entrance(name)`, `get_locations()`,
`push_precollected(item)` (start inventory), `create_filler()`, `set_rule(spot, rule)`, `set_completion_rule(rule)`,
`create_entrance(from_region, to_region, rule, name)`, `self.multiworld.get_unfilled_locations(self.player)`.

### Regions / Locations / Entrances (`BaseClasses.py`)

```python
menu = Region("Menu", self.player, self.multiworld)         # Region(name, player, multiworld, hint=None)
area = Region("Area", self.player, self.multiworld)
self.multiworld.regions += [menu, area]
area.add_locations({"Chest 1": 1001, "Chest 2": 1002}, MyGameLocation)   # {name: id}; id None -> event
area.locations.append(MyGameLocation(self.player, "Boss", None, area))   # Location(player, name, address, parent)
# events: item with code None on location with address None
victory = area.add_event("Defeat Boss", "Victory", rule=None, location_type=MyGameLocation, item_type=MyGameItem)
loc.place_locked_item(MyGameItem("Victory", ItemClassification.progression, None, self.player))  # manual equivalent
self.multiworld.completion_condition[self.player] = lambda state: state.has("Victory", self.player)
# connections
menu.connect(area)                                                    # Entrance named "Menu -> Area"
menu.connect(area, "Front Door", lambda state: state.has("Key", self.player))   # connect(region, name=None, rule=None)
area.add_exits({"Boss Room": "Boss Door"}, {"Boss Room": lambda s: s.has("Sword", self.player)})  # target regions must exist
e = Entrance(self.player, "Go To X", parent_region); parent.exits.append(e); e.connect(target)   # low-level (DS3/KH1 style)
loc.progress_type = LocationProgressType.EXCLUDED  # DEFAULT | PRIORITY | EXCLUDED
```
`Item(name, classification, code, player)`; `ItemClassification` is an IntFlag: `filler`, `progression`, `useful`,
`trap`, `skip_balancing`, `deprioritized`, plus combos `progression_skip_balancing`, `progression_deprioritized`,
`progression_deprioritized_skip_balancing`; combine with `|` (e.g. `progression | useful`). Anything referenced by
logic MUST be `progression`.

### Rules

```python
from worlds.generic.Rules import set_rule, add_rule, forbid_item, add_item_rule
set_rule(self.get_location("Chest 2"), lambda state: state.has("Sword", self.player))
add_rule(self.get_entrance("Boss Door"), lambda state: state.has("Key", self.player, 2), combine="and")  # or "or"
add_item_rule(loc, lambda item: item.player != self.player or item.name != "Sword")
forbid_item(loc, "Sword", self.player)
```
`CollectionState` API: `has(item, player, count=1)`, `has_all(items, player)`, `has_any`, `has_all_counts`,
`has_any_count`, `count(item, player)`, `has_group(group, player, count=1)`, `has_group_unique`,
`can_reach_region(name, player)`, `can_reach_location`, `can_reach_entrance`. Using `can_reach*` inside an
**entrance** rule requires `self.multiworld.register_indirect_condition(region, entrance)`.

New declarative alternative (used by APQuest): `from rule_builder.rules import Has, HasAll, HasAny, CanReachRegion, ...`,
`from rule_builder.options import OptionFilter`; combine with `&`/`|`, assign via `self.set_rule(spot, Has("Key"))`
and `self.set_completion_rule(Has("Victory"))`; handles indirect conditions automatically (see `docs/rule builder.md`).

### Options (`Options.py`, `docs/options api.md`)

```python
from dataclasses import dataclass
from Options import Toggle, DefaultOnToggle, Choice, TextChoice, Range, NamedRange, FreeText, OptionSet, OptionList, \
    OptionDict, OptionCounter, ItemSet, ItemDict, LocationSet, StartInventoryPool, DeathLink, DeathLinkMixin, \
    PerGameCommonOptions, OptionGroup, Visibility

class HardMode(Toggle):                      # 0/1; DefaultOnToggle defaults to 1
    """Docstring is the user-facing help text."""
    display_name = "Hard Mode"
class Difficulty(Choice):
    display_name = "Difficulty"
    option_easy = 0; option_normal = 1; option_hard = 2
    alias_beginner = 0
    default = 1
class BossHP(Range):
    display_name = "Boss HP"; range_start = 100; range_end = 10000; default = 2000
class Hidden(Choice):
    visibility = Visibility.none             # none|template|simple_ui|complex_ui|spoiler|all

@dataclass
class MyGameOptions(PerGameCommonOptions, DeathLinkMixin):   # DeathLinkMixin adds `death_link: DeathLink`
    hard_mode: HardMode
    difficulty: Difficulty
    boss_hp: BossHP
    start_inventory_from_pool: StartInventoryPool          # opt-in: removes start items from the pool
```
`PerGameCommonOptions` already includes `local_items, non_local_items, start_inventory, start_hints,
start_location_hints, exclude_locations, priority_locations, item_links, plando_items` (plus `accessibility`,
`progression_balancing` from `CommonOptions`). Access: `self.options.hard_mode` (truthy), `.value` (int/str/set),
`self.options.difficulty == "hard"` / `== Difficulty.option_hard`, `self.options.as_dict("a", "b")`.

## Generation & tests

```bash
cd /home/claude/Archipelago && export SKIP_REQUIREMENTS_UPDATE=1
# YAML in a directory (Players/ by default). Minimal:
#   name: Tester
#   game: My Game
#   My Game:
#     hard_mode: true
python Generate.py --player_files_path /home/claude/research/players --outputpath /home/claude/research/output --seed 1
# -> AP_<seed>.zip containing the .archipelago multidata and spoiler log
python Launcher.py "Generate Template Options"          # writes Players/Templates/<Game>.yaml
python -m unittest discover -s worlds/<name>/test -t .  # world tests
AP_TEST_WORLDS=<folder> python -m unittest test.general # core suite scoped to one world (works with pytest too)
```
Tests (`test/bases.py`): subclass `WorldTestBase` with `game = "My Game"` and optional class-level
`options = {...}`; helpers `collect_by_name`, `collect_all_but`, `get_item_by_name`, `remove`,
`can_reach_location`, `assertAccessDependency(locations, [["Sword"], ["Axe"]], only_check_listed=False)`;
it auto-runs `test_all_state_can_reach_everything`, `test_empty_state_can_reach_something`, `test_fill`.

## Precedents

- **Dark Souls III** (`worlds/dark_souls_3`): data-driven `DS3ItemData`/`DS3LocationData` dataclasses with auto-assigned
  ids from `base_id = 100000`; `create_region(name, location_table)` builds one Region per area with `Entrance` objects
  appended by hand; non-randomized locations get locked event items so logic still knows about them; rules via
  `add_rule` wrappers `_add_location_rule` / `_add_entrance_rule` (string = item name shortcut); `fill_slot_data` ships
  AP-id→game-id maps and option values. Its client is **not** Python: an external C++ DLL mod
  (`nex3/Dark-Souls-III-Archipelago-client`, uses apclientpp) — the apworld ships no client.
- **KH1** (`worlds/kh1`): `Regions.py` table of `KH1RegionData(locations, region_exits)`; `create_regions` builds regions
  + exits, `connect_entrances()` links `get_entrance(x).connect(get_region(x))` later; `Rules.py` uses `add_rule`.
- **KH2** (`worlds/kh2/ClientStuff/Client.py`): the in-repo pymem memory-reading Python client — the model for a
  Windows process-memory client. Only KH2 uses pymem in the repo (`from pymem import pymem`).

## Pymem client skeleton (`CommonClient.py`)

```python
# worlds/mygame/client.py
import asyncio, typing
from pymem import pymem                      # worlds/mygame/requirements.txt: Pymem>=1.10.0
from CommonClient import CommonContext, ClientCommandProcessor, server_loop, gui_enabled, logger, get_base_parser, handle_url_arg
from NetUtils import ClientStatus, NetworkItem
import Utils

class MyGameCommandProcessor(ClientCommandProcessor):
    def _cmd_deathlink(self):                 # becomes "/deathlink" in the client
        """Toggle death link"""
        self.ctx.death_link_enabled = not self.ctx.death_link_enabled
        asyncio.create_task(self.ctx.update_death_link(self.ctx.death_link_enabled))

class MyGameContext(CommonContext):
    command_processor = MyGameCommandProcessor
    game = "My Game"
    items_handling = 0b111                     # 0b001 remote items, 0b010 own-world items, 0b100 starting inventory
    want_slot_data = True

    def __init__(self, server_address, password):
        super().__init__(server_address, password)
        self.proc: typing.Optional[pymem.Pymem] = None
        self.slot_data: dict = {}
        self.items_given = 0                   # index into ctx.items_received already applied in-game
        self.death_link_enabled = False
        self.goal_sent = False

    async def server_auth(self, password_requested: bool = False):
        if password_requested and not self.password:
            await super().server_auth(password_requested)
        await self.get_username()              # prompts for slot name if not given
        await self.send_connect()              # sends Connect with game/tags/items_handling/uuid

    def on_package(self, cmd: str, args: dict):
        if cmd == "Connected":
            self.slot_data = args.get("slot_data", {})
            # ctx.slot, ctx.team, ctx.missing_locations, ctx.checked_locations are set by CommonClient already
            asyncio.create_task(self.update_death_link(bool(self.slot_data.get("death_link"))))
        elif cmd == "ReceivedItems":
            pass                               # ctx.items_received (list[NetworkItem]) is maintained for you
        elif cmd == "RoomInfo":
            self.seed_name = args["seed_name"]

    def on_deathlink(self, data: dict):        # dispatched from a "Bounced" packet with the DeathLink tag
        super().on_deathlink(data)             # updates ctx.last_death_link and logs
        self.pending_death = True              # apply to the game in the watcher

    def make_gui(self):
        ui = super().make_gui(); ui.base_title = "Archipelago My Game Client"; return ui

def attach(ctx: MyGameContext) -> bool:
    try:
        ctx.proc = pymem.Pymem("mygame.exe"); return True
    except Exception:
        ctx.proc = None; return False

async def game_watcher(ctx: MyGameContext):
    while not ctx.exit_event.is_set():
        try:
            if ctx.proc is None and not attach(ctx):
                await asyncio.sleep(3); continue
            if ctx.server and ctx.slot:        # connected & authenticated
                base = ctx.proc.base_address    # or ctx.proc.process_base.lpBaseOfDll
                # 1) locations: read flags -> AP ids
                new_checks = {loc_id for loc_id in ctx.missing_locations if flag_is_set(ctx.proc, base, loc_id)}
                if new_checks:
                    await ctx.check_locations(new_checks)   # == send_msgs([{"cmd": "LocationChecks", "locations": [...]}])
                    ctx.locations_checked |= new_checks
                # 2) items: apply anything not yet granted (items_received order is authoritative, resync-safe)
                while ctx.items_given < len(ctx.items_received):
                    item: NetworkItem = ctx.items_received[ctx.items_given]
                    give_item(ctx.proc, base, item.item)    # ctx.item_names.lookup_in_game(item.item) for the name
                    ctx.items_given += 1
                # 3) death link
                if ctx.death_link_enabled:
                    if getattr(ctx, "pending_death", False):
                        kill_player(ctx.proc, base); ctx.pending_death = False
                    elif player_died(ctx.proc, base):
                        await ctx.send_death(f"{ctx.player_names[ctx.slot]} died.")   # Bounce with tags ["DeathLink"]
                # 4) goal
                if not ctx.goal_sent and goal_reached(ctx.proc, base):
                    await ctx.send_msgs([{"cmd": "StatusUpdate", "status": ClientStatus.CLIENT_GOAL}])
                    ctx.finished_game = True; ctx.goal_sent = True
        except pymem.exception.PymemError:
            logger.info("Lost game process"); ctx.proc = None
        await asyncio.sleep(0.5)

def launch(*launch_args: str):
    async def main(args):
        ctx = MyGameContext(args.connect, args.password)
        ctx.server_task = asyncio.create_task(server_loop(ctx), name="server loop")
        if gui_enabled:
            ctx.run_gui()
        ctx.run_cli()
        watcher = asyncio.create_task(game_watcher(ctx), name="GameWatcher")
        await ctx.exit_event.wait()
        ctx.server_address = None
        await watcher
        await ctx.shutdown()
    parser = get_base_parser(description="My Game Client")
    parser.add_argument("url", nargs="?", help="archipelago://... URL")
    args = handle_url_arg(parser.parse_args(launch_args), parser=parser)
    import colorama; colorama.just_fix_windows_console()
    asyncio.run(main(args))
    colorama.deinit()
```
Register it in the Launcher (`worlds/mygame/components.py`, imported from `__init__.py`):
```python
from worlds.LauncherComponents import Component, Type, components, launch
def run_client(*args): 
    from .client import launch as launch_client
    launch(launch_client, name="MyGameClient", args=args)
components.append(Component("My Game Client", func=run_client, game_name="My Game", component_type=Type.CLIENT, supports_uri=True))
```
Key `CommonContext` state: `ctx.slot`, `ctx.team`, `ctx.auth` (slot name), `ctx.player_names[slot]`,
`ctx.missing_locations` / `ctx.checked_locations` / `ctx.server_locations` (from server), `ctx.locations_checked`
(client-side set), `ctx.items_received: list[NetworkItem(item, location, player, flags)]`, `ctx.finished_game`,
`ctx.tags` (add `"DeathLink"` via `update_death_link`), `ctx.exit_event`, `ctx.item_names.lookup_in_game(id)`,
`ctx.location_names.lookup_in_game(id)`, `ctx.stored_data` + `ctx.set_notify(key)` for data storage.
Network messages: `LocationChecks {locations:[ids]}`, `StatusUpdate {status: ClientStatus.CLIENT_GOAL(30)}`,
`Sync`, `LocationScouts`, `Bounce {tags:["DeathLink"], data:{time, source, cause}}`, `Set`/`Get`/`SetNotify`.
