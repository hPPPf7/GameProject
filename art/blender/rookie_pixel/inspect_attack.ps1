$ErrorActionPreference = 'Stop'
$rookieInspector = Join-Path $PSScriptRoot '..\..\..\inspect_sprites.ps1'
$rookieAttackSheet = Join-Path $PSScriptRoot 'rookie_sword_attack.png'
& $rookieInspector $rookieAttackSheet
