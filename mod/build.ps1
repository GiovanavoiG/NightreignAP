<#
.SYNOPSIS  Build the Nightreign Archipelago DLL and stage an me3 mod folder.
.EXAMPLE   .\build.ps1 -Deploy
#>
param([switch]$Deploy, [string]$Me3Mods = "$env:LOCALAPPDATA\me3\mods\nightreign-archipelago")
$ErrorActionPreference = "Stop"
cargo build --release --target x86_64-pc-windows-msvc
$dll = "target\x86_64-pc-windows-msvc\release\nightreign_archipelago.dll"
if (-not (Test-Path $dll)) { throw "build failed" }
New-Item -ItemType Directory -Force dist | Out-Null
Copy-Item $dll dist\ -Force
Copy-Item nightreign-archipelago.me3, archipelago.toml dist\ -Force
Write-Host "Staged dist\"
if ($Deploy) {
    New-Item -ItemType Directory -Force $Me3Mods | Out-Null
    Copy-Item dist\* $Me3Mods -Force
    Write-Host "Deployed to $Me3Mods - double-click nightreign-archipelago.me3 to play"
}
