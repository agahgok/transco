from youtube_transcript_api import YouTubeTranscriptApi
from urllib.parse import urlparse, parse_qs
import sys

# No monkeypatching, just exact logic as requested by user

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

def get_transcript_text(youtube_url):
    video_id = get_video_id(youtube_url)
    if not video_id:
        return "Invalid YouTube URL"

    try:
        # User Logic:
        # ytt = YouTubeTranscriptApi()
        # fetched = ytt.fetch(video_id, languages=["tr", "en"])
        
        ytt = YouTubeTranscriptApi()
        fetched = ytt.fetch(video_id, languages=['tr', 'en'])

        # User Logic for text extraction:
        # text = "\n".join(snippet.text for snippet in fetched)
        
        # Check if snippet has .text attribute or is a dict
        if fetched:
            first = fetched[0]
            if isinstance(first, dict):
                # Standard library returns dicts usually
                return "\n".join(item['text'] for item in fetched)
            else:
                # User code implies object access
                return "\n".join(item.text for item in fetched)
        
        return ""

    except Exception as e:
        import traceback
        return f"Python Error: {repr(e)}\n{traceback.format_exc()}"
