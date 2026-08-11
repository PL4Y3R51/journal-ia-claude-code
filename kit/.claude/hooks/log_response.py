#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""log_response.py — hook Stop.

Journalise le message final de Claude pour le tour qui vient de se terminer, lu
dans le champ « last_assistant_message » de l'entrée du hook.

Contrairement au prompt, ce texte EST tronqué à 2000 caractères, avec un champ
booléen « truncated ». C'est un choix assumé : la réponse sert de base de résumé,
pas de pièce à conviction. Seuls les prompts sont garantis mot pour mot. Ce point
est déclaré dans le README et dans le rapport.

Sortie toujours 0.
"""

import os
import sys

# Pas de __pycache__ dans le dépôt de l'étudiant.
sys.dont_write_bytecode = True
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import journal_lib  # noqa: E402

journal_lib.run(journal_lib.ligne_response)
