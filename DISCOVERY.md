# Elden Ring: Nightreign — Archipelago Discovery Document

Status: prototype 0.1.0 (2026-09-09). APWorld generates and passes its tests; game mod is an uncompiled Rust skeleton
following the Elden Ring / DS3 AP architecture, with all game-specific constants marked `TODO(RE)`. Companion research
dump with all sources: `research/nightreign_research.md`.

## 1. Bottom line

No Nightreign Archipelago world exists, but every building block does. The FromSoftware AP community has converged
on one stack — **Mod Engine 3 loads a Rust DLL; the DLL uses `vswarte/fromsoftware-rs` for engine access,
`archipelago_rs` for the protocol, `ilhook` for detours and `hudhook` for an ImGui overlay** — and the same people
(4laric, thefifthmatt) who wrote the Elden Ring AP client also ship Nightreign randomizers on me3. `fromsoftware-rs`
already has a `nightreign` crate (params only so far). The blocker is not tooling; it is (a) porting the runtime
singleton layouts (`CSEventFlagMan`, `GameDataMan`, `WorldChrMan`, the item-give routine) to Nightreign, and (b) the
design question of what a "check" is in a 40-minute roguelite with no persistent world pickups.

Answer to (b), implemented here: **randomize meta-progression only**. Checks are first-time events the game
already tracks in event flags; items are the meta unlocks that gate them.

## 2. Confirmed facts that shape the design

| Topic | Finding |
|---|---|
| Loader | me3 supports Nightreign since 0.4.0; natives with `premain` since 0.11.0; profile options `savefile`, `start_online=false`, `disable_arxan`. |
| EAC | Nightreign uses EAC (EOS). All mod routes run `nightreign.exe` directly (me3, or `steam_appid.txt` = 2622380). Consequences: no official matchmaking, no achievements, **no Everdark Sovereigns** (online-only) → cannot be checks. |
| Co-op with mods | Only via Yui's Seamless Co-op (v1.12, ≤6 players, own `.co2` save). Conflicts with me3's launcher; workaround documented in me3 discussion #655. |
| Params / tools | Smithbox edits Nightreign `regulation.bin`; `AttachEffectTableParam` drives relic effect rolls; WitchyBND/soulstruct handle the archives. Hexinton's CE table (Nexus #127) has an item spawner and param editor; FearLess t=35248/35266 (Relic Editor). |
| Save | `%AppData%\Nightreign\<SteamID>\NR0000.sl2` (BND4 + AES, ER-style). alfizari's Python editor reads relics/Murk/Sigils. Soft-ban risk on edited saves → we use a separate `NR_AP.sl2`. |
| Expedition seed | thefifthmatt: a single u32 seed chosen after Nightlord selection fixes map pattern, Shifting Earth and active Remembrance (40 patterns per base Nightlord, 60 for DLC). Useful for Shifting Earth gating. |
| Precedent | 4laric/er-archipelago: pure-runtime Rust DLL, no file edits, Region Locks enforced by warping back to Roundtable, contract hash between apworld and DLL. |
| Content | 10 Nightlords (8 base + 2 DLC), 10 Nightfarers (8 + 2 DLC), 82 Remembrance chapters, 5 Shifting Earths (4 + 1 DLC), 15 Night-1 and 17 Night-2 bosses (+3 DLC), ~60 field bosses, vessels (Urn/Goblet/Chalice + 3 Grails), Deep of Night (5 depths), currencies Murk and Sovereign Sigils. |

## 3. Randomizer design (implemented in `apworld/nightreign`)

### Regions
`Roundtable Hold` (origin) → one region per expedition (`Expedition: Tricephalos` … `Expedition: Dreglord`) → a
shared `Any Expedition` region (night/field/Shifting Earth/Remembrance checks) and `Deep of Night`.

Entrance rules: `Expedition Access: X` when `expedition_locks` is on (Tricephalos always open); Night Aspect
additionally needs the seven base "`<expedition> Cleared`" events; DLC expeditions need Tricephalos cleared; Deep of
Night needs Night Aspect cleared (+ `Deep of Night Access` item when its checks are on).

### Locations (up to 212)
| Pool | Count | Option |
|---|---|---|
| Nightlord defeated | 10 (8 base) | always |
| Night 1 / Night 2 boss first kills | 35 (32 base) | `night_boss_checks` |
| Field / evergaol boss first kills | 35 (subset; extend from the Trophy Wall) | `field_boss_checks` |
| Remembrance chapters | 82 (67 base) | always; gated by progressive items when `remembrance_locks` |
| Small Jar Bazaar vessel purchases (Goblets ×10, Grails ×3) | 13 | `vessel_checks` |
| Character unlock quests (Duchess, Revenant, Scholar, Undertaker) | 4 (2 base) | always |
| Shifting Earth boss cleared | 5 (4 base) | always; gated by items when `shifting_earth_locks` |
| Deep of Night depth reached | 5 | `deep_of_night_checks` |

### Items
10 Nightfarers (start with one), 10 Expedition Access, 5 Shifting Earth unlocks, 82 Progressive Remembrances
(per Nightfarer), 10 Goblets + 3 Grails, Deep of Night Access, filler (Murk 500/1500, Scenic Flatstones, Polished/Grand
relics per colour) and traps (Cursed Relic, Murk Tax, Night's Cavalry Ambush, Circle Collapse).

Not included on purpose: Everdark Sovereigns / Sovereign Sigils (online-only), per-run weapons and relic drops (not
persistent), Sparring Grounds and outfits (cosmetic; possible later filler checks).

### Options
`goal` (heolstor / all base / all incl. DLC), `include_dlc`, `expedition_locks`, `nightfarer_shuffle`,
`starting_nightfarer`, `remembrance_locks`, `shifting_earth_locks`, the four location-pool toggles,
`trap_percentage`, `death_link`.

## 4. Game-side architecture (`mod/`)

```
me3 profile (offline, NR_AP.sl2, disable_arxan) ──▶ nightreign.exe
   └─ nightreign_archipelago.dll  (Rust cdylib, premain)
        ap.rs          archipelago_rs session (Connect / LocationChecks / ReceivedItems / DeathLink / goal)
        game/flags.rs  CSEventFlagMan get/set → checks come from slot_data.location_flags
        game/grant.rs  items → set flag / ItemGib goods / Murk write / traps
        game/locks.rs  expedition, Nightfarer, Shifting Earth, Remembrance gating (mod-side state + confirm hooks)
        overlay.rs     hudhook ImGui (F9): server/slot/password, log, toasts
```

The apworld ships `location_flags` (AP id → event flag) in slot data so the DLL needs no copy of the location table,
and the mod's item-offset table mirrors `items.py` (this pair should be protected by a contract hash like 4laric's).

## 5. Reverse-engineering plan (hands-on, in order)

1. Build the crate once against the real `archipelago_rs`/`hudhook`/`fromsoftware-rs` versions and fix API drift.
2. Resolve the FD4 singletons on the current patch with `fromsoftware-shared`'s finder; port `CSEventFlagMan`,
   `GameDataMan`/`PlayerGameData` (Murk field) and `WorldChrMan` layouts from the `eldenring` crate and verify with
   Hexinton's CE table (its "player stats" and "item spawner" scripts contain the AOBs for `GameDataMan` and the
   item-give routine).
3. Capture event-flag ids: watch flags in CE while (a) defeating each Nightlord, (b) completing a Remembrance chapter,
   (c) buying a vessel, (d) unlocking Duchess/Revenant, (e) clearing a Shifting Earth. Alternatively diff `NR_AP.sl2`
   before/after with alfizari's editor. Fill `flag` in `locations.py` and `catalogue` in `flags.rs`.
4. Find the four confirm sites for locks (expedition map table, Nightfarer select, Shifting Earth seed selection,
   active Remembrance) and detour them with `ilhook`; for Shifting Earth, re-roll the u32 expedition seed until the
   pattern has no locked event (same mechanism thefifthmatt's randomizer manipulates).
5. Goods ids for Goblets/Grails/flatstones/relics from Smithbox `EquipParamGoods`; relic effects roll automatically
   from `AttachEffectTableParam` when the goods are created.
6. Night/field boss first-kill flags may not exist as individual flags (the Trophy Wall implies they do — verify);
   fallback is hooking the boss-death EMEVD event or the "boss defeated" banner.

## 6. Open verification items

- Whether Murk is stored in `GameDataMan` like runes or elsewhere (speculative).
- Field boss list is a curated subset of ~35 from memory; replace with the Trophy Wall enumeration.
- Deep of Night unlock condition (assumed: Heolstor defeated).
- DLC expedition unlock wording (Tricephalos + both DLC Nightfarers).
- Duo/trio expeditions: only the host's client should be authoritative; needs Seamless Co-op integration testing.

## 7. Mod administration

Nightreign is not on r2modman/Thunderstore. The intended manager is me3 itself (double-click profile) or the
**Mod Engine 3 Manager** (Nexus Nightreign #213) which imports folder mods. `mod/build.ps1 -Deploy` stages the
folder in the standard me3 mods location.

## 8. Update 2026-09-10 — offline extraction from the installed game (App 1.03.2 / Regulation 1.03.5)

Done with the user's install (`regulation.bin`, the `.bhd` headers, byte slices out of the `.bdt` archives and the
exe itself, moved through the desktop bridge in 4 MB pieces):

- **Params**: all 252 params decrypted and dumped (`tools/nr_params.py`, layouts from `fromsoftware-rs`); the
  AP-relevant tables are in `research/params/` with Smithbox row names in `research/names/`.
- **Flags are now exact**: Nightlord defeat 150–162 (unlock 0/110/115/135/136), Everdark 170–181, Nightfarer
  unlocks 6031/6037/6038/6039, Deep of Night unlock 130, **Remembrance chapter flags per hero** (row names
  "Wylder: Chapter N" → `REMEMBRANCE_CHAPTER_FLAGS` in `data.py`; the row blocks are *not* in hero-type order:
  2000s = Duchess, 3000s = Raider, 4000s = Executor, 5000s = Recluse, 6000s = Ironeye, 7000s = Guardian,
  8000s = Revenant, 9000s = Scholar, 10000s = Undertaker), vessel unlock flags + goods ids for all 74 vessels
  (`VESSEL_ROWS`, Grails 60410/60420/60400 + DLC Scadutree 60430), relic/flatstone/Murk antique ids, garb goods.
- **Roundtable Hold EMEVD** (`m10_00_00_00`) confirms the semantics: the Duchess-unlock event writes 6031, the
  Night Aspect unlock writes 115, Deep of Night toggles 130 gated on 136.
- **Exe scan** (`tools/nr_scan.py`, `research/nightreign_exe_scan.md`, `nightreign_rvas.json`): version gate
  ProductVersion 1.3.3.0; 232 FD4 singletons resolved by name; `GameDataMan` 0x3c078d0 (CONFIRMED),
  `CSEventFlagMan` 0x3c115a8, `WorldChrMan` 0x3c0f0a8, `CSFD4VirtualMemoryFlag::GetFlag` 0x60ce40 /
  `SetFlag` 0x60d330 (ER-compatible layout), `CS::EquipGameData::AddInventoryEquip` 0x1f0160 (LIKELY grant/hook
  target; `EquipGameData = PlayerGameData+0x1d8`, `last_add_item_result +0x304`). The mod now uses these through
  `mod/src/game/rva.rs` with byte-signature guards and a version gate.
- **dlc01 archive key** recovered from the exe (`tools/nr_key_dlc01.pem`); the base-game message bundles are
  `item_dlc01`/`menu_dlc01` (the exe references only those names).

Still live-only: the `ItemEntry` layout for `AddInventoryEquip`, the Murk field / HP offsets in `PlayerGameData`
(DeathLink kill and Murk-tax trap are disabled until confirmed), Shifting Earth availability flags, the four
UI confirm sites for locks, and per-run challenge detection.
