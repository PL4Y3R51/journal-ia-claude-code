# Rapport d'usage de l'IA

| | |
|---|---|
| Journal source | `exemples/journal-exemple.jsonl` |
| Généré le | 2026-03-12 13:41 |
| Séances | 1 |
| Tours | 5 |
| Actions journalisées | 12 |

**Comment lire ce rapport.** Chaque tour donne d'abord le *Prompt*, copié mot pour mot depuis le journal — aucune correction d'orthographe ni de formulation —, puis le *Résultat* : une ou deux phrases disant ce que la demande a produit. Les *Actions journalisées* détaillent ensuite les fichiers touchés et les commandes lancées. Seuls les prompts sont garantis littéraux ; les résultats sont rédigés par Claude et peuvent être imprécis.

---

## Séance 1

- Identifiant de séance : `7f3a9c12-4b8e-4d21-9a76-2e5c81df0b44`
- Première entrée : 2026-03-12T13:04:18Z
- Dernière entrée : 2026-03-12T13:35:09Z
- Tours : 5

### Séance 1, tour 1 — 2026-03-12T13:04:18Z

**Prompt (verbatim)**

```text
Crée un projet console en C# qui calcule la moyenne d'une liste de notes. On est en .NET 8. Appelle le projet MoyenneNotes.
```

**Résultat**

Le projet console `MoyenneNotes` existe et tourne : il calcule la moyenne
d'un tableau de notes codé en dur et l'affiche à deux décimales.

**Actions journalisées**

- commande `dotnet new console -n MoyenneNotes -f net8.0`
- `MoyenneNotes/Program.cs` créé

### Séance 1, tour 2 — 2026-03-12T13:09:27Z

**Prompt (verbatim)**

```text
il faut que le programme demande les notes à l'utilisateur au clavier au lieu de les avoir en dur. il s'arrête quand on tape une ligne vide
```

**Résultat**

Le programme lit désormais les notes au clavier et s'arrête sur une ligne
vide ; le cas « aucune note saisie » est traité au lieu de diviser par zéro.
La compilation passe sans avertissement.

**Actions journalisées**

- `MoyenneNotes/Program.cs` modifié
- commande `dotnet build MoyenneNotes`

### Séance 1, tour 3 — 2026-03-12T13:16:05Z

**Prompt (verbatim)**

```text
j'ai une FormatException quand je tape 4,5 avec une virgule alors que 4.5 marche. corrige ça, chez moi c'est un clavier suisse
```

**Résultat**

Le bug de saisie signalé est corrigé : `4,5` et `4.5` sont tous deux
acceptés, la conversion étant forcée sur `CultureInfo.InvariantCulture`. Les
saisies réellement invalides restent rejetées.

**Actions journalisées**

- `MoyenneNotes/Program.cs` modifié (×2)

### Séance 1, tour 4 — 2026-03-12T13:24:39Z

**Prompt (verbatim)**

```text
mets une classe Note dans un fichier séparé, avec une validation : une note doit être entre 1 et 6, sinon exception
```

**Résultat**

La validation des notes existe : `Models/Note.cs` refuse toute valeur hors de
l'intervalle [1, 6], et la saisie continue au lieu de s'interrompre quand une
note est refusée.

**Actions journalisées**

- `MoyenneNotes/Models/Note.cs` créé
- `MoyenneNotes/Program.cs` modifié
- commande `dotnet run --project MoyenneNotes`

### Séance 1, tour 5 — 2026-03-12T13:33:20Z

**Prompt (verbatim)**

```text
écris des tests unitaires pour la validation de Note (cas limites 1 et 6 inclus, et 0.9 / 6.1 qui doivent échouer)
```

**Résultat**

La validation est couverte par des tests : 5 tests xUnit passent, dont les
bornes 1 et 6 acceptées et 0.9 / 6.1 rejetées.

**Actions journalisées**

- commande `dotnet new xunit -n MoyenneNotes.Tests`
- `MoyenneNotes.Tests/NoteTests.cs` créé
- commande `dotnet test MoyenneNotes.Tests`

---

## Note méthodologique

Ce rapport est généré à partir d'un journal horodaté écrit automatiquement à
chaque interaction. Les prompts sont reproduits littéralement depuis ce journal.
Les résultats sont résumés par Claude à partir des réponses enregistrées. Les
commandes de consultation en lecture seule ne sont pas journalisées.

Les réponses complètes dont ces résumés sont tirés ne figurent pas dans ce
document : elles restent dans le journal, qui les conserve intégralement.

