param(
    [string]$Engine = 'C:\Modlists\POTI\.OpenMW\openmw.exe',
    [string]$GameData = 'D:\Steam\steamapps\common\Morrowind\Data Files',
    [string]$InventoryExtender = 'C:\Modlists\POTI\mods\Inventory Extender (OpenMW)',
    [string]$CraftingFramework = 'C:\Modlists\POTI\mods\(OpenMW) Crafting Framework',
    [switch]$VanillaInventory,
    [switch]$NoCrafting,
    [switch]$PrepareOnly,
    [switch]$SmokeTest
)
$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $PSScriptRoot
$name = if ($SmokeTest) { 'wayfarer-packs-smoke' } else { 'wayfarer-packs-manual' }
$profile = Join-Path $root ".runtime\$name-profile"
$userData = Join-Path $root ".runtime\$name-user-data"
$mod = Join-Path $root 'Wayfarer Packs'
$fixture = Join-Path $root 'tests\wayfarer_manual'
$resources = Join-Path (Split-Path -Parent $Engine) 'resources'
if (-not (Test-Path -LiteralPath $Engine -PathType Leaf)) { throw "Missing engine: $Engine" }
$version = (Get-Content -LiteralPath (Join-Path $resources 'version') -TotalCount 1).Trim()
if ($version -notmatch '^0\.52\.') { throw "Use the tested OpenMW 0.52 build, not $version. Override -Engine if needed." }
foreach ($file in @('Morrowind.esm','Tribunal.esm','Bloodmoon.esm','Morrowind.bsa','Tribunal.bsa','Bloodmoon.bsa')) {
    if (-not (Test-Path -LiteralPath (Join-Path $GameData $file) -PathType Leaf)) { throw "Missing game file: $file" }
}
foreach ($path in @((Join-Path $mod 'WayfarerPacks.esp'), (Join-Path $mod 'WayfarerPacks.omwscripts'),
    (Join-Path $fixture 'WayfarerPacksTest.omwscripts'), (Join-Path $fixture 'WayfarerPacksTestSmoke.omwscripts'))) {
    if (-not (Test-Path -LiteralPath $path -PathType Leaf)) { throw "Missing test content: $path" }
}
$ieData = ''
$ieContent = ''
$craftingData = ''
$craftingContent = ''
if (-not $NoCrafting) {
    if (-not (Test-Path -LiteralPath (Join-Path $CraftingFramework 'CraftingFramework.omwscripts') -PathType Leaf)) {
        throw 'Crafting Framework not found. Supply -CraftingFramework or use -NoCrafting.'
    }
    $craftingData = 'data="' + $CraftingFramework.Replace('\','/') + '"'
    $craftingContent = 'content=CraftingFramework.omwscripts'
}
if (-not $VanillaInventory) {
    if (-not (Test-Path -LiteralPath (Join-Path $InventoryExtender 'InventoryExtender.omwscripts') -PathType Leaf)) {
        throw 'Inventory Extender not found. Supply -InventoryExtender or use -VanillaInventory.'
    }
    $ieData = 'data="' + $InventoryExtender.Replace('\','/') + '"'
    $ieContent = 'content=InventoryExtender.omwscripts'
}
$localData = Join-Path $userData 'data'
New-Item -ItemType Directory -Force -Path $profile,$userData,$localData | Out-Null
$smokeContent = if ($SmokeTest) { 'content=WayfarerPacksTestSmoke.omwscripts' } else { '' }
$config = @"
replace=config
replace=data
replace=content
replace=groundcover
replace=fallback-archive
data="$($resources.Replace('\','/'))/vfs-mw"
data="$($GameData.Replace('\','/'))"
$ieData
$craftingData
data="$($mod.Replace('\','/'))"
data="$($fixture.Replace('\','/'))"
data-local="$($localData.Replace('\','/'))"
resources="$($resources.Replace('\','/'))"
content=Morrowind.esm
content=Tribunal.esm
content=Bloodmoon.esm
$ieContent
$craftingContent
content=WayfarerPacks.esp
content=WayfarerPacks.omwscripts
content=WayfarerPacksTest.omwscripts
$smokeContent
fallback-archive=Morrowind.bsa
fallback-archive=Tribunal.bsa
fallback-archive=Bloodmoon.bsa
"@
[IO.File]::WriteAllText((Join-Path $profile 'openmw.cfg'), $config)
$settingsPath = Join-Path $profile 'settings.cfg'
if ($SmokeTest -or -not (Test-Path -LiteralPath $settingsPath)) {
    $volume = if ($SmokeTest) { 'master volume = 0' } else { 'master volume = 1' }
    [IO.File]::WriteAllText($settingsPath, @"
[Video]
resolution x = 1280
resolution y = 720
fullscreen = false
vsync = false

[Sound]
music volume = 0
$volume
"@)
}
$arguments = @('--replace','config','--config',('"'+$profile+'"'),
    '--user-data',('"'+$userData+'"'),'--skip-menu','--new-game=0',
    '--start','"Seyda Neen, Arrille''s Tradehouse"','--no-grab')
Write-Host "OpenMW $version; isolated profile: $profile"
Write-Host "Test saves: $userData"
Write-Host 'Fresh character: Arrille''s Tradehouse, 5,000 gold, third-person view.'
if ($PrepareOnly) { return }
if ($SmokeTest) {
    $process = Start-Process -FilePath $Engine -ArgumentList $arguments -WorkingDirectory (Split-Path -Parent $Engine) -WindowStyle Hidden -PassThru
    if (-not $process.WaitForExit(120000)) {
        $process.Kill()
        $process.WaitForExit()
        throw "Test timed out. See $profile\openmw.log"
    }
    $log = Get-Content -LiteralPath (Join-Path $profile 'openmw.log') -Raw
    if ($process.ExitCode -ne 0 -or $log -notmatch 'WFP_MANUAL_PASS' -or $log -match 'WFP_MANUAL_FAIL| E\]') {
        throw "Manual fixture smoke test failed. See $profile\openmw.log"
    }
    if (-not $VanillaInventory -and $log -notmatch 'WFP_MANUAL_INVENTORY_EXTENDER') {
        throw "Inventory Extender interface missing. See $profile\openmw.log"
    }
    if (-not $NoCrafting -and ($log -notmatch 'WFP_MANUAL_CRAFTING_PASS' -or $log -notmatch 'WFP_MANUAL_BATCH_PASS' -or $log -notmatch 'WFP_MANUAL_STACK_PASS' -or $log -notmatch 'WFP_MANUAL_ARTISAN_PASS')) {
        throw "Crafting recipe check failed. See $profile\openmw.log"
    }
    Write-Host 'WFP_MANUAL_PASS: spawn, gold, clothing, merchant stock, and mod interface verified.'
} else {
    # The user launches this explicitly to interact with the test game.
    Start-Process -FilePath $Engine -ArgumentList $arguments -WorkingDirectory (Split-Path -Parent $Engine) -WindowStyle Normal
}
