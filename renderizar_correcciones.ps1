$env:PUPPETEER_EXECUTABLE_PATH = "C:\Program Files\Google\Chrome\Application\chrome.exe"
$BASE = "C:\Videos_Josue\workshop-animaciones"
$SRC  = "$BASE\compositions\leccion_1\correcciones"
$OUT  = "$BASE\animaciones\leccion_1\correcciones"

if (!(Test-Path $OUT)) {
    New-Item -ItemType Directory -Path $OUT | Out-Null
}

$duraciones = @{
    "anim_l1_an2_v2"  =  8400
    "anim_l1_an3_v2"  = 28700
    "anim_l1_an4_v3"  = 28800
    "anim_l1_an7_v2"  =  8800
    "anim_l1_an8_v2"  = 38900
    "anim_l1_an12_v2" = 31500
    "anim_l1_an13_v2" =  8500
    "anim_l1_an15_v2" = 18500
    "anim_l1_an16_v2" = 14700
    "anim_l1_an17_v2" = 20200
    "anim_l1_an20_v2" =  8400
}

$ok = 0
$errores = @()

Write-Host "Renderizando correcciones leccion 1..."
Write-Host ""

foreach ($nombre in ($duraciones.Keys | Sort-Object)) {
    $html  = "$SRC\$nombre.html"
    $mp4   = "$OUT\$nombre.mp4"
    $durMs = $duraciones[$nombre]

    if (!(Test-Path $html)) {
        Write-Host "NO ENCONTRADO: $nombre"
        $errores += $nombre
        continue
    }

    Write-Host "Renderizando: $nombre ($durMs ms)"
    node "C:\Videos_Josue\capture_animation.js" $html $mp4 $durMs

    if ($LASTEXITCODE -eq 0) {
        Write-Host "OK: $nombre"
        $ok++
    } else {
        Write-Host "ERROR: $nombre"
        $errores += $nombre
    }
    Write-Host ""
}

Write-Host "Terminado: $ok de $($duraciones.Count) renderizados"

if ($errores.Count -gt 0) {
    Write-Host "Errores en:"
    $errores | ForEach-Object { Write-Host "  - $_" }
}
