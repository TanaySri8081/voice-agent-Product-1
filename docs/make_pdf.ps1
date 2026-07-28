$ErrorActionPreference = 'SilentlyContinue'
$cands = @(
  'C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe',
  'C:\Program Files\Microsoft\Edge\Application\msedge.exe',
  'C:\Program Files\Google\Chrome\Application\chrome.exe',
  'C:\Program Files (x86)\Google\Chrome\Application\chrome.exe'
)
$b = $cands | Where-Object { Test-Path $_ } | Select-Object -First 1
if (-not $b) { Write-Output 'NO_BROWSER'; exit 0 }
Write-Output ('BROWSER=' + $b)

$src = 'file:///C:/Users/acer/Desktop/AI-Calling-Agent/docs/Cost-Reduction-Plan.html'
$out = 'C:\Users\acer\Desktop\AI-Calling-Agent\docs\Cost-Reduction-Plan.pdf'
if (Test-Path $out) { Remove-Item $out -Force }

& $b '--headless=new' '--disable-gpu' '--no-pdf-header-footer' "--print-to-pdf=$out" '--run-all-compositor-stages-before-draw' '--virtual-time-budget=12000' $src 2>&1 | Out-Null
Start-Sleep -Seconds 3

if (-not (Test-Path $out)) {
  # retry with legacy headless flag
  & $b '--headless' '--disable-gpu' '--no-pdf-header-footer' "--print-to-pdf=$out" $src 2>&1 | Out-Null
  Start-Sleep -Seconds 3
}

if (Test-Path $out) { Write-Output ('OK_SIZE=' + (Get-Item $out).Length) } else { Write-Output 'PDF_NOT_CREATED' }
