# SPDX-License-Identifier: Apache-2.0
#
# Stop the workshop app and the workshop's own copy of Ollama (an Ollama the
# user installed separately is left alone).
# Dừng ứng dụng workshop và Ollama của workshop.
#
#     powershell -ExecutionPolicy Bypass -File windows\stop.ps1

$Log = Join-Path (Split-Path -Parent $PSScriptRoot) '.run\start-log.txt'
. (Join-Path $PSScriptRoot 'lib.ps1')

Stop-WorkshopApp
Show-Ok 'Workshop app stopped' 'Đã dừng ứng dụng workshop'

$pidFile = Join-Path $Run 'ollama.pid'
$ownExe = Join-Path $OllamaDir 'ollama.exe'
if (Test-Path -LiteralPath $pidFile) {
    $id = 0
    if ([int]::TryParse(([IO.File]::ReadAllText($pidFile)).Trim(), [ref]$id)) {
        $proc = Get-Process -Id $id -ErrorAction SilentlyContinue
        if ($proc -and $proc.Path -eq $ownExe) {
            # Its model runners are child processes: stop them too.
            Get-CimInstance Win32_Process -Filter "ParentProcessId=$id" -ErrorAction SilentlyContinue |
                ForEach-Object { Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue }
            Stop-Process -Id $id -Force -ErrorAction SilentlyContinue
            Show-Ok 'Ollama stopped' 'Đã dừng Ollama'
        }
    }
    Remove-Item -LiteralPath $pidFile -ErrorAction SilentlyContinue
}
