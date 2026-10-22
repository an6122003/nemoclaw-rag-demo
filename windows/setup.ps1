# SPDX-License-Identifier: Apache-2.0
#
# ============================================================================
#  RTX SPARK AI WORKSHOP - one-command setup for Windows
#  WORKSHOP AI TRÊN RTX SPARK - cài đặt bằng một lệnh trên Windows
# ============================================================================
#
#  The install command runs it (PowerShell):    Lệnh cài đặt sẽ chạy tệp này:
#
#      irm https://raw.githubusercontent.com/an6122003/nemoclaw-rag-demo/main/install.ps1 | iex
#
#  or again, from the workshop folder:          hoặc chạy lại trong thư mục workshop:
#
#      powershell -ExecutionPolicy Bypass -File windows\setup.ps1
#
#  It installs and checks everything for the hands-on labs, then opens the
#  workshop in the browser. Safe to run again: finished steps are skipped.
#  No administrator rights needed.
#  Chương trình cài và kiểm tra mọi thứ cho các bài thực hành rồi mở workshop
#  trên trình duyệt. Chạy lại an toàn. Không cần quyền quản trị.
#
#  Options / Tuỳ chọn:
#    -Yes        do not pause for the third-party software notice
#    -CheckOnly  inspect this computer, change nothing
#    -NoStart    do not open the workshop app at the end
#    -Test       small CPU models for GitHub's test machines: checks the wiring, not the answers
#
#  Everything is logged to setup-log.txt. / Mọi chi tiết được ghi vào setup-log.txt.
# ============================================================================

param([switch]$Yes, [switch]$CheckOnly, [switch]$NoStart, [switch]$Test)

$RootDir = Split-Path -Parent $PSScriptRoot
$LocalEnv = Join-Path $RootDir 'workshop.local.env'
$TestMark = '# Written by windows\setup.ps1 -Test'
if ($Test) {
    # Tiny models that run on a 4-core CPU without a GPU (the GitHub test machines).
    $lines = @(
        ($TestMark + ": small models for GitHub's CPU-only test machines."),
        'CHAT_MODEL=qwen2.5:1.5b-instruct',
        'EMBED_MODEL=qwen3-embedding:0.6b',
        'WIN_CHAT_CONTEXT=8192',
        'OLLAMA_CONTEXT_LENGTH=8192'
    )
    [IO.File]::WriteAllLines($LocalEnv, $lines)
} elseif ((Test-Path -LiteralPath $LocalEnv) -and
          ([IO.File]::ReadAllLines($LocalEnv) | Select-Object -First 1) -like "$TestMark*") {
    Remove-Item -LiteralPath $LocalEnv   # a test run's settings must not stay on a real machine
}
$Log = Join-Path $RootDir 'setup-log.txt'
[IO.File]::WriteAllText($Log, '')
. (Join-Path $PSScriptRoot 'lib.ps1')

$Arch = [string][Runtime.InteropServices.RuntimeInformation]::OSArchitecture
Write-Log "setup started: $([Environment]::OSVersion.VersionString) $Arch, PowerShell $($PSVersionTable.PSVersion), folder $Root"
if ($Test) { Write-Log 'test mode: small CPU models (workshop.local.env)' }

$CoreOk = $true
$Lab1 = 'missing'; $Lab2 = 'unchecked'; $Lab3 = 'unchecked'
$Lab1Note = ''; $Lab2Note = ''; $Lab3Note = ''

if ($Interactive) { try { Clear-Host } catch {} }
Write-Host @'

   ┌──────────────────────────────────────────────────────────────┐
   │                                                              │
   │     R T X   S P A R K   A I   W O R K S H O P                │
   │     Workshop AI chạy hoàn toàn trên máy RTX Spark            │
   │                                                              │
   │     1  Fine-tuning Local LLMs   · Tinh chỉnh mô hình         │
   │     2  Build RAG                · Hỏi đáp trên tài liệu      │
   │     3  Build an Agentic Workflow· Agent phân tích dữ liệu    │
   │                                                              │
   └──────────────────────────────────────────────────────────────┘

'@

if ($Interactive -and -not $Yes -and -not $CheckOnly) {
    Write-Host @'
   This will download and install third-party software, each under its own
   license: Ollama, uv, Python and Python packages, and open AI models (NVIDIA
   Nemotron, Qwen). About 31 GB is downloaded. Leave this window open.

   Chương trình sẽ tải và cài phần mềm của bên thứ ba, mỗi phần mềm theo giấy
   phép riêng: Ollama, uv, Python và các gói Python, cùng các mô hình AI mở
   (NVIDIA Nemotron, Qwen). Tải khoảng 31 GB. Hãy để cửa sổ này mở.

'@
    Write-Host '   Press Enter to continue, or Ctrl-C to cancel.'
    $null = Read-Host '   Nhấn Enter để tiếp tục, hoặc Ctrl-C để huỷ'
}
Write-Host "`n   Full details / Chi tiết đầy đủ: $Log"

function Test-Url([string]$Url) {
    try {
        $null = Invoke-WebRequest -Uri $Url -Method Head -UseBasicParsing -TimeoutSec 15
        return $true
    } catch {
        return [bool]$_.Exception.Response   # an HTTP error still means the site is reachable
    }
}

# ================================================================ computer ===
Show-Step 'Checking this computer' 'Kiểm tra máy tính'

$os = [Environment]::OSVersion.Version
if ($os.Build -ge 22000) {
    Show-Ok "Windows 11 (build $($os.Build))"
} else {
    Show-Warn "Windows build $($os.Build): this edition is made for Windows 11" 'Bản này dành cho Windows 11'
}
if ($Arch -eq 'Arm64') {
    Show-Ok 'Processor: Arm64 (Windows on Arm)'
} elseif ($Arch -eq 'X64') {
    Show-Warn 'Processor: x64. This edition is made for the RTX Spark (Windows on Arm); it also works with an NVIDIA graphics card' `
              'Bản này dành cho RTX Spark (Windows on Arm); máy x64 có card NVIDIA vẫn dùng được'
} else {
    Show-Bad "Processor: $Arch is not supported" 'Bộ xử lý này không được hỗ trợ'
    exit 1
}

$GpuName = ''
$smi = Get-Command 'nvidia-smi.exe' -ErrorAction SilentlyContinue
if ($smi) {
    $q = & $smi.Source --query-gpu=name,driver_version --format=csv,noheader 2>$null | Select-Object -First 1
    if ($q) {
        $parts = ([string]$q).Split(',')
        $GpuName = $parts[0].Trim()
        Show-Ok "Graphics: $GpuName (driver $($parts[1].Trim()))"
    }
}
if (-not $GpuName) {
    Show-Warn 'No NVIDIA graphics driver found: the AI models will run on the processor, slowly' `
              'Không tìm thấy driver đồ hoạ NVIDIA: mô hình AI sẽ chạy trên CPU, rất chậm'
}

$MemGB = [math]::Round((Get-CimInstance Win32_ComputerSystem).TotalPhysicalMemory / 1GB)
if ($Test -or $MemGB -ge 48) { Show-Ok "$MemGB GB memory" }
else { Show-Warn "$MemGB GB memory: the chat model needs about 32 GB of it" "Máy có $MemGB GB bộ nhớ; mô hình chat cần khoảng 32 GB" }

$FreeGB = [math]::Round((Get-Item -LiteralPath $Root).PSDrive.Free / 1GB)
$NeedGB = if ($Test) { 8 } else { 40 }
if ($FreeGB -ge $NeedGB) { Show-Ok "$FreeGB GB free disk" }
else {
    Show-Bad "Only $FreeGB GB free on this drive; about $NeedGB GB is needed" "Chỉ còn $FreeGB GB trống; cần khoảng $NeedGB GB"
    if (-not $CheckOnly) { exit 1 }
}

$Online = (Test-Url 'https://registry.ollama.ai/v2/') -and (Test-Url 'https://github.com')
if ($Online) { Show-Ok 'Internet connection works' 'Kết nối internet hoạt động' }
else { Show-Warn 'No internet connection: only what is already installed can be used' 'Không có internet: chỉ dùng được những gì đã cài' }

if ($CheckOnly) {
    Write-Host "`n   -CheckOnly: nothing was changed. / Không thay đổi gì.`n"
    exit 0
}

# ================================================================== python ===
Show-Step 'Preparing the Python environment' 'Chuẩn bị môi trường Python'

$uv = Get-Uv
if (-not $uv -and $Online) {
    $null = Invoke-Logged 'Installing uv (Python installer)' 'powershell.exe' @(
        '-NoProfile', '-ExecutionPolicy', 'Bypass', '-Command', 'irm https://astral.sh/uv/install.ps1 | iex')
    $uv = Get-Uv
}
if (-not $uv) {
    Show-Bad 'Could not install uv, the tool that installs Python' 'Không cài được uv (công cụ cài Python)'
    Show-LogTail
    exit 1
}
Show-Ok "uv: $(& $uv --version 2>$null)"

$needVenv = -not (Test-Path -LiteralPath $VenvPy)
if (-not $needVenv) {
    $have = & $VenvPy -c "import sys; print('%d.%d' % sys.version_info[:2])" 2>$null
    if ("$have".Trim() -ne $PythonVersion) { $needVenv = $true }
}
if ($needVenv) {
    $venvArgs = @('venv', '--python', $PythonVersion)
    if (Test-Path -LiteralPath (Join-Path $Root '.venv')) { $venvArgs += '--clear' }
    $venvArgs += (Join-Path $Root '.venv')
    $null = Invoke-Logged "Installing Python $PythonVersion" $uv $venvArgs
}
$code = Invoke-Logged 'Installing pandas, matplotlib and openpyxl' $uv @(
    'pip', 'install', '--python', $VenvPy, '-r', (Join-Path $Root 'hands-on-3-agent\requirements.txt'))
$probe = & $VenvPy -c "import platform, sys, pandas, matplotlib, openpyxl; print(sys.version.split()[0], platform.machine())" 2>$null
if ($code -eq 0 -and $probe) {
    Show-Ok "Python environment ready: Python $probe" 'Môi trường Python đã sẵn sàng'
} else {
    Show-Bad 'The Python environment is incomplete' 'Môi trường Python chưa đầy đủ'
    Show-LogTail
    exit 1
}

# ================================================================== ollama ===
Show-Step 'Preparing the AI model server (Ollama)' 'Chuẩn bị máy chủ mô hình AI (Ollama)'

$ArchTag = if ($Arch -eq 'Arm64') { 'arm64' } else { 'amd64' }
$ownExe = Join-Path $OllamaDir 'ollama.exe'
$verFile = Join-Path $OllamaDir 'VERSION'
$ownVer = if (Test-Path -LiteralPath $verFile) { ([IO.File]::ReadAllText($verFile)).Trim() } else { '' }

# Is the Ollama that answers our own copy? (Then a new pinned version can replace it.)
$ownRunning = $false
$pidFile = Join-Path $Run 'ollama.pid'
if (Test-Path -LiteralPath $pidFile) {
    $opid = 0
    if ([int]::TryParse(([IO.File]::ReadAllText($pidFile)).Trim(), [ref]$opid)) {
        $proc = Get-Process -Id $opid -ErrorAction SilentlyContinue
        $ownRunning = [bool]($proc -and $proc.Path -and ($proc.Path -eq $ownExe))
    }
}

$needOwn = -not (Test-OllamaUp) -or $ownRunning
if ($needOwn -and ((-not (Test-Path -LiteralPath $ownExe)) -or $ownVer -ne $OllamaVersion)) {
    if (-not $Online) {
        Show-Bad 'Ollama is not installed and there is no internet' 'Chưa có Ollama và không có internet'
        exit 1
    }
    $zip = Join-Path $Run "ollama-windows-$ArchTag.zip"
    $url = "https://github.com/ollama/ollama/releases/download/$OllamaVersion/ollama-windows-$ArchTag.zip"
    Show-Info "Downloading Ollama $OllamaVersion ($ArchTag)..." "Đang tải Ollama $OllamaVersion..."
    if (-not (Get-Download $url $zip)) {
        Show-Bad "Could not download Ollama from $url" 'Không tải được Ollama'
        exit 1
    }
    if ($ownRunning) { Stop-Process -Id $opid -Force -ErrorAction SilentlyContinue; Start-Sleep -Seconds 2 }
    Remove-Item -LiteralPath $OllamaDir -Recurse -Force -ErrorAction SilentlyContinue
    if (-not (Expand-Zip $zip $OllamaDir)) {
        Show-Bad 'Could not unpack Ollama' 'Không giải nén được Ollama'
        exit 1
    }
    [IO.File]::WriteAllText($verFile, $OllamaVersion)
    Remove-Item -LiteralPath $zip -ErrorAction SilentlyContinue
    Show-Ok "Ollama $OllamaVersion installed in the workshop folder" 'Đã cài Ollama trong thư mục workshop'
}
if (-not (Test-OllamaUp)) {
    if (-not (Start-WorkshopOllama)) {
        Show-Bad 'Ollama does not start' 'Ollama không khởi động được'
        if (Test-Path -LiteralPath (Join-Path $Run 'ollama.log')) {
            Get-Content -LiteralPath (Join-Path $Run 'ollama.log') -Tail 15 | ForEach-Object { Write-Log "ollama: $_" }
        }
        Show-LogTail
        exit 1
    }
    Start-Sleep -Seconds 3   # it logs the GPU it found just after starting
}
$ver = Get-OllamaRunningVersion
if (Test-VersionAtLeast $ver $MinOllama) { Show-Ok "Ollama $ver is running" 'Ollama đang chạy' }
else { Show-Warn "Ollama $ver is older than $MinOllama: tool calls may not work" "Ollama $ver quá cũ" }

$compute = Get-OllamaCompute
if ($compute -eq 'cuda') {
    Show-Ok 'Ollama runs the models on the NVIDIA GPU (CUDA)' 'Ollama chạy mô hình trên GPU NVIDIA'
} elseif ($GpuName -and $compute) {
    Show-Warn "Ollama found no usable GPU ($compute): models run on the processor" `
              'Ollama không dùng được GPU: mô hình chạy trên CPU'
} elseif ($compute) {
    Write-Log "ollama compute: $compute"
}

# ================================================================== models ===
Show-Step 'Downloading the AI models' 'Tải các mô hình AI'

$models = @($ChatModel, $EmbedModel, $Lab1Base) | Select-Object -Unique
foreach ($m in $models) {
    if (Test-OllamaHas $m) { Show-Ok "$m ready" "$m đã có"; continue }
    if (-not $Online) { Show-Bad "$m is missing and there is no internet" "Thiếu $m và không có internet"; $CoreOk = $false; continue }
    Write-Log "pull $m"
    $ok = $false
    for ($attempt = 1; $attempt -le 3 -and -not $ok; $attempt++) {
        if ($attempt -gt 1) { Show-Info "Trying again ($attempt/3)..." "Thử lại ($attempt/3)..." }
        Show-Info "Downloading $m..." "Đang tải $m..."
        & $VenvPy (Join-Path $Root 'scripts\pull-model.py') $m
        $ok = ($LASTEXITCODE -eq 0) -and (Test-OllamaHas $m)
    }
    if ($ok) { Show-Ok "$m downloaded" "Đã tải $m" }
    else { Show-Bad "Could not download $m" "Không tải được $m"; $CoreOk = $false }
}
if (Test-OllamaHas $ChatModel) {
    # Hands-on 3 sends the tool list and the data preview with every step: give the chat model room.
    $out = & $VenvPy (Join-Path $Root 'scripts\ollama-context.py') $ChatModel $WinChatContext 2>&1
    $out | ForEach-Object { Write-Log "context: $_" }
    if ($LASTEXITCODE -eq 0) { Show-Ok "Chat model context: $WinChatContext tokens" }
    else { Show-Warn 'Could not set the chat model context' 'Không đặt được ngữ cảnh cho mô hình chat' }
}

# ================================================================== lab 1 ===
Show-Step 'Hands-on 1: the fine-tuned Aurora model' 'Bài 1: mô hình Aurora đã tinh chỉnh'

$OllamaExe = Get-OllamaExe
if (Test-OllamaHas $Lab1Tuned) {
    Show-Ok "$Lab1Tuned is in Ollama" "$Lab1Tuned đã có trong Ollama"
    $Lab1 = 'compare-only'
} elseif ($AuroraUrl -and $Online -and $OllamaExe) {
    $dir = Join-Path $Run 'aurora'
    New-Item -ItemType Directory -Force -Path $dir | Out-Null
    $gguf = Join-Path $dir 'aurora-assistant-q8_0.gguf'
    if (-not (Test-Path -LiteralPath $gguf)) {
        Show-Info 'Downloading the ready-trained Aurora model (about 1.6 GB)...' 'Đang tải mô hình Aurora đã huấn luyện sẵn...'
        $null = Get-Download $AuroraUrl $gguf
    }
    $good = Test-Path -LiteralPath $gguf
    if ($good -and $AuroraSha) {
        $good = (Get-FileHash -LiteralPath $gguf -Algorithm SHA256).Hash -eq $AuroraSha.ToUpper()
        if (-not $good) { Remove-Item -LiteralPath $gguf -ErrorAction SilentlyContinue; Write-Log 'aurora: checksum mismatch' }
    }
    if ($good) {
        Copy-Item -LiteralPath (Join-Path $PSScriptRoot 'aurora.Modelfile') -Destination (Join-Path $dir 'Modelfile') -Force
        $code = Invoke-Logged "Adding $Lab1Tuned to Ollama" $OllamaExe @('create', $Lab1Tuned, '-f', (Join-Path $dir 'Modelfile')) $dir
        if ($code -eq 0 -and (Test-OllamaHas $Lab1Tuned)) {
            Show-Ok "$Lab1Tuned added to Ollama" "Đã thêm $Lab1Tuned vào Ollama"
            $Lab1 = 'compare-only'
        } else { Show-Bad "Could not add $Lab1Tuned to Ollama" 'Không thêm được mô hình Aurora'; $Lab1 = 'failed' }
    } else { Show-Bad 'Could not download the Aurora model' 'Không tải được mô hình Aurora'; $Lab1 = 'failed' }
} else {
    Show-Warn 'The ready-trained Aurora model is not published yet: Hands-on 1 shows the original model only' `
              'Mô hình Aurora huấn luyện sẵn chưa được phát hành: Bài 1 chỉ có mô hình gốc'
    $Lab1Note = 'Aurora model not published yet'
}
if ($Lab1 -eq 'compare-only') { $Lab1Note = 'training on Windows comes later' }

# ================================================================== lab 2 ===
Show-Step 'Hands-on 2: the document index' 'Bài 2: chỉ mục tài liệu'

$env:WORKSHOP_APP = Join-Path $Root 'app'
$indexCheck = "import os, sys; sys.path.insert(0, os.environ['WORKSHOP_APP']); import lab2_rag; d = lab2_rag.load_index(); print(d['chunk_count'] if d else 0)"
$chunks = [int]("0" + (& $VenvPy -c $indexCheck 2>$null))
if ($chunks -gt 0) {
    Show-Ok "Document index ready: $chunks passages, $EmbedModel" 'Chỉ mục tài liệu đã sẵn sàng'
} else {
    $code = Invoke-Logged 'Building the document index' $VenvPy @(
        (Join-Path $Root 'hands-on-2-rag\ingestion\build_index.py'),
        '--corpus', (Join-Path $Root 'hands-on-2-rag\corpus'), '--out', (Join-Path $Run 'rag-index'),
        '--base-url', $OllamaUrl, '--model', $EmbedModel, '--target-chars', '1600', '--overlap-chars', '320')
    $chunks = [int]("0" + (& $VenvPy -c $indexCheck 2>$null))
    if ($code -eq 0 -and $chunks -gt 0) { Show-Ok "Document index built: $chunks passages, $EmbedModel" 'Đã tạo chỉ mục tài liệu' }
    else { Show-Bad 'Could not build the document index' 'Không tạo được chỉ mục tài liệu'; $CoreOk = $false }
}

# ============================================================ final check ===
Show-Step 'Final check - every lab, end to end' 'Kiểm tra cuối - chạy thử từng bài'

$stArgs = @((Join-Path $Root 'app\selftest.py'), '--lab2', '--lab3', '--tools', '--json')
if ($Lab1 -eq 'compare-only') { $stArgs += '--lab1' }
if ($Test) { $stArgs += '--plumbing' }
$null = Invoke-Logged 'Running every lab once' $VenvPy $stArgs
$stOut = Join-Path $Run 'step-out.txt'
$results = @()
if (Test-Path -LiteralPath $stOut) {
    $raw = [IO.File]::ReadAllText($stOut, [Text.Encoding]::UTF8)
    [IO.File]::WriteAllText((Join-Path $Run 'selftest.json'), $raw, (New-Object System.Text.UTF8Encoding $false))
    # ConvertFrom-Json as a parameter, not in a pipeline: Windows PowerShell 5.1
    # passes a JSON array down a pipeline as one object.
    try { $results = ConvertFrom-Json $raw } catch { $results = @() }
}
foreach ($r in $results) {
    $detail = [string]$r.detail
    switch ([string]$r.lab) {
        '1' {
            if ($r.ok) { Show-Ok "Hands-on 1: $detail" 'Bài 1 hoạt động' }
            elseif ($r.skipped) { Show-Warn "Hands-on 1: $detail" }
            else { Show-Bad "Hands-on 1: $detail"; $Lab1 = 'failed' }
        }
        '2' {
            if ($r.ok) { Show-Ok "Hands-on 2: $detail" 'Bài 2 hoạt động'; $Lab2 = 'ready' }
            else { Show-Bad "Hands-on 2: $detail"; $Lab2 = 'failed' }
        }
        '3' {
            if ($r.ok) { Show-Ok "Hands-on 3: $detail" 'Bài 3 hoạt động'; if ($Lab3 -ne 'failed') { $Lab3 = 'ready' } }
            else { Show-Bad "Hands-on 3: $detail"; $Lab3 = 'failed' }
        }
        'tools' {
            if ($r.ok) { Show-Ok "Hands-on 3 tools: $detail" 'Công cụ Python của Bài 3 hoạt động' }
            else { Show-Bad "Hands-on 3 tools: $detail"; $Lab3 = 'failed' }
        }
    }
}
if (-not $results) {
    Show-Bad 'The final check did not run' 'Bước kiểm tra cuối không chạy được'
    Show-LogTail
    $Lab2 = 'failed'; $Lab3 = 'failed'
}

# Desktop and Start-menu shortcuts, so the next start is a double-click.
$IconFile = Join-Path $Run 'workshop.ico'
& $VenvPy (Join-Path $PSScriptRoot 'make_icon.py') $IconFile 2>$null
function New-WorkshopShortcut([string]$Path) {
    try {
        $shell = New-Object -ComObject WScript.Shell
        $lnk = $shell.CreateShortcut($Path)
        $lnk.TargetPath = Join-Path $env:SystemRoot 'System32\WindowsPowerShell\v1.0\powershell.exe'
        $lnk.Arguments = '-NoProfile -ExecutionPolicy Bypass -File "' + (Join-Path $Root 'windows\start.ps1') + '"'
        $lnk.WorkingDirectory = $Root
        if (Test-Path -LiteralPath $IconFile) { $lnk.IconLocation = $IconFile }
        $lnk.Description = 'Start the AI workshop / Mở workshop AI'
        $lnk.Save()
        return $true
    } catch {
        Write-Log "shortcut ${Path}: $($_.Exception.Message)"
        return $false
    }
}
$ShortcutName = 'RTX Spark Workshop.lnk'
foreach ($folder in [Environment]::GetFolderPath('Desktop'), [Environment]::GetFolderPath('Programs')) {
    if ($folder -and (Test-Path -LiteralPath $folder)) { $null = New-WorkshopShortcut (Join-Path $folder $ShortcutName) }
}

# ================================================================ summary ===
function Show-Status([string]$Name, [string]$State, [string]$Note) {
    switch ($State) {
        'ready'        { $text = ([string][char]0x2714) + ' ready / sẵn sàng'; $color = 'Green' }
        'compare-only' { $text = '! comparison only / chỉ phần so sánh'; $color = 'Yellow' }
        'later'        { $text = '- in a later update / có trong bản cập nhật sau'; $color = 'DarkGray' }
        'missing'      { $text = '- not installed / chưa cài'; $color = 'DarkGray' }
        default        { $text = ([string][char]0x2718) + ' needs help / cần hỗ trợ'; $color = 'Red' }
    }
    Write-Host ('   {0,-32}' -f $Name) -NoNewline
    Write-Host $text -ForegroundColor $color -NoNewline
    if ($Note) { Write-Host "  $Note" -ForegroundColor DarkGray } else { Write-Host '' }
}
if (-not $CoreOk) {
    if ($Lab2 -eq 'unchecked') { $Lab2 = 'failed' }
    if ($Lab3 -eq 'unchecked') { $Lab3 = 'failed' }
}
Write-Host ''
Write-Host ([string][char]0x2500 * 66) -ForegroundColor DarkGray
Write-Host ''
Show-Status 'Hands-on 1  Fine-tuning' $Lab1 $Lab1Note
Show-Status 'Hands-on 2  RAG' $Lab2 $Lab2Note
Show-Status 'Hands-on 3  Agentic workflow' $Lab3 $Lab3Note
Show-Status 'Enterprise  Batch demos' 'later' ''
Write-Log "summary: lab1=$Lab1 lab2=$Lab2 lab3=$Lab3 enterprise=later"

$failed = ($Lab1 -eq 'failed') -or ($Lab2 -ne 'ready') -or ($Lab3 -ne 'ready')
if (-not $failed) {
    Write-Host @'

   ┌──────────────────────────────────────────────────────────────┐
   │   ✔  S E T U P   C O M P L E T E                             │
   │      C À I   Đ Ặ T   H O À N   T Ấ T                          │
   └──────────────────────────────────────────────────────────────┘

   Next time, double-click "RTX Spark Workshop" on the desktop.
   Lần sau, bấm đúp "RTX Spark Workshop" trên màn hình nền.
'@ -ForegroundColor Green
} else {
    Write-Host @"

   ┌──────────────────────────────────────────────────────────────┐
   │   !  SETUP FINISHED - SOME PARTS NEED HELP                   │
   │      ĐÃ CÀI XONG - MỘT SỐ PHẦN CẦN HỖ TRỢ                     │
   └──────────────────────────────────────────────────────────────┘

   The parts marked above need attention. Send this file to the organiser:
   Các phần được đánh dấu cần hỗ trợ. Hãy gửi tệp này cho người phụ trách:

       $Log

   Running the install command again is safe:
   Chạy lại lệnh cài đặt hoàn toàn an toàn:

       $InstallCmd
"@ -ForegroundColor Yellow
}

if (-not $NoStart) {
    if (Test-HubUp) {
        Show-Info 'Restarting the workshop app with the new version...' 'Đang khởi động lại ứng dụng workshop với phiên bản mới...'
        Stop-WorkshopApp
    }
    Write-Host "`n   Opening the workshop... / Đang mở workshop...`n"
    & (Join-Path $PSScriptRoot 'start.ps1')
    exit $LASTEXITCODE
}
if ($failed) { exit 1 }
exit 0
