<#
install.ps1 — dépose le kit « Journal IA » dans un projet, sous Windows.

    .\install.ps1 C:\chemin\vers\projet

Équivalent strict de install.sh, pour ne pas exiger Git Bash. Sous Linux et
macOS, utilise install.sh.

Le kit s'active par dossier : rien n'est installé globalement, et aucun autre
projet n'est affecté. Relancer ce script deux fois ne casse rien.

Aucun appel réseau.

Si Windows refuse d'exécuter le script :
    powershell -ExecutionPolicy Bypass -File .\install.ps1 C:\chemin\vers\projet
#>

param(
  [Parameter(Position = 0)]
  [string]$Projet
)

$ErrorActionPreference = 'Stop'

$SrcDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$Kit = Join-Path $SrcDir 'kit\.claude'

function Ok    ($m) { Write-Host "  ok  $m" -ForegroundColor Green }
function Avert ($m) { Write-Host "  !   $m" -ForegroundColor Yellow }
function Mauv  ($m) { Write-Host "  X   $m" -ForegroundColor Red }
function Titre ($m) { Write-Host ""; Write-Host $m -ForegroundColor White }

function Usage {
  Write-Host @'
Usage : .\install.ps1 C:\chemin\vers\projet

Copie .claude\ (hooks + skill /rapport-ia) dans le projet indiqué, puis prépare
le dossier de journal. Le projet doit déjà exister.
'@
}

if (-not $Projet -or $Projet -in @('-h', '--help', '/?')) {
  Usage
  exit ($(if ($Projet) { 0 } else { 1 }))
}

if (-not (Test-Path -LiteralPath $Kit -PathType Container)) {
  Mauv "Gabarit introuvable : $Kit"
  Write-Host "      Lance ce script depuis le depot clone, sans deplacer install.ps1."
  exit 1
}

if (-not (Test-Path -LiteralPath $Projet -PathType Container)) {
  Mauv "Dossier de projet introuvable : $Projet"
  Write-Host "      Cree-le d'abord (New-Item -ItemType Directory '$Projet'), puis relance."
  exit 1
}

$Target = (Resolve-Path -LiteralPath $Projet).Path
$Dest = Join-Path $Target '.claude'

Write-Host "Kit << Journal IA >> - installation"
Write-Host "  source : $SrcDir"
Write-Host "  cible  : $Target"

# --- Prerequis -------------------------------------------------------------
# Diagnostic lisible plutot qu'un echec silencieux. Seul Python 3 est
# indispensable : c'est le seul runtime des hooks comme du rapport.
Titre 'Prerequis'
$Py = $null
foreach ($c in @('python3', 'python', 'py')) {
  $cmd = Get-Command $c -ErrorAction SilentlyContinue
  if (-not $cmd) { continue }
  # Les alias du Microsoft Store existent parfois sans Python installe :
  # on tranche en executant reellement l'interpreteur.
  $v = ''
  try { $v = (& $c --version 2>&1 | Select-Object -First 1) } catch { $v = '' }
  if ($v -match '^Python 3\.') {
    $Py = $c
    Ok "$c - $v"
    break
  } elseif ($v) {
    Avert "$c ignore - $v (Python 3 requis)"
  }
}
if (-not $Py) {
  Mauv 'Python 3 introuvable - obligatoire (hooks + rapport).'
  Write-Host '      https://www.python.org/downloads/ (cocher << Add python.exe to PATH >>)'
}

$git = Get-Command git -ErrorAction SilentlyContinue
if ($git) {
  Ok "git - $((& git --version 2>&1 | Select-Object -First 1))"
} else {
  Avert 'git introuvable - le journal notera << touche >> au lieu de << cree >>/<< modifie >>.'
}

$claude = Get-Command claude -ErrorAction SilentlyContinue
if ($claude) {
  $cv = (& claude --version 2>&1 | Select-Object -First 1)
  Ok "claude - $cv"
  # Le skill a besoin de la substitution de ${CLAUDE_PROJECT_DIR}, arrivee en 2.1.196.
  if ($cv -match '(\d+)\.(\d+)\.(\d+)') {
    $n = [int]$Matches[1] * 1000000 + [int]$Matches[2] * 1000 + [int]$Matches[3]
    if ($n -lt (2 * 1000000 + 1 * 1000 + 196)) {
      Avert 'Claude Code < 2.1.196 : /rapport-ia ne substituera pas ${CLAUDE_PROJECT_DIR}. Mets a jour.'
    }
  }
} else {
  Avert 'claude introuvable dans le PATH - le kit s''installe quand meme.'
}

if (-not $Py) {
  Titre 'Installation interrompue'
  Write-Host 'Installe Python 3, puis relance. Rien n''a ete copie.'
  exit 1
}

# --- settings.json : on n'ecrase jamais ------------------------------------
# Le gabarit invoque << python3 >>. Si cette machine n'a que << python >> ou
# << py >>, on inscrit le nom qui marche ici.
Titre 'Configuration'
New-Item -ItemType Directory -Force -Path $Dest | Out-Null
$gabarit = Get-Content -LiteralPath (Join-Path $Kit 'settings.json') -Raw -Encoding UTF8
if ($Py -ne 'python3') {
  $gabarit = $gabarit.Replace('"command": "python3"', '"command": "' + $Py + '"')
  Avert "Hooks configures avec << $Py >> (python3 absent de cette machine)."
}
# LF et UTF-8 sans BOM, pour que le fichier soit identique a celui de install.sh.
$gabarit = $gabarit.Replace("`r`n", "`n")
$cfgPath = Join-Path $Dest 'settings.json'
$sansBom = New-Object System.Text.UTF8Encoding($false)

if (Test-Path -LiteralPath $cfgPath) {
  $actuel = [System.IO.File]::ReadAllText($cfgPath).Replace("`r`n", "`n")
  if ($actuel -eq $gabarit) {
    Ok '.claude\settings.json deja identique au gabarit - rien a faire.'
  } else {
    Mauv '.claude\settings.json existe deja et differe du gabarit.'
    Write-Host @"

Il n'a PAS ete touche. Ouvre-le et fusionne a la main le bloc << hooks >>
ci-dessous (si une cle << hooks >> existe deja, ajoute les entrees dedans) :

--------------------------------------------------------------------------
$gabarit
--------------------------------------------------------------------------

Fichier a modifier : $cfgPath
Le reste du kit n'a pas ete installe. Relance ce script apres la fusion, ou
copie les dossiers a la main :
  Copy-Item -Recurse "$Kit\hooks"  "$Dest\"
  Copy-Item -Recurse "$Kit\skills" "$Dest\"
"@
    exit 1
  }
} else {
  [System.IO.File]::WriteAllText($cfgPath, $gabarit, $sansBom)
  Ok '.claude\settings.json installe (3 hooks).'
}

# --- Hooks et skill --------------------------------------------------------
New-Item -ItemType Directory -Force -Path (Join-Path $Dest 'hooks') | Out-Null
New-Item -ItemType Directory -Force -Path (Join-Path $Dest 'skills') | Out-Null
Copy-Item -Force -Path (Join-Path $Kit 'hooks\*.py') -Destination (Join-Path $Dest 'hooks')
Copy-Item -Recurse -Force -Path (Join-Path $Kit 'skills\rapport-ia') -Destination (Join-Path $Dest 'skills')
# Le skill pre-approuve << python3 >> dans allowed-tools. Si cette machine
# utilise un autre nom, on l'aligne : sinon le skill demanderait une permission
# a chaque generation de rapport.
if ($Py -ne 'python3') {
  $skPath = Join-Path $Dest 'skills\rapport-ia\SKILL.md'
  $sk = [System.IO.File]::ReadAllText($skPath).Replace('python3 ', $Py + ' ')
  [System.IO.File]::WriteAllText($skPath, $sk, $sansBom)
}
Ok 'hooks installes    : log_prompt.py, log_response.py, log_action.py'
Ok 'skill installe     : /rapport-ia'

# --- Dossier de journal ----------------------------------------------------
$jdir = Join-Path $Dest 'journal-ia'
New-Item -ItemType Directory -Force -Path $jdir | Out-Null
$gitkeep = Join-Path $jdir '.gitkeep'
if (-not (Test-Path -LiteralPath $gitkeep)) {
  New-Item -ItemType File -Path $gitkeep | Out-Null
}
Ok 'journal pret       : .claude\journal-ia\'

# --- Controle a blanc ------------------------------------------------------
# Verifie que le hook tourne vraiment sur cette machine, plutot que de le
# decouvrir a la premiere vraie session.
Titre 'Controle a blanc'
$journal = Join-Path $jdir 'journal.jsonl'
$essai = '{"session_id":"installation-essai","hook_event_name":"UserPromptSubmit","prompt":"essai d installation"}'
$env:CLAUDE_PROJECT_DIR = $Target
try {
  $essai | & $Py (Join-Path $Dest 'hooks\log_prompt.py') 2>$null
  if ((Test-Path -LiteralPath $journal) -and
      (Select-String -LiteralPath $journal -Pattern 'installation-essai' -Quiet)) {
    Ok 'le hook ecrit bien dans .claude\journal-ia\journal.jsonl'
    # On retire la ligne d'essai pour laisser un journal propre. @() force un
    # tableau : sans cela, un journal qui ne contient que la ligne d'essai
    # donnerait $null et l'ecriture echouerait en laissant la ligne en place.
    $reste = @(Get-Content -LiteralPath $journal -Encoding UTF8 |
      Where-Object { $_ -notmatch 'installation-essai' })
    $contenu = if ($reste.Count -gt 0) { ($reste -join "`n") + "`n" } else { '' }
    [System.IO.File]::WriteAllText($journal, $contenu, $sansBom)
  } else {
    Avert "le hook s'est execute mais n'a rien ecrit - verifie les droits sur $jdir"
  }
} catch {
  Avert "le hook n'a pas pu s'executer avec << $Py >> - verifie ton installation Python."
}

# --- Suite -----------------------------------------------------------------
Titre 'Termine'
Write-Host @"
1. cd "$Target" puis : claude
2. Accepte le dialogue de confiance de l'espace de travail (il autorise le skill).
3. Tape /hooks : tu dois voir UserPromptSubmit, Stop et PostToolUse
   sous << Project Settings >>.
4. Envoie un prompt quelconque, puis verifie que le journal grossit :
     Get-Content "$journal" | Measure-Object -Line
5. En fin de seance : /rapport-ia

Les hooks ne s'appliquent qu'aux sessions demarrees APRES cette installation.
Rien n'est capture retroactivement.
"@
exit 0
