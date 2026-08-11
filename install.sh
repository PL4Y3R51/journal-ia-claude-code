#!/usr/bin/env bash
# install.sh — dépose le kit « Journal IA » dans un projet. Linux, macOS, et
# Windows si tu as Git Bash. Sous Windows sans Git Bash : utilise install.ps1.
#
#   ./install.sh /chemin/vers/projet
#
# Le kit s'active par dossier : rien n'est installé globalement, et aucun autre
# projet n'est affecté. Relancer ce script deux fois ne casse rien.
#
# Aucun appel réseau. Compatible bash 3.2 (macOS par défaut).

trap 'exit 1' ERR

SRC_DIR=$(cd "$(dirname "$0")" && pwd)
KIT="$SRC_DIR/kit/.claude"

if [ -t 1 ]; then
  B=$(printf '\033[1m'); R=$(printf '\033[31m'); G=$(printf '\033[32m')
  Y=$(printf '\033[33m'); Z=$(printf '\033[0m')
else
  B=""; R=""; G=""; Y=""; Z=""
fi

ok()   { printf '%s  ok %s %s\n' "$G" "$Z" "$1"; }
warn() { printf '%s  !  %s %s\n' "$Y" "$Z" "$1"; }
bad()  { printf '%s  X  %s %s\n' "$R" "$Z" "$1"; }
titre(){ printf '\n%s%s%s\n' "$B" "$1" "$Z"; }

usage() {
  cat <<'EOF'
Usage : ./install.sh /chemin/vers/projet

Copie .claude/ (hooks + skill /rapport-ia) dans le projet indiqué, puis prépare
le dossier de journal. Le projet doit déjà exister.
EOF
}

case "${1:-}" in
  -h|--help) usage; exit 0 ;;
esac
if [ "$#" -ne 1 ]; then
  usage
  exit 1
fi

TARGET="$1"

if [ ! -d "$KIT" ]; then
  bad "Gabarit introuvable : $KIT"
  echo "     Lance ce script depuis le dépôt cloné, sans déplacer install.sh."
  exit 1
fi

if [ ! -d "$TARGET" ]; then
  bad "Dossier de projet introuvable : $TARGET"
  echo "     Crée-le d'abord (mkdir -p \"$TARGET\"), puis relance."
  exit 1
fi

TARGET=$(cd "$TARGET" && pwd)
DEST="$TARGET/.claude"

printf '%sKit « Journal IA » — installation%s\n' "$B" "$Z"
echo "  source : $SRC_DIR"
echo "  cible  : $TARGET"

# --- Prérequis -------------------------------------------------------------
# Diagnostic lisible plutôt qu'un échec silencieux. Seul Python 3 est
# indispensable : c'est le seul runtime des hooks comme du rapport.
titre "Prérequis"
PY=""
for c in python3 python; do
  if command -v "$c" >/dev/null 2>&1; then
    V=$("$c" --version 2>&1 | head -1)
    case "$V" in
      "Python 3."*) PY="$c"; ok "$c — $V"; break ;;
      *) warn "$c ignoré — $V (Python 3 requis)" ;;
    esac
  fi
done
if [ -z "$PY" ]; then
  bad "Python 3 introuvable — obligatoire (hooks + rapport)."
  echo "     macOS         : brew install python3"
  echo "     Debian/Ubuntu : sudo apt install python3"
  echo "     Windows       : https://www.python.org/downloads/ (cocher « Add to PATH »)"
fi

if command -v git >/dev/null 2>&1; then
  ok "git — $(git --version 2>&1 | head -1)"
else
  warn "git introuvable — le journal notera « touché » au lieu de « créé »/« modifié »."
fi

if command -v claude >/dev/null 2>&1; then
  CV=$(claude --version 2>&1 | head -1)
  ok "claude — $CV"
  # Le skill a besoin de la substitution de ${CLAUDE_PROJECT_DIR}, arrivée en 2.1.196.
  N=$(printf '%s' "$CV" | tr -dc '0-9.' | cut -d. -f1-3)
  MAJ=$(printf '%s' "$N" | cut -d. -f1)
  MIN=$(printf '%s' "$N" | cut -d. -f2)
  PAT=$(printf '%s' "$N" | cut -d. -f3)
  if [ -n "$MAJ" ] && [ -n "$MIN" ] && [ -n "$PAT" ]; then
    if [ "$MAJ" -lt 2 ] \
      || { [ "$MAJ" -eq 2 ] && [ "$MIN" -lt 1 ]; } \
      || { [ "$MAJ" -eq 2 ] && [ "$MIN" -eq 1 ] && [ "$PAT" -lt 196 ]; }; then
      warn "Claude Code < 2.1.196 : /rapport-ia ne substituera pas \${CLAUDE_PROJECT_DIR}. Mets à jour."
    fi
  fi
else
  warn "claude introuvable dans le PATH — le kit s'installe quand même."
fi

if [ -z "$PY" ]; then
  titre "Installation interrompue"
  echo "Installe Python 3, puis relance. Rien n'a été copié."
  exit 1
fi

# --- settings.json : on n'écrase jamais ------------------------------------
# Le gabarit invoque « python3 ». Si cette machine n'a que « python », on
# inscrit le nom qui marche ici, pour que les hooks démarrent partout.
titre "Configuration"
RENDU="$DEST.settings.tmp.$$"
mkdir -p "$DEST"
if [ "$PY" = "python3" ]; then
  cp "$KIT/settings.json" "$RENDU"
else
  sed "s/\"command\": \"python3\"/\"command\": \"$PY\"/g" \
    "$KIT/settings.json" > "$RENDU"
  warn "Hooks configurés avec « $PY » (python3 absent de cette machine)."
fi

if [ -f "$DEST/settings.json" ]; then
  if cmp -s "$RENDU" "$DEST/settings.json"; then
    rm -f "$RENDU"
    ok ".claude/settings.json déjà identique au gabarit — rien à faire."
  else
    bad ".claude/settings.json existe déjà et diffère du gabarit."
    cat <<EOF

Il n'a PAS été touché. Ouvre-le et fusionne à la main le bloc « hooks »
ci-dessous (si une clé « hooks » existe déjà, ajoute les entrées dedans) :

--------------------------------------------------------------------------
EOF
    cat "$RENDU"
    cat <<EOF
--------------------------------------------------------------------------

Fichier à modifier : $DEST/settings.json
Le reste du kit n'a pas été installé. Relance ce script après la fusion, ou
copie les dossiers à la main :
  cp -R "$KIT/hooks"  "$DEST/"
  cp -R "$KIT/skills" "$DEST/"
EOF
    rm -f "$RENDU"
    exit 1
  fi
else
  mv "$RENDU" "$DEST/settings.json"
  ok ".claude/settings.json installé (3 hooks)."
fi

# --- Hooks et skill --------------------------------------------------------
mkdir -p "$DEST/hooks" "$DEST/skills"
cp "$KIT/hooks/"*.py "$DEST/hooks/"
cp -R "$KIT/skills/rapport-ia" "$DEST/skills/"
# Le skill pré-approuve « python3 » dans allowed-tools. Si cette machine utilise
# un autre nom, on l'aligne : sinon le skill demanderait une permission à chaque
# génération de rapport. sed -i n'est pas portable (GNU vs BSD) : passage par un
# fichier temporaire.
if [ "$PY" != "python3" ]; then
  SK="$DEST/skills/rapport-ia/SKILL.md"
  sed "s/python3 /$PY /g" "$SK" > "$SK.tmp.$$" && mv "$SK.tmp.$$" "$SK"
fi
chmod +x "$DEST/hooks/"*.py 2>/dev/null || true
chmod +x "$DEST/skills/rapport-ia/scripts/build-report.py" 2>/dev/null || true
ok "hooks installés    : log_prompt.py, log_response.py, log_action.py"
ok "skill installé     : /rapport-ia"

# --- Dossier de journal ----------------------------------------------------
mkdir -p "$DEST/journal-ia"
if [ ! -f "$DEST/journal-ia/.gitkeep" ]; then
  : > "$DEST/journal-ia/.gitkeep"
fi
ok "journal prêt       : .claude/journal-ia/"

# --- Contrôle à blanc ------------------------------------------------------
# Vérifie que le hook tourne vraiment sur cette machine, plutôt que de le
# découvrir à la première vraie session.
titre "Contrôle à blanc"
ESSAI='{"session_id":"installation-essai","hook_event_name":"UserPromptSubmit","prompt":"essai d installation"}'
if printf '%s' "$ESSAI" | (cd "$TARGET" && CLAUDE_PROJECT_DIR="$TARGET" "$PY" \
     "$DEST/hooks/log_prompt.py") 2>/dev/null; then
  if grep -q "installation-essai" "$DEST/journal-ia/journal.jsonl" 2>/dev/null; then
    ok "le hook écrit bien dans .claude/journal-ia/journal.jsonl"
    # On retire la ligne d'essai pour laisser un journal propre.
    grep -v "installation-essai" "$DEST/journal-ia/journal.jsonl" \
      > "$DEST/journal-ia/journal.tmp.$$" 2>/dev/null || true
    mv "$DEST/journal-ia/journal.tmp.$$" "$DEST/journal-ia/journal.jsonl"
  else
    warn "le hook s'est exécuté mais n'a rien écrit — vérifie les droits sur $DEST/journal-ia/"
  fi
else
  warn "le hook n'a pas pu s'exécuter avec « $PY » — vérifie ton installation Python."
fi

# --- Suite -----------------------------------------------------------------
titre "Terminé"
cat <<EOF
1. cd "$TARGET" && claude
2. Accepte le dialogue de confiance de l'espace de travail (il autorise le skill).
3. Tape /hooks : tu dois voir UserPromptSubmit, Stop et PostToolUse
   sous « Project Settings ».
4. Envoie un prompt quelconque, puis vérifie que le journal grossit :
     wc -l "$DEST/journal-ia/journal.jsonl"
5. En fin de séance : /rapport-ia

Les hooks ne s'appliquent qu'aux sessions démarrées APRÈS cette installation.
Rien n'est capturé rétroactivement.
EOF
exit 0
