# Vidéo voix quotidienne Datenshi (TikTok, 19h)

Chaque jour : un script → voix ElevenLabs → motion design HTML synchronisé mot à mot → publication TikTok à 19h (Paris) via Metricool.
Higgsfield n'est jamais utilisé.

## Fichiers
- `motion.html` : moteur de motion design (1080x1920). `setup(cfg)` puis `render(t)`.
- `sfx.py` : sound design synthétisé (nappe sombre, whoosh, impacts, cloche…), calé sur les événements de la vidéo.
- `build.py` : rendu.
  - `python3 tools/voice/build.py SPEC.json DOSSIER --stills` → `DOSSIER/contact.jpg` (planche de contrôle)
  - `python3 tools/voice/build.py SPEC.json DOSSIER --voice voice.mp3` → `DOSSIER/ID.mp4` (vidéo finale, -14 LUFS)
- `specs/AAAA-MM-JJ.json` : une spec par jour (script, voix, mots, scènes). Lire les anciennes pour ne pas répéter les accroches.

## Réglages fixes
- Voix ElevenLabs : Corentin, `voice_id` `IHngRooVccHyPqB4uQkG`, modèle `eleven_v4`, `generations_count` 1.
- Transcription (timings mot à mot) : `creative_transcribe_audio`, modèle `eleven_scribe_v1`, `connect_from` = nœud de la voix.
- Metricool : `blogId` `7784021` (TikTok userrr_4837), fuseau `Europe/Paris`.

## Script (français, 14 à 22 s, 40 à 60 mots)
Structure : accroche (un agacement réel avec les IA classiques : morale, refus, réponses tièdes) → rupture → « Datenshi, c'est l'IA sans censure » → 2-3 bénéfices concrets (code, analyse, création, avis franc…) → « dès un euro par mois » → fin **toujours** : « Datenshi. Le lien est en bio. »
- Phrases courtes, ton TikTok direct. Varier l'accroche chaque jour.
- Exemples de demandes inoffensifs (avis franc, roast, business plan, fiction sombre, débat…). Jamais de contenu illégal ou dangereux.
- Ne jamais nommer de concurrent. Prix exact : forfait Small à 1 €/mois. Ne rien promettre d'autre que ce qui est sur datenshi.fr.

## Spec
```json
{ "id": "AAAA-MM-JJ", "seed": 1234, "acc": "#ff2b4a", "acc2": "#8f5bff", "lead": 0.3, "tail": 1.8,
  "script": "...", "voice": {...}, "caption": "lien en bio #ia #sanscensure #datenshi ... ",
  "words": [{"text": "Tu", "start": 0.0, "end": 0.16}, ...],   // = entrées "word" de la transcription, dans l'ordre
  "scenes": [ ... ] }
```
`from`/`to`/`at`/... sont des **index de mots** (0 = premier mot). Une scène commence au mot `from` et dure jusqu'à la suivante ; enchaîner les scènes sans trou, la première commence au mot 0, la dernière (`cta`) finit au dernier mot.

Types de scènes :
| type | paramètres | usage |
|---|---|---|
| `chat` | `ask`, `lecture`, `lectureAt`, `punchAt`, `warnings[]`, `botName` | une « IA classique » générique fait la morale ; sous-titres karaoké |
| `flood` | `text`, `count`, `texts[]` | l'écran se remplit de refus génériques + un mot géant |
| `stamp` | `text`, `sub`, `bg` | un mot qui claque (STOP., NON., ASSEZ.) |
| `brand` | `tagAt`, `ripAt`, `tagPre`, `tag` | 堕天使 + DATENSHI ; la barre « CENSURÉ » est arrachée au mot `ripAt` |
| `slam` | `items[{text, at}]`, `captions` | 2-4 formules empilées qui claquent sur leurs mots |
| `features` | `cards[{icon, label, at}]` (icônes : code, chart, spark, pen, chat, bolt) | 2-3 cartes animées |
| `price` | `pre`, `price`, `per`, `landAt`, `perAt` | compteur qui tombe sur 1€ |
| `cta` | `pill`, `url` | logo + LIEN EN BIO + datenshi.fr |
| `words` | `hl[]` (index à mettre en couleur), `size`, `y` | typo cinétique générique mot à mot |

Varier chaque jour : ordre et choix des scènes, `acc`/`acc2` (couleurs vives sur fond noir), `seed`. Toujours `brand` tôt et `cta` à la fin.

## Pièges connus
- Les fichiers ElevenLabs (`elevenlabsusercontent.com`) doivent être téléchargeables depuis l'espace de travail : domaine à autoriser dans claude.ai → Paramètres → Capacités.
- Ne jamais relancer une génération ElevenLabs pour « réessayer » (chaque appel est facturé).
- Après `--stills`, regarder `contact.jpg` : aucun texte ne doit déborder ni passer sous les boutons TikTok (bas de l'écran, bord droit).
