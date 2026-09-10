# Elden Ring: Nightreign (PC) — memory signatures / offsets / event flags for an Archipelago mod DLL

Compiled 2026-09-10. Target: `nightreign.exe` App Ver. **1.03.2** (Regulation Ver. **1.03.5**, see §7).

Every item is tagged:
- **[NR-CONFIRMED]** — read directly from Nightreign data or Nightreign-specific code/tables.
- **[ER-ONLY]** — Elden Ring (`eldenring.exe`) values/patterns. Same engine generation; useful as *templates* to re-scan, but NOT valid Nightreign RVAs.
- **[INFERRED]** — my inference; verify before shipping.

Sources cloned locally for inspection (all public GitHub):
`/home/claude/research/fromsoftware-rs` (vswarte, HEAD 16d2661, 2026-09-08), `/home/claude/research/from-singleton` (Dasaav-dsv), `/home/claude/research/me3` (garyttierney), `/home/claude/research/4laric-fsap` (4laric/from-software-archipelago-clients, ER AP client), `/home/claude/research/nightreign-enemy-rando` (4laric), `/home/claude/research/Elden-Ring-Nightreign-Save-Editor` (alfizari), `/home/claude/research/Elden-Ring-Nightreign-Cheat-Table` (kwwsyk), `/home/claude/research/Erd-Tools` (Nordgaren), `/home/claude/research/SoulsRandomizers` (thefifthmatt), `/home/claude/research/eldenring-practice-tool` (veeenu).

---

## 0. TL;DR

1. **No public Nightreign-specific AOB/RVA list exists** for GameDataMan / CSEventFlagMan / WorldChrMan / SoloParamRepository / CSMenuMan / ItemGib / Get/SetEventFlag. Every Nightreign cheat table found (kwwsyk GitHub .CT, Hexinton Nexus #127, ColonelRVH v1.7 for 1.03.2, matthew80 vgtimes, alfzari911 Nexus #725, Cissa90 Relic Editor Nexus #125) either ships no AOBs in public text or is behind fearlessrevolution.com (blocked to non-browser fetch, Wayback/archive.ph also blocked from this sandbox) / Yandex disk. **[NR-CONFIRMED absence after ~30 searches/fetches]**
2. **The DLRF/FD4 singleton scanner works on Nightreign without any RVAs.** `me3` (the mod loader every Nightreign mod uses) calls `from_singleton::address_of::<CSSystemProperties>()` in production on `Game::Nightreign` (`crates/mod-host/src/host/game_properties.rs`). So `CSEventFlagMan`, `WorldChrMan`, `SoloParamRepository`, `CSMenuMan`, `MapItemMan`, `MsgRepository` etc. can be located by *name* at runtime via `from-singleton` / `fromsoftware-shared::FromStatic`. `GameDataMan` is **not** a DLRF singleton in ER (the `eldenring` crate resolves it by pinned RVA), so it needs an AOB (ER template in §3). **[NR-CONFIRMED for the scanner; INFERRED for GameDataMan]**
3. The `nightreign` crate in fromsoftware-rs (v0.14.0, 2026-05-29) contains **only** a generated `param.rs` (59k lines, 230+ param structs) and no `cs`/`rva`/singleton code. **[NR-CONFIRMED]**
4. **Nightreign event-flag IDs recovered from the regulation.bin** bundled in 4laric's enemy rando (decrypted locally): Nightlord defeat flags **150–162** (Everdark **170–181**), Nightlord unlock flags 110/115/130/135/136, Nightfarer unlock flags **6031 (Duchess) / 6037 (Revenant) / 6038 (Scholar) / 6039 (Undertaker)**, vessel (AntiqueStand) unlock flags **60010–60530 range**, Remembrance objective flags **1009101–1009817 & 1029900–1029926**. See §5. **[NR-CONFIRMED from params; boss-name-to-row mapping INFERRED]**
5. Patch: App 1.03.2 released **2026-01-15** (Regulation 1.03.4); Hotfix **1.03.5 on 2026-03-31 was regulation-only ("App Ver. remains 1.03.2")**. No exe change since January 2026, so any 1.03.2 signatures remain valid today. **[NR-CONFIRMED]**

---

## 1. How fromsoftware-rs resolves FD4 singletons (and why it works for Nightreign)

### 1.1 The mechanism (crate `fromsoftware-shared` → dependency `from-singleton = "3"`)

`crates/shared/src/static.rs` (fromsoftware-rs):

```rust
/// Looks up instances of singleton instances by their name. Some singletons
/// aren't necessarily always instanciated and available. Discovered singletons
/// are cached so invokes after the first will be much faster.
impl<T: FromSingleton> FromStatic for T {
    fn name() -> Cow<'static, str> { <Self as FromSingleton>::name() }
    /// ... the caller must ensure that the main module (the exe) is a From Software title
    /// with DLRF reflection data, and that the DLRF reflection metadata has been
    /// populated (usually by calling the current game's `wait_for_system_init`
    /// function).
    fn instance_ptr() -> InstanceResult<*mut T> {
        address_of::<T>().map(|nn| nn.as_ptr()).ok_or(InstanceError::NotFound(Self::name()))
    }
}
```

`from-singleton/src/lib.rs` (Dasaav-dsv/from-singleton, https://github.com/Dasaav-dsv/from-singleton):

```rust
/// Returns a pointer to a singleton instance using Dantelion2 reflection. ...
pub fn address_of<T>() -> Option<NonNull<T>> where T: FromSingleton + Sized {
    let static_ptr = static_of::<T>()?;
    unsafe { NonNull::new(static_ptr.read()) }
}
static DERIVED_SINGLETON_MAP: LazyLock<FD4SingletonMap> = LazyLock::new(|| unsafe {
    let image_base = GetModuleHandleW(ptr::null());
    let pe = pelite::pe::PeView::module(image_base as _);
    find::derived_singletons(pe)
});
static PARTIAL_SINGLETON_MAP: LazyLock<FD4SingletonPartialResult> = LazyLock::new(|| unsafe {
    ... find::fd4_singletons(pe)
});
```

`from-singleton/src/find.rs`: two byte-pattern walkers over `.text` (no fixed AOB string; they decode instruction shapes):
- **`FD4DerivedSingleton`** pattern: `mov rax,[rip+disp32]` (static slot) → `test rax,rax` (REX.W, mod=11, reg==rm) → `jne/jnz` → `lea rdx/r8,[rip+disp32]` (the class-name C string). The static slot must be in `.data`; the name is read as a C string.
- **`FD4Singleton`** pattern: same `mov`/`test`/`jne` prefix then `lea rcx,[rip+disp32]` (a DLRF reflection primitive) + `call rel32` (the `get_name` function, captured once). Names are only known after DLRF is initialised, hence `FD4SingletonPartialResult::finish()` is `unsafe`.
- Constants used: `REX_W = 0x48`, `JNE_SHORT = 0x75`, `JNE = 0f 85`, `CALL = 0xe8`, `LEA_RCX = 48 8d 0d`, `LEA_R8 = 4c 8d 05`, `LEA_R9 = 4c 8d 0d`, `MOV_R9 = 4c 8b c8`.
- README: "Supported games (with versions tested): DS3 1.15.0/1.15.2, Sekiro 1.06, ER 1.16, AC6 1.07.1" — Nightreign not in the README list, but see 1.2. README credit: "The singleton scanner idea is based on work by tremwil and vswarte." fromsoftware-rs README credits "Sfix (for coming up with the FD4 singleton finder approach at all)".

The name used for lookup is the type name (or an override), e.g. in the `eldenring` crate:
```rust
#[shared::singleton("CSEventFlagMan")]
pub struct CSEventFlagMan { pub virtual_memory_flag: CSFD4VirtualMemoryFlag, pub world_type: u32, unk7c: [u8; 0x1f4] }
```
Singleton names the `eldenring` crate registers (all DLRF names, expected identical in NR): `CSActionButtonMan CSAutoInvadePoint CSBulletManager CSCamera CSEventFlagMan CSEventMan CSFade CSFeMan CSFlipper CSGaitem CSHavokMan CSLuaEventMan CSMenuMan CSMouseMan CSNetMan CSNowLoadingHelper CSPairAnimManager CSServerInterface CSSessionManager CSSfx CSTask CSTaskGroup CSTrophy CSWindow CSWorldGeomMan CSWorldSceneDrawParamManager MapItemMan MsbRepository MsgRepository RendMan SoloParamRepository WorldAreaTime WorldChrMan WorldChrManDbg WorldSfxMan`. **[ER-ONLY names; INFERRED same in NR — CSMenuMan/CSEventFlagMan/WorldChrMan/SoloParamRepository/MapItemMan are core Dantelion2 classes]**

**`GameDataMan` is NOT looked up by DLRF** in the `eldenring` crate — it uses a pinned RVA:
```rust
impl FromStatic for GameDataMan {
    fn name() -> Cow<'static, str> { Cow::Borrowed("GameDataMan") }
    fn instance_ptr() -> shared::InstanceResult<*mut Self> {
        unsafe { load_static_indirect(crate::rva::get().game_data_man) }
    }
}
```
So for Nightreign you need an AOB for the GameDataMan static (ER template §3.1). **[NR-relevant]**

### 1.2 Proof the scanner works on Nightreign (me3 production code) [NR-CONFIRMED]

`me3/crates/mod-host/src/host/game_properties.rs` (https://github.com/garyttierney/me3):
```rust
unsafe fn from_singleton(game: Game) -> Option<PropertyMap<'a>> {
    match game {
        Game::DarkSouls3 | Game::Sekiro => unsafe { SprjSystemProperties::get_mut_dyn_map().map(PropertyMap::String) },
        Game::EldenRing | Game::ArmoredCore6 => unsafe { CSSystemProperties::get_mut_dyn_map().map(PropertyMap::String) },
        Game::Nightreign => unsafe { CSSystemProperties::get_mut_dyn_map().map(PropertyMap::Custom) },
    }
}
...
unsafe fn get_mut_dyn_map<'a>() -> Option<&'a mut dyn Tree<T, T>> {
    let instance = unsafe { from_singleton::address_of::<Self>()?.as_mut() };
    ...
impl<T> FromSingleton for CSSystemProperties<T> {
    fn name() -> Cow<'static, str> { Cow::Borrowed("CSSystemProperties") }
}
```
Note the NR-specific twist: on Nightreign the property map key/value type is `DlCustomUtf16Str` rather than `DlUtf16String` — a reminder that NR struct layouts can differ from ER even when class names match.

me3 also locates things on NR by string/RTTI scanning rather than RVAs, e.g. `skip_logos.rs`: finds UTF-16 `"TitleStep::STEP_BeginLogo"` in `.rdata`, finds its pointer in `.data`, and swaps the neighbouring function pointer ("Skip logos (ELDEN RING and later games)").

### 1.3 Version detection / RVA bundles (ER only today)

`crates/shared/src/game_version.rs`: reads the PE VERSIONINFO `dwProductVersion` + `ProductName` + language id (`LANG_ID_EN = 0x0009`, `LANG_ID_JP = 0x0011`). `crates/eldenring/src/rva.rs`:
```rust
const NAME: &'static str = "elden ring";
(LANG_ID_EN, "2.7.1.0") => Some(Self::Ww2710),
(LANG_ID_JP, "2.7.1.1") => Some(Self::Jp2711),
```
RVAs are generated by `tools/binary-mapper` from `crates/eldenring/mapper-profile.toml` (patterns + RTTI `[[vmts]]`). **There is no `crates/nightreign/mapper-profile.toml` and no `rva` module for Nightreign**; running `binary-mapper` against `nightreign.exe` with a copied/adapted profile is the obvious path to NR RVAs. **[NR-CONFIRMED absence]**

### 1.4 What `crates/nightreign/src` contains today [NR-CONFIRMED]

```
crates/nightreign/src/lib.rs   -> "pub mod param;"   (1 line)
crates/nightreign/src/param.rs -> 59,023 lines, generated by tools/param-generator
```
Cargo: `description = "Raw structures and bindings for From Software's title Elden Ring: Nightreign"`, workspace version 0.14.0 (docs.rs: "Latest Version: 0.14.0 (released 2026-05-29)", 12,236 items). Param structs include NR-specific ones: `ANTIQUE_STAND_PARAM_ST, EQUIP_PARAM_ANTIQUE_ST, ATTACHEFFECT_PARAM_ST, ATTACHEFFECT_TABLE_PARAM_ST, HERO_PARAM_ST, HERO_STATUS_PARAM, NIGHT_BOSS_MENU_PARAM_ST, PERSONAL_SCENARIO_PARAM_ST, MISSION_MANAGEMENT_PARAM_ST, MAIN_SCENARIO_MENU_PARAM_ST, MAP_PATTERN_*`, `LOT_BASE_MAP_PATTERN_FLAG_ST`, `PLAY_AREA_CREATE_*`, `SMALLBASE_*`, `ACROSS_DAY_CORRECT_PARAM_ST`, `CLEAR_COUNT_CORRECT_PARAM_ST`, `EVENT_FLAG_USAGE_PARAM_ST`, `DEFEAT_BOSS_SOUL_PARAM_ST`, plus the usual ER ones (`EQUIP_PARAM_GOODS_ST, ITEMLOT_PARAM_ST, SHOP_LINEUP_PARAM, SP_EFFECT_PARAM_ST, NPC_PARAM_ST, ...`).
Relevant generated fields: `NIGHT_BOSS_MENU_PARAM_ST { unknown_0, expedition_name_id, boss_icon_id, unlock_event_flag, defeat_event_flag, unknown_5, boss_name_id, defeated_boss_icon_id, sort_id, description_id, expedition_background_id, ... }`, `HERO_PARAM_ST { ..., character_unlock_flag: i32 @+0x14, character_name_id, ... }`, `ANTIQUE_STAND_PARAM_ST { ..., unlock_flag, goods_id, ... }`, `PERSONAL_SCENARIO_PARAM_ST { ..., objective_flag_id @+8, ..., flashback_flag_id @+0x28, spawnpoint_entity_id }`.

No `cs::`, no `WorldChrMan`, no `CSEventFlagMan`, no RVAs for Nightreign in the crate. The ER `cs` structs can be *tried* against NR (same names), but layouts are unverified.

---

## 2. Reference implementation: how the ER Archipelago client (4laric) uses these — pattern to copy [ER-ONLY code, NR-applicable design]

Repo: https://github.com/4laric/from-software-archipelago-clients (`crates/eldenring-archipelago`, Rust cdylib loaded by me3). Uses `eldenring` crate singletons + 8 client-private RVAs.

`src/flags.rs`:
```rust
pub fn get_event_flag(flag_id: u32) -> bool {
    match unsafe { CSEventFlagMan::instance() } { Ok(m) => m.virtual_memory_flag.get_flag(flag_id), Err(_) => false }
}
pub fn try_set_event_flag(flag_id: u32, enabled: bool) -> bool {
    match unsafe { CSEventFlagMan::instance_mut() } { Ok(m) => { m.virtual_memory_flag.set_flag(flag_id, enabled); ... true } Err(_) => false }
}
pub fn play_region_id() -> Option<i32> { let wcm = unsafe { WorldChrMan::instance() }.ok()?; Some(wcm.main_player.as_ref()?.play_region_id as i32) }
```
i.e. event flags are read/written **directly through the `CSFD4VirtualMemoryFlag` structure** (no GetEventFlag/SetEventFlag function call needed). `eldenring/src/cs/event_flag.rs`:
```rust
pub struct CSFD4VirtualMemoryFlag {
    vftable: usize, allocator: usize, unk10: u32, unk14: u32, unk18: u32,
    pub event_flag_divisor: u32,        // "Used to determine the event flag group."
    pub event_flag_holder_size: u32,    // "Size of an event flag group in bytes."
    pub event_flag_holder_count: u32,   // "Amount of event flag groups."
    pub flag_blocks: *mut FlagBlock,
    pub flag_block_descriptors: DLMap<u32, FlagBlockDescriptor>,
    unk38: [u8; 0x30],
}
impl EventFlag { group = id/1000; byte = (id%1000)/8; bit = 7 - ((id%1000)%8) }
```
Caveat quoted from the client (`reconcile_io.rs`): "flag-block descriptor on this build (CSEventFlagMan::set_flag silently discards" — i.e. writing a flag whose group has no descriptor is a silent no-op.

`src/rva_table.rs` — the client's private ER RVAs, showing exactly what an NR port must re-find:
```rust
pub struct ClientRvas {
    pub add_item_func: usize,        // `AddItemFunc` -- the item-grant hook target (`detour`).
    pub inventory_ptrloc: usize,     // Static slot holding the inventory pointer
    pub lua_warp_func: usize,        // `LuaWarp` entry
    pub cslem_candidates: [usize; 2],// `CSLuaEventManager` static-slot candidates
    pub fmg_repo: usize, pub fmg_search: usize, pub chr_asm_commit: usize,
}
/// Elden Ring 2.7.1.0 Worldwide (the 2026-09-08 patch, Steam build 25080141).
pub const WW2710: ClientRvas = ClientRvas {
    add_item_func: 0x0056_1400, inventory_ptrloc: 0x03D6_BAC0, lua_warp_func: 0x0059_AA60,
    cslem_candidates: [0x03D6_BEB8, 0x03D5_F040], fmg_repo: 0x03D8_1568, fmg_search: 0x0266_FC40, chr_asm_commit: 0x0024_5C00,
};
```
`src/detour.rs` — the item-give function ("AddItemFunc" == community "ItemGib"/`MapItemMan::ItemGib` caller) prologue used as a safety signature and its ABI:
```rust
type AddItemFn = unsafe extern "C" fn(*mut c_void, *mut c_void, *mut c_void, u64) -> u64;
const ADD_ITEM_FUNC_SIG: &[u8] = &[0x40, 0x55, 0x56, 0x57, 0x41, 0x54, 0x41, 0x55, 0x41, 0x56, 0x41, 0x57, 0x48, 0x8D, 0xAC, 0x24];
const ITEMBUF_ENTRY_ID_OFF: usize = 0x04;
const ITEMBUF_ENTRY_OFF: usize = 0x20; // a constructed itembuf's entry sits at buf+0x20
```
(ER Goods FullID packing: `er_code | 0x40000000`; `EquipGameData.last_add_item_result`: Success = 0, UniqueItemDuplicate = 2, InventoryFull = 4.) **[ER-ONLY]**

Inventory walk: "`GameDataMan -> main_player_game_data -> equipment.equip_inventory_data.items_data.items()`"; runes: `GameDataMan.main_player_game_data.rune_count` (`PlayerGameData { ..., pub rune_count: u32, pub rune_memory: u32, ... }`). **[ER-ONLY]**

---

## 3. AOB signature templates (ER) to re-scan in `nightreign.exe` [ER-ONLY — untested on NR]

### 3.1 Nordgaren `Erd-Tools/src/Erd-Tools/Hook/Offsets.cs` (https://github.com/Nordgaren/Erd-Tools)
```
GameDataManAoB           = "48 8B 05 ? ? ? ? 48 85 C0 74 05 48 8B 40 58 C3 C3"
GameManAoB               = "48 8B 05 ? ? ? ? 80 B8 ? ? ? ? 0D 0F 94 C0 C3"
SoloParamRepositoryAoB   = "48 8B 0D ? ? ? ? 48 85 C9 0F 84 ? ? ? ? 45 33 C0 BA 8E 00 00 00"
WorldChrManAoB           = "48 8B 05 ?? ?? ?? ?? 48 85 C0 74 0F 48 39 88"
CSFD4VirtualMemoryFlagAoB= "48 8B 3D ? ? ? ? 48 85 FF 74 ? 48 8B 49"
IsEventCallAoB           = "48 83 EC 28 8B 12 85 D2"                       // GetEventFlag(CSEventFlagMan*, u32* flag)
SetEventCallAoB          = "? ? ? ? ? 48 89 74 24 18 57 48 83 EC 30 48 8B DA 41 0F B6 F8 8B 12 48 8B F1 85 D2 0F 84 ? ? ? ? 45 84 C0"  // SetEventFlag(CSEventFlagMan*, u32* flag, bool)
ItemGiveAoB              = "8B 02 83 F8 0A"          ; ItemGiveOffset = -0x52   (scan hit is inside ItemGib; function start = hit - 0x52)
MapItemManAoB            = "48 8B 0D ? ? ? ? C7 44 24 50 FF FF FF FF C7 45 A0 FF FF FF FF 48 85 C9 75 2E"
//public const string ItemGiveAoB = "40 55 56 57 41 54 41 55 41 56 41 57 48 8D 6C 24 B0 48 81 EC 50 01 00 00 48 C7 45 C0 FE FF FF FF";  (older full-prologue variant)
RemoveItemAoB            = "?? 83 ec ?? 8b f2 ?? 8b e9 ?? 85 c0 74" ; RemoveItemOffset = -0x10
CSLuaEventManagerAoB     = "48 83 3D ? ? ? ? 00 48 8B F9 0F 84 ? ? ? ? 48"
LuaWarp_01AoB            = "C3 ? ? ? ? ? ? 57 48 83 EC ? 48 8B FA 44"
MsgRepositoryImpAoB      = "48 8B 3D ?? ?? ?? ?? 44 0F B6 30 48 85 FF 75"
ChrDebugFlagsAoB         = "80 3D ?? ?? ?? ?? 00 0F 85 ?? ?? ?? ?? 32 C0 48"
WorldAreaWeatherAoB      = "48 8B 15 ? ? ? ? 32 C0 48 85 D2 ? ? 8B 82"
```
`ItemInfoArraySize = 0xA0`. Note that the ER ItemGib prologue (`40 55 56 57 41 54 41 55 41 56 41 57 48 8D 6C 24 ...`) is exactly the `ADD_ITEM_FUNC_SIG` the ER AP client checks (§2), so these are the same function family.

### 3.2 fromsoftware-rs `crates/eldenring/mapper-profile.toml` (mapper DSL: `$ { ' }` = capture rip-relative target)
```
[[patterns]] captures = ["", "game_data_man"]                         pattern = "48 89 05 ${ ' } 48 83 c4 38 e9 ${}"
[[patterns]] captures = ["", "cs_menu_man_imp_display_status_message"] pattern = "ba d0 07 00 00 48 83 c4 28 e9 $ { ' }"
[[patterns]] captures = ["", "world_chr_man_dbg_flags"]               pattern = "80 3d $ { ? ' } 00 0f 85 [4] 32 c0 "
[[patterns]] captures = ["", "runtime_heap_allocator"]                pattern = "e8 [4] 48 8b 05 ${ ' } 48 85 c0 75 0c e8 [4] 48 89 05 [4] 48 89 05 [4]"
[[patterns]] captures = ["", "register_task"]                         pattern = "e8 ? ? ? ? 48 8b 0d ? ? ? ? 4c 8b c7 8b d3 e8 $ { ' }"
[[patterns]] captures = ["", "global_hinstance"]                      pattern = "48 8b ce 48 8b f8 e8 $ { 48 89 0d $ { ' } c3 }"
[[vmts]] class = "CS::ChrIns" vftable = "chr_ins_vmt"   (etc. — RTTI-name based, game-agnostic)
```
ER 2.7.1.0 WW results (`rva_ww.rs`): `game_data_man: 0x3d61f98`, `cs_menu_man_imp_display_status_message: 0x7671f0`, `solo_param_repository_vmt: 0x2bb84c8`, `world_chr_man_dbg_flags: 0x3d6a210`. **[ER-ONLY]**

### 3.3 ER practice tool (veeenu) pointer chains, for the shape of PlayerGameData [ER-ONLY]
`lib/libeldenring/src/pointers.rs`: `runes: pointer_chain!(game_data_man, 0x8, 0x6C)`, `character_stats: pointer_chain!(game_data_man, 0x8, 0x3c)`, `igt: pointer_chain!(game_data_man, 0xA0)`, `character_blessings (V2_07_x): pointer_chain!(game_data_man, 0x8, 0xfc)`.

---

## 4. Nightreign-specific memory data actually found [NR-CONFIRMED but stale]

### 4.1 kwwsyk/Elden-Ring-Nightreign-Cheat-Table (https://github.com/kwwsyk/Elden-Ring-Nightreign-Cheat-Table) — CE 7.5, game **v1.0.2**; README: "**WARNING** In version 1.01.2 this entries are out of date."
Static pointer paths (module `nightreign.exe`, 4-byte values):
```
"夜痕" (Murk):  nightreign.exe+038D6810 -> [+180] -> [+5B8] -> [+E0] -> [+A0] -> [+28] -> [+D0]
rune:           nightreign.exe+045FDCB0 -> [+270] -> [+290] -> [+1B8] -> [+498] -> [+B0] -> [+28] -> [+6C]
HP:             nightreign.exe+0457F208 -> [+168] -> [+0] -> [+28] -> [+1B8] -> [+60] -> [+8] -> [+B70]
MaxHP +B7C, FP +B80, MaxFP +B88, Stamina +B8C, MaxStamina +B94  (same chain)
```
(CE lists offsets last-first; shown here in dereference order.) The rune chain's final `+6C` matches the ER `PlayerGameData` rune offset (`game_data_man, 0x8, 0x6C` in the practice tool), suggesting `PlayerGameData.rune_count` is at `+0x6C` in NR too. **[INFERRED]** README diary (2025-06-10): "nr.exe+137E05C — Break point hit when opening Sparring menu"; "nr.exe+137DEA0 — hit before F interaction tip emerged". No AOBs.

### 4.2 Murk in the save file (alfizari save editor, `src/inventory_handler.py`) — save layout, not process memory
```python
START_OFFEST = 0x14        # Item State Datas start at offset 0x14
STATE_SLOT_COUNT = 5120    # MAX slots count of Item States
ENTRY_SLOT_COUNT = 3065    # MAX slots count of Item Entries
...
cur_offset += 0x94
self.player_name_offset = cur_offset
self.murks_offset = cur_offset + 52
self.sigs_offset = cur_offset - 64
cur_offset += 0x5B8
self.entry_count_offset = cur_offset
```
`murks` is a `<I` at `player_name_offset + 52`; "Sigs" (Sovereign Sigils) at `player_name_offset - 64`. Relic ga_handle type bits: `ITEM_TYPE_RELIC = 0xC0000000` (`ga & 0xF0000000`), goods `0x80000000 | (real_id & 0x00FFFFFF)` (relics live in GaItem space). `UnlockStateManager` is a **placeholder** ("Character unlock parsing is currently a work in progress") — the editor does NOT parse event flags. **[NR-CONFIRMED]**
Hero/vessel numbering used by the editor (`src/globals.py`): `CHARACTER_NAMES = ['Wylder','Guardian','Ironeye','Duchess','Raider','Revenant','Recluse','Executor','Scholar','Undertaker']` (heroType 1..10), `CHARACTER_NAME_ID = [100000,100030,100050,100010,100040,100090,100070,100060,110000,110010]` (NpcName FMG ids).

### 4.3 Other NR cheat tables (no public AOBs)
- Hexinton "Ultimate" table, Nexus NR #127 (v1.0.0, updated 2025-12-17): "item adding murks, player status editing, ... Param manipulation". No AOB text on page.
- ColonelRVH table v1.7 for **game v1.03.2** (2026-01-24, thecheatscript.com): Unlimited Rune / Murk / HP / FP / Stamina, Instant Kill, Force Pause, Speedhack. Download only via Yandex disk.
- fearlessrevolution threads t=35248 (main), t=35231, t=35266 (Relic Editor), t=35990 ("[ARM] Cheat Table 1.02.1"), t=35219 (request) — all blocked (404/robots) from this environment; Wayback/archive.ph also blocked by the proxy.
- alfzari911 "Item and Legal Relics Spawner Table", Nexus NR #725 (2026-06-25): spawns weapons/goods/talismans (i.e. an ItemGib script exists in that .CT — would need the file).
- Cissa90 "Relic Editor CE Table", Nexus NR #125 (v14.0, 2025-12-10).
- matthew80 table (vgtimes, 2025-06-05): "Health, FP, Stamina, Rune, Murk, Infinite Item, ... Player Position".

---

## 5. Nightreign event flag IDs [NR-CONFIRMED — read from regulation.bin params]

Method: decrypted `bundled_regulation/regulation.bin` from 4laric/nightreign-enemy-rando (MMV-based but these params are untouched) with the repo's `regulation_io.py` (`NR_REGULATION_KEY`, AES-CBC → DCX/ZSTD → BND4), parsed rows with the field layouts from `crates/nightreign/src/param.rs`. BND holds 252 params. Decrypted BND saved at `/home/claude/research/nr_regulation.bnd`.

### 5.1 NightBossMenuParam (Nightlord expeditions) — `unlock_event_flag` / `defeat_event_flag`
| row | expedition_name_id | unlock_flag | **defeat_flag** | unk5 | boss_name_id | sort |
|---|---|---|---|---|---|---|
| 0 | 131050 | 0 | **150** | 100100 | 131060 | 10 |
| 1 | 131051 | 110 | **151** | 100200 | 131061 | 20 |
| 2 | 131052 | 110 | **152** | 100300 | 131062 | 30 |
| 3 | 131053 | 110 | **153** | 100400 | 131063 | 40 |
| 4 | 131054 | 110 | **154** | 100500 | 131064 | 50 |
| 5 | 131055 | 110 | **155** | 100600 | 131065 | 60 |
| 6 | 131056 | 110 | **156** | 100700 | 131066 | 70 |
| 7 | 131057 | 115 | **160** | 100800 | 131067 | 100 |
| 8 | 131058 | 135 | **161** | -1 | 131068 | 80 |
| 9 | 131059 | 136 | **162** | -1 | 131069 | 90 |
| 10–16 | 131050–131056 | 150–156 | **170–176** (Everdark) | -1 | 131060–66 | 210–270 |
| 18 | 131058 | 161 | **181** (Everdark) | -1 | 131068 | 280 |
| 100 | 131150 | 130 | 0 | -1 | -1 | 300 |

Interpretation **[INFERRED]**: rows 0–6 = the seven base Nightlords in menu order (Tricephalos/Gladius, Gaping Jaw/Adel, Sentient Pest/Gnoster, Augur/Maris, Equilibrious Beast/Libra, Darkdrift Knight/Fulghor, Fissure in the Fog/Caligo — verify with the Menu FMG ids 131050–131059); row 7 = Night Aspect/Heolstor (unlock 115 after all seven; row 0 unlock 0 = available from start; 110 = "cleared first expedition"); rows 8–9 = the two Forsaken Hollows DLC Nightlords (unlock 135/136); rows 10–18 = Everdark Sovereign variants (unlock = base defeat flag; so Everdark X requires flag 15X); row 100 = Deep of Night (unlock 130). Cross-check: Nexus NR #511 "(Offline) Switch Bosses to Everdark" changelog mentions "the ED Balancer flag (181)" — row 18 (defeat 181) is the Everdark of row 8 (defeat 161), consistent with this table.

### 5.2 HeroParam — `character_unlock_flag` (Nightfarer unlocks)
| heroType | name | character_unlock_flag |
|---|---|---|
| 1 Wylder, 2 Guardian, 3 Ironeye, 5 Raider, 7 Recluse, 8 Executor | | 0 (always unlocked) |
| 4 | Duchess | **6031** |
| 6 | Revenant | **6037** |
| 9 | Scholar (DLC) | **6038** |
| 10 | Undertaker (DLC) | **6039** |
(`character_name_id` 288050–288059.)

### 5.3 AntiqueStandParam — vessel (relic-stand) `unlockFlag` per hero (74 rows)
Pattern: hero N's 7 vessels → flags `0` (default), then `60000+50*(N-1)+{10,20,30,40}` and `60600+20*(N-1)+{0,10}`; e.g. Wylder 60010/60020/60030/60040/60600/60610; Guardian 60060/60070/60080/60090/60620/60630; … Executor 60360/60370/60380/60390/60740/60750; Scholar 60510/60520/60530…; goodsId 9600–9956 (vessel goods). Source: `src/Resources/Param/AntiqueStandParam.csv` (save editor) and the regulation.

### 5.4 PersonalScenarioParam — Remembrance chapter objective flags (`objective_flag_id`, 227 rows)
Row blocks per hero (row id thousands = hero slot): 1000s Wylder → objective flags **1009101–1009124**; 2000s → **1009400–1009430** (Guardian); 3000s → **1009501–1009526** (Ironeye); 4000s → **1009801–1009817** (Duchess); 5000s → **1009701–1009722** (Raider); 6000s → **1009301–1009317** (Revenant); 7000s → **1009201–1009229** (Recluse); 8000s → **1009600–1009616** (Executor); 9000s → **1029900–1029926** (DLC hero). `flashback_flag_id` values 1119120–1189231 / 1029880–1029881 (per-chapter flashback flags). Rows with `unk1 == 1150` sit at chapter ends (likely "chapter complete" gate). Hero↔block assignment beyond the row numbering is **[INFERRED]** from the hero_type ordering.

### 5.5 MissionManagementParam (22 rows, 4 ints): e.g. `101 (0, 65637, 0, 10101)`, `901 (0, 66437, 0, 1010901)`, `1001 (0, 66537, 0, 1011001)`, `9999 (1, 131071, 0, -1)` — field 3 looks like an event flag (10101…10803, 1010901, 1010902, 1011001). **[INFERRED semantics]**

### 5.6 In-expedition (non-persistent) flags seen in vanilla EMEVD (4laric rando `patched_emevd_js/common_func.emevd.js`, decompiled with DarkScript3 `nr-common.emedf.json`)
Most-referenced: `8062` (x190), `8061` (x155), `7512` (x147), `7511`, `7604`, `9999`, `6011`, `7603`, `8027`, `7505`, `8085–8087`, `8105`, `7707/7727`, `7521`, `7015–7017`. From the rando's `emevd_patch.py` comments: "The N2 EventFlag(7512) 'a night boss has died' guard"; 7530 is "network-synced"; boss-encounter handlers use `SetNetworkconnectedEventFlagID(8061, ON)` (encounter started) / `8062` (encounter finished). Nexus article "The Nightreign MEMEVD Hall of Shame" (Nexus NR articles/86, Seamless 6-player author): new flag block "11007000–11007012 (using post-Heolstor Roundtable Hold space)", player slot constants "10002–10007", events 1180/1308/90015469/99075460-65, SpEffects 98440-98442, 49300-49375.

---

## 6. Recommended runtime strategy for the AP DLL (from the above) [INFERRED, grounded]

1. Load via **me3** `[[natives]]` (me3 ≥ v0.4.0 supports NR; `Game::Nightreign` aliases `nr`, `nightrein`). Keep EAC off (me3 launches `nightreign.exe` directly).
2. Depend on `fromsoftware-shared` (+ `from-singleton`) and resolve **CSEventFlagMan, WorldChrMan, SoloParamRepository, CSMenuMan, MapItemMan, MsgRepository** by DLRF name. Wait for DLRF init the way me3 does (hook after `wait_for_system_init`-style point / first task tick) — the from-singleton doc says "may not find all singletons if it is called before Dantelion2 reflection is initialized".
3. **Do not reuse the `eldenring` crate's struct layouts blindly.** me3 already shows `CSSystemProperties` differs on NR. Re-derive `CSFD4VirtualMemoryFlag` (the ER layout: divisor/holder_size/holder_count/flag_blocks/DLMap descriptors at +0x1c…+0x30) and `WorldChrMan.main_player`, `PlayerGameData` (rune at +0x6C per kwwsyk chain) on NR with a debugger / RTTI.
4. Obtain NR RVAs for the non-DLRF statics/functions (GameDataMan static, AddItemFunc/ItemGib, Get/SetEventFlag, CSMenuManImp::DisplayStatusMessage) by running `tools/binary-mapper` with an adapted `mapper-profile.toml` against `nightreign.exe` 1.03.2, seeding it with the ER patterns in §3 and the ItemGib prologue `40 55 56 57 41 54 41 55 41 56 41 57 48 8D 6C 24`/`48 8D AC 24`. Ship them as a version-gated table like 4laric's `rva_table.rs` with prologue-byte guards that "fail CLOSED".
5. For checks: poll `defeat_event_flag`s **150–162 / 170–181** (Nightlords), Remembrance `objective_flag_id`s (§5.4), hero unlock flags **6031/6037/6038/6039**, vessel flags (§5.3). For items: set those same flags via `CSFD4VirtualMemoryFlag::set_flag`, grant Murk by writing the Murk field in PlayerGameData (locate via the kwwsyk chain shape / save-file analog), grant goods/relics via ItemGib.

---

## 7. Patch 1.03.x facts [NR-CONFIRMED]

| App Ver | Regulation Ver | Date | Notes |
|---|---|---|---|
| 1.03 | 1.03.1 | 2025-12-03 | The Forsaken Hollows DLC support (DLC released 2025-12-04); relic preset naming; character-select shows relics |
| 1.03.1 | 1.03.2 | 2025-12-17 | hotfix |
| **1.03.2** | 1.03.4 | **2026-01-15** | "Balance Adjustments and Feature Updates": Nightfarer buffs (Guardian, Raider, Executor, Scholar, Undertaker, Duchess), relic effect tuning, Rotten Crystal Staff sorcery change, 40+ bug fixes, Steam fix for "connection issues ... immediately after matchmaking was completed". Console build ids 1.003.002 / 1.22. |
| 1.03.2 | **1.03.5** | **2026-03-31** | "Hotfix 1.03.5": "App Ver. remains 1.03.2 / Regulation Ver. updated to 1.03.5" — "Fixed a bug where repeatedly using specific actions during a multiplayer Expedition would lead to degraded performance for all players." ~2 MB regulation-only. |

→ The **executable has not changed since 2026-01-15**; only `regulation.bin` moved (1.03.4 → 1.03.5), so code RVAs/AOBs scanned on 1.03.2 are current, and param row *ids/flags* in §5 (from a 1.03.x-era regulation) are stable, though field values could shift with regulation updates. No 1.03.3/1.04 found (Wikipedia, patchbot, wiki.gg all end at 1.03.2/1.03.5).

Sources: https://www.bandainamcoent.com/news/elden-ring-nightreign-patch-notes-version-1-03-2 ; https://www.bandainamcoent.com/news/elden-ring-nightreign-hotfix-1-03-5 ; https://steamcommunity.com/app/2622380/discussions/0/806847153386419148/ ; https://eldenring.wiki.gg/wiki/Nightreign:Patch_Notes ; https://patchbot.io/games/elden-ring-nightreign ; https://en.wikipedia.org/wiki/Elden_Ring_Nightreign.

---

## 8. Projects checked that do NOT contain NR signatures
- `thefifthmatt/SoulsRandomizers` — has `FromGame.NR`, `NightreignVersion = "v0.1.6"`, `CheckNightreignGameFiles(... "nightreign.exe" ...)`, requires `NightreignRandomizerHelper.dll` (closed; "alternate save file management and a logo skip feature"), but the `NightreignRandomizer` class and the helper DLL source are not in the repo.
- `4laric/nightreign-enemy-rando` — pure file-side (regulation/EMEVD/MSB via me3). Contains `NIGHTREIGN-AP-DESIGN.md` (draft v0.1, 2026-06-23, "Reverse Heat"/de-escalation AP design; §8 says use "a native runtime client in the style of the ER AP client, loaded through the existing me3_profile.py setup"). No memory offsets.
- `4laric/er-archipelago` / `from-software-archipelago-clients` — crates: `archipelago-rs bb-archipelago client-ui ds3-archipelago eldenring-archipelago er-codec er-logic er-semver sdt-archipelago shared standalone-*`; **no nightreign crate**.
- `veeenu/eldenring-practice-tool` — no NR support; `veeenu/nightreign-practice-tool` does not exist (clone → auth prompt = 404).
- `Nordgaren/Elden-Ring-Debug-Tool` + `Erd-Tools` — ER only (AOBs in §3.1). `Dasaav-dsv/libER` — ER only (`symbols/singletons.csv` etc.).
- `alfizari/Elden-Ring-Nightreign-Save-Editor` — save-file parser only, flags unparsed.
- GitHub topic `nightreign` (20 repos: me3, fromsoftware-rs, fxr, fxr-ws-reloader, RemoveVignette, save backup/relic tools) — none hooks game singletons except me3.
- Many "nightreign cheat table/trainer" GitHub repos in search results (rahulx21, Emelie96, austinwrig09, anarxeflame38, DriverRelay, picker343, …) are SEO/malware-style download pages, not source.
