$ErrorActionPreference = "Stop"

if (-not [string]::IsNullOrWhiteSpace($env:GITHUB_RUN_NUMBER) -and $env:GITHUB_RUN_NUMBER -match '^\d+$') {
    $buildPartA = 0
    $buildPartB = [int]$env:GITHUB_RUN_NUMBER
} else {
    $epochSeconds = [DateTimeOffset]::UtcNow.ToUnixTimeSeconds()
    $buildPartA = [int][Math]::Floor($epochSeconds / 65536)
    $buildPartB = [int]($epochSeconds % 65536)
}

if ($buildPartA -gt 65535 -or $buildPartB -gt 65535) {
    throw "Windowsの製品バージョンに使えるビルド番号の範囲を超えました。"
}

$appVersion = "1.0.$buildPartA.$buildPartB"
$onefileCache = "{CACHE_DIR}/kinoko34077/bmp2png-pdf/{VERSION}"
$env:NUITKA_CACHE_DIR = Join-Path $PSScriptRoot ".nuitka-cache"
New-Item -ItemType Directory -Force -Path $env:NUITKA_CACHE_DIR | Out-Null
$nuitkaArguments = @(
    "--mode=onefile",
    "--windows-console-mode=disable",
    "--enable-plugin=tk-inter",
    "--include-package=tkinterdnd2",
    "--include-package-data=tkinterdnd2",
    "--mingw64",
    "--assume-yes-for-downloads",
    "--company-name=kinoko34077",
    "--product-name=bmp2png-pdf",
    "--file-version=$appVersion",
    "--product-version=$appVersion",
    "--onefile-tempdir-spec=$onefileCache",
    "--output-dir=dist",
    "--output-filename=bmp2png_pdf.exe",
    "bmp_to_png_gui.py"
)

Push-Location $PSScriptRoot
try {
    & python -m nuitka @nuitkaArguments
    $buildExitCode = $LASTEXITCODE
} finally {
    Pop-Location
}

if ($buildExitCode -ne 0) {
    exit $buildExitCode
}
