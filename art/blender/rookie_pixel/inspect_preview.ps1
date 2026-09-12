$ErrorActionPreference = 'Stop'
$rookieInspector = Join-Path $PSScriptRoot '..\..\..\inspect_sprites.ps1'
$rookieSheet = Join-Path $PSScriptRoot 'rookie_walk_3d.png'
& $rookieInspector $rookieSheet
