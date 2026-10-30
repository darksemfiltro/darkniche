# Instala a skill analise-mercado-yt (Windows / PowerShell 5.1+)
#
#   powershell -ExecutionPolicy Bypass -File .\install.ps1                         # Claude Code
#   powershell -ExecutionPolicy Bypass -File .\install.ps1 -Agent codex            # claude, codex, opencode, antigravity ou all
#   powershell -ExecutionPolicy Bypass -File .\install.ps1 -Agent claude,codex     # mais de um
#   powershell -ExecutionPolicy Bypass -File .\install.ps1 -Dest "D:\minhas-skills" # outra pasta (soma ao -Agent, se houver)
#   -NonInteractive: não pergunta a chave (usa a variável YT_API_KEY, se existir). -SkipDeps: não roda o pip.
#   -ReplaceKey: pede a chave de novo e troca a que está gravada (use depois de revogar uma chave).
#
# Pasta de cada agente (conferidas em 30/10/2026; fontes em analise-mercado-yt\references\hosts.md):
#   claude       %USERPROFILE%\.claude\skills
#   codex        %USERPROFILE%\.agents\skills
#   opencode     %USERPROFILE%\.config\opencode\skills
#   antigravity  %USERPROFILE%\.gemini\config\skills (app e IDE) e %USERPROFILE%\.gemini\antigravity-cli\skills (CLI agy)
#
# O que faz, nesta ordem:
#   1. confere o Python (3.10+) antes de mexer em qualquer arquivo;
#   2. copia a skill para cada pasta escolhida. Se já houver uma, move a anterior para
#      <dados>\backups\analise-mercado-yt-AAAAMMDD-HHMMSS-N (fora das pastas de skills, para o agente não carregar duas);
#   3. grava a chave da YouTube Data API em %USERPROFILE%\.analise-mercado-yt\.env (só se ainda não existir, ou com
#      -ReplaceKey), pedindo sem mostrar o que você digita. A chave NÃO é aceita como argumento: argumento fica no
#      histórico do terminal;
#   4. instala yt-dlp e Pillow com pip (requirements.txt) e roda a checagem (doctor.py).
# Nada é enviado para a rede além do pip e da checagem da chave (1 unidade de cota).
param([string[]]$Agent, [string[]]$Dest, [switch]$NonInteractive, [switch]$SkipDeps, [switch]$ReplaceKey)
$ErrorActionPreference = 'Stop'

function Find-Python {
  foreach ($c in @('python', 'py')) {
    $cmd = Get-Command $c -ErrorAction SilentlyContinue
    if (-not $cmd) { continue }
    try {
      $v = (& $c -c "import sys; print('%d.%d' % sys.version_info[:2])" 2>$null)
      if ($LASTEXITCODE -eq 0 -and $v -match '^3\.(\d+)$' -and [int]$Matches[1] -ge 10) { return $c }
    } catch { }
  }
  return $null
}

$py = Find-Python
if (-not $py) {
  Write-Warning 'Python 3.10 ou mais novo não encontrado (o "python" da Microsoft Store sem instalação não conta). Instale em python.org ou com: winget install Python.Python.3.12'
  exit 1
}

$src = Join-Path $PSScriptRoot 'analise-mercado-yt'
if (-not (Test-Path (Join-Path $src 'SKILL.md'))) { throw "Não achei a pasta analise-mercado-yt ao lado deste script." }

# pastas de skills por agente
$userHome = $env:USERPROFILE
$known = [ordered]@{
  claude      = @((Join-Path $userHome '.claude\skills'))
  codex       = @((Join-Path $userHome '.agents\skills'))
  opencode    = @((Join-Path $userHome '.config\opencode\skills'))
  antigravity = @((Join-Path $userHome '.gemini\config\skills'), (Join-Path $userHome '.gemini\antigravity-cli\skills'))
}
$names = @()
foreach ($a in @($Agent)) { foreach ($n in ([string]$a -split ',')) { if ($n.Trim()) { $names += $n.Trim().ToLower() } } }
if ($names -contains 'all') { $names = @($known.Keys) }
foreach ($n in $names) {
  if (-not $known.Contains($n)) { throw "Agente desconhecido: '$n'. Use: $($known.Keys -join ', '), all, ou -Dest <pasta>." }
}
if (-not $names -and -not $Dest) { $names = @('claude') }
$targets = @()
foreach ($n in $names) { $targets += $known[$n] }
foreach ($d in @($Dest)) { if ($d) { $targets += $d } }
$targets = @($targets | Select-Object -Unique)

$data = if ($env:AMY_HOME) { $env:AMY_HOME } else { Join-Path $userHome '.analise-mercado-yt' }
$stamp = Get-Date -Format 'yyyyMMdd-HHmmss'
$installed = @(); $n = 0
foreach ($t in $targets) {
  $dst = Join-Path $t 'analise-mercado-yt'
  New-Item -ItemType Directory -Force $t | Out-Null
  if (Test-Path -LiteralPath $dst) {
    $n++
    $bak = Join-Path $data "backups\analise-mercado-yt-$stamp-$n"
    New-Item -ItemType Directory -Force (Split-Path $bak) | Out-Null
    try { Move-Item -LiteralPath $dst -Destination $bak }
    catch { Copy-Item -Recurse -Force -LiteralPath $dst -Destination $bak; Remove-Item -Recurse -Force -LiteralPath $dst }
    Write-Host "Versão anterior de $t guardada em $bak (fora das pastas de skills, para o agente não carregar duas; apague quando quiser)."
  }
  Copy-Item -Recurse -Force $src $dst
  Get-ChildItem -Path $dst -Recurse -Directory -Filter '__pycache__' | Remove-Item -Recurse -Force
  Write-Host "Skill copiada para $dst"
  $installed += $dst
}

New-Item -ItemType Directory -Force $data | Out-Null
$envFile = Join-Path $data '.env'
$aliasNoAmbiente = @('YT_API_KEY', 'YOUTUBE_API_KEY', 'YOUTUBE_DATA_API_KEY', 'YOUTUBE_DATA_API_V3_KEY') | Where-Object { [Environment]::GetEnvironmentVariable($_) } | Select-Object -First 1
$temArquivo = Test-Path $envFile
if ($temArquivo -and -not $ReplaceKey) {
  Write-Host "Mantive o $envFile que já existia (para trocar a chave: -ReplaceKey)."
} elseif (-not $temArquivo -and -not $ReplaceKey -and $aliasNoAmbiente -and $aliasNoAmbiente -ne 'YT_API_KEY') {
  Write-Host "Encontrei a chave na variável de ambiente $aliasNoAmbiente; não gravei arquivo (a skill lê a variável)."
} else {
  $ApiKey = $env:YT_API_KEY
  if (-not $ApiKey -and -not $NonInteractive) {
    $sec = Read-Host 'Cole sua YT_API_KEY (YouTube Data API v3; Enter para pular)' -AsSecureString
    $ptr = [Runtime.InteropServices.Marshal]::SecureStringToBSTR($sec)
    try { $ApiKey = [Runtime.InteropServices.Marshal]::PtrToStringBSTR($ptr) } finally { [Runtime.InteropServices.Marshal]::ZeroFreeBSTR($ptr) }
  }
  if ($ApiKey) {
    if ($ApiKey -notmatch '^AIza[0-9A-Za-z_-]{30,}$') { Write-Warning 'A chave não parece uma chave do Google (começa com AIza). Gravei mesmo assim; o doctor testa.' }
    # UTF-8 sem BOM (o PowerShell 5 colocaria BOM com Set-Content -Encoding UTF8)
    [IO.File]::WriteAllText($envFile, "YT_API_KEY=$ApiKey`n", (New-Object System.Text.UTF8Encoding $false))
    try { & icacls $envFile /inheritance:r /grant:r "$($env:USERNAME):(R,W)" | Out-Null } catch { }
    Write-Host "Chave gravada em $envFile, legível só pelo seu usuário. Não compartilhe este arquivo."
    Write-Host "Dica: no Google Cloud, restrinja a chave à YouTube Data API v3."
  } elseif ($temArquivo) {
    Write-Host "Nenhuma chave nova: mantive o $envFile que já existia."
  } else {
    Write-Host "Sem chave por enquanto. Depois crie $envFile com a linha YT_API_KEY=... (o modo sem chave é reduzido)."
  }
}

$req = Join-Path $PSScriptRoot 'requirements.txt'
if ($SkipDeps) {
  Write-Host "Dependências puladas (-SkipDeps). Instale: $py -m pip install --upgrade -r `"$req`""
} else {
  & $py -m pip install --upgrade --quiet -r $req
  if ($LASTEXITCODE -ne 0) { Write-Warning "O pip falhou. Rode manualmente: $py -m pip install --upgrade -r `"$req`"" }
}
if (-not (Get-Command ffmpeg -ErrorAction SilentlyContinue)) { Write-Warning 'ffmpeg não encontrado (opcional; necessário para prints de vídeo e grades): winget install ffmpeg' }

# a checagem roda sem gravar __pycache__ dentro da skill instalada
$antes = $env:PYTHONDONTWRITEBYTECODE
$env:PYTHONDONTWRITEBYTECODE = '1'
& $py (Join-Path $installed[0] 'scripts\doctor.py')
$ok = ($LASTEXITCODE -eq 0)
$env:PYTHONDONTWRITEBYTECODE = $antes
Write-Host ""
if ($ok) {
  Write-Host "Pronto. No seu agente, peça: 'analise o nicho de finanças pessoais em PT e EN' ou 'quero modelar o canal @exemplo'."
} else {
  Write-Warning "Instalado, mas o doctor apontou pendências (acima). Resolva e rode de novo: $py `"$($installed[0])\scripts\doctor.py`""
  exit 2
}
