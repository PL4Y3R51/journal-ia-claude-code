#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""log_prompt.py — hook UserPromptSubmit.

Journalise le prompt de l'étudiant MOT POUR MOT, au moment de la soumission.

Le champ « text » n'est jamais tronqué, nettoyé ni normalisé. C'est le verbatim :
toute transformation détruirait la seule propriété qui justifie ce kit.

Sortie toujours 0. Sur UserPromptSubmit, le code 2 effacerait le prompt.
"""

import os
import sys

# Pas de __pycache__ dans le dépôt de l'étudiant : le gain de démarrage est
# négligeable pour un hook asynchrone, le dossier parasite ne l'est pas.
sys.dont_write_bytecode = True
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import journal_lib  # noqa: E402

journal_lib.run(journal_lib.ligne_prompt)
