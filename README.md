# Journal IA pour Claude Code

Kit prêt à déposer dans un projet scolaire : il journalise automatiquement ce que
tu demandes à Claude Code et ce que Claude fait, puis transforme ce journal en
rapport de documentation d'usage de l'IA.

---

## 1. À quoi ça sert

Beaucoup d'écoles autorisent l'IA à condition que son usage soit documenté.
Documenter à la main est fastidieux, et se reconstituer de mémoire la veille du
rendu ne produit rien de fiable. Ce kit écrit le journal pendant que tu
travailles, sans que tu y penses, et le met en forme quand tu le demandes.

---

## 2. Ce qui est capturé

Trois types de lignes, une par ligne, dans `.claude/journal-ia/journal.jsonl` :

| Type | Quand | Contenu | Fidélité |
|---|---|---|---|
| `prompt` | à chaque message que tu envoies | ton texte **mot pour mot** | verbatim, jamais tronqué ni corrigé |
| `response` | à la fin de chaque tour | le message final de Claude | tronqué à 2000 caractères |
| `action` | à chaque fichier écrit ou commande lancée | le fichier (créé / modifié) ou la commande | commande tronquée à 80 caractères |

Extrait réel (`exemples/journal-exemple.jsonl`, mis en forme ici pour la
lisibilité — dans le fichier, chaque entrée tient sur une seule ligne) :

```json
{"ts":"2026-03-12T13:04:18Z","session":"7f3a9c12-…","type":"prompt","text":"Crée un projet console en C# qui calcule la moyenne d'une liste de notes. On est en .NET 8. Appelle le projet MoyenneNotes."}
{"ts":"2026-03-12T13:04:41Z","session":"7f3a9c12-…","type":"action","tool":"Bash","target":"dotnet new console -n MoyenneNotes -f net8.0","state":"run"}
{"ts":"2026-03-12T13:04:52Z","session":"7f3a9c12-…","type":"action","tool":"Write","target":"MoyenneNotes/Program.cs","state":"created"}
{"ts":"2026-03-12T13:05:03Z","session":"7f3a9c12-…","type":"response","text":"J'ai créé le projet `MoyenneNotes` avec…","truncated":false}
```

**Pourquoi la réponse est tronquée et pas le prompt.** Le prompt est la pièce
qui compte : c'est lui qui montre ce que tu as demandé, et il est copié
mécaniquement, sans aucune retouche. La réponse ne sert qu'à écrire le résumé du
tour ; 2000 caractères suffisent, et un journal qui contient l'intégralité des
réponses devient illisible en une séance. Le champ `truncated` dit quand la
coupe a eu lieu.

**Ce qui n'est pas journalisé :** les commandes de simple consultation
(`ls`, `cat`, `git status`, `git log`, `git diff`, `git show`, `grep`, `find`,
`head`, `tail`, `pwd`, `echo`, `which`, `wc`, `cd`, `sed`, `awk`). Sans ce
filtre, les actions réelles seraient noyées dans du bruit. La liste est en haut
de `.claude/hooks/log_action.py` et se modifie — voir les limitations.

---

## 3. Prérequis

| Outil | Nécessaire | Remarque |
|---|---|---|
| **Claude Code** ≥ 2.1.196 | oui | `claude --version`. Les versions antérieures ne substituent pas `${CLAUDE_PROJECT_DIR}` dans un skill. |
| **Python 3** | oui | `python3 --version`. Seul runtime du kit : il fait la journalisation *et* le rapport. |
| **Git** | non | Sans git, le journal note « touché » au lieu de « créé »/« modifié ». Tout le reste fonctionne. |

Les hooks sont écrits en Python, pas en shell : ils tournent à l'identique sur
**Linux, macOS et Windows**. Aucune bibliothèque à installer, aucun accès réseau.

Sous Windows, Git Bash n'est nécessaire que si tu veux lancer `install.sh` ;
`install.ps1` fait exactement la même chose en PowerShell.

---

## 4. Installation dans un nouveau projet

Deux chemins à compléter, à toi de choisir où :

| Placeholder | Ce que tu mets à la place |
|---|---|
| `CHEMIN_DU_KIT` | où tu ranges le kit, une fois pour toutes (il ne bouge plus ensuite) |
| `CHEMIN_DU_PROJET` | le dossier du travail scolaire à journaliser, qui doit déjà exister |

Rien n'est supposé de ton arborescence : le kit n'écrit jamais dans ton dossier
personnel de sa propre initiative, et l'installeur refuse de démarrer si
`CHEMIN_DU_PROJET` n'existe pas encore, plutôt que de le créer au hasard.

**Linux, macOS, ou Windows avec Git Bash :**

```bash
git clone https://github.com/PL4Y3R51/journal-ia-claude-code CHEMIN_DU_KIT
CHEMIN_DU_KIT/install.sh CHEMIN_DU_PROJET
cd CHEMIN_DU_PROJET && claude
```

**Windows, PowerShell :**

```powershell
git clone https://github.com/PL4Y3R51/journal-ia-claude-code CHEMIN_DU_KIT
& CHEMIN_DU_KIT\install.ps1 CHEMIN_DU_PROJET
cd CHEMIN_DU_PROJET ; claude
```

Si PowerShell refuse d'exécuter le script :

```powershell
powershell -ExecutionPolicy Bypass -File CHEMIN_DU_KIT\install.ps1 CHEMIN_DU_PROJET
```

<details>
<summary>Exemple complet, si tu veux voir à quoi ça ressemble rempli</summary>

```bash
git clone https://github.com/PL4Y3R51/journal-ia-claude-code ~/outils/journal-ia
~/outils/journal-ia/install.sh ~/cours/projet-csharp
cd ~/cours/projet-csharp && claude
```

```powershell
git clone https://github.com/PL4Y3R51/journal-ia-claude-code D:\outils\journal-ia
& D:\outils\journal-ia\install.ps1 D:\cours\projet-csharp
cd D:\cours\projet-csharp ; claude
```

</details>

Tu peux aussi te placer dans le dossier du kit et installer avec des chemins
relatifs, si tu préfères :

```bash
cd CHEMIN_DU_KIT
./install.sh ../mon-projet
```

L'installeur vérifie les prérequis, copie `.claude/`, prépare le dossier de
journal, puis fait tourner un hook à blanc pour confirmer qu'il écrit vraiment.
Il ne touche rien en dehors du dossier que tu lui indiques. Le lancer deux fois
ne casse rien.

**Si le projet a déjà un `.claude/settings.json`**, l'installeur ne l'écrase
pas : il affiche le bloc `hooks` à recopier et s'arrête. Fusionne à la main, puis
relance.

Au premier `claude` dans le dossier, accepte le dialogue de confiance de
l'espace de travail : sans lui, le skill `/rapport-ia` ne peut pas s'exécuter
sans demander une permission à chaque étape.

---

## 5. Vérifier que ça marche

1. Dans Claude Code, tape `/hooks`. Tu dois voir trois entrées sous
   **Project Settings** : `UserPromptSubmit`, `Stop` et `PostToolUse`.
2. Envoie un prompt quelconque, par exemple « bonjour ».
3. Vérifie que le journal a grossi :

```bash
wc -l .claude/journal-ia/journal.jsonl
```

```powershell
Get-Content .claude\journal-ia\journal.jsonl | Measure-Object -Line
```

Si le compte reste à zéro, regarde `.claude/journal-ia/errors.log` : le kit y
écrit ses pannes, une fois par message d'erreur.

---

## 6. Activer / désactiver

**La présence de `.claude/settings.json` dans le dossier *est* l'interrupteur.**
Rien n'est installé globalement, et aucun autre projet de ta machine n'est
affecté. Les hooks ne tournent que dans les dossiers où tu as lancé
l'installeur.

- **Désinstaller** : supprime `.claude/hooks/`, `.claude/skills/rapport-ia/` et
  le bloc `hooks` de `.claude/settings.json`. Le journal déjà écrit reste.
- **Couper temporairement**, sans rien supprimer : ajoute
  `"disableAllHooks": true` dans `.claude/settings.json`, puis retire-le pour
  réactiver.
- **Une seule séance** hors journal : travaille dans un autre dossier.

---

## 7. Générer le rapport

Dans Claude Code, en fin de séance ou de projet :

```
/rapport-ia
```

Le rapport atterrit dans `rapports/rapport-ia-<date>.md`, à la racine du projet.
Un argument facultatif restreint la portée : `/rapport-ia last` pour la dernière
séance seulement, `/rapport-ia <identifiant>` pour une séance précise.

Le squelette est produit par un script Python qui ne fait que copier et compter ;
c'est ensuite Claude qui rédige les résultats, à partir des réponses enregistrées
dans le journal et de rien d'autre.

**Ce que contient le rapport rendu.** Pour chaque tour : le prompt verbatim, puis
un **Résultat** d'une à deux phrases disant ce que la demande a produit, puis la
liste des fichiers et commandes. Les réponses complètes de Claude n'y figurent
pas — elles restent dans `journal.jsonl`. C'est voulu : le rapport est le
document qu'on lit, le journal est la pièce qu'on produit si on demande le
détail. Les deux se remettent ensemble.

Le skill génère le squelette avec les réponses jointes en commentaires
invisibles, s'en sert pour rédiger, puis les retire :

```bash
python3 .claude/skills/rapport-ia/scripts/build-report.py --nettoyer rapports/rapport-ia-2026-03-12.md
```

Ce nettoyage refuse de tourner s'il reste des résumés à écrire, et il suit les
clôtures de blocs de code : un prompt qui contiendrait lui-même le texte d'un
commentaire n'est pas touché.

Regarde `exemples/rapport-exemple.md` pour voir le rendu attendu.

**Conversion en Word**, si ton école le demande — optionnel, nécessite
[pandoc](https://pandoc.org/installing.html) :

```bash
pandoc rapports/rapport-ia-2026-03-12.md -o rapport.docx
```

**Génération hors Claude Code**, si tu veux seulement le squelette :

```bash
python3 .claude/skills/rapport-ia/scripts/build-report.py --sortie auto
```

Options : `--session <id|last|all>`, `--depuis AAAA-MM-JJ`, `--sortie <fichier>`,
`--avec-reponses` (joindre les réponses en commentaires), `--nettoyer <rapport>`
(les retirer d'un rapport déjà rédigé).

---

## 8. Limitations

Un outil de traçabilité qui surpromet est un outil qui se retourne contre son
utilisateur le jour d'une contestation. Lis cette section avant de t'appuyer sur
le kit.

- **Claude Code uniquement.** Rien n'est capturé sur claude.ai, l'application
  mobile, Cowork, ou les sessions cloud : les hooks n'y existent pas. Un projet
  mené moitié en web, moitié en CLI aura un journal partiel — et un journal
  partiel présenté comme complet est un problème d'honnêteté, pas un problème
  technique.
- **Aucune capture rétroactive.** Les hooks ne s'appliquent qu'aux sessions
  démarrées après l'installation. Installe le kit *avant* de commencer à
  travailler.
- **Les autres outils d'IA ne sont pas tracés.** ChatGPT, Copilot, Gemini, un
  collègue : rien. Le journal documente l'usage de Claude Code, pas l'usage de
  l'IA en général.
- **Le journal est un fichier texte modifiable.** Ce n'est pas une preuve
  infalsifiable, c'est un registre de bonne foi. Pour le renforcer : commite le
  journal à chaque fin de séance. La chaîne de hachage Git et les horodatages
  rendent une réécriture *a posteriori* détectable.
- **`last_assistant_message` ne contient que le message final du tour**, pas les
  étapes intermédiaires ni le raisonnement.
- **Le filtrage des commandes de lecture seule est un choix délibéré.** La liste
  est en haut de `.claude/hooks/log_action.py` et se modifie ; si tu la changes,
  dis-le dans le rapport, dont le pied de page déclare ce filtrage. Le filtre
  n'examine que le premier mot de la commande : `sed -i` ou
  `awk … > fichier` écrivent vraiment et passent quand même à travers.
- **Les résultats sont résumés par un LLM** et peuvent être imprécis ou
  incomplets. Seuls les prompts sont garantis mot pour mot, parce qu'ils sont
  copiés mécaniquement. Le rapport distingue visuellement les deux.
- **Le rapport ne contient pas les réponses complètes.** Un résultat de deux
  phrases n'est pas vérifiable depuis le rapport seul : c'est le journal qui
  permet de le contrôler. Remets les deux si on te demande de justifier, et ne
  présente jamais le rapport comme se suffisant à lui-même. `--avec-reponses`
  sans nettoyage final produit un rapport qui les conserve, si tu préfères un
  document autoportant.
- **Hooks asynchrones** : ils tournent en arrière-plan pour ne jamais ralentir
  ta session. En cas de crash du terminal, une ligne peut manquer. Le transcript
  JSONL interne de Claude Code (`~/.claude/projects/…`) sert de filet de secours
  indépendant.
- **Créé ou modifié n'est pas toujours décidable.** L'état vient de
  `git status --porcelain`. Hors dépôt Git, sans git installé, ou pour un fichier
  ignoré par `.gitignore`, le journal note `unknown` et le rapport dit
  simplement « touché » plutôt que d'inventer.
- **Vie privée.** Le journal contient l'intégralité de ce que tu as tapé.
  Relis-le avant de le pousser sur un dépôt public ou de le remettre à un tiers.
- **Travail en groupe** : plusieurs personnes sur le même dossier produisent un
  journal entremêlé. Le champ `session` permet de démêler, mais rien n'identifie
  l'auteur.
- **Ce kit ne remplace pas les règles de ton établissement.** Vérifie le format
  attendu avant de t'appuyer dessus, et adapte le gabarit si nécessaire.

---

## 9. Conseils d'usage scolaire

- Installe le kit au premier commit du projet, pas la veille du rendu.
- Commite `journal.jsonl` à chaque séance : l'horodatage Git corrobore le
  journal. Le `.gitignore` de *ce dépôt* exclut les journaux réels, mais rien
  n'exclut le tien dans *ton* projet — c'est voulu.
- Fais valider `exemples/rapport-exemple.md` par ton enseignant **avant** de
  t'engager sur le format.
- Garde le pied de page méthodologique, que le script écrit automatiquement :

  > Ce rapport est généré à partir d'un journal horodaté écrit automatiquement à
  > chaque interaction. Les prompts sont reproduits littéralement depuis ce
  > journal. Les résultats sont résumés par Claude à partir des réponses
  > enregistrées. Les commandes de consultation en lecture seule ne sont pas
  > journalisées.
  >
  > Les réponses complètes dont ces résumés sont tirés ne figurent pas dans ce
  > document : elles restent dans le journal, qui les conserve intégralement.

- Relis le rapport avant de le rendre. C'est toi qui le signes.

---

## 10. Licence et contribution

MIT — voir [LICENSE](LICENSE). Copie, modifie et partage librement, y compris
dans le cadre de l'école.

### Structure du dépôt

```
kit/.claude/            le gabarit copié dans ton projet (inactif ici)
  settings.json         déclare les 3 hooks
  hooks/                journal_lib.py + les 3 hooks Python
  skills/rapport-ia/    le skill /rapport-ia et son script d'agrégation
exemples/               un journal réaliste et le rapport correspondant
install.sh              installeur Linux / macOS / Git Bash
install.ps1             installeur Windows PowerShell
```

### Ce qui a été vérifié

Ces comportements ont été testés automatiquement sous Windows, en appelant les
hooks exactement comme Claude Code les appelle : capture verbatim d'un prompt
contenant guillemets, antislash, sauts de ligne, emoji et accents ; sortie en
code 0 sur toute entrée dégradée, journal en lecture seule, git absent et
interpréteur absent ; `créé` puis `modifié` sur un fichier réécrit ; filtre de
lecture seule ; dégradation en `unknown` hors dépôt Git ; deux séances
simultanées écrivant 100 lignes sans corruption ; et concordance entre le
rapport généré et `exemples/rapport-exemple.md`.

Deux points restent à contrôler à l'œil, parce qu'ils demandent une vraie
session : l'affichage des trois hooks dans `/hooks`, et le rendu de
`/rapport-ia` de bout en bout. La section 5 les couvre.

### Contribuer

Les corrections utiles : élargir le filtre de lecture seule, améliorer la
détection créé/modifié, adapter le gabarit de rapport à d'autres formats
d'établissement. Merci de ne pas proposer d'envoi du journal vers un service
distant, de chiffrement (qui promettrait une infalsifiabilité inexistante), ni
de capture du raisonnement interne du modèle.
