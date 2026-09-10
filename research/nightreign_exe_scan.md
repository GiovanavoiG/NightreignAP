# nightreign.exe static scan — RVAs / signatures for the AP mod DLL

Generated 2026-09-10 by `tools/nr_scan.py` (pure Python, no disassembler) from
`nightreign.exe` (118,835,320 bytes, image base `0x140000000`). Everything here is
**static** — nothing was executed. All addresses are **RVAs** (add the module base at runtime).
Machine-readable copy: `research/nightreign_rvas.json`; full RTTI class list: `research/rtti_cs_names.txt`.

Tags: **CONFIRMED** = pattern is unambiguous / cross-validated by two independent methods;
**LIKELY** = one strong method, no contradiction; **GUESS** = heuristic only, verify in a debugger.

## 0. TL;DR for the DLL

| what | value | tag |
|---|---|---|
| Version gate (PE VERSIONINFO) | ProductName `ELDEN RING NIGHTREIGN`, ProductVersion / dwProductVersion **`1.3.3.0`**, StringFileInfo translation lang `0x409` (`lang_id & 0x3ff == 0x0009` = `LANG_ID_EN`), resource dir language 1041 | CONFIRMED |
| `CSEventFlagMan` static (FD4Singleton) | `0x3c115a8` | CONFIRMED |
| `CSFD4VirtualMemoryFlag` is at `CSEventFlagMan+0` (divisor `+0x1c`, holder size `+0x20`, flag_blocks `+0x28`, descriptor tree head `+0x38`) | | CONFIRMED (from GetFlag body) |
| `CSFD4VirtualMemoryFlag::GetFlag(this, u32 id) -> bool` | `0x60ce40` | CONFIRMED |
| `CSFD4VirtualMemoryFlag::SetFlag(this, u32 id, bool)` | `0x60d330` | CONFIRMED |
| `CSEventFlagMan::GetEventFlag(this, u32* id) -> bool` | `0x5e7260` | CONFIRMED |
| `CSEventFlagMan::SetEventFlag(this, u32* id, bool value, r9)` | `0x5e79f0` | CONFIRMED |
| `GameDataMan` static (not DLRF) | `0x3c078d0` (object size 0x458, `main_player_game_data` at `+8`) | CONFIRMED |
| `GameMan` static | `0x3c13258` | CONFIRMED |
| `WorldChrMan` static | `0x3c0f0a8` | CONFIRMED |
| `MapItemMan` static | `0x3c10b68` | CONFIRMED |
| `CSMenuMan` / `SoloParamRepository` / `MsgRepository` / `CSNetMan` / `CSFile` / `CSRegulationManager` / `CSSystemProperties` | `0x3c149d8` / `0x3c28880` / `0x3c246a8` / `0x3c046a8` / `0x3c04a28` / `0x3c2d400` / `0x442f1d0` | CONFIRMED (CSSystemProperties CONFIRMED via vftable trampoline) |
| `CS::EquipGameData::AddInventoryEquip` (the AP grant/pickup hook target; `EquipGameData` = `PlayerGameData+0x1d8`, `last_add_item_result` at `EquipGameData+0x304`) | `0x1f0160` | LIKELY |
| `CS::MapItemManImpl::_RequestRegistGetItem` (item-lot "get item" entry, ItemGib-like) | `0x581800` (thunks `0x5769a0` / `0x5769b0` / `0x5769c0`) | LIKELY |
| per-item give helper between the two (MapItemMan → AddInventoryEquip) | `0x57ca60` → `0x57a0f0` | LIKELY |
| FD4 `get_name` (the function the from-singleton crate captures) | `0x2153380` | CONFIRMED |
| `CSLuaEventMan` static (FD4Singleton) | `0x3c10f60` | CONFIRMED |

The `from-singleton` crate approach **works on this binary** (232 FD4Singleton + 5 FD4DerivedSingleton statics found by the ported walker), so the DLL can still resolve singletons by name at runtime; the table below is what it will find.

## 1. Binary facts

Sections: `.text` @`0x1000` (0x2bb3c00), `.interpr` @`0x2bb5000`, `.rdata` @`0x2bc2000` (0xdc2c00), `.data` @`0x3985000` (vsize 0xd87d0c, raw 0x27f600 → most singleton statics live in bss above `0x3c04600`), `.pdata` @`0x470d000` (215,952 RUNTIME_FUNCTION entries; Arxan splits functions into chained-unwind chunks — 153,948 roots), `.rsrc` @`0x499a000`, second Arxan `.text` @`0x4a94000`.

Arxan artefacts that break naive scanners (handled by `nr_scan.py`): (a) function bodies split into chunks joined by `jmp` (use chained UNWIND_INFO to find the root), (b) vftable slots replaced by `jmp rel32` trampolines, (c) `ret` rewritten as `lea rsp,[rsp+8]; jmp [rsp-8]`, (d) some functions have no `.pdata` entry at all (e.g. `GetFlag`).

## 2. Version info (PE VERSIONINFO) — CONFIRMED

```
ProductName      = "ELDEN RING NIGHTREIGN"      (fromsoftware-rs normalize() -> "elden ring nightreign")
ProductVersion   = "1.3.3.0"   dwProductVersion = 1.3.3.0   FileVersion = 1.3.3.0
CompanyName      = "FromSoftware, Inc."
Translation      = lang 0x0409, codepage 1200  (-> lang_id & 0x3ff = 0x0009 = LANG_ID_EN)
RT_VERSION resource language id = 1041 (JP) — irrelevant to fromsoftware-rs, which uses the StringFileInfo translation
```
So the fromsoftware-rs style gate is `(LANG_ID_EN, "1.3.3.0")`. (Marketing "App Ver 1.03.2" ≠ the PE product version string; gate on the PE string.)

## 3. How the singleton scan works on NR (and what changed vs. the Rust crate)

`from-singleton`'s two walkers were ported 1:1 (`candidates_iter` → `mov edx,LINE` + `lea rcx,FILE` + `lea r8` + `lea r9,NAME` [derived] or `mov r9,rax` [FD4] → `jne` → `test r,r` → `mov r,[rip+static]`). Additions:

* MSVC also emits `cmp qword ptr [rip+static],0` (`48 83 3D disp32 00`) instead of `mov`+`test` in this build; the port matches both (`kinds` in the JSON).
* **Static name resolution for FD4Singleton** (the crate only gets names at runtime): the `lea rcx,[rip+key]` operand is a 1-byte static "key" whose address is looked up (binary search at `0x21532b0`, called from `get_name` `0x2153380`) in a runtime registry of `(key, DLRuntimeClass*)`. The registry is fed from the `DLRuntimeClassImpl<FD4Singleton<T,TImp>>` vftable, whose slot 3 is `lea rax,[rip+key]; ret`. So: key → that getter → the vftable containing it → its RTTICompleteObjectLocator → `.?AV?$DLRuntimeClassImpl@V?$FD4Singleton@V<T>@CS@@V<TImp>@2@@FD4@@$0A@@DLRF@@`. 205/232 resolve this way (**CONFIRMED**). The remaining 27 (FD4-namespace ones whose vftables have no RTTI locator, plus 3 debug managers) are named by adjacency to the class's lazy DLRuntimeClass registration slot (`mov rax,[rip+X]; test; jne +5; call; lea rcx,"Name"; mov [rax+38h],rcx` — 1,261 such slots, JSON `runtime_class_slots`), which sits at static+0x10 / static-0x8 in every confirmed case (**LIKELY**).
* `get_name` = `0x2153380` (9,116 call sites agree).

## 4. Singleton statics (name → static slot RVA)

Read the pointer at `base + RVA`; NULL until the singleton is constructed (most are created after the title screen / on world load — e.g. WorldChrMan, MapItemMan, CSEventFlagMan are NULL in the main menu).
### FD4DerivedSingleton (5)

| static RVA | name | null-check sites |
|---|---|---|
| `0x3c04a28` | CSFile | 557 |
| `0x3c1ac60` | CSGuiManager | 3 |
| `0x3c230e8` | CSResManager | 1 |
| `0x3c246a8` | MsgRepository | 67 |
| `0x4707208` | FD4FileManager | 16 |

### FD4Singleton (232)

| static RVA | name | resolved via | tag | sites |
|---|---|---|---|---|
| `0x3c045a8` | AnimThreadMan | vftable RTTI | CONFIRMED | 4 |
| `0x3c046a8` | CSNetMan | vftable RTTI | CONFIRMED | 330 |
| `0x3c04928` | FaceGenMan | vftable RTTI | CONFIRMED | 9 |
| `0x3c049a8` | CSEblFileManager | vftable RTTI | CONFIRMED | 4 |
| `0x3c075d8` | CSPcKeyConfig | vftable RTTI | CONFIRMED | 42 |
| `0x3c09860` | CSNowLoadingHelper | vftable RTTI | CONFIRMED | 5 |
| `0x3c099e8` | CSEntryfilelistRepository | vftable RTTI | CONFIRMED | 6 |
| `0x3c09b38` | CSRapidReentryHelper | vftable RTTI | CONFIRMED | 35 |
| `0x3c0a3b8` | LuaDatMan | vftable RTTI | CONFIRMED | 19 |
| `0x3c0a870` | CSTargetBankManager | vftable RTTI | CONFIRMED | 3 |
| `0x3c0a9c8` | CSSightRateRegionMan | vftable RTTI | CONFIRMED | 3 |
| `0x3c0ab38` | CSWorldWaypointManager | vftable RTTI | CONFIRMED | 24 |
| `0x3c0abd8` | CSWorldAiManager | vftable RTTI | CONFIRMED | 189 |
| `0x3c0ae30` | CSBulletManager | vftable RTTI | CONFIRMED | 32 |
| `0x3c0b0e8` | CSCamera | vftable RTTI | CONFIRMED | 40 |
| `0x3c0b320` | CSChrAimCamAssistMan | vftable RTTI | CONFIRMED | 9 |
| `0x3c0b408` | CSBattleGroupMan | vftable RTTI | CONFIRMED | 6 |
| `0x3c0b498` | CSNecroBuddyMan | vftable RTTI | CONFIRMED | 16 |
| `0x3c0b518` | CSNpcBotMan | vftable RTTI | CONFIRMED | 3 |
| `0x3c0b5d0` | CSRebornBuddyMan | vftable RTTI | CONFIRMED | 11 |
| `0x3c0e828` | ChrresRepository | vftable RTTI | CONFIRMED | 1 |
| `0x3c0ea38` | EneDatMan | vftable RTTI | CONFIRMED | 17 |
| `0x3c0eee0` | CSPairAnimManager | vftable RTTI | CONFIRMED | 26 |
| `0x3c0f0a8` | WorldChrMan | vftable RTTI | CONFIRMED | 1181 |
| `0x3c0f338` | WorldChrManDbg | vftable RTTI | CONFIRMED | 155 |
| `0x3c0f3a8` | ChrNonActiveBlockManager | vftable RTTI | CONFIRMED | 14 |
| `0x3c0f428` | DmgHitRecordMan | vftable RTTI | CONFIRMED | 14 |
| `0x3c0f4c0` | DmgMan | vftable RTTI | CONFIRMED | 49 |
| `0x3c0f590` | CSDeathBoxInsMan | vftable RTTI | CONFIRMED | 3 |
| `0x3c102a8` | CSDbgDistMeasure | vftable RTTI | CONFIRMED | 3 |
| `0x3c10328` | CSDrawGroupDebugManager | proximity-to-runtime-class-slot(+0x10) | LIKELY | 8 |
| `0x3c103a8` | CSKeyboardDebugMng | vftable RTTI | CONFIRMED | 1 |
| `0x3c10520` | CSPlacementDebugManager | vftable RTTI | CONFIRMED | 9 |
| `0x3c10698` | CSDbgSignboardMng | vftable RTTI | CONFIRMED | 3 |
| `0x3c10718` | CSStageDebug | proximity-to-runtime-class-slot(+0x10) | LIKELY | 14 |
| `0x3c10808` | CSDistViewManager | vftable RTTI | CONFIRMED | 7 |
| `0x3c10a18` | CSHitMtrlMan | vftable RTTI | CONFIRMED | 2 |
| `0x3c10b68` | MapItemMan | vftable RTTI | CONFIRMED | 70 |
| `0x3c10be8` | RumbleMan | vftable RTTI | CONFIRMED | 13 |
| `0x3c10d08` | CSEmkSystem | vftable RTTI | CONFIRMED | 33 |
| `0x3c10f60` | CSLuaEventMan | vftable RTTI | CONFIRMED | 69 |
| `0x3c111d0` | CSDbgEvent | vftable RTTI | CONFIRMED | 4 |
| `0x3c11248` | CSEventState | vftable RTTI | CONFIRMED | 2 |
| `0x3c114b0` | CSWorldObjActMan | vftable RTTI | CONFIRMED | 32 |
| `0x3c11528` | CSEventFlagAllocList | vftable RTTI | CONFIRMED | 6 |
| `0x3c115a8` | CSEventFlagMan | vftable RTTI | CONFIRMED | 262 |
| `0x3c117c8` | CSEventMan | vftable RTTI | CONFIRMED | 91 |
| `0x3c11848` | CSEventRegionMan | vftable RTTI | CONFIRMED | 15 |
| `0x3c118d8` | EventNonActiveBlockManager | vftable RTTI | CONFIRMED | 7 |
| `0x3c124b0` | CSWeatherLotRegionMan | vftable RTTI | CONFIRMED | 7 |
| `0x3c12538` | SmallBaseAttachPointMan | vftable RTTI | CONFIRMED | 8 |
| `0x3c125d8` | WorldAreaTime | vftable RTTI | CONFIRMED | 28 |
| `0x3c12648` | WorldAreaWeather | vftable RTTI | CONFIRMED | 20 |
| `0x3c13158` | WorldPlayAreaManager | vftable RTTI | CONFIRMED | 24 |
| `0x3c131c8` | CSGaitem | vftable RTTI | CONFIRMED | 130 |
| `0x3c13378` | CSGeomModelInsDelayCreator | vftable RTTI | CONFIRMED | 4 |
| `0x3c134f8` | CSWorldGeomMan | vftable RTTI | CONFIRMED | 207 |
| `0x3c135f0` | GeomFlagSaveDataManager | vftable RTTI | CONFIRMED | 5 |
| `0x3c13668` | GeomNonActiveBlockManager | vftable RTTI | CONFIRMED | 3 |
| `0x3c136e8` | BloodStainMan | vftable RTTI | CONFIRMED | 23 |
| `0x3c137a0` | CSJamaisVuMan | vftable RTTI | CONFIRMED | 33 |
| `0x3c13a78` | WanderGhostMan | vftable RTTI | CONFIRMED | 7 |
| `0x3c13b30` | WorldHitMan | vftable RTTI | CONFIRMED | 90 |
| `0x3c13bc8` | ActPntMan | vftable RTTI | CONFIRMED | 14 |
| `0x3c13c48` | LockTgtMan | vftable RTTI | CONFIRMED | 20 |
| `0x3c13d90` | WorldMapMan | vftable RTTI | CONFIRMED | 41 |
| `0x3c149d8` | CSMenuMan | vftable RTTI | CONFIRMED | 353 |
| `0x3c14a70` | CSFeMan | vftable RTTI | CONFIRMED | 76 |
| `0x3c14c38` | CSItemGetMenuMan | vftable RTTI | CONFIRMED | 3 |
| `0x3c17248` | CSServerInterface | vftable RTTI | CONFIRMED | 372 |
| `0x3c176a0` | CSPlayRegionPointMan | vftable RTTI | CONFIRMED | 8 |
| `0x3c17758` | CSBirdMovePointMan | vftable RTTI | CONFIRMED | 19 |
| `0x3c177d8` | CSActionButtonMan | vftable RTTI | CONFIRMED | 19 |
| `0x3c17858` | CSActionButtonRegionSystem | vftable RTTI | CONFIRMED | 21 |
| `0x3c17908` | CSAutoInvadePoint | vftable RTTI | CONFIRMED | 1 |
| `0x3c179a0` | CSFastTravelOverrideRegionMan | vftable RTTI | CONFIRMED | 3 |
| `0x3c17a18` | CSGroupPlacementPointMan | vftable RTTI | CONFIRMED | 13 |
| `0x3c17ac8` | CSMapPlaceNameOverrideRegionMan | vftable RTTI | CONFIRMED | 7 |
| `0x3c17b48` | CSOpenChrActivateThresholdRegionMan | vftable RTTI | CONFIRMED | 5 |
| `0x3c17be0` | CSPinMan | vftable RTTI | CONFIRMED | 20 |
| `0x3c17c88` | CSRespawnPointMan | vftable RTTI | CONFIRMED | 16 |
| `0x3c17d48` | CSRideJumpRegionMan | vftable RTTI | CONFIRMED | 8 |
| `0x3c17e20` | CSWorldMapPointMan | vftable RTTI | CONFIRMED | 11 |
| `0x3c17eb0` | CSRemo | vftable RTTI | CONFIRMED | 60 |
| `0x3c18648` | CSWorldSceneDrawParamManager | vftable RTTI | CONFIRMED | 11 |
| `0x3c186c8` | WorldSfxMan | vftable RTTI | CONFIRMED | 18 |
| `0x3c18758` | CSShareClearDataInsMan | vftable RTTI | CONFIRMED | 2 |
| `0x3c18988` | CSShareClearDataPointMan | vftable RTTI | CONFIRMED | 4 |
| `0x3c18a50` | WorldSoundMan | vftable RTTI | CONFIRMED | 31 |
| `0x3c1a680` | CSGraphics | vftable RTTI | CONFIRMED | 59 |
| `0x3c1abc0` | CSFade | vftable RTTI | CONFIRMED | 89 |
| `0x3c1ac80` | CSFD4Location | vftable RTTI | CONFIRMED | 6 |
| `0x3c1aea8` | CSLod | vftable RTTI | CONFIRMED | 4 |
| `0x3c1afe8` | FlverRepository | vftable RTTI | CONFIRMED | 24 |
| `0x3c1b138` | FontRepository | vftable RTTI | CONFIRMED | 7 |
| `0x3c1b288` | CSGparamRepository | vftable RTTI | CONFIRMED | 11 |
| `0x3c1b3d8` | IvInfoRepository | vftable RTTI | CONFIRMED | 1 |
| `0x3c1b6f0` | MtdRepository | vftable RTTI | CONFIRMED | 3 |
| `0x3c1b928` | ShaderbdleRepository | vftable RTTI | CONFIRMED | 4 |
| `0x3c1ba18` | CpoRepository | vftable RTTI | CONFIRMED | 4 |
| `0x3c1bb68` | DpoRepository | vftable RTTI | CONFIRMED | 5 |
| `0x3c1be08` | GpoRepository | vftable RTTI | CONFIRMED | 4 |
| `0x3c1bf58` | HpoRepository | vftable RTTI | CONFIRMED | 4 |
| `0x3c1c0a8` | PpoRepository | vftable RTTI | CONFIRMED | 2 |
| `0x3c1c268` | VpoRepository | vftable RTTI | CONFIRMED | 5 |
| `0x3c1c428` | TexRepository | vftable RTTI | CONFIRMED | 69 |
| `0x3c1c578` | TpfRepository | vftable RTTI | CONFIRMED | 9 |
| `0x3c1cca8` | CSFakeLoadingScreen | vftable RTTI | CONFIRMED | 2 |
| `0x3c1cec0` | CSHkAiManager | vftable RTTI | CONFIRMED | 65 |
| `0x3c1d038` | CSHkAiNvmRepository | vftable RTTI | CONFIRMED | 3 |
| `0x3c1d360` | CSHkBehCallBackAdapter | vftable RTTI | CONFIRMED | 6 |
| `0x3c1d3d8` | CSHkBehScriptAdapter | vftable RTTI | CONFIRMED | 4 |
| `0x3c1d4a8` | CSHkBehManager | vftable RTTI | CONFIRMED | 36 |
| `0x3c1d5a8` | CSHkBehScriptRepository | vftable RTTI | CONFIRMED | 1 |
| `0x3c1d768` | CSHkBehStringRepository | vftable RTTI | CONFIRMED | 8 |
| `0x3c1d9a8` | CSWorldNvmManager | vftable RTTI | CONFIRMED | 131 |
| `0x3c1dbe8` | CSDebugSeedPointCtrl | vftable RTTI | CONFIRMED | 1 |
| `0x3c1dc68` | CSBehavior | vftable RTTI | CONFIRMED | 34 |
| `0x3c1df70` | CSCloth | vftable RTTI | CONFIRMED | 49 |
| `0x3c1e028` | CSHavokMan | vftable RTTI | CONFIRMED | 226 |
| `0x3c20b28` | CSHkShapeRepository | vftable RTTI | CONFIRMED | 10 |
| `0x3c20fb0` | HkxpwvRepository | vftable RTTI | CONFIRMED | 4 |
| `0x3c210f8` | CSHavokCompendiumRepository | vftable RTTI | CONFIRMED | 5 |
| `0x3c21248` | HkxRepository | vftable RTTI | CONFIRMED | 10 |
| `0x3c21398` | NvaRepository | vftable RTTI | CONFIRMED | 4 |
| `0x3c214e8` | NvcRepository | vftable RTTI | CONFIRMED | 2 |
| `0x3c21638` | CSBlockPlayerList | vftable RTTI | CONFIRMED | 12 |
| `0x3c21e50` | CSNetworkUserManager | vftable RTTI | CONFIRMED | 43 |
| `0x3c21ec8` | CSSessionManager | vftable RTTI | CONFIRMED | 847 |
| `0x3c21f48` | CSTeamSessionDataMan | vftable RTTI | CONFIRMED | 23 |
| `0x3c21fc8` | CSTeamSessionManager | vftable RTTI | CONFIRMED | 80 |
| `0x3c22048` | CSTestUserNameManager | vftable RTTI | CONFIRMED | 1 |
| `0x3c220d0` | CSWordChecker | vftable RTTI | CONFIRMED | 2 |
| `0x3c22150` | NetLocalDebugBufferQueue | vftable RTTI | CONFIRMED | 2 |
| `0x3c22500` | CSPlatformNetworkMan | vftable RTTI | CONFIRMED | 16 |
| `0x3c22750` | RendMan | vftable RTTI | CONFIRMED | 355 |
| `0x3c22ba8` | AnibndRepository | vftable RTTI | CONFIRMED | 19 |
| `0x3c22cf8` | GeombndRepository | vftable RTTI | CONFIRMED | 3 |
| `0x3c22e48` | GeomhkxbndRepository | vftable RTTI | CONFIRMED | 2 |
| `0x3c22f98` | BehbndRepository | vftable RTTI | CONFIRMED | 1 |
| `0x3c23300` | CSEddRepository | vftable RTTI | CONFIRMED | 2 |
| `0x3c23448` | EsdRepository | vftable RTTI | CONFIRMED | 7 |
| `0x3c23598` | CSEmkResMan | vftable RTTI | CONFIRMED | 13 |
| `0x3c23618` | CSEmedfRepository | vftable RTTI | CONFIRMED | 3 |
| `0x3c23708` | CSEmeldRepository | vftable RTTI | CONFIRMED | 3 |
| `0x3c237f8` | CSEmevdRepository | vftable RTTI | CONFIRMED | 10 |
| `0x3c238e8` | FfxRepository | vftable RTTI | CONFIRMED | 5 |
| `0x3c23a38` | FfxreslistRepository | vftable RTTI | CONFIRMED | 4 |
| `0x3c23b88` | GfxRepository | vftable RTTI | CONFIRMED | 5 |
| `0x3c23d48` | LuaRepository | vftable RTTI | CONFIRMED | 3 |
| `0x3c23e98` | CSMapbndRepository | vftable RTTI | CONFIRMED | 1 |
| `0x3c23fe8` | PartsbndRepository | vftable RTTI | CONFIRMED | 3 |
| `0x3c240d8` | MpwRepository | vftable RTTI | CONFIRMED | 2 |
| `0x3c24388` | MsbRepository | vftable RTTI | CONFIRMED | 8 |
| `0x3c24628` | CSMsbPointMan | vftable RTTI | CONFIRMED | 51 |
| `0x3c246b0` | MsgTagMan | vftable RTTI | CONFIRMED | 57 |
| `0x3c27538` | OnavRepository | vftable RTTI | CONFIRMED | 1 |
| `0x3c27688` | CSEventFlagUsageParamManager | vftable RTTI | CONFIRMED | 6 |
| `0x3c27708` | ParamRepository | vftable RTTI | CONFIRMED | 25 |
| `0x3c27cb0` | SystemParamRepository | vftable RTTI | CONFIRMED | 5 |
| `0x3c28880` | SoloParamRepository | vftable RTTI | CONFIRMED | 261 |
| `0x3c28990` | PartsRelationinfobndRepository | vftable RTTI | CONFIRMED | 1 |
| `0x3c28ad8` | CsResMemStatistics | vftable RTTI | CONFIRMED | 54 |
| `0x3c28ca8` | RumblebndRepository | vftable RTTI | CONFIRMED | 2 |
| `0x3c28d98` | ScaleformTexRepository | vftable RTTI | CONFIRMED | 13 |
| `0x3c28e18` | WavbndRepository | vftable RTTI | CONFIRMED | 1 |
| `0x3c28f08` | CSScaleformArabic | vftable RTTI | CONFIRMED | 3 |
| `0x3c299c8` | CSScaleform | vftable RTTI | CONFIRMED | 65 |
| `0x3c2a098` | CSSfx | vftable RTTI | CONFIRMED | 160 |
| `0x3c2a128` | CSDebugBankPlayerMng | vftable RTTI | CONFIRMED | 2 |
| `0x3c2a3b0` | CSSound | vftable RTTI | CONFIRMED | 155 |
| `0x3c2a768` | MoWwiseMan | vftable RTTI | CONFIRMED | 82 |
| `0x3c2a8a8` | CSFD4MoWwisebankRepository | vftable RTTI | CONFIRMED | 42 |
| `0x3c2acd8` | CSBudgetMonitor | vftable RTTI | CONFIRMED | 34 |
| `0x3c2aff8` | CSBugReportManager | vftable RTTI | CONFIRMED | 3 |
| `0x3c2c1a0` | CSCheatEOS | vftable RTTI | CONFIRMED | 36 |
| `0x3c2c830` | CSDbgIdName | vftable RTTI | CONFIRMED | 1 |
| `0x3c2cc18` | CSPanic | vftable RTTI | CONFIRMED | 2 |
| `0x3c2d128` | SoundEventCheckMan | vftable RTTI | CONFIRMED | 3 |
| `0x3c2d218` | CSDlc | vftable RTTI | CONFIRMED | 43 |
| `0x3c2d400` | CSRegulationManager | vftable RTTI | CONFIRMED | 5 |
| `0x3c2d640` | EntityThumbnailMan | vftable RTTI | CONFIRMED | 7 |
| `0x3c2d728` | CSGxLoadBalancerHelper | vftable RTTI | CONFIRMED | 5 |
| `0x3c2d7a8` | CSLoadBalancer | vftable RTTI | CONFIRMED | 6 |
| `0x3c2d828` | CSMemLoadBalancer | vftable RTTI | CONFIRMED | 3 |
| `0x3c2df48` | CSMemory | vftable RTTI | CONFIRMED | 9 |
| `0x442e028` | CSMouseMan | vftable RTTI | CONFIRMED | 7 |
| `0x442e0a8` | CSMovie | vftable RTTI | CONFIRMED | 12 |
| `0x442e7b0` | CSPerfMan | vftable RTTI | CONFIRMED | 3 |
| `0x442e8a8` | CSPlaygo | vftable RTTI | CONFIRMED | 18 |
| `0x442ec00` | CSPlaylogSystem | vftable RTTI | CONFIRMED | 72 |
| `0x442f1d0` | CSSystemProperties | vftable RTTI | CONFIRMED | 89 |
| `0x442f288` | CSPS5Activity | vftable RTTI | CONFIRMED | 11 |
| `0x442f3f8` | CSReportSystem | vftable RTTI | CONFIRMED | 2 |
| `0x442f688` | MsgCheckReport | vftable RTTI | CONFIRMED | 1 |
| `0x442f960` | CSTrophy | vftable RTTI | CONFIRMED | 4 |
| `0x442f9e8` | UserConfig | vftable RTTI | CONFIRMED | 50 |
| `0x442fa68` | UserMan | proximity-to-runtime-class-slot(+0x10) | LIKELY | 3 |
| `0x442fb88` | CSDelayDeleteMan | vftable RTTI | CONFIRMED | 23 |
| `0x442fe78` | CSEzWorkPool | vftable RTTI | CONFIRMED | 17 |
| `0x442fef8` | CSFlipper | vftable RTTI | CONFIRMED | 45 |
| `0x442ff78` | CSLuaConsoleServer | vftable RTTI | CONFIRMED | 2 |
| `0x4433980` | CSWindow | vftable RTTI | CONFIRMED | 38 |
| `0x4433a18` | CSResidentTalkFileMan | vftable RTTI | CONFIRMED | 2 |
| `0x4433a98` | CSScenarioPlacementManager | vftable RTTI | CONFIRMED | 5 |
| `0x4433df0` | CSWorldTalkMan | vftable RTTI | CONFIRMED | 62 |
| `0x4434000` | CSTask | vftable RTTI | CONFIRMED | 24 |
| `0x4434088` | CSTaskGroup | vftable RTTI | CONFIRMED | 5 |
| `0x4706e98` | FD4DebugMenuManager | proximity-to-runtime-class-slot(+-0x8) | LIKELY | 276 |
| `0x4707290` | FD4ComponentAttachSystemSeed | proximity-to-runtime-class-slot(+-0x8) | LIKELY | 22 |
| `0x4707350` | FD4HkClothClm2Repository | proximity-to-runtime-class-slot(+-0x8) | LIKELY | 4 |
| `0x4707370` | FD4HkClothDataRepository | proximity-to-runtime-class-slot(+-0x8) | LIKELY | 4 |
| `0x47073d0` | FD4ParamdefRepositoryImplement | proximity-to-runtime-class-slot(+-0x8) | LIKELY | 8 |
| `0x4707d48` | FD4PadManager | proximity-to-runtime-class-slot(+0x10) | LIKELY | 57 |
| `0x4707dd8` | FD4HkClothManager | proximity-to-runtime-class-slot(+-0x8) | LIKELY | 7 |
| `0x4707df8` | FD4HkClothCollidableDataRepositoryImp | proximity-to-runtime-class-slot(+-0x8) | LIKELY | 2 |
| `0x4707e18` | FD4RemoManager | proximity-to-runtime-class-slot(+-0x10) | LIKELY | 24 |
| `0x4707e38` | FD4MqbRepositoryImp | proximity-to-runtime-class-slot(+-0x8) | LIKELY | 3 |
| `0x4707e68` | FD4RemoHkxRepositoryImp | proximity-to-runtime-class-slot(+-0x8) | LIKELY | 2 |
| `0x4707e90` | FD4FontManager | proximity-to-runtime-class-slot(+-0x8) | LIKELY | 5 |
| `0x4707ea8` | FD4RemoteUserInputSystem | proximity-to-runtime-class-slot(+-0x8) | LIKELY | 2 |
| `0x4707ed0` | FD4EzDrawManager | proximity-to-runtime-class-slot(+-0x8) | LIKELY | 1 |
| `0x4707ee8` | FD4HkEzDrawRigidBodyDispBufferManager | proximity-to-runtime-class-slot(+-0x8) | LIKELY | 1 |
| `0x4707f68` | FD4ParameterManager | proximity-to-runtime-class-slot(+-0x8) | LIKELY | 1 |
| `0x4707f70` | FD4ParamNametdfRepository | proximity-to-runtime-class-slot(+0x8) | LIKELY | 4 |
| `0x4707f90` | FD4ParamNametdfRepositoryImplement | proximity-to-runtime-class-slot(+-0x8) | LIKELY | 2 |
| `0x4708010` | FD4ReportSystem | proximity-to-runtime-class-slot(+-0x8) | LIKELY | 9 |
| `0x4708070` | FD4LoggerManager | proximity-to-runtime-class-slot(+-0x8) | LIKELY | 2 |
| `0x4708090` | FD4PerformanceManager | proximity-to-runtime-class-slot(+-0x10) | LIKELY | 1 |
| `0x4708140` | FD4PerfManager | proximity-to-runtime-class-slot(+-0x10) | LIKELY | 4 |
| `0x47081f0` | FD4DelayDeleteManager | proximity-to-runtime-class-slot(+-0x8) | LIKELY | 4 |
| `0x4708438` | FD4ParamtdfRepository | proximity-to-runtime-class-slot(+-0x8) | LIKELY | 1 |

## 5. RTTI vftables (primary, offset 0) — CONFIRMED

Interface classes (`CSEventFlagMan`, `WorldChrMan`, `CSMenuMan`, `MapItemMan`, `SoloParamRepository`, `MsgRepository`, `CSSystemProperties`, `CSNetMan`, `CSFile`, `CSRegulationManager`) have no RTTI of their own in this build; their `*Imp`/`*Impl` concrete classes do. `GameDataMan` has neither RTTI nor a DLRF class (same as ER). 5,228 `@CS@@` type descriptors dumped to `rtti_cs_names.txt` (name → vftable RVA).

| class | primary vftable RVA |
|---|---|
| CSEventFlagMan | no RTTI (interface w/o RTTI or non-virtual) |
| CSEventFlagManImp | no RTTI (interface w/o RTTI or non-virtual) |
| CSFD4VirtualMemoryFlag | `0x2c2b300` |
| GameDataMan | no RTTI (interface w/o RTTI or non-virtual) |
| GameMan | `0x2c325d8` |
| WorldChrMan | no RTTI (interface w/o RTTI or non-virtual) |
| WorldChrManImp | `0x2c1b930` |
| CSMenuMan | no RTTI (interface w/o RTTI or non-virtual) |
| CSMenuManImp | `0x2c3ad00` |
| MapItemMan | no RTTI (interface w/o RTTI or non-virtual) |
| MapItemManImpl | `0x2c234c0` |
| SoloParamRepository | no RTTI (interface w/o RTTI or non-virtual) |
| SoloParamRepositoryImp | `0x2cb1e08` |
| MsgRepository | no RTTI (interface w/o RTTI or non-virtual) |
| MsgRepositoryImp | `0x2ca9688` |
| CSSystemProperties | no RTTI (interface w/o RTTI or non-virtual) |
| CSSystemPropertiesImp | `0x2cd3ca8` |
| CSNetMan | no RTTI (interface w/o RTTI or non-virtual) |
| CSNetManImp | `0x2bda5d8` |
| PlayerGameData | `0x2be6e28` |
| EquipInventoryData | `0x2be4a40` |
| EquipGameData | `0x2be4970` |
| CSGaitemGameData | `0x2be41d0` |
| CSFile | no RTTI (interface w/o RTTI or non-virtual) |
| CSFileImp | `0x2bdc638` |
| CSRegulationManager | no RTTI (interface w/o RTTI or non-virtual) |
| CSRegulationManagerImp | `0x2cc44d8` |
| CSItemGetMenuManImpl | `0x2c3b8e8` |
| CSGaitemImp | `0x2c32260` |
| CSGaitemIns | `0x2c32318` |
| ChrIns | `0x2c0ba90` |
| PlayerIns | `0x2c307f8` |
| CSLuaEventManagerImp | no RTTI (interface w/o RTTI or non-virtual) |
| CSEventFlagUsageParamManagerImp | no RTTI (interface w/o RTTI or non-virtual) |

Extra: `CSFD4VirtualMemoryFlag` vftable `0x2c2b300` has a single virtual (deleting dtor `0x60c920`); GetFlag/SetFlag are **non-virtual** (see §7).

## 6. Statics for non-DLRF classes (data-xref heuristics)

### 6.1 `GameDataMan` — `0x3c078d0` — CONFIRMED (two independent methods agree)

1. Creation site `0x1fd5e5` (function `0x1fd5d0`), NR-specific AOB (unique in .text):
   ```
   B9 58 04 00 00 E8 ?? ?? ?? ?? 48 89 44 24 38 48 85 C0 74 09 48 8B C8 E8 ?? ?? ?? ?? 90 48 89 05 ?? ?? ?? ?? 48 83 C4 28 E9
   mov ecx,458h ; call alloc ; mov [rsp+38],rax ; test rax,rax ; jz ; mov rcx,rax ; call GameDataMan::ctor (0x1fa740) ; nop ; mov [rip+0x3c078d0],rax ; add rsp,28h ; jmp
   ```
   Same shape as the ER mapper pattern `48 89 05 ${'} 48 83 c4 38 e9` (ER's frame is 0x38, NR's is 0x28 → the ER pattern gets 0 hits, the generic `48 89 05 ? ? ? ? 48 83 C4 28 E9` gets 108, so use the `B9 58 04 00 00`-anchored form).
2. It is the most-referenced non-DLRF `.data` slot from the translation unit that contains the `CS::GameDataMan::*` profiler strings (`OnGameClear` fn `0x200320`, `OnMoveMapInitialize` `0x200480`, `UpdatePlayPhase` `0x203250`, `UpdateStatisticsData` `0x2034f0`, `Reset_forEnterLobby` `0x201040`, `Reset_forEnterIngameTutorial` `0x200af0`): 979 references in total (747 `mov rax,[rip+X]`), 412 from that TU. The most common reader shape is `mov rax,[rip+X]; test rax,rax; jz; mov rcx,[rax+8]` → **`main_player_game_data` at `GameDataMan+0x8`** (ER layout preserved).

### 6.2 Others via vftable → constructor → caller → `mov [rip+X],rax` (within 64 B after the ctor call)

| class (vftable) | static found | cross-check | tag |
|---|---|---|---|
| `GameMan` (`0x2c325d8`, ctor `0x6a7c20`, store at `0x6ae220`) | **`0x3c13258`** (376 refs) | ER `GameManAoB` `48 8B 05 ? ? ? ? 80 B8 ? ? ? ? 0D 0F 94 C0 C3` hits exactly once at `0x6ae7b0` and resolves to the same slot (`cmp byte [GameMan+0xdc0],0Dh` — the "is in game" byte moved from ER's offset to `+0xdc0`) | CONFIRMED |
| `CSMenuManImp` (ctor `0x7b3d10`) | `0x3c149d8` | = FD4Singleton `CSMenuMan` | CONFIRMED |
| `CSRegulationManagerImp` (ctor `0xf4cdb0`) | `0x3c2d400` | = FD4Singleton `CSRegulationManager` | CONFIRMED |
| `MsgRepositoryImp` (ctor `0xe5a640`) | `0x3c246a8` | = derived singleton `MsgRepository` | CONFIRMED |
| `CSNetManImp` (ctor `0x1867b0`) | `0x3c046a8` | = FD4Singleton `CSNetMan` | CONFIRMED |
| `CSFileImp` (ctor `0x193e90`) | `0x3c04a28` | = derived singleton `CSFile` | CONFIRMED |
| `WorldChrManImp` (ctor `0x514e70`) | `0x3c0f0a8` | = FD4Singleton `WorldChrMan` (2,974 refs) | CONFIRMED |
| `MapItemManImpl` (ctor `0x56e5b0`) | `0x3c10b68` | = FD4Singleton `MapItemMan` | CONFIRMED |
| `CSGaitemImp` | `0x3c131c8` | = FD4Singleton `CSGaitem` | CONFIRMED |
| `PlayerGameData` (ctor `0x2087c0`, store at `0x20b6ca`) | `0x3c078f8` (only 3 refs) | a static `PlayerGameData*` right after the GameDataMan slot — probably a default/dummy player-data object, **not** the live one (live one is `GameDataMan->+8`) | GUESS |
| `EquipGameData`, `CSFD4VirtualMemoryFlag`, `SoloParamRepositoryImp`, `CSSystemPropertiesImp`, `CSEventFlagManImp`, `CSItemGetMenuManImpl` | no ctor→static store found (embedded members / constructed through other paths) | use the FD4 slots instead | — |

The agreement between the ctor heuristic and the DLRF walker on 8 classes is the validation for the method used on GameMan.

## 7. Event flags — CONFIRMED

Found by the divisor idiom (`mov r32,[rcx+1Ch]; xor edx,edx; div r32` = `id / event_flag_divisor`), then classified by the bit ops. Both functions are unique matches for the AOBs below. Neither uses the 1000 magic-multiply — the divisor is read from the object (as in ER).

### 7.1 `CSFD4VirtualMemoryFlag::GetFlag(this, u32 flag_id) -> bool` — `0x60ce40` (size 0xa3, **no .pdata entry**)
```
44 8B 41 1C 44 8B DA 33 D2 41 8B C3 41 F7 F0 4C 8B D1 45 33 C9 44 0F AF C0 45 2B D8 4C 8B 41 38   ; unique AOB
mov r8d,[rcx+1Ch]  ; divisor (1000)
mov r11d,edx ; xor edx,edx ; mov eax,r11d ; div r8d      ; eax = group, r11d = id - group*divisor
mov r10,rcx ; xor r9d,r9d ; imul r8d,eax ; sub r11d,r8d
mov r8,[rcx+38h] ; mov rdx,r8 ; mov rcx,[r8+8]           ; DLMap<u32,FlagBlockDescriptor> tree: head at +0x38, root = head->+8
  loop: cmp byte [rcx+19h],0 (nil) ; cmp [rcx+20h],eax (key) ; rcx=[rcx+10h] / [rcx] (left/right)
cmp eax,[rdx+20h] ; jb fail ; ... (lower_bound on group id)
mov ecx,[rdx+28h] ; sub ecx,1 ; jz -> mov rax,[rdx+30h]            ; descriptor kind 1: block pointer stored inline
   else cmp ecx,1 ; jne fail ; mov eax,[rdx+30h] ; imul eax,[r10+20h] ; add rax,[r10+28h]   ; kind 2: index * holder_size + flag_blocks
test rax,rax ; jz ret0
mov ecx,7 ; mov edx,r11d ; and edx,7 ; mov r8d,1 ; sub ecx,edx ; shl r8d,cl   ; bit = 7 - (rem & 7)
mov ecx,r11d ; shr rcx,3 ; test [rcx+rax],r8b ; setne r9b ; mov eax,r9d ; ret   ; byte = rem >> 3
```
→ layout of `CSFD4VirtualMemoryFlag`: `+0x1c event_flag_divisor`, `+0x20 event_flag_holder_size`, `+0x28 flag_blocks`, `+0x38 flag_block_descriptors` tree head (ER has the DLMap at `+0x30`, i.e. head ptr at `+0x38` — identical). Descriptor node: `+0x20 key(group)`, `+0x28 kind`, `+0x30 ptr-or-index`. Bit order matches ER (`7 - (id%1000)%8`).

### 7.2 `CSFD4VirtualMemoryFlag::SetFlag(this, u32 flag_id, bool value)` — `0x60d330` (size 0xb3)
```
48 89 5C 24 08 44 8B 49 1C 44 8B D2 33 D2 41 8B C2 41 F7 F1 4C 8B D9 41 8B D8 48 8B 49 38          ; unique AOB
... same tree walk ...; test ebx,ebx ; jz -> btr eax,edx ; else bts eax,edx ; mov [rcx],al
```
If no descriptor exists for the group the function returns without writing (same silent no-op the ER client documents).

### 7.3 `CSEventFlagMan` wrappers (translation unit `0x5e72xx–0x5e7bxx`; `CSFD4VirtualMemoryFlag` is at `CSEventFlagMan+0`, a lock/critical-section object at `+0x1f0`)

| fn | RVA | AOB (unique) | notes |
|---|---|---|---|
| `CSEventFlagMan::GetEventFlag(this, u32* flag_id) -> bool` | `0x5e7260` (0x48 B) | `48 89 5C 24 08 57 48 83 EC 20 83 3A 00 48 8B DA 48 8B F9 74 ? 48 81 C1 F0 01 00 00 E8` | `cmp dword [rdx],0 ; jz ret false ; lea rcx,[this+1F0h] ; call lock-ish (0x5e1480) ; mov edx,[rbx] ; mov rcx,rdi ; call GetFlag ; test eax,eax ; setne al`. Same ABI as ER's `IsEventCall` (`GetEventFlag(CSEventFlagMan*, u32*)`). |
| `CSEventFlagMan::SetEventFlag(this, u32* flag_id, bool value, r9=unk)` | `0x5e79f0` (root; Arxan chunks `0x5e7a12/0x5e7a21/0x5e7ad1`) | `48 89 5C 24 20 55 56 57 48 83 EC 30 83 3A 00 49 8B E9 41 0F B6 F8 48 8B DA 48 8B F1 0F 84` | reads current value via GetFlag, consults `CSEventFlagUsageParamManager` (`0x3c27688`) / logs, then `mov edx,[rbx]; mov r8d,edi; mov rcx,rsi; call SetFlag`. Byte-for-byte the same register choreography as ER's `SetEventCallAoB` (`... 48 8B DA 41 0F B6 F8 8B 12 48 8B F1 85 D2 0F 84`). |
| variant with net-sync (`0x5e7740`, 0x1d8 B) | `0x5e7740` | — | calls both GetFlag and SetFlag, references `CSEventFlagUsageParamManager`; likely `SetEventFlag` for the networked path (EMEVD `SetNetworkconnectedEventFlagID`). GUESS on the exact name. |
| batch getter (`0x5e7570`, 0xae B, loops `r8d` times over an id array) | `0x5e7570` | — | GUESS: `GetEventFlags(this, u32* ids, u32 count, …)`. |

Other divisor users (not flag get/set): `0x60d0d0`, `0x60d3f0` (range/block helpers), `0x23fe2d5`, `0x25d1940` (unrelated).

For the DLL the cheapest path is still the ER-client approach — read `CSEventFlagMan` (`0x3c115a8`), treat it as `CSFD4VirtualMemoryFlag` at `+0` and walk the tree as above — or just `call` `0x60ce40` / `0x60d330` with `rcx=[0x3c115a8]`, `edx=id`, (`r8b=value`). Calling `0x5e79f0` additionally goes through the usage-param / logging path the game itself uses.

## 8. Item give ("ItemGib") candidates

The ER `ItemGib` AOBs do **not** transfer: `8B 02 83 F8 0A` (0 hits), the full ER prologue (0 hits); the bare prologue `40 55 56 57 41 54 41 55 41 56 41 57 48 8D 6C 24` / `48 8D AC 24` hits `0x1dbe4f0`, `0x1dbffc0`, `0x1efb240` — all three are 5–6-chunk Arxan-split functions with **no** singleton references, no item-category constants and no strings → **not** item code (GUI/Scaleform region). Ranked candidates from semantic evidence instead:

| rank | RVA | identity / evidence | tag |
|---|---|---|---|
| 1 | **`0x1f0160`** (0x48f B, 1 chunk, 47 callers) | **`CS::EquipGameData::AddInventoryEquip`** (profiler string referenced from inside). Prologue `48 89 5C 24 10 48 89 74 24 18 48 89 7C 24 20 55 41 54 41 55 41 56 41 57 48 8D 6C 24 D9 48 81 EC 90 00 00 00 45 0F B6 F1 45 8B F8 4C 8B E2` (unique). Args: `rcx=EquipGameData*`, `rdx=item entry ptr` (r12), `r8d=quantity` (r15d), `r9b=bool` (r14b), + stack bools. Writes `mov [rcx+304h],0` on entry and `mov dword [rbx+304h],2` on the duplicate-unique path → `last_add_item_result` at **`EquipGameData+0x304`** (ER values Success=0 / UniqueItemDuplicate=2). Uses `id & 0xF0000000` vs `0x40000000`/`0x80000000` and `id & 0x0FFFFFFF`; passes `this+0x1c8` (inventory sub-object) to the inner add. References GameDataMan/WorldChrMan/CSEventFlagMan. This is the NR analogue of 4laric's `AddItemFunc` (inventory, entry, …) and the recommended detour target for both pickup detection and AP grants. | LIKELY |
| 2 | **`0x581800`** (0x317 B; reached via thunks `0x5769a0` = plain `jmp`, `0x5769b0`/`0x5769c0` = `mov r9d,1; xor r8d,r8d; jmp`) | **`CS::MapItemManImpl::_RequestRegistGetItem(MapItemMan*, u32 edx, bool r8b, u32 r9d)`**; reads `GameDataMan->+8`, sets an event flag via `0x5e79f0`; callers pass an id read from map-object/talk data (`mov rcx,[MapItemMan]; mov edx,[rdi+18h]; mov r9d,1; xor r8d,r8d`). Call graph: `0x581800 → 0x57ca60 → 0x57a0f0 → 0x1f0160`. This is the item-lot / world-pickup entry point (ItemGib-like), **not** a raw (id,qty) giver. | LIKELY |
| 3 | `0x57a0f0` (0x37c B, single caller `0x57ca60`) | per-item give: `mov r14,[GameDataMan]->+8 ; add r14,1D8h` (**`EquipGameData` = `PlayerGameData+0x1d8`**), `mov eax,[rdi]; and edx,0FFFFFFFh; and eax,0F0000000h; cmp eax,40000000h` (goods), then `call AddInventoryEquip`. Also touches `CSFeMan` (HUD notification) and `CSServerInterface`. Prologue `4C 89 4C 24 20 44 88 44 24 18 48 89 4C 24 08 55 53 56 57 41 54 41 55 41 56 41 57 48 8B EC 48 83 EC 68 48 8B FA 4C 8B F9` (unique). Args `(MapItemMan*, ItemEntry* rdx {id @+0,…}, bool r8b, void* r9)`. Closest thing to a "give this item entry to the player with UI" primitive. | LIKELY |
| 4 | `0x57ca60` (0x36c B, 6 callers incl. `Limited_RequestRegistGetTalkItem` `0x5732f0`) | dispatcher on a request struct (`movzx eax,byte [rdx]; cmp al,1` type byte, entry at `rdx+8`); calls `0x57a0f0` / `0x57a470`. | GUESS |
| 5 | `0x1fd620` (0x48c B, right after the GameDataMan factory) | GameDataMan-TU function that builds an entry on the stack and calls AddInventoryEquip with `rcx=r14+1D8h`; has all category masks. Probably a `GameDataMan::AddItem…` convenience wrapper — good secondary hook. | GUESS |
| 6 | `0xfdee30` (0x4fb8 B) | huge dispatcher referencing `CSItemGetMenuMan`, `CSMenuMan`, `CSWorldTalkMan`, `MsgRepository`, with the only `cmp eax,0Ah` near item code — the talk/ESD command table (calls the `0x5769a0` thunk twice). Not a hook target. | GUESS |

`CS::EquipGameData::CheckAddItem_forDLC` = `0x1f0a90` (reached by `jmp` from `0x209ee7`), `CS::MapItemManImpl::_NotifyRemoveMapItem` = `0x57d400`, `CS::ItemLotUtil::_ResetCumulateNum` = `0x569330`, `CS::ItemLotParam::Util_CanExecByEventFlag` = `0xe8fcd0`, `CS::MenuGaitemEnumerator::_Enumerate_ArchiveItems` = `0x8c0320` (inventory enumeration for the menu; useful for an inventory walk). Top `AddInventoryEquip` callers (wrappers worth hooking/inspecting): `0x2057b0` (10 call sites), `0x7fa120`, `0x1f1540`, `0x204a40`, `0x2054b0`, `0x7f8f40` (refs GameDataMan+MapItemMan+CSMenuMan), `0x204e80`, `0x2046e0`.

What is still unknown statically: the exact layout of the entry struct passed in `rdx` (ER: `{count, {id, qty, ...}}` with count at +0 and id at +4; NR reads `[rdi]` as the id in `0x57a0f0`, so NR may pass the entry directly). Verify with a breakpoint on `0x1f0160` at a world pickup before shipping.

## 9. ER AOB templates re-tested on NR

| ER AOB | hits | comment |
|---|---|---|
| `GameDataManAoB` `48 8B 05 ? ? ? ? 48 85 C0 74 05 48 8B 40 58 C3 C3` | 0 | getter changed; use §6.1 |
| `GameManAoB` | **1** (`0x6ae7b0`) | valid → `0x3c13258` |
| `SoloParamRepositoryAoB`, `WorldChrManAoB`, `CSFD4VirtualMemoryFlagAoB`, `MapItemManAoB`, `MsgRepositoryImpAoB`, `ChrDebugFlagsAoB`, `RemoveItemAoB`, `IsEventCallAoB`, `SetEventCallAoB`, `ItemGiveAoB`, `cs_menu_man_imp_display_status_message` | 0 | use the DLRF slots / §7 / §8 |
| `CSLuaEventManagerAoB` `48 83 3D ? ? ? ? 00 48 8B F9 0F 84 ? ? ? ? 48` | 1 (`0x5ced06`) | **false positive**: the rip target is `0x605130` (in .text, not .data). `CSLuaEventMan` is an FD4Singleton at `0x3c10f60`. |
| ItemGib prologues | 2 + 1 | false positives (see §8) |

## 10. Suggested DLL strategy (static-only conclusions)

1. Gate on VERSIONINFO `("elden ring nightreign", lang 0x0009, "1.3.3.0")` **and** on the unique AOBs of §7/§8 at the pinned RVAs (fail closed).
2. Singletons: either keep `from-singleton` (works — 770 of the 9,144 matched FD4 null-check sites use the `cmp qword [rip+X],0` form the crate ignores, but only `MsgCheckReport` (`0x442f688`) and the derived `CSResManager` (`0x3c230e8`) are reachable *solely* through that form, so the unmodified crate finds every singleton the DLL needs) or use the pinned slots from §4.
3. Flags: `CSEventFlagMan` `0x3c115a8` → `GetFlag 0x60ce40` / `SetFlag 0x60d330` (or the wrappers `0x5e7260` / `0x5e79f0`). Layout is ER-compatible, so 4laric's `CSFD4VirtualMemoryFlag` struct walker should work unchanged.
4. Items: detour `0x1f0160` (`EquipGameData::AddInventoryEquip`); grant by calling it with `rcx = *(GameDataMan+8) + 0x1d8` once the entry layout is confirmed in a debugger; `last_add_item_result` at `+0x304`.
5. Murk/runes: `PlayerGameData = *(0x3c078d0)->+8`; the rune offset (`+0x6C` in ER / kwwsyk chain) is not derivable statically — confirm live.
