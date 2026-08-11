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
python3 ${CLAUDE_SKILL_DIR}/scripts/build-report.py --session all --avec-reponses --sortie auto
```

`--avec-reponses` joint à chaque tour la réponse enregistrée, en commentaire
invisible : c'est ta matière de travail pour l'étape 2. L'étape 4 la retirera.

Le script écrit `rapports/rapport-ia-<date>.md` et affiche le chemin. Il agrège
seulement : il ne résume rien. Si le journal est introuvable ou vide, dis-le et
arrête-toi — ne fabrique pas de rapport.

## 2. Remplir les résultats

Lis le fichier produit. Pour chaque `<!-- RÉSUMÉ À RÉDIGER -->`, remplace le
marqueur par **une à deux phrases** disant ce que la demande a produit.

Écris le **résultat**, pas la démarche. La question à laquelle ces phrases
répondent : qu'est-ce qui existe, fonctionne ou a changé après ce tour, qui
n'existait pas avant ? Un fichier créé, un bug corrigé, des tests qui passent,
une question tranchée sans rien modifier.

- Pas de récit d'étapes (« j'ai d'abord…, puis…, ensuite… »).
- Deux phrases au maximum : le détail est déjà dans **Actions journalisées**.
- Si le tour n'a rien produit — question, exploration, refus — dis-le en une
  phrase, sans le gonfler.

**Sources autorisées, et elles seules :**

- le commentaire `<!-- RÉPONSE ENREGISTRÉE ... -->` en fin de bloc du tour ;
- la liste **Actions journalisées** du même tour.

**Interdit :** t'appuyer sur la conversation en cours, sur ta mémoire de la
séance, ou sur ce que tu sais du projet. Le journal est la seule source. Si un
tour n'a ni réponse enregistrée ni action, écris
`*Aucune trace exploitable dans le journal pour ce tour.*` et passe au suivant.

## 3. Ne jamais toucher aux prompts

Les blocs **Prompt (verbatim)** sont la raison d'être de ce rapport.

- Ne les reformule pas.
- Ne corrige ni l'orthographe, ni la grammaire, ni la ponctuation, ni la casse.
- Ne les complète pas, ne les abrège pas, ne les traduis pas.
- Ne les réordonne pas.

Un prompt maladroit, fautif ou incomplet reste **exactement** tel quel. Si tu es
tenté d'y toucher, ne le fais pas : un prompt retouché rend tout le rapport
irrecevable. Ne modifie que les marqueurs de résumé, rien d'autre.

## 4. Retirer les réponses complètes

Une fois tous les résultats rédigés :

```bash
python3 ${CLAUDE_SKILL_DIR}/scripts/build-report.py --nettoyer rapports/rapport-ia-<date>.md
```

Le script retire les commentaires de réponse et aligne la note méthodologique
sur ce que le document contient désormais. Il refuse de tourner s'il reste un
marqueur : dans ce cas, termine l'étape 2 d'abord.

Ne retire jamais ces commentaires à la main. Le script suit les clôtures de blocs
de code, donc il ne touche pas un prompt qui contiendrait lui-même ce texte ; un
effacement manuel, lui, peut mutiler un verbatim.

Le rapport remis ne contient donc que les résultats. Les réponses complètes
restent dans `journal.jsonl`, qui fait foi si on les demande.

## 5. Vérifier avant de rendre

- Plus aucun `<!-- RÉSUMÉ À RÉDIGER -->` dans le fichier.
- Plus aucun `<!-- RÉPONSE ENREGISTRÉE ... -->` (l'étape 4 les a retirés).
- Chaque **Résultat** tient en une ou deux phrases et dit ce qui a été produit.
- Les prompts sont identiques à ceux du squelette produit à l'étape 1.
- La section **Note méthodologique** est présente en fin de document, et sa
  dernière phrase dit bien que les réponses complètes ne figurent pas ici.

Puis annonce le chemin du rapport et rappelle deux choses à l'étudiant : relire
le rapport avant de le remettre, et vérifier le format attendu par
l'établissement.
