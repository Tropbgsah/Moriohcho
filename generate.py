"""Morioh-cho Radio : actu -> script (Gemini gratuit) -> voix (edge-tts) -> mix ffmpeg."""
import os, json, subprocess, datetime, asyncio, pathlib, requests, feedparser

MODEL = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")
VOICE = os.getenv("TTS_VOICE", "fr-FR-HenriNeural")
DUCK_AT, VOICE_AT, MUSIC_LOW = 8.0, 8.6, 0.14   # le son baisse à 8 s
OUT = pathlib.Path("site"); OUT.mkdir(exist_ok=True)
FEEDS = {
 "une": ["https://www.francetvinfo.fr/titres.rss", "https://www.lemonde.fr/rss/une.xml",
         "https://news.google.com/rss?hl=fr&gl=FR&ceid=FR:fr"],
 "insolite": ["https://news.google.com/rss/search?q=insolite&hl=fr&gl=FR&ceid=FR:fr"],
}

def headlines(urls, n=12):
    out = []
    for u in urls:
        try:
            out += [e.title for e in feedparser.parse(u).entries[:n]]
        except Exception as e:
            print("flux ignoré", u, e)
    return out

def write_script():
    today = datetime.date.today().strftime("%A %d %B %Y")
    prompt = f"""Tu es l'animateur de "Morioh-cho Radio", une radio de réveil énergique, drôle et un peu excentrique.
Nous sommes le {today}. Écris l'émission du matin (environ 450 mots, à dire à voix haute), en français, dans cet ordre :
1) accroche courte ; 2) LE GROS TITRE du jour (choisis dans la liste "une") bien expliqué : contexte, enjeu, pourquoi c'est important ;
3) "Les news de merde" : 3 infos absurdes ou futiles (choisis dans la liste "insolite"), traitées avec second degré ;
4) une anecdote vraie et vérifiable (histoire, science, culture) ; 5) le mot du jour : un mot peu courant, sa définition, un exemple ; 6) conclusion motivante pour bien démarrer.
Règles : uniquement du texte parlé, sans markdown, sans didascalies, n'invente aucun fait d'actualité hors des titres fournis.
LISTE une : {json.dumps(headlines(FEEDS['une']), ensure_ascii=False)}
LISTE insolite : {json.dumps(headlines(FEEDS['insolite']), ensure_ascii=False)}
Réponds en JSON : {{"titre": "le gros titre en une phrase", "script": "le texte complet"}}"""
    r = requests.post(
        f"https://generativelanguage.googleapis.com/v1beta/models/{MODEL}:generateContent",
        headers={"x-goog-api-key": os.environ["GEMINI_API_KEY"]},
        json={"contents": [{"parts": [{"text": prompt}]}],
              "generationConfig": {"responseMimeType": "application/json"}}, timeout=120)
    r.raise_for_status()
    return json.loads(r.json()["candidates"][0]["content"]["parts"][0]["text"])

def tts(text, path):
    try:
        import edge_tts
        asyncio.run(edge_tts.Communicate(text, VOICE, rate="+4%").save(str(path)))
    except Exception as e:
        print("edge-tts KO, repli gTTS:", e)
        from gtts import gTTS
        gTTS(text, lang="fr").save(str(path))

def duration(p):
    return float(subprocess.check_output(["ffprobe", "-v", "error", "-show_entries", "format=duration",
                                          "-of", "csv=p=0", str(p)]))

def mix(voice, jingle, dest):
    total = VOICE_AT + duration(voice) + 4
    graph = (f"[0:a]volume='{MUSIC_LOW}+{1-MUSIC_LOW}*clip({DUCK_AT+1}-t,0,1)':eval=frame[m];"
             f"[1:a]aformat=channel_layouts=stereo,adelay={int(VOICE_AT*1000)}|{int(VOICE_AT*1000)}[v];"
             f"[m][v]amix=inputs=2:duration=longest:dropout_transition=0,volume=2,"
             f"alimiter=limit=0.95,afade=t=out:st={total-4:.2f}:d=4[o]")
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-stream_loop", "-1", "-i", str(jingle), "-i", str(voice),
                    "-filter_complex", graph, "-map", "[o]", "-t", f"{total:.2f}", "-ac", "2",
                    "-b:a", "96k", str(dest)], check=True)
    return total

if __name__ == "__main__":
    ep = write_script()
    voice = OUT / "voice.mp3"
    tts(ep["script"], voice)
    total = mix(voice, "assets/jingle.mp3", OUT / "latest.mp3")
    voice.unlink()
    (OUT / "episode.json").write_text(json.dumps({
        "date": datetime.date.today().isoformat(), "titre": ep["titre"],
        "script": ep["script"], "duree": round(total)}, ensure_ascii=False, indent=1), encoding="utf-8")
    print("OK", ep["titre"])
