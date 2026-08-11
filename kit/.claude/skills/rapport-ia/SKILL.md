---
name: rapport-ia
description: Génère le rapport de documentation d'usage de l'IA à partir du journal local. À invoquer manuellement en fin de séance ou de projet.
disable-model-invocation: true
argument-hint: [session|all]
allowed-tools: Bash(python3 ${CLAUDE_SKILL_DIR}/scripts/build-report.py *)
---

Génère le rapport d'usage de l'IA depuis `.claude/journal-ia/journal.jsonl`.

## 1. Produire le squelette

`$ARGUMENTS` vaut un identifiant de séance, `last`, ou `all`. Sans argument, utilise `all`.

```bash
python3 ${CLAUDE_SKILL_DIR}/scripts/build-report.py --session all --sortie auto
```

Le script écrit `rapports/rapport-ia-<date>.md` et affiche le chemin. Il agrège
seulement : il ne résume rien. Si le journal est introuvable ou vide, dis-le et
arrête-toi — ne fabrique pas de rapport.

## 2. Remplir les résumés

Lis le fichier produit. Pour chaque `<!-- RÉSUMÉ À RÉDIGER -->`, remplace le
marqueur par 1 à 3 phrases décrivant ce qui a été fait à ce tour.

**Sources autorisées, et elles seules :**

- le commentaire `<!-- RÉPONSE ENREGISTRÉE ... -->` juste au-dessus du marqueur ;
- la liste **Actions journalisées** du même tour.

**Interdit :** t'appuyer sur la conversation en cours, sur ta mémoire de la
séance, ou sur ce que tu sais du projet. Le journal est la seule source. Si un
tour n'a ni réponse enregistrée ni action, écris
`*Aucune trace exploitable dans le journal pour ce tour.*` et passe au suivant.

Laisse les commentaires `<!-- RÉPONSE ENREGISTRÉE -->` en place : ils sont
invisibles dans le rendu et servent de justificatif.

## 3. Ne jamais toucher aux prompts

Les blocs **Prompt (verbatim)** sont la raison d'être de ce rapport.

- Ne les reformule pas.
- Ne corrige ni l'orthographe, ni la grammaire, ni la ponctuation, ni la casse.
- Ne les complète pas, ne les abrège pas, ne les traduis pas.
- Ne les réordonne pas.

Un prompt maladroit, fautif ou incomplet reste **exactement** tel quel. Si tu es
tenté d'y toucher, ne le fais pas : un prompt retouché rend tout le rapport
irrecevable. Ne modifie que les marqueurs de résumé, rien d'autre.

## 4. Vérifier avant de rendre

- Plus aucun `<!-- RÉSUMÉ À RÉDIGER -->` dans le fichier.
- Les prompts sont identiques à ceux du squelette produit à l'étape 1.
- La section **Note méthodologique** est présente en fin de document (le script
  l'écrit ; si elle manque, remets-la).

Puis annonce le chemin du rapport et rappelle deux choses à l'étudiant : relire
le rapport avant de le remettre, et vérifier le format attendu par
l'établissement.
