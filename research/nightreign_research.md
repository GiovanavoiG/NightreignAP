# Elden Ring: Nightreign — Archipelago Integration Discovery Report

Date: 2026-09-09. Compiled from ~35 web searches/fetches. Each claim is tagged **[Confirmed]** (read directly from a primary source), **[Reported]** (secondary source / summary of a page), or **[Speculative]** (my inference).

---

## 0. Executive summary

- There is **no existing Nightreign Archipelago world or client** anywhere I could find (GitHub, Nexus, Steam forums, Archipelago wiki). Nightreign is *not* in the archipelago.gg supported-games list and no community thread discussing feasibility surfaced. **[Confirmed – absence of evidence after targeted searches]**
- The closest precedent is **4laric's "Archipelago in Elden Ring"** (Nexus #10334, GitHub `4laric/er-archipelago`, v0.6.0.2 updated 2026-09-07). It is a **pure-runtime Rust DLL loaded by Mod Engine 3 (me3)**; no `regulation.bin` edits; region locks + item grants + grace lighting all done live. The same author also ships a **Nightreign Enemy Randomizer** (Nexus #679) built on me3 — so the exact person/toolchain most likely to produce a Nightreign AP already works in both games. **[Confirmed]**
- The FromSoft AP ecosystem has converged on: **me3 as loader → Rust DLL → `vswarte/fromsoftware-rs` bindings (which already has a `nightreign` crate) → `archipelago_rs` for the AP protocol → `ilhook`/`hudhook` for function hooks and an in-game overlay.** The DS3 4.x client (`fswap/from-software-archipelago-clients`) is the reference implementation of that stack. **[Confirmed from Cargo.toml]**
- Nightreign modding is mature: me3 supports Nightreign since v0.4.0 (2025-06-07); Smithbox edits Nightreign params; Cheat Engine tables (Hexinton "Ultimate" table, FearlessRevolution) exist; Seamless Co-op (Yui) v1.12 supports up to 6 players with its own matchmaking and a separate `.co2` save; thefifthmatt's Randomizer/Derandomizer and 4laric's Enemy Randomizer are both me3-based. **[Confirmed]**
- EAC: Nightreign uses Easy Anti-Cheat; every mod route launches `nightreign.exe` directly (me3 does this; or `steam_appid.txt`=2622380 / batch launchers). Without EAC there is **no official matchmaking and no Everdark Sovereigns** (online-only weekly bosses). Co-op with mods is only possible through **Seamless Co-op**. **[Confirmed]**
- Biggest design risk is not tooling but **game structure**: Nightreign is a 40-minute roguelite run with no persistent overworld pickups. The "checks" have to be meta-progression events (Nightlord kills, night-boss kills, Remembrance chapters, Shifting Earth bosses, vessel/relic unlocks, character unlocks) and "items" have to be meta-unlocks (Nightfarers, vessels/Grails, Shifting Earths, Nightlord access, relic effects, Murk). **[Speculative but well-grounded]**

---

## 1. Existing FromSoftware Archipelago precedents

### 1.1 Elden Ring — 4laric "Archipelago in Elden Ring" (the primary precedent)
- Nexus: https://www.nexusmods.com/eldenring/mods/10334 (v0.6.0.2, updated 2026-09-07). GitHub: https://github.com/4laric/er-archipelago. **[Confirmed]**
- Architecture (from README/PROVENANCE): **[Confirmed]**
  - "Rust DLL loaded by the ModEngine3 (me3) mod loader" — cdylib; apworld in `greenfield/eldenring/`; Rust client lives in a **submodule of `fswap/from-software-archipelago-clients`**; `me3/` staging dir; `build.ps1` pipeline with `-Generate -Rust -Me3Deploy -Serve -Apworld` stages; Archipelago pinned at 0.6.7 via `.ap-version`; client verifies a "contract hash" against the apworld on connect.
  - "The game stays completely vanilla on disk. No game files are patched, no `regulation.bin` is modified." Detecting checks, granting items, lighting graces, enforcing region locks all happen live after connect.
  - Locations: boss drops, merchant inventory, pickups, Sites of Grace lit. Items: weapons/armor/spells/spirit ashes/materials/consumables/quest items, Great Runes, **Region Locks** (17 base / 31 with DLC; player starts at Roundtable Hold with one region open; entering a locked region warps you back to Roundtable), optional ability unlocks, boss "sweeps", traps, progressive upgrades.
  - Data derived offline from vanilla params (13 param CSVs incl. `ItemLotParam_map`, `ItemLotParam_enemy`, `ShopLineupParam`, `BonfireWarpParam`, `EquipParamWeapon`, `EquipMtrlSetParam`, `NpcParam`), 15 FMG XMLs, decompiled EMEVD and talk ESD — using soulstruct/WitchyBND ("soulsmods/fswap ecosystem"). No game data in repo.
  - Nexus page says "No EAC bypass required" — this means me3 handles launch; the game is still running **without** EAC/online. **[Confirmed wording; interpretation Speculative]**
  - Community issues (Nexus posts): RVA→VA crash (fixed 0.3.12), region-lock visibility, merchant display of AP items, power-scaling complaints. No mention of Nightreign. **[Reported]**
- Exact hook targets (which functions are detoured for item-lot pickup / item grant) are **not documented** in README/PROVENANCE and GitHub's tree view was robots-blocked for me. **[Uncertain]** By analogy with DS3/ER community knowledge the item grant almost certainly calls the engine's `ItemGib`-style function (`CS::GameDataMan → PlayerGameData → equip inventory add`), and check detection hooks the item-lot award path plus event-flag reads via `CSEventFlagMan`. **[Speculative]**
- Other ER AP attempts: `jambinjambo/ER_Archipelago` (fork of Archipelago with an ER world; no runtime docs found) and `AlmightyFridge/AP-Manual-ER-Key-Item-Rando` (a *Manual* apworld — honour-system, no game hook). **[Confirmed existence only]**

### 1.2 Dark Souls III (the mature reference)
- Old client: `Marechal-L/Dark-Souls-III-Archipelago-client` → `nex3/Dark-Souls-III-Archipelago-client` (C++ DLL, `apclientpp`, credits `LukeYui/DS3-Item-Randomiser-OS`, launched via `DS3-Archipelago.bat`; ran alongside ModEngine 2). **[Confirmed]**
- Current client (v4.0.x): `fswap/from-software-archipelago-clients` — "built on Mod Engine 3, which is more reliable than Mod Engine 2 and is actively maintained" (https://nex-3.com/ds3/info/). Bundles its own `dark_souls_3.apworld`; ~1,500 locations (pickups, shops, enemy drops); in-game overlay; DeathLink with amnesty. **[Confirmed]**
- `Cargo.toml` of that repo **[Confirmed]**: workspace members `crates/ds3-archipelago`, `crates/sdt-archipelago` (Sekiro), `crates/shared`; dependencies **`fromsoftware-shared` (vswarte/fromsoftware-rs)**, `fromsoftware-extra-shared` (nex3/fromsoftware-extra), **`ilhook` 2.3 (x64 inline hooks)**, **`hudhook` 0.9 (ImGui overlay)**, **`archipelago_rs` 2.1.1**, `windows` 0.62, serde/bincode. README says "support for Sekiro and Elden Ring planned" — and 4laric's ER client is a submodule of it.

### 1.3 Dark Souls Remastered / DS2 / Sekiro
- **DSR**: `ArsonAssassin/DSAP` — C# **external-process memory reading** client (`DSAP.client.exe`) + Python apworld; uses the author's `Archipelago.Core` C# library (memory read/write, location monitors via bit checks, overlay, function hooking). Alternative `gigsabyte/dsr-archipelago` uses MinHook + AOB scan of the `GetItem` function (WIP). **[Confirmed]**
- **DS2**: `WildBunnie/DarkSoulsII-Archipelago` — C++ `dinput8.dll` wrapper (SeanPesce DLL_Wrapper_Generator) + apclientpp; forces offline mode. **[Confirmed]**
- **Sekiro**: `Amfales/Sekiro-Archipelago-client` (C++ fork of DS3 client, no releases) and `antonovanton000/SekiroArchipelagoClient`; the fswap repo now has an `sdt-archipelago` crate. **[Confirmed]**
- **Takeaway**: two viable patterns exist — (a) in-process DLL with hooks (all serious FromSoft clients) and (b) external pymem/C#-style memory polling (DSR/DSAP). Pattern (a) is what the ecosystem has standardized on for ER and is what a Nightreign world should use; pattern (b) can only *read* (event flags, position) safely and cannot cleanly grant items or block progression.

---

## 2. Nightreign-specific modding landscape

### 2.1 Loaders
- **Mod Engine 3 (me3)** — https://github.com/garyttierney/me3 (567★). Supports DS3, Sekiro, Elden Ring, AC6, **Nightreign**. Nightreign added **v0.4.0 (2025-06-07)**; Wwise override fixes v0.5.0; game-agnostic asset override v0.6.0; `disable_arxan` profile option v0.6.0; anti-anti-debug (`ThreadHideFromDebugger` block) v0.8.1; **custom savefile name/location** v0.8.1 (`savefile` profile field); `start_online` flag ("By default, me3 prevents the game from connecting to the official multiplayer matchmaking servers"); native DLLs via `[[natives]]` (premain loading v0.11.0, 2026-02-28); packages via `[[packages]]`. **[Confirmed from CHANGELOG/config reference]**
- **Mod Engine 3 Manager** (Nexus Nightreign #213) — GUI wrapper, Nexus integration. Known conflict: Seamless Co-op's launcher vs me3 ("signin is not available"), workaround is pointing me3 at the SC launcher exe, which then disables other me3 mods. **[Reported]**
- **Elden Mod Loader (techiew)** `dinput8.dll` + `mods/` folder — works in Nightreign; e.g. "Pause The Game" (Nexus NR #107) requires EAC disabled and uses techiew's DirectX hook. `techiew/EldenRingEacToggler` has a Nightreign fork `aechXIII/EldenRingNightreignEacToggler`. **[Confirmed]**
- ModEngine2: superseded; no Nightreign support found. **[Reported]**

### 2.2 EAC / offline
- Nightreign uses **Easy Anti-Cheat (EOS)**, launched via `start_protected_game.exe`. Bypass methods: `taskkill EasyAntiCheat_EOS.exe` + set `SteamAppId`/`SteamGameId` env and run `nightreign.exe`, or simply create `steam_appid.txt` containing **2622380** next to `nightreign.exe` (Nexus NR #15 "Simple Offline Launcher", #46 "Anti-Cheat Toggler", #190, #5). me3 launches the exe directly, so it is EAC-free by construction. **[Confirmed]**
- Consequences: no official matchmaking, no achievements, **no Everdark Sovereigns** ("Launching the game without EAC prevents us from fighting the Everdark Sovereign"). Vanilla offline is also available in-game (Settings → Network → Launch Settings → Play Offline) and allows solo runs and Remembrance progress. **[Confirmed]**
- Soft-ban risk: Hexinton table warns edited saves can softban matchmaking; mods should use a separate save (me3 `savefile` option, or SC's `.co2`). **[Reported]**
- **Co-op with mods**: only via **Seamless Co-op (Nightreign)** by Yui (Nexus NR #3, v1.12, 2026-07-02): own launcher, disables EAC, own matchmaking, separate `NR0000.co2` save, up to 6 players. thefifthmatt's randomizer states it is SC-compatible if all players share seed/settings. An AP world could therefore in principle support 2–3 players in one Nightreign slot via SC, but each player's client would need to agree on state — treat as stretch goal. **[Confirmed facts; multiworld-in-coop Speculative]**

### 2.3 Param / file tools
- **Smithbox** (vawser) supports Nightreign param editing (`regulation.bin`); Nightreign Nexus mods routinely ship modified `regulation.bin` (e.g. "Unlock all skins-outfits" #547, "Better Relics" #112, "Relics cost 1 Murk" #495). Relevant param names seen: **`AttachEffectTableParam`** (relic effect roll weights; groups 100/200/300 normal relics, 2000000/2100000 Deep relics, 3000000 Deep-relic curses) — Nexus #393. **[Confirmed]** Other Nightreign params (by analogy with ER, unverified names): `EquipParamGoods` (relics are goods), `ShopLineupParam` (Small Jar Bazaar / Collector Signboard), `ItemLotParam_*`, plus new map-pattern/expedition tables. **[Speculative]**
- **WitchyBND / soulstruct** handle Nightreign archives; **`EvenTorset/fxr`** supports Nightreign FXR. **[Confirmed]**
- **Nightreign Randomizer and Derandomizer** by thefifthmatt (Nexus #277, v0.1.6c, 2025-10-10): me3-based; randomizes map patterns, night-boss picks, camp reward types, circle timing, Shifting Earth frequency; ships `NightreignRandomizerHelper.dll` (save management + logo skip); documents that a **32-bit "expedition seed"** chosen after matchmaking/Nightlord selection determines map pattern + Shifting Earth + active remembrance; 40 patterns per base Nightlord (20 plain + 5 per Shifting Earth), 60 for DLC Nightlords, +10 DLC-exclusive per base Nightlord (https://thefifthmatt.github.io/nightreign/). **[Confirmed]**
- **Nightreign Enemy Randomizer** by 4laric (Nexus #679, v0.28.1): Python GUI that reads vanilla MSB/EMEVD from the install at runtime and generates pre-patched EMEVD into an me3 profile. **[Confirmed]**
- **Unlock DLC bosses/maps in Deep of Night** (Nexus #516) shows the boss list and map mapping tables are param-editable. **[Reported]**

### 2.4 Cheat Engine / memory tools
- **Hexinton "Ultimate Cheat Engine Table"** (Nexus NR #127, updated 2025-12-17): item spawner, player stats, game speed, **param editing**, ships `offline_launcher.bat`. FearlessRevolution threads: t=35248 (main table), t=35266 (**Relic Editor**), t=35990. **[Confirmed]** Detailed AOBs (WorldChrMan/GameDataMan/EventFlagMan/SoloParamRepository) were not retrievable via fetch (forum blocked) — assume they mirror ER's FD4 singleton layout. **[Speculative]**
- **`vswarte/fromsoftware-rs`** — "Rust bindings to Elden Ring, Dark Souls 3, Nightreign and Sekiro"; crates `eldenring`, `nightreign`, `darksouls3`, `sekiro`, `shared`, `macros`; uses FD4 singleton finder (Sfix/Tremwil/Dasaav), arxan disabler (Tremwil/Yui), param definitions from Vawser. The `nightreign` crate's `lib.rs` currently exposes only `pub mod param;` — i.e. **param bindings exist but the CS::* runtime structs (WorldChrMan, CSEventFlagMan, GameDataMan) for Nightreign are not yet ported**, whereas the `eldenring` crate has them. This is the main engineering gap. **[Confirmed as of fetch]**
- No dedicated "Nightreign practice tool", "nightreign-pointers", or Nordgaren Debug Tool build for Nightreign was found. **[Confirmed absence]**
- Save file: `%AppData%\Nightreign\<SteamID>\NR0000.sl2` (BND4, AES-encrypted like ER). Editors: `alfizari/Elden-Ring-Nightreign-Save-Editor` (Python 3.12; relics, Murk, Sigils, vessel detection, "character unlock parsing WIP"), Nexus #38, #551 Relic Editor, `G1ZMODRAG0N/NightreignSaveManager`, `TheNorland/Nightreign-Seamless-Co-Op-Save-Transferer` (renames `.sl2` → `.co2`). **[Confirmed]**

---

## 3. Game structure (for location / item design)

### 3.1 Nightlords (expedition name → boss) **[Confirmed]**
| # | Expedition | Nightlord | Notes |
|---|---|---|---|
| 1 | Tricephalos | Gladius, Beast of Night | first; unlocks Goblets, DLC gate |
| 2 | Gaping Jaw | Adel, Baron of Night | |
| 3 | Sentient Pest | Gnoster, Wisdom of Night | |
| 4 | Augur | Maris, Fathom of Night | |
| 5 | Equilibrious Beast | Libra, Creature of Night | |
| 6 | Darkdrift Knight | Fulghor, Champion of Nightglow | |
| 7 | Fissure in the Fog | Caligo, Miasma of Night | |
| 8 | Night Aspect | Heolstor the Nightlord | final; requires the 7 above |
| 9 (DLC) | Balancers | Weapon-Bequeathed Harmonia | |
| 10 (DLC) | Dreglord | Traitorous Straghess | |

- **Everdark Sovereigns** (harder, online-only, weekly rotation; grant **Sovereign Sigils** + "Dark Night of the X" relics from Collector Signboard): Tricephalos, Gaping Jaw, Sentient Pest, Augur, Equilibrious Beast, Darkdrift Knight, Fissure in the Fog (7; no Heolstor/DLC versions confirmed). **Unavailable without EAC** → cannot be AP locations. **[Confirmed]**

### 3.2 Nightfarers **[Confirmed]**
Base: Wylder, Guardian, Ironeye, Raider, Recluse, Executor (unlocked at start); **Duchess** (defeat Gladius → Old Pocketwatch → Priestess); **Revenant** (buy Besmirched Frame at Bazaar → phantom in east wing → beat the tutorial fight). DLC (The Forsaken Hollows, **2025-12-04**): **Scholar** and **Undertaker** — defeat Tricephalos, talk to Iron Menial → Small Jar Merchant message. Balancers/Great Hollow additionally require ≥2 Nightlords beaten and both DLC characters unlocked; a chapel behind the Small Jar Merchant opens.

Remembrance chapter counts (Steam guide 3492008179): Wylder 9 (secret ending), Guardian 10, Ironeye 8 (secret ending), Duchess 9, Raider 8, Revenant 8, Recluse 8 (secret ending), Executor 7, Scholar 8, Undertaker 7 → **82 chapters** total; each yields a Chalice, a unique relic, an outfit, and key items (e.g. Slate Whetstone, Silver Tear, Edge of Order, Old Portrait, Vestige of Night). **[Confirmed]**

### 3.3 Relics & vessels **[Confirmed]**
- Relics = goods with up to 3 effects; colors Red/Blue/Yellow/Green; grey = wildcard. Tiers Delicate/Polished/Grand (Scenic Flatstones roll randomly); preset relics from Remembrances/Nightlords; Everdark "Dark Night" relics; **Depths relics** (Deep of Night only, 3 extra slots, positive+negative effects). Inventory cap ≈1,960.
- Vessels per character: **Urn** (default 3-slot), **Goblet** (1,200 Murk after Tricephalos), **Chalice** (from Remembrance, 3rd slot universal), plus three shared **Grails** (3,000 Murk each: Spirit Shelter = 4 Nightlords, Giant's Cradle = first 7, Sacred Erdtree = Heolstor). DLC adds Decrepit/Forgotten Goblets & Urns.
- Currencies: **Murk** (sell relics 150/350/550; buy vessels/flatstones/outfits) and **Sovereign Sigils** (Everdark only). Relic effects are rolled from `AttachEffectTableParam` weights.

### 3.4 Shifting Earth **[Confirmed]**
Crater (first one after your first expedition; 2 bosses on descent; reward: upgrade a weapon to legendary), Mountaintop (frost resistance + dragon damage), Rotted Woods (scarlet rot immunity), Noklateo the Shrouded City (auto-revive; one boss), DLC **The Great Hollow** (cavern with cursed crystals). Unlocked by beating Nightlords / some Remembrances; cycled by Nightlord kills; can be skipped at Roundtable.

### 3.5 Expedition & modes **[Confirmed]**
- Run = Day 1 (two circle collapses, Night 1 boss) → Day 2 (same, Night 2 boss) → Day 3 Nightlord. Solo/duo/trio. **Duo Expeditions** and **Deep of Night** (ranked; 5 Depths, 4–5 endless; fully random Nightlords; Everdark variants from Depth 2–3; Depths relics; red-rarity weapons) added **2025-09-11** (patch 1.02). Deep of Night DLC content requires all 3 players own the DLC.
- Night 1 boss pool (15): Bell Bearing Hunter, Demi-Human Queen, Battlefield Commander, Centipede Demon, Gaping Dragon, Grafted Monarch, Night's Cavalry, Royal Revenant, Smelter Demon, Tibia Mariner, Duke's Dear Freja, Ulcerated Tree Spirit, Valiant Gargoyle, Wormface, Death Knights.
- Night 2 boss pool (~17): Fell Omen, Tree Sentinel, Ancient Dragon, Crucible Knight, Dancer of the Boreal Valley, Death Rite Bird, Draconic Tree Sentinel, Full-Grown Fallingstar Beast, Godskin Noble/Apostle, Great Wyrm, Nameless King, Nox Dragonkin Soldier, Outland Commander, Knight Artorias, Demon Prince, Divine Beast Dancing Lion, Mohg Lord of Blood. DLC adds Demon in Pain & Demon from Below, Curseblade & Divine Beast Warrior, Great Red Bear.
- Field/evergaol/POI bosses: ~60 types across POI classes Church, Fort, Gaol, Great Church, Main Encampment, Old/Sorcerer's Rise, Ruins, Spectral Hawk Tree, Spiritstream, Township, Tunnel.
- Roundtable Hold: Relic Rites (equip/sell), Small Jar Bazaar, Collector Signboard (Sigils), Journal/Remembrance, Trophy wall, Sparring/training area, Priestess, Iron Menial. **[Reported]**

### 3.6 Candidate AP location/item model **[Speculative]**
- Locations (~250+): 10 Nightlord kills (+ first-clear per character?), 82 Remembrance chapters, per-boss "first kill" for 30+ night bosses and ~60 field bosses, 5 Shifting Earth completions, 10 vessel purchases, character unlock events, Deep of Night depth milestones, murk thresholds.
- Items: Nightfarer unlocks (10), Nightlord access "keys" (10), Shifting Earth unlocks (5), Goblets/Chalices/Grails (~23), Remembrance progression (progressive per character), relic effect pools, Murk bundles, Depths access; traps (curse relic, cataclysm).
- All of these are governed by **event flags** in ER-style engines (character unlock, Nightlord defeated, remembrance chapter, vessel owned) → detection via `CSEventFlagMan` reads; granting via flag sets + `ItemGib` for relics/vessels/goods + Murk write in `GameDataMan`. Gating access to a Nightlord = intercept expedition-select UI or force-return to Roundtable when the seed's Nightlord isn't unlocked (same warp-back trick 4laric uses for region locks).

---

## 4. Client architecture options for a Python AP world

1. **Recommended: me3 native Rust DLL** (fork the fswap workspace; add `crates/nr-archipelago`). Reuse `archipelago_rs`, `hudhook` overlay, `ilhook`; extend `fromsoftware-rs::nightreign` with `CSEventFlagMan`, `GameDataMan`/`PlayerGameData` (Murk, relic inventory), `WorldChrMan`, item-give function, and expedition-state singleton (needs RE with Ghidra + Hexinton table AOBs). Ship `.me3` profile with `savefile = "NR_AP.sl2"` and `start_online = false`. Python side is just the apworld. **[Speculative but matches ER precedent]**
2. **External Python client with pymem** (DSAP-style): read event flags/Murk by walking FD4 singletons from `nightreign.exe`; only viable for a "tracker/locations-only" MVP; item granting via memory writes is fragile and Arxan integrity checks may fight writes (me3 `disable_arxan` exists precisely for this). **[Speculative]**
3. **Save-file editing between runs** (using alfizari's editor logic): grant relics/vessels/Murk by rewriting `NR0000.sl2` while at title screen. Simple but poor UX; usable as fallback for item receipt. **[Speculative]**
4. **`regulation.bin`/EMEVD pre-patch per seed** (fifthmatt/4laric style): could remap rewards, but conflicts with "no file edits" design and multiworld dynamics. **[Speculative]**

---

## 5. Community sentiment
- No Archipelago-discord/reddit thread proposing a Nightreign world was findable via search (Discord isn't indexed; Reddit results were empty). Steam forums have no AP discussion. Press coverage of fifthmatt's and 4laric's Nightreign randomizers (GameSpot, PCGamesN, GamesRadar) is positive and shows demand for Nightreign randomization. **[Confirmed]**
- Feasibility signals: same authors (4laric, thefifthmatt) active in both ER-AP and Nightreign modding; fromsoftware-rs already has a Nightreign crate; me3 already supports Nightreign natives. The blockers are RE of Nightreign runtime structs and the design question of what "checks" mean in a roguelite. **[Speculative]**

---

## Sources
- https://github.com/4laric/er-archipelago · https://www.nexusmods.com/eldenring/mods/10334 · https://github.com/jambinjambo/ER_Archipelago · https://github.com/AlmightyFridge/AP-Manual-ER-Key-Item-Rando
- https://github.com/fswap/from-software-archipelago-clients · https://nex-3.com/ds3/info/ · https://github.com/nex3/Dark-Souls-III-Archipelago-client · https://github.com/Marechal-L/Dark-Souls-III-Archipelago-client
- https://github.com/ArsonAssassin/DSAP · https://github.com/ArsonAssassin/Archipelago.Core · https://github.com/gigsabyte/dsr-archipelago · https://github.com/WildBunnie/DarkSoulsII-Archipelago · https://github.com/Amfales/Sekiro-Archipelago-client · https://github.com/antonovanton000/SekiroArchipelagoClient
- https://github.com/garyttierney/me3 · https://github.com/garyttierney/me3/discussions/90 · https://github.com/garyttierney/me3/discussions/655 · https://www.nexusmods.com/eldenringnightreign/mods/213
- https://github.com/vswarte/fromsoftware-rs · https://github.com/topics/nightreign
- https://www.nexusmods.com/eldenringnightreign/mods/15 · /mods/46 · /mods/127 · /mods/3 · /mods/277 · /mods/679 · /mods/393 · /mods/516 · /mods/547 · /mods/107 · https://github.com/aechXIII/EldenRingNightreignEacToggler · https://steamcommunity.com/sharedfiles/filedetails/?id=3492675518
- https://fearlessrevolution.com/viewtopic.php?t=35248 · https://fearlessrevolution.com/viewtopic.php?t=35266
- https://github.com/alfizari/Elden-Ring-Nightreign-Save-Editor · https://github.com/G1ZMODRAG0N/NightreignSaveManager · https://github.com/TheNorland/Nightreign-Seamless-Co-Op-Save-Transferer
- https://thefifthmatt.github.io/nightreign/ · https://github.com/vawser/Smithbox
- https://eldenring.wiki.gg/wiki/Nightreign:Bosses · https://eldenring.wiki.gg/wiki/Nightreign:Relics · https://eldenring.fandom.com/wiki/Elden_Ring_Nightreign:_The_Forsaken_Hollows · https://eldenring.fandom.com/wiki/Deep_of_Night · https://eldenring.fandom.com/wiki/Everdark_Sovereigns · https://eldenring.fandom.com/wiki/Nightreign_Locations
- https://en.bandainamcoent.eu/elden-ring/news/elden-ring-nightreign-how-unlock-the-dlc-content · https://www.keengamer.com/articles/guides/elden-ring-nightreign-dlc-all-new-bosses-and-how-to-defeat-them/
- https://steamcommunity.com/sharedfiles/filedetails/?id=3492008179 · https://eip.gg/nightreign/guides/rites-and-goblets/ · https://www.powerpyx.com/elden-ring-nightreign-all-shifting-earth-locations-guide/ · https://game8.co/games/Elden-Ring-Nightreign/archives/524177
