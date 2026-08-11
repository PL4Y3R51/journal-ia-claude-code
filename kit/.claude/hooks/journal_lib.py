#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""journal_lib.py — cœur commun des trois hooks du kit « Journal IA ».

Pourquoi Python et rien d'autre
-------------------------------
Le kit doit tourner à l'identique sur Linux, macOS et Windows. Des hooks en bash
imposeraient Git Bash aux étudiants sous Windows ; des hooks en PowerShell ne
tourneraient pas ailleurs. Python 3 est le seul runtime nécessaire — il l'était
déjà pour générer le rapport — et le module `json` de la bibliothèque standard
échappe guillemets, antislash, sauts de ligne, accents et emoji exactement comme
il faut. Aucune dépendance à installer, aucun appel réseau.

---------------------------------------------------------------------------
RÈGLE ABSOLUE : un hook ne sort JAMAIS avec le code 2.

Sur UserPromptSubmit, le code 2 EFFACE le prompt de l'étudiant. Une panne de
journalisation ne doit jamais coûter du travail. `run()` rattrape donc toute
exception et sort systématiquement en 0 — voir la fin de ce fichier.
---------------------------------------------------------------------------
"""

import datetime
import json
import os
import re
import shutil
import subprocess
import sys
import time

MAX_REPONSE = 2000       # la réponse est une base de résumé, pas une preuve
MAX_COMMANDE = 80        # garder les lignes de journal courtes
MAX_SCAN_JOURNAL = 5000  # lignes relues au plus pour la détection créé/modifié
LOCK_PERIME = 60         # secondes avant de considérer un verrou comme mort


# --------------------------------------------------------------------------
# Chemins
# --------------------------------------------------------------------------

def project_root():
    """CLAUDE_PROJECT_DIR est exporté par Claude Code dans le processus du hook.
    Le repli sur le dossier courant ne sert qu'aux tests lancés à la main."""
    racine = os.environ.get("CLAUDE_PROJECT_DIR") or os.getcwd()
    return racine.replace("\\", "/").rstrip("/")


def journal_dir():
    return os.path.join(project_root(), ".claude", "journal-ia")


def journal_file():
    return os.path.join(journal_dir(), "journal.jsonl")


def now():
    """Horodatage UTC ISO 8601."""
    return datetime.datetime.now(datetime.timezone.utc).strftime(
        "%Y-%m-%dT%H:%M:%SZ")


def rel_path(chemin):
    """Rend un chemin relatif à CLAUDE_PROJECT_DIR.

    Un journal ne doit pas révéler l'arborescence personnelle de l'étudiant.
    Hors du projet, on ne garde que le nom du fichier, préfixé pour que le
    rapport reste honnête sur son origine.
    """
    racine = project_root()
    q = chemin.replace("\\", "/")
    if q == racine:
        return "."
    if q.startswith(racine + "/"):
        return q[len(racine) + 1:]
    # Windows : CLAUDE_PROJECT_DIR et file_path peuvent différer par la casse.
    if q.lower().startswith(racine.lower() + "/"):
        return q[len(racine) + 1:]
    if q.startswith("/") or re.match(r"^[A-Za-z]:/", q):
        return "(hors-projet)/" + os.path.basename(q)
    return q


# --------------------------------------------------------------------------
# Écriture
# --------------------------------------------------------------------------

def warn_once(message):
    """Écrit un avertissement dans errors.log, une seule fois par message, pour
    ne pas transformer une anomalie récurrente en fichier de plusieurs Mo."""
    try:
        os.makedirs(journal_dir(), exist_ok=True)
        chemin = os.path.join(journal_dir(), "errors.log")
        if os.path.isfile(chemin):
            with open(chemin, encoding="utf-8", errors="replace") as f:
                if message in f.read():
                    return
        with open(chemin, "a", encoding="utf-8", newline="\n") as f:
            f.write("%s %s\n" % (now(), message))
    except OSError:
        pass


def emit(ligne):
    """Ajoute une ligne au journal.

    Atomicité : en mode « append », une écriture de moins de PIPE_BUF (4096 o)
    passe en un seul write(), donc deux hooks asynchrones ne peuvent pas
    s'entrelacer. Les lignes « action » et « response » restent sous cette
    limite par construction (cible tronquée à 80 caractères, réponse à 2000).

    Un prompt verbatim, lui, n'est JAMAIS tronqué : il peut dépasser 4096 o, et
    l'argument PIPE_BUF ne tient alors plus. On prend donc en plus un verrou par
    création de dossier — `mkdir` est atomique sur tous les systèmes visés,
    Windows compris, et ne demande aucune dépendance. Si le verrou reste
    indisponible, on écrit quand même : perdre l'atomicité vaut mieux que
    perdre la ligne.
    """
    if not ligne:
        return
    dossier = journal_dir()
    try:
        os.makedirs(dossier, exist_ok=True)
    except OSError:
        return
    verrou = os.path.join(dossier, ".lock")

    # Verrou orphelin laissé par un terminal tué.
    try:
        if time.time() - os.path.getmtime(verrou) > LOCK_PERIME:
            os.rmdir(verrou)
    except OSError:
        pass

    tenu = False
    for _ in range(100):
        try:
            os.mkdir(verrou)
            tenu = True
            break
        except OSError:
            time.sleep(0.02)

    try:
        with open(journal_file(), "a", encoding="utf-8", newline="\n") as f:
            f.write(ligne + "\n")
    except OSError:
        warn_once("ecriture du journal impossible (droits ou disque plein).")
    finally:
        if tenu:
            try:
                os.rmdir(verrou)
            except OSError:
                pass


# --------------------------------------------------------------------------
# Git : créé, modifié, ou indéterminable
# --------------------------------------------------------------------------

def git(*args):
    """Lance git et retourne (ok, sortie). Ne lève jamais."""
    try:
        r = subprocess.run(
            ["git", "-C", project_root()] + list(args),
            stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, timeout=10)
    except Exception:
        return False, ""
    return r.returncode == 0, r.stdout.decode("utf-8", "replace")


def deja_cree(session, cible):
    """Vrai si le journal note déjà une création de cette cible dans la séance.

    Un fichier créé mais pas encore commité reste « ?? » pour git : sans ce
    garde-fou, toutes les écritures suivantes seraient vues comme des créations.
    """
    chemin = journal_file()
    if not os.path.isfile(chemin):
        return False
    try:
        with open(chemin, encoding="utf-8", errors="replace") as f:
            lignes = f.readlines()
    except OSError:
        return False
    for brut in reversed(lignes[-MAX_SCAN_JOURNAL:]):
        brut = brut.strip()
        if not brut:
            continue
        try:
            e = json.loads(brut)
        except ValueError:
            continue
        if (isinstance(e, dict)
                and e.get("type") == "action"
                and e.get("session") == session
                and e.get("target") == cible
                and e.get("state") == "created"):
            return True
    return False


def git_state(chemin_brut, cible, session):
    """« created », « modified », ou « unknown » hors dépôt Git."""
    if not shutil.which("git"):
        return "unknown"
    if not git("rev-parse", "--is-inside-work-tree")[0]:
        return "unknown"

    ok, sortie = git("status", "--porcelain", "--", chemin_brut)
    if not ok:
        return "unknown"

    if sortie[:2] in ("??", "A ", "AM"):
        etat = "created"
    elif sortie.strip() == "":
        # Soit le fichier est suivi et identique à l'index, soit il est ignoré
        # par .gitignore. On interroge l'index pour trancher.
        suivi = git("ls-files", "--error-unmatch", "--", chemin_brut)[0]
        etat = "modified" if suivi else "unknown"
    else:
        etat = "modified"

    if etat == "created" and deja_cree(session, cible):
        etat = "modified"
    return etat


# --------------------------------------------------------------------------
# Construction des lignes
# --------------------------------------------------------------------------

def ligne_prompt(d):
    """Le texte est repris tel quel : jamais tronqué, nettoyé ni normalisé.
    C'est le verbatim, et toute transformation détruirait la seule propriété qui
    justifie ce kit."""
    texte = d.get("prompt") or ""
    if texte == "":
        return None
    return {"ts": now(), "session": d.get("session_id") or "",
            "type": "prompt", "text": texte}


def ligne_response(d):
    texte = d.get("last_assistant_message") or ""
    if texte == "":
        return None
    return {"ts": now(), "session": d.get("session_id") or "",
            "type": "response", "text": texte[:MAX_REPONSE],
            "truncated": len(texte) > MAX_REPONSE}


def est_lecture_seule(commande, cmds, git_sous_cmds):
    # PowerShell est insensible à la casse : « Get-Content » et « get-content »
    # sont la même commande. On compare donc en minuscules, ce qui ne change
    # rien aux commandes POSIX de la liste, déjà toutes en minuscules.
    mots = commande.strip().split()
    if not mots:
        return True
    premier = mots[0].lower()
    if premier == "git":
        return len(mots) > 1 and mots[1].lower() in git_sous_cmds
    return premier in cmds


def ligne_action(d, cmds, git_sous_cmds):
    outil = d.get("tool_name") or ""
    entree = d.get("tool_input") or {}
    session = d.get("session_id") or ""
    if not isinstance(entree, dict):
        return None

    if outil in ("Write", "Edit"):
        brut = entree.get("file_path") or ""
        if not brut:
            return None
        cible = rel_path(brut)
        return {"ts": now(), "session": session, "type": "action",
                "tool": outil, "target": cible,
                "state": git_state(brut, cible, session)}

    # Sous Windows, Claude Code peut exposer le shell comme outil « PowerShell »
    # et non « Bash » (variable CLAUDE_CODE_USE_POWERSHELL_TOOL). Les deux outils
    # portent la commande dans le même champ « command » : sans ce second nom,
    # aucune commande n'était journalisée chez les étudiants sous Windows.
    if outil in ("Bash", "PowerShell"):
        commande = entree.get("command") or ""
        if not commande or est_lecture_seule(commande, cmds, git_sous_cmds):
            return None
        return {"ts": now(), "session": session, "type": "action",
                "tool": outil, "target": commande[:MAX_COMMANDE],
                "state": "run"}

    return None


# --------------------------------------------------------------------------
# Point d'entrée commun
# --------------------------------------------------------------------------

def run(constructeur):
    """Lit l'entrée du hook sur stdin, écrit au plus une ligne, sort en 0.

    `constructeur` reçoit le dictionnaire de l'événement et retourne la ligne à
    journaliser, ou None s'il n'y a rien à dire (prompt vide, outil hors
    périmètre, commande de consultation).

    Aucun chemin de sortie ne renvoie autre chose que 0.
    """
    try:
        # Sous Windows la sortie standard n'est pas en UTF-8 par défaut : sans
        # cela, un accent ou un emoji dans un prompt ferait échouer l'écriture.
        for flux in (sys.stdin, sys.stdout, sys.stderr):
            try:
                flux.reconfigure(encoding="utf-8", errors="replace")
            except Exception:
                pass

        brut = sys.stdin.read()
        if not brut or not brut.strip():
            sys.exit(0)
        try:
            d = json.loads(brut)
        except ValueError:
            warn_once("entree de hook illisible (JSON invalide).")
            sys.exit(0)
        if not isinstance(d, dict):
            sys.exit(0)

        ligne = constructeur(d)
        if ligne is not None:
            emit(json.dumps(ligne, ensure_ascii=False, separators=(",", ":")))
    except SystemExit:
        raise
    except BaseException as exc:  # y compris KeyboardInterrupt : on ne remonte
        try:                      # jamais un code non nul vers Claude Code
            warn_once("erreur interne du hook : %r" % (exc,))
        except BaseException:
            pass
    sys.exit(0)
