import os
import re
import glob
import sys
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
        if "-->" in line:   # timestamps
            continue
        if re.fullmatch(r"\d+", line):  # cue index
            continue

        line = re.sub(r"<[^>]+>", "", line).strip()
        if not line:
            continue
        out.append(line)

    # remove consecutive duplicates
    cleaned = []
    for line in out:
        if not cleaned or cleaned[-1] != line:
            cleaned.append(line)

    return "\n".join(cleaned).strip()

def get_transcript_text(youtube_url):
    video_id = get_video_id(youtube_url)
    if not video_id:
        return "Invalid YouTube URL"

    # Use a temporary directory for yt-dlp operations
    with tempfile.TemporaryDirectory() as tmpdirname:
        # Step 1: Try Manual Subtitles
        # Corresponds to '--write-subs'
        ydl_opts_manual = {
            'skip_download': True,
            'writesubtitles': True,
            'writeautomaticsub': False,
            'subtitleslangs': ['tr', 'en', 'en.*'], 
            'subtitlesformat': 'vtt',
            'outtmpl': f'{tmpdirname}/%(id)s.%(ext)s',
            'quiet': True,
            'no_warnings': True,
        }

        found_vtt = None

        try:
            with yt_dlp.YoutubeDL(ydl_opts_manual) as ydl:
                ydl.download([youtube_url])
            
            vtts = sorted(glob.glob(f"{tmpdirname}/*.vtt"))
            if vtts:
                found_vtt = vtts
        except Exception:
            # Ignore errors and proceed to step 2 (Auto subs)
            pass

        # Step 2: Try Auto Subtitles if Manual failed
        if not found_vtt:
            # Corresponds to '--write-auto-subs'
            ydl_opts_auto = {
                'skip_download': True,
                'writesubtitles': False,
                'writeautomaticsub': True,
                'subtitleslangs': ['tr', 'en', 'en.*'], 
                'subtitlesformat': 'vtt',
                'outtmpl': f'{tmpdirname}/%(id)s.%(ext)s',
                'quiet': True,
                'no_warnings': True,
            }
            try:
                with yt_dlp.YoutubeDL(ydl_opts_auto) as ydl:
                    ydl.download([youtube_url])
                
                vtts = sorted(glob.glob(f"{tmpdirname}/*.vtt"))
                if vtts:
                    found_vtt = vtts
            except Exception as e:
                # If both failed, return error
                pass

        if not found_vtt:
             # Try one last ditch effort with the player_client workaround if standard methods failed
             # But only if standard attempts failed, to match user logic priority
            return "No subtitles found for this video (checked manual and auto)."

        # Rank files: prefer TR over EN
        def rank(path):
            p = path.lower()
            if ".tr." in p or ".tr-" in p:
                return 0
            if ".en." in p or ".en-" in p:
                return 1
            if ".en-gb." in p or ".en-gb-" in p:
                return 2
            return 999

        best_vtt = sorted(found_vtt, key=lambda p: (rank(p), p))[0]

        try:
            with open(best_vtt, "r", encoding="utf-8", errors="replace") as f:
                vtt_content = f.read()
            return _vtt_to_text(vtt_content)
        except Exception as e:
             return f"Error reading subtitle file: {e}"
