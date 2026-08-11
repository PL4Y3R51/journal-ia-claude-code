#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""log_action.py — hook PostToolUse, matcher « Write|Edit|Bash|PowerShell ».

Une ligne par action concrète : fichier créé/modifié, commande exécutée. La
distinction créé / modifié et la mise en chemin relatif sont faites dans
journal_lib, qui interroge « git status --porcelain » et dégrade proprement en
« unknown » hors dépôt Git.

Sortie toujours 0. (Sur PostToolUse le code 2 ne bloque rien — l'outil a déjà
tourné — mais il afficherait une erreur à Claude. On garde la même discipline
que sur les autres hooks.)
"""

import os
import sys

# Pas de __pycache__ dans le dépôt de l'étudiant.
sys.dont_write_bytecode = True
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import journal_lib  # noqa: E402

# ===========================================================================
# FILTRE « LECTURE SEULE » — c'est ici, et nulle part ailleurs, qu'on l'ajuste.
#
# Ces commandes ne modifient rien : les journaliser noierait les actions réelles
# dans du bruit de consultation. La liste est MODIFIABLE — mais toute
# modification doit être reflétée dans le rapport, dont le pied de page
# méthodologique déclare que les commandes de consultation ne sont pas
# journalisées. Si tu retires une entrée d'ici, dis-le dans le rapport.
#
# Limite connue et assumée : seul le PREMIER mot est examiné (le second pour
# « git »). « sed -i » ou « awk ... > fichier » modifient des fichiers et passent
# quand même à travers le filtre. Retire « sed » et « awk » de la liste si ton
# usage les emploie pour écrire.
# ===========================================================================
#
# La comparaison est insensible à la casse (voir est_lecture_seule) : cette liste
# s'écrit donc entièrement en minuscules, y compris les cmdlets PowerShell.
# ===========================================================================
COMMANDES_LECTURE_SEULE = [
    # POSIX — outil « Bash ».
    "ls", "cat", "cd", "pwd", "echo", "grep", "find",
    "head", "tail", "which", "wc", "sed", "awk",
    # PowerShell — outil « PowerShell » sous Windows. Sans ces entrées, chaque
    # « Get-Content » finirait dans le journal comme une action concrète.
    "get-content", "get-childitem", "get-item", "get-itemproperty",
    "get-location", "get-command", "get-date", "get-help", "get-member",
    "get-process", "get-service", "get-module", "select-string", "test-path",
    "measure-object", "where-object", "select-object", "sort-object",
    "group-object", "format-table", "format-list", "out-string",
    "resolve-path", "split-path", "join-path", "compare-object",
    "write-output", "write-host",
    # Alias PowerShell courants des mêmes consultations.
    "gc", "gci", "gi", "gl", "gcm", "gm", "sls", "gps",
]
SOUS_COMMANDES_GIT_LECTURE_SEULE = ["status", "log", "diff", "show"]


def constructeur(evenement):
    return journal_lib.ligne_action(
        evenement, COMMANDES_LECTURE_SEULE, SOUS_COMMANDES_GIT_LECTURE_SEULE)


journal_lib.run(constructeur)
