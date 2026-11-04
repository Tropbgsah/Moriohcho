"""Morioh-cho Radio : actu -> script (Gemini) -> voix (Gemini TTS, repli edge-tts) -> mix ffmpeg."""
import os, re, json, base64, wave, subprocess, datetime, asyncio, pathlib, time, requests, feedparser

KEY = os.environ.get("GEMINI_API_KEY", "")
API = "https://generativelanguage.googleapis.com/v1beta/models/{}:generateContent"
MODELS = [os.getenv("GEMINI_MODEL", "gemini-3.8-flash"), "gemini-3.6-flash", "gemini-3.5-flash-lite"] * 4
TTS_MODELS = ["gemini-3.8-flash-tts", "gemini-3.8-flash-lite-tts"] * 3
GEMINI_VOICE = os.getenv("GEMINI_VOICE", "Puck")
EDGE_VOICE = os.getenv("TTS_VOICE", "fr-FR-RemyMultilingualNeural")
DUCK_AT, VOICE_AT, MUSIC_LOW = 8.0, 8.6, 0.14   # intro 8 s à fond, puis la musique baisse et boucle
OUT = pathlib.Path("site"); OUT.mkdir(exist_ok=True)
FEEDS = {
 "une": ["https://www.francetvinfo.fr/titres.rss", "https://www.lemonde.fr/rss/une.xml",
         "https://news.google.com/rss?hl=fr&gl=FR&ceid=FR:fr"],
 "insolite": ["https://news.google.com/rss/search?q=insolite&hl=fr&gl=FR&ceid=FR:fr"],
}
INTRO = ("Good morning ! Bonjour à tous. Ici Morioh Cho Radio, et votre animateur, une fois de plus, "
         "c'est moi, votre voisin, Kéï Harada. Quel beau matin ! "
         "Et j'ai la news parfaite pour bien commencer la journée. ")
STYLE = ("Parle en français, avec une voix d'homme cool, naturelle et décontractée, énergique comme un "
         "animateur radio du matin, avec le sourire dans la voix, un rythme vif et vivant, jamais robotique. "
         "Dis ce texte : ")
JOURS = ["lundi", "mardi", "mercredi", "jeudi", "vendredi", "samedi", "dimanche"]
MOIS = ["janvier", "février", "mars", "avril", "mai", "juin", "juillet", "août", "septembre",
        "octobre", "novembre", "décembre"]

def call(model, body):
    return requests.post(API.format(model), headers={"x-goog-api-key": KEY}, json=body, timeout=300)

def headlines(urls, n=12):
    out = []
    for u in urls:
        try:
            out += [e.title for e in feedparser.parse(u).entries[:n]]
        except Exception as e:
            print("flux ignoré", u, e)
    return out

def write_script():
    d = datetime.date.today()
    today = f"{JOURS[d.weekday()]} {d.day} {MOIS[d.month - 1]} {d.year}"
    prompt = f"""Tu écris la SUITE d'une émission de radio du matin, "Morioh Cho Radio", animée par Kai Harada.
Nous sommes le {today}. L'intro est DÉJÀ dite : ne dis pas bonjour, ne te présente pas, commence directement par la news.
Voici l'ordre, environ 400 mots à dire à voix haute :
1) LA news importante du jour (choisis dans la liste "une"), bien expliquée : ce qui s'est passé, pourquoi ça compte. Environ 150 mots.
2) Tu enchaînes avec "Passons aux autres news" puis 4 ou 5 news moins importantes (listes "une" et "insolite"), citées vite, une phrase chacune.
3) Une anecdote drôle liée à l'actu du jour ou à la date d'aujourd'hui. Elle doit être vraie et vérifiable, sinon fais une blague claire sans inventer de fait précis.
4) Le mot du jour : un mot français peu courant, sa définition, un exemple rigolo.
5) Tu conclus en souhaitant une agréable journée, avec une dernière phrase cool.
Style : tu parles comme un vrai mec cool et naturel, phrases courtes, ton familier mais pas vulgaire, petites réactions ("bon", "franchement", "allez"), jamais un ton de robot ni de journaliste. Écris les chiffres et sigles comme on les dit. Aucune parenthèse, aucun markdown, aucune didascalie. N'invente aucun fait d'actualité hors des titres fournis.
LISTE une : {json.dumps(headlines(FEEDS['une']), ensure_ascii=False)}
LISTE insolite : {json.dumps(headlines(FEEDS['insolite']), ensure_ascii=False)}
Réponds en JSON : {{"titre": "la news importante en une phrase", "script": "le texte complet"}}"""
    body = {"contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {"responseMimeType": "application/json"}}
    for model in MODELS:
        r = call(model, body)
        if r.ok:
            return json.loads(r.json()["candidates"][0]["content"]["parts"][0]["text"])
        print("échec", model, r.status_code, r.text[:200])
        time.sleep(20)
    r.raise_for_status()

def gemini_tts(text, path):
    body = {"contents": [{"parts": [{"text": STYLE + text}]}],
            "generationConfig": {"responseModalities": ["AUDIO"],
                                 "speechConfig": {"voiceConfig": {"prebuiltVoiceConfig": {"voiceName": GEMINI_VOICE}}}}}
    for model in TTS_MODELS:
        try:
            r = call(model, body)
            if r.ok:
                part = r.json()["candidates"][0]["content"]["parts"][0]["inlineData"]
                m = re.search(r"rate=(\d+)", part.get("mimeType", ""))
                with wave.open(str(path), "wb") as w:
                    w.setnchannels(1); w.setsampwidth(2); w.setframerate(int(m[1]) if m else 24000)
                    w.writeframes(base64.b64decode(part["data"]))
                print("voix Gemini OK", model)
                return True
            print("TTS échec", model, r.status_code, r.text[:200])
        except Exception as e:
            print("TTS erreur", model, e)
        time.sleep(15)
    return False

def tts(text):
    p = OUT / "voice.wav"
    if gemini_tts(text, p):
        return p
    print("Gemini TTS KO, repli edge-tts")
    p = OUT / "voice.mp3"
    try:
        import edge_tts
        asyncio.run(edge_tts.Communicate(text, EDGE_VOICE, rate="+6%", pitch="-2Hz").save(str(p)))
    except Exception as e:
        print("edge-tts KO, repli gTTS:", e)
        from gtts import gTTS
        gTTS(text, lang="fr").save(str(p))
    return p

def duration(p):
    return float(subprocess.check_output(["ffprobe", "-v", "error", "-show_entries", "format=duration",
                                          "-of", "csv=p=0", str(p)]))

def mix(voice, jingle, dest):
    total = VOICE_AT + duration(voice) + 4
    body = OUT / "body.wav"          # la partie du jingle APRÈS l'intro : c'est elle qui boucle
    n = max(duration(jingle) - DUCK_AT, 2)
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-ss", str(DUCK_AT), "-i", str(jingle),
                    "-af", f"afade=t=in:d=0.4,afade=t=out:st={n-0.4:.2f}:d=0.4",
                    "-ar", "44100", "-ac", "2", str(body)], check=True)
    f = "aformat=sample_rates=44100:channel_layouts=stereo"
    graph = (f"[0:a]{f}[a0];[1:a]{f}[a1];[a0][a1]concat=n=2:v=0:a=1[mus];"
             f"[mus]volume='{MUSIC_LOW}+{1-MUSIC_LOW}*clip({DUCK_AT+1}-t,0,1)':eval=frame[m];"
             f"[2:a]{f},adelay={int(VOICE_AT*1000)}|{int(VOICE_AT*1000)}[v];"
             f"[m][v]amix=inputs=2:duration=longest:dropout_transition=0,volume=2,"
             f"alimiter=limit=0.95,afade=t=out:st={total-4:.2f}:d=4[o]")
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-t", str(DUCK_AT), "-i", str(jingle),
                    "-stream_loop", "-1", "-i", str(body), "-i", str(voice),
                    "-filter_complex", graph, "-map", "[o]", "-t", f"{total:.2f}",
                    "-b:a", "96k", str(dest)], check=True)
    body.unlink()
    return total

if __name__ == "__main__":
    ep = write_script()
    full = INTRO + ep["script"]
    voice = tts(full)
    total = mix(voice, "assets/jingle.mp3", OUT / "latest.mp3")
    voice.unlink()
    (OUT / "episode.json").write_text(json.dumps({
        "date": datetime.date.today().isoformat(), "titre": ep["titre"],
        "script": full, "duree": round(total)}, ensure_ascii=False, indent=1), encoding="utf-8")
    print("OK", ep["titre"])
