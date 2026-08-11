#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""build-report.py — agrège journal.jsonl en un squelette de rapport Markdown.

Ce script AGRÈGE, il ne résume pas. Il copie les prompts mot pour mot, compte
les actions répétées, et laisse un marqueur « <!-- RÉSUMÉ À RÉDIGER --> » à
chaque endroit où un résumé est attendu. Le remplissage de ces marqueurs est le
travail du skill /rapport-ia, pas celui de ce script.

Bibliothèque standard uniquement. Aucun appel réseau.
"""

import argparse
import datetime
import json
import os
import re
import sys

MARQUEUR = "<!-- RÉSUMÉ À RÉDIGER -->"

# Libellés de rendu. « unknown » se dit « touché » : hors dépôt Git, on ne peut
# pas distinguer une création d'une modification, et prétendre le contraire
# serait une invention.
ETATS = {
    "created": "créé",
    "modified": "modifié",
    "unknown": "touché",
}

PIED_DE_PAGE = """\
## Note méthodologique

Ce rapport est généré à partir d'un journal horodaté écrit automatiquement à
chaque interaction. Les prompts sont reproduits littéralement depuis ce journal.
Les résumés d'actions sont rédigés par Claude à partir des réponses
enregistrées. Les commandes de consultation en lecture seule ne sont pas
journalisées.
"""


# --------------------------------------------------------------------------
# Lecture du journal
# --------------------------------------------------------------------------

def lire_journal(chemin):
    """Retourne (entrées valides, nombre de lignes illisibles)."""
    entrees = []
    illisibles = 0
    with open(chemin, "r", encoding="utf-8", errors="replace") as f:
        for brut in f:
            brut = brut.strip()
            if not brut:
                continue
            try:
                obj = json.loads(brut)
            except (ValueError, TypeError):
                illisibles += 1
                continue
            if not isinstance(obj, dict) or "type" not in obj:
                illisibles += 1
                continue
            entrees.append(obj)
    return entrees, illisibles


def filtrer(entrees, session, depuis):
    """Filtre par séance et par date. Les horodatages sont en UTC ISO 8601,
    donc la comparaison lexicographique de chaînes suffit."""
    out = entrees

    if session and session not in ("all", "tout", "toutes"):
        if session == "last":
            derniere = None
            for e in out:
                if e.get("session"):
                    derniere = e["session"]
            session = derniere
        out = [e for e in out if e.get("session") == session]

    if depuis:
        out = [e for e in out if str(e.get("ts", "")) >= depuis]

    return out


# --------------------------------------------------------------------------
# Regroupement en tours
# --------------------------------------------------------------------------

def grouper(entrees):
    """Regroupe les entrées d'une séance en tours.

    Un « prompt » ouvre un tour, les « action » suivantes lui sont rattachées,
    le « response » le ferme. Les actions qui précèdent tout prompt (journal
    tronqué, séance reprise) tombent dans un tour d'en-tête sans prompt.
    """
    tours = []
    courant = None

    for e in entrees:
        t = e.get("type")

        if t == "prompt":
            courant = {
                "ts": e.get("ts", ""),
                "prompt": e.get("text", ""),
                "actions": [],
                "reponse": None,
                "tronquee": False,
                "hors_tour": False,
            }
            tours.append(courant)

        elif t == "action":
            if courant is None:
                courant = {
                    "ts": e.get("ts", ""),
                    "prompt": None,
                    "actions": [],
                    "reponse": None,
                    "tronquee": False,
                    "hors_tour": True,
                }
                tours.append(courant)
            courant["actions"].append(e)

        elif t == "response":
            if courant is None:
                courant = {
                    "ts": e.get("ts", ""),
                    "prompt": None,
                    "actions": [],
                    "reponse": None,
                    "tronquee": False,
                    "hors_tour": True,
                }
                tours.append(courant)
            courant["reponse"] = e.get("text", "")
            courant["tronquee"] = bool(e.get("truncated"))
            courant = None  # le tour est clos

    return tours


def grouper_seances(entrees):
    """Sépare les séances (le journal d'un dossier partagé les entremêle),
    puis regroupe chaque séance en tours. Ordre d'apparition conservé."""
    ordre = []
    par_session = {}
    for e in entrees:
        sid = e.get("session") or "(séance inconnue)"
        if sid not in par_session:
            par_session[sid] = []
            ordre.append(sid)
        par_session[sid].append(e)
    seances = []
    for sid in ordre:
        brut = par_session[sid]
        horodatages = [str(e.get("ts", "")) for e in brut if e.get("ts")]
        seances.append({
            "id": sid,
            "tours": grouper(brut),
            "debut": min(horodatages) if horodatages else "",
            "fin": max(horodatages) if horodatages else "",
        })
    return seances


def replier_actions(actions):
    """Écrase les répétitions : trois Edit sur le même fichier donnent une
    seule entrée comptée ×3. L'ordre de première apparition est conservé."""
    cles = []
    compte = {}
    for a in actions:
        cle = (a.get("tool", ""), a.get("target", ""), a.get("state", ""))
        if cle not in compte:
            compte[cle] = 0
            cles.append(cle)
        compte[cle] += 1
    return [(cle, compte[cle]) for cle in cles]


# --------------------------------------------------------------------------
# Rendu
# --------------------------------------------------------------------------

def cloture(texte):
    """Choisit une clôture de bloc de code plus longue que la plus longue
    suite d'accents graves du texte, pour qu'un prompt contenant ``` reste
    reproduit exactement."""
    plus_long = 0
    for suite in re.findall(r"`+", texte or ""):
        plus_long = max(plus_long, len(suite))
    return "`" * max(3, plus_long + 1)


def libelle_action(cle, n):
    outil, cible, etat = cle
    if outil == "Bash":
        texte = "commande `%s`" % cible
    else:
        texte = "`%s` %s" % (cible, ETATS.get(etat, "touché"))
    if n > 1:
        texte += " (×%d)" % n
    return texte


def bloc_reponse(tour):
    """Insère la réponse enregistrée dans un commentaire HTML.

    C'est la source dont le skill doit se servir pour rédiger le résumé — et
    seulement elle, jamais la mémoire de la conversation en cours. Le
    commentaire est invisible dans le Markdown rendu comme dans une conversion
    pandoc, donc il ne pollue pas le document remis à l'enseignant.

    « --> » est neutralisé pour ne pas fermer le commentaire par accident.
    C'est la seule retouche appliquée à ce texte ; le prompt, lui, n'en subit
    aucune.
    """
    if tour["reponse"] is None:
        return ("<!-- RÉPONSE ENREGISTRÉE : aucune (tour non clos dans le "
                "journal) -->")
    texte = tour["reponse"].replace("-->", "--&gt;")
    suffixe = " [texte tronqué à 2000 caractères]" if tour["tronquee"] else ""
    return ("<!-- RÉPONSE ENREGISTRÉE%s — source unique du résumé ci-dessous.\n"
            "%s\n-->" % (suffixe, texte))


def rendre(seances, meta):
    L = []
    a = L.append

    a("# Rapport d'usage de l'IA")
    a("")
    a("| | |")
    a("|---|---|")
    a("| Journal source | `%s` |" % meta["journal"])
    a("| Généré le | %s |" % meta["date"])
    a("| Séances | %d |" % len(seances))
    a("| Tours | %d |" % meta["tours"])
    a("| Actions journalisées | %d |" % meta["actions"])
    if meta["filtre"]:
        a("| Filtre appliqué | %s |" % meta["filtre"])
    if meta["illisibles"]:
        a("| Lignes illisibles ignorées | %d |" % meta["illisibles"])
    a("")
    a("**Comment lire ce rapport.** Les blocs *Prompt* sont copiés mot pour mot "
      "depuis le journal : ils n'ont subi aucune correction, ni d'orthographe "
      "ni de formulation. Les blocs *Résumé* sont rédigés par Claude à partir "
      "des réponses enregistrées et peuvent être imprécis. Seuls les prompts "
      "sont garantis littéraux.")
    a("")

    for i, seance in enumerate(seances, start=1):
        tours = seance["tours"]
        a("---")
        a("")
        a("## Séance %d" % i)
        a("")
        a("- Identifiant de séance : `%s`" % seance["id"])
        if seance["debut"]:
            a("- Première entrée : %s" % seance["debut"])
            a("- Dernière entrée : %s" % seance["fin"])
        a("- Tours : %d" % len(tours))
        a("")

        for j, tour in enumerate(tours, start=1):
            if tour["hors_tour"]:
                a("### Séance %d — actions hors tour" % i)
                a("")
                a("Actions présentes dans le journal avant le premier prompt "
                  "retenu (journal filtré, ou séance reprise).")
            else:
                a("### Séance %d, tour %d — %s" % (i, j, tour["ts"] or "?"))
                a("")
                a("**Prompt (verbatim)**")
                a("")
                f = cloture(tour["prompt"])
                a(f + "text")
                a(tour["prompt"])
                a(f)
            a("")

            a("**Actions journalisées**")
            a("")
            repliees = replier_actions(tour["actions"])
            if repliees:
                for cle, n in repliees:
                    a("- " + libelle_action(cle, n))
            else:
                a("- *aucune action journalisée pour ce tour*")
            a("")

            a("**Résumé**")
            a("")
            a(bloc_reponse(tour))
            a("")
            a(MARQUEUR)
            a("")

    a("---")
    a("")
    a(PIED_DE_PAGE)

    return "\n".join(L) + "\n"


# --------------------------------------------------------------------------

def defaut_journal():
    racine = os.environ.get("CLAUDE_PROJECT_DIR") or os.getcwd()
    return os.path.join(racine, ".claude", "journal-ia", "journal.jsonl")


def chemin_affichable(chemin):
    """Rend le chemin du journal relatif au projet avant de l'écrire dans le
    rapport. Le document part chez l'enseignant : il n'a pas à contenir
    « C:/Users/<prénom nom>/... »."""
    racine = (os.environ.get("CLAUDE_PROJECT_DIR") or os.getcwd())
    racine = racine.replace("\\", "/").rstrip("/")
    q = os.path.abspath(chemin).replace("\\", "/")
    if q.lower().startswith(racine.lower() + "/"):
        return q[len(racine) + 1:]
    # Hors du projet : le nom de fichier suffit à identifier la source.
    return os.path.basename(q)


def main(argv):
    # Sous Windows, la sortie standard est en cp1252 : sans cela, un simple
    # « → » dans une réponse enregistrée ferait planter le script.
    for flux in (sys.stdout, sys.stderr):
        try:
            flux.reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            pass

    p = argparse.ArgumentParser(
        description="Agrège un journal.jsonl en squelette de rapport Markdown. "
                    "Ne résume rien.")
    p.add_argument("journal", nargs="?", default=None,
                   help="chemin du journal (défaut : "
                        "$CLAUDE_PROJECT_DIR/.claude/journal-ia/journal.jsonl)")
    p.add_argument("--session", default=None,
                   help="identifiant de séance, « last » pour la dernière, "
                        "« all » pour toutes (défaut : all)")
    p.add_argument("--depuis", default=None,
                   help="ne garder que les entrées à partir de cette date "
                        "(AAAA-MM-JJ ou horodatage ISO 8601 complet)")
    p.add_argument("--sortie", default=None,
                   help="fichier de sortie, ou « auto » pour "
                        "rapports/rapport-ia-AAAA-MM-JJ.md à la racine du projet "
                        "(défaut : sortie standard)")
    args = p.parse_args(argv)

    # « auto » évite de faire calculer la date au modèle : elle vient de
    # l'horloge de la machine, donc le nom de fichier est toujours juste.
    if args.sortie == "auto":
        racine = os.environ.get("CLAUDE_PROJECT_DIR") or os.getcwd()
        args.sortie = os.path.join(
            racine, "rapports",
            "rapport-ia-%s.md" % datetime.date.today().isoformat())

    chemin = args.journal or defaut_journal()
    if not os.path.isfile(chemin):
        sys.stderr.write(
            "Journal introuvable : %s\n"
            "Le kit n'a peut-être jamais tourné dans ce dossier, ou les hooks "
            "ne sont pas actifs.\n" % chemin)
        return 1

    if args.depuis and not re.match(r"^\d{4}-\d{2}-\d{2}", args.depuis):
        sys.stderr.write("--depuis attend AAAA-MM-JJ ou un horodatage ISO 8601 "
                         "(reçu : %s)\n" % args.depuis)
        return 2

    entrees, illisibles = lire_journal(chemin)
    retenues = filtrer(entrees, args.session, args.depuis)

    if not retenues:
        sys.stderr.write(
            "Aucune entrée retenue (%d ligne(s) lue(s), %d illisible(s)). "
            "Vérifie les filtres --session / --depuis.\n"
            % (len(entrees), illisibles))
        return 1

    seances = grouper_seances(retenues)

    filtre = []
    if args.session and args.session != "all":
        filtre.append("séance = %s" % args.session)
    if args.depuis:
        filtre.append("à partir du %s" % args.depuis)

    meta = {
        "journal": chemin_affichable(chemin),
        "date": datetime.datetime.now().strftime("%Y-%m-%d %H:%M"),
        "tours": sum(len(s["tours"]) for s in seances),
        "actions": sum(len(t["actions"]) for s in seances for t in s["tours"]),
        "filtre": ", ".join(filtre),
        "illisibles": illisibles,
    }

    texte = rendre(seances, meta)

    if args.sortie:
        dossier = os.path.dirname(os.path.abspath(args.sortie))
        if dossier and not os.path.isdir(dossier):
            os.makedirs(dossier)
        with open(args.sortie, "w", encoding="utf-8", newline="\n") as f:
            f.write(texte)
        sys.stderr.write("Squelette écrit dans %s (%d tour(s)).\n"
                         % (args.sortie, meta["tours"]))
    else:
        sys.stdout.write(texte)

    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
