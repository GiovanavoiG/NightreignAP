# Elden Ring: Nightreign — Archipelago

An [Archipelago](https://archipelago.gg) multiworld randomizer integration for Elden Ring: Nightreign (Steam, Windows,
App 1.03.2). Status: **prototype 0.2.0** — the APWorld generates and is tested against Archipelago 0.6.7; the
game-side mod is a Rust me3 native skeleton with the confirmed event-flag ids wired in and the runtime singleton
offsets still to be verified (see `DISCOVERY.md` and `research/nightreign_signatures.md`).

```
apworld/nightreign/          the Archipelago world (Python)
mod/                         me3 native DLL (Rust) + me3 profile + archipelago.toml
players/                     example YAML
research/                    raw research with sources; signatures/event flags; Archipelago API notes
tools/pack_apworld.py        builds build/nightreign.apworld
DISCOVERY.md                 findings, design, reverse-engineering plan, open items
```

## What gets randomized

Meta-progression only (Nightreign runs are still random 3-day expeditions). Items: Nightfarers, Expedition Access,
Shifting Earth unlocks, Remembrance Keys (or progressive Remembrances), Goblets/Grails, Murk, relics, traps. Checks:
Nightlord kills, night/field boss first kills, Remembrance chapters, Bazaar purchases, character unlock quests,
Shifting Earth clears, optional per-run challenges and Deep of Night depths.

Key options: `dlc_forsaken_hollows`, `expedition_locks`, `nightfarer_shuffle`, `remembrance_locks`
(none / key / progressive), `shifting_earth_locks`, `per_run_checks`, `deep_of_night_checks`, `seamless_coop`.

## Development

```powershell
git clone --branch 0.6.7 https://github.com/ArchipelagoMW/Archipelago.git; cd Archipelago; pip install -r requirements.txt
New-Item -ItemType SymbolicLink -Path worlds\nightreign -Target <this repo>\apworld\nightreign
python -m unittest discover -s worlds\nightreign\test -t .
python Generate.py --player_files_path <this repo>\players
python <this repo>\tools\pack_apworld.py     # -> build\nightreign.apworld
cd <this repo>\mod; .\build.ps1 -Deploy     # Rust DLL -> %LOCALAPPDATA%\me3\mods\nightreign-archipelago
```

CI (`.github/workflows/ci.yml`) runs the tests against Archipelago 0.6.7, packages the `.apworld`, builds the DLL on a
Windows runner (allowed to fail until the crate has been reconciled with the current `archipelago_rs` / `hudhook`
APIs), and attaches everything to a GitHub Release on `v*` tags.

## Installing (players)

1. Drop `nightreign.apworld` into Archipelago's `custom_worlds/`.
2. Install [Mod Engine 3](https://github.com/garyttierney/me3/releases); extract the mod folder and double-click
   `nightreign-archipelago.me3` (launches without EAC, offline, with its own `NR_AP.sl2` save).
3. Press F9 in game to open the Archipelago overlay and connect.
