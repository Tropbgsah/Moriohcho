# Morioh-cho Radio — réveil IA 100 % gratuit

Chaque matin, GitHub Actions : lit l'actu (RSS) → Gemini écrit l'émission → voix edge-tts → ffmpeg mixe avec ton jingle
(volume plein jusqu'à 8 s, puis la musique baisse et la voix démarre) → publie sur GitHub Pages.

## Installation (10 min, une seule fois)
1. Crée un dépôt **public** sur GitHub et envoie-y tout ce dossier (garde `assets/jingle.mp3`).
2. Clé gratuite : https://aistudio.google.com/apikey → dépôt > Settings > Secrets and variables > Actions > **New secret** `GEMINI_API_KEY`.
3. Settings > Pages > Source : **GitHub Actions**.
4. Onglet Actions > « Morioh-cho Radio » > **Run workflow** (premier test). Ton site : `https://TON-PSEUDO.github.io/NOM-DU-DEPOT/`.

Ensuite tout tourne seul chaque jour (~5-6 h, heure FR). Ajuste l'heure dans `daily.yml` (cron en UTC).

## Le réveil
- **Page web** : choisis l'heure, « Armer le réveil », laisse l'onglet ouvert + écran allumé + téléphone branché.
  Un navigateur ne peut pas sonner s'il est fermé ou en veille : c'est la limite du web.
- **Fiable (conseillé)** — iPhone : Raccourcis > Automatisation > Heure du jour > actions « Obtenir le contenu de l'URL » (`.../latest.mp3`) puis « Lire le son ».
  Android : MacroDroid ou Tasker, déclencheur heure → lire l'URL du mp3. Ça sonne téléphone verrouillé.

## Réglages (variables dans `generate.py`)
`DUCK_AT` (8 s), `MUSIC_LOW` (volume de la musique sous la voix), `TTS_VOICE` (ex. `fr-FR-DeniseNeural`), flux dans `FEEDS`.
Si le modèle Gemini change de nom : variable d'env `GEMINI_MODEL`.
