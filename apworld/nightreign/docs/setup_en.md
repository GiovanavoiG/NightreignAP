# Elden Ring: Nightreign Setup Guide

## Required software

- Elden Ring: Nightreign on Steam (Windows). The Forsaken Hollows DLC is optional.
- [Mod Engine 3 (me3)](https://github.com/garyttierney/me3/releases) 0.11 or newer.
- `nightreign.apworld` (drop into Archipelago's `custom_worlds/`).
- The `nightreign-archipelago` mod: `nightreign_archipelago.dll` + `nightreign-archipelago.me3` profile.

## Installing the mod

1. Install me3 and run it once so it registers the `.me3` file type.
2. Extract the mod release into a folder, e.g. `%LOCALAPPDATA%\me3\mods\nightreign-archipelago\`.
3. Double-click `nightreign-archipelago.me3`. me3 starts `nightreign.exe` **without EAC**, offline, using a separate
   save file (`NR_AP.sl2`) so your normal save is never touched.

## Connecting

At the title screen press `F9` (default) to open the Archipelago overlay, enter `server:port`, slot name and
password, then press *Connect*. Items you already own are granted the moment you load into the Roundtable Hold.

## Co-op (optional)

Install Seamless Co-op for Nightreign and point the me3 profile at its launcher (see the mod README). Only the host
needs the Archipelago mod; guests' kills still count as the host's checks.

## Troubleshooting

- *"signin is not available"* — you launched with EAC. Always start via the `.me3` profile.
- *Overlay does not appear* — make sure the DLL is listed under `[[natives]]` in the profile and that no other
  DirectX overlay mod (e.g. Pause the Game) is loaded twice.
- *Checks not sending* — the contract hash of the DLL must match the apworld version; update both together.
