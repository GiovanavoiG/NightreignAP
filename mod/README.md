# Elden Ring: Nightreign — Archipelago mod (prototype)

Rust `cdylib` loaded by **Mod Engine 3** (`[[natives]]`). Follows the architecture of the current Dark Souls III
4.x client and 4laric's Elden Ring AP client: the DLL itself is the Archipelago client (no Python client process),
nothing on disk is patched, and all locking/granting happens live.

```
src/lib.rs          DllMain -> spawn: logging, config, game::init, overlay, AP task, poller
src/ap.rs           archipelago_rs session: Connect, LocationChecks, ReceivedItems, DeathLink, goal
src/state.rs        shared state (parking_lot mutex)
src/config.rs       archipelago.toml next to the DLL
src/overlay.rs      hudhook ImGui window (F9): server/slot/password, log, toasts
src/game/
   singletons.rs    FD4 singleton lookup (CSEventFlagMan, GameDataMan, WorldChrMan)   TODO(RE) offsets
   flags.rs         event-flag get/set + flag catalogue                                  TODO(RE) ids
   grant.rs         item id -> flag set / ItemGib / Murk write                           TODO(RE) goods ids
   locks.rs         expedition / nightfarer / shifting-earth / remembrance gating        TODO(RE) hook sites
nightreign-archipelago.me3   me3 profile (offline, separate save NR_AP.sl2, arxan disabled, premain native)
archipelago.toml             connection settings
build.ps1                    cargo build + stage/deploy
```

## Status

Complete scaffolding, **not yet compiled against the real crates** (this sandbox cannot reach crates.io). Expect
minor API adjustments to `archipelago_rs` / `hudhook` calls when first building. Every game-specific constant is
`TODO(RE)` — see the discovery document for the reverse-engineering plan and the tools to use (Hexinton CE table,
Smithbox, fromsoftware-rs `eldenring` crate as the layout reference).

## Build

```powershell
rustup target add x86_64-pc-windows-msvc
.\build.ps1 -Deploy
```

## Mod management

me3 profiles are self-contained folders; the Mod Engine 3 Manager (Nexus Nightreign #213) can import the `dist\`
folder as a mod. r2modman does not support Nightreign, so me3 (or its Manager) is the intended manager.

## Co-op

To play with Seamless Co-op: point the `.me3` profile's launcher at `nrsc_launcher.exe` (see me3 discussion #655) and
load this DLL through Seamless Co-op's `mods/` folder instead of `[[natives]]`. Only the host runs the AP mod.
