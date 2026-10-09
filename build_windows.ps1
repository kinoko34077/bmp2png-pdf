$ErrorActionPreference = "Stop"

$repoRoot = (Resolve-Path $PSScriptRoot).Path
$distRoot = [System.IO.Path]::GetFullPath((Join-Path $repoRoot "dist"))
if (Test-Path -LiteralPath $distRoot) {
    $distInfo = Get-Item -LiteralPath $distRoot -Force
    if ($distInfo.Attributes -band [System.IO.FileAttributes]::ReparsePoint) {
        throw "Build dist folder cannot be a link: $distRoot"
    }
    $distRoot = (Resolve-Path -LiteralPath $distRoot).Path
}
$distPrefix = $distRoot.TrimEnd([System.IO.Path]::DirectorySeparatorChar) + [System.IO.Path]::DirectorySeparatorChar
$outputPaths = @(
    [System.IO.Path]::GetFullPath((Join-Path $distRoot "bmp2png_pdf-windows-x64")),
    [System.IO.Path]::GetFullPath((Join-Path $distRoot "bmp2png_pdf")),
    [System.IO.Path]::GetFullPath((Join-Path $distRoot "bmp2png_pdf.exe"))
)

foreach ($outputPath in $outputPaths) {
    if (-not $outputPath.StartsWith($distPrefix, [System.StringComparison]::OrdinalIgnoreCase)) {
        throw "Build output path escaped the repository dist folder: $outputPath"
    }
    if (Test-Path -LiteralPath $outputPath) {
        $outputInfo = Get-Item -LiteralPath $outputPath -Force
        if ($outputInfo.Attributes -band [System.IO.FileAttributes]::ReparsePoint) {
            throw "Build output cannot be a link: $outputPath"
        }
        $resolvedOutputPath = (Resolve-Path -LiteralPath $outputPath).Path
        if (-not $resolvedOutputPath.StartsWith($distPrefix, [System.StringComparison]::OrdinalIgnoreCase)) {
            throw "Build output resolves outside the repository dist folder: $resolvedOutputPath"
        }
        Remove-Item -LiteralPath $outputPath -Recurse -Force
    }
}

Push-Location $repoRoot
try {
    & python -m PyInstaller --noconfirm bmp2png_pdf.spec
    $buildExitCode = $LASTEXITCODE
} finally {
    Pop-Location
}

if ($buildExitCode -ne 0) {
    exit $buildExitCode
}
