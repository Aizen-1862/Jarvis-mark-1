param(
  [Parameter(Mandatory = $true)]
  [ValidatePattern('^[a-p]{32}$')]
  [string]$ExtensionId
)

$ErrorActionPreference = 'Stop'
$hostName = 'com.jarvis.app_launcher'
$nativeHost = Join-Path $PSScriptRoot 'native_host.exe'
$hostSource = Join-Path $PSScriptRoot 'native_host.cs'
$manifestPath = Join-Path $PSScriptRoot 'com.jarvis.app_launcher.json'

if (-not (Test-Path -LiteralPath $nativeHost)) {
  $framework = Join-Path $env:WINDIR 'Microsoft.NET\Framework64\v4.0.30319'
  if (-not (Test-Path -LiteralPath (Join-Path $framework 'csc.exe'))) {
    $framework = Join-Path $env:WINDIR 'Microsoft.NET\Framework\v4.0.30319'
  }
  $compiler = Join-Path $framework 'csc.exe'
  $jsonLibrary = Join-Path $framework 'System.Web.Extensions.dll'
  if (-not (Test-Path -LiteralPath $compiler) -or -not (Test-Path -LiteralPath $hostSource)) {
    throw 'The JARVIS host source or Windows .NET Framework C# compiler is missing.'
  }
  & $compiler /nologo /target:exe "/out:$nativeHost" "/reference:$jsonLibrary" $hostSource
  if ($LASTEXITCODE -ne 0) { throw 'Compiling the JARVIS native host failed.' }
}

$manifest = [ordered]@{
  name = $hostName
  description = 'Launches Calculator, Notepad, File Explorer, Paint, or Spotify for JARVIS.'
  path = $nativeHost
  type = 'stdio'
  allowed_origins = @("chrome-extension://$ExtensionId/")
}
[System.IO.File]::WriteAllText($manifestPath, ($manifest | ConvertTo-Json -Depth 4), [System.Text.UTF8Encoding]::new($false))

$registryPath = "HKCU:\Software\Google\Chrome\NativeMessagingHosts\$hostName"
New-Item -Path $registryPath -Force | Out-Null
Set-Item -Path $registryPath -Value $manifestPath
Write-Host "Installed the JARVIS app launcher for Chrome extension $ExtensionId. Restart Chrome to apply it."
