$ErrorActionPreference = 'Stop'
$taskRoot = $PSScriptRoot
$taskPython = Join-Path $taskRoot 'work\venv\Scripts\python.exe'
if (-not (Test-Path -LiteralPath $taskPython)) {
    py -3.12 -m venv (Join-Path $taskRoot 'work\venv')
    if ($LASTEXITCODE -ne 0) { throw 'Python 3.12 is required.' }
    & $taskPython -m pip install -r (Join-Path $taskRoot 'app\requirements-ai.txt')
    if ($LASTEXITCODE -ne 0) { throw 'Dependency installation failed.' }
}
$env:PANTRY_DEV = '1'
$env:PANTRY_PORT = '8767'
& $taskPython (Join-Path $taskRoot 'app\server.py')
