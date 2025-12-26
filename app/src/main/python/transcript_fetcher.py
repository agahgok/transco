import os
import re
import glob
import tempfile
from urllib.parse import urlparse, parse_qs
import yt_dlp


def get_video_id(youtube_url):
    try:
        parsed = urlparse(youtube_url)
        if "youtube.com" in parsed.netloc:
            v = parse_qs(parsed.query).get("v")
            if v:
                return v[0]
        if "youtu.be" in parsed.netloc:
            return parsed.path.lstrip("/")
    except:
        pass
    return None


def _vtt_to_text(vtt_content):
    out = []
    for raw in vtt_content.splitlines():
        line = raw.strip()
        if not line:
            continue
        if line == "WEBVTT":
            continue
        if "-->" in line:
            continue
        if re.fullmatch(r"\d+", line):
            continue

        line = re.sub(r"<[^>]+>", "", line).strip()
        if not line:
            continue
        out.append(line)

    cleaned = []
    for line in out:
        if not cleaned or cleaned[-1] != line:
            cleaned.append(line)

    return "\n".join(cleaned).strip()


def _pick_lang(available_langs, preferred=("tr", "en")):
    """
    available_langs: iterable of language codes (e.g. ['en', 'en-GB', 'de', ...])
    preferred: preference order; if none match, fallback to the first available
    """
    if not available_langs:
        return None
    langs = list(available_langs)

    # exact match first
    for p in preferred:
        if p in langs:
            return p

    # prefix match (e.g. preferred 'en' matches 'en-GB', 'en-US')
    for p in preferred:
        for l in langs:
            if l.startswith(p + "-"):
                return l

    # fallback: first available
    return langs[0]


def get_transcript_text(youtube_url):
    video_id = get_video_id(youtube_url)
    if not video_id:
        return "Invalid YouTube URL"

    with tempfile.TemporaryDirectory() as tmpdirname:
        base_opts = {
            "skip_download": True,
            "subtitlesformat": "vtt",
            "outtmpl": f"{tmpdirname}/%(id)s.%(ext)s",
            "quiet": True,
            "no_warnings": True,
        }

        # 1) Önce bilgi çek: hangi manuel/otomatik caption dilleri var?
        info_opts = dict(base_opts)
        try:
            with yt_dlp.YoutubeDL(info_opts) as ydl:
                info = ydl.extract_info(youtube_url, download=False)
        except Exception as e:
            return f"Error fetching video info: {e}"

        subtitles = info.get("subtitles") or {}
        auto_caps = info.get("automatic_captions") or {}

        manual_langs = list(subtitles.keys())
        auto_langs = list(auto_caps.keys())

        # 2) Manuel altyazı varsa onu indir
        if manual_langs:
            chosen = _pick_lang(manual_langs, preferred=("tr", "en"))
            ydl_opts_manual = dict(base_opts)
            ydl_opts_manual.update({
                "writesubtitles": True,
                "writeautomaticsub": False,
                # sadece seçtiğimiz dili indir
                "subtitleslangs": [chosen],
            })

            try:
                with yt_dlp.YoutubeDL(ydl_opts_manual) as ydl:
                    ydl.download([youtube_url])
            except Exception:
                # manuel indirme başarısız olursa otomatiğe düş
                pass
        else:
            chosen = None  # manuel yok

        vtts = sorted(glob.glob(f"{tmpdirname}/*.vtt"))

        # 3) Manuelden vtt çıkmadıysa (ya manuel yoktu ya da indirme başarısız)
        #    YouTube otomatik altyazı varsa onu indir (dil filtresi olmadan / seçerek)
        if not vtts:
            if not auto_langs:
                return "No subtitles found for this video (manual yok, auto da yok)."

            chosen_auto = _pick_lang(auto_langs, preferred=("tr", "en"))
            ydl_opts_auto = dict(base_opts)
            ydl_opts_auto.update({
                "writesubtitles": False,
                "writeautomaticsub": True,
                # seçtiğimiz auto dili indir (yoksa zaten _pick_lang ilk dili seçiyor)
                "subtitleslangs": [chosen_auto],
            })

            try:
                with yt_dlp.YoutubeDL(ydl_opts_auto) as ydl:
                    ydl.download([youtube_url])
            except Exception as e:
                return f"Auto subtitles download failed: {e}"

            vtts = sorted(glob.glob(f"{tmpdirname}/*.vtt"))
            if not vtts:
                return "Auto subtitles were reported available but no VTT was downloaded."

        # 4) Birden fazla vtt çıkarsa: tr/en’i tercih ederek seç
        def rank(path):
            p = path.lower()
            if ".tr." in p or ".tr-" in p:
                return 0
            if ".en." in p or ".en-" in p:
                return 1
            if ".en-gb." in p or ".en-gb-" in p:
                return 2
            return 999

        best_vtt = sorted(vtts, key=lambda p: (rank(p), p))[0]

        try:
            with open(best_vtt, "r", encoding="utf-8", errors="replace") as f:
                vtt_content = f.read()
            return _vtt_to_text(vtt_content)
        except Exception as e:
            return f"Error reading subtitle file: {e}"
