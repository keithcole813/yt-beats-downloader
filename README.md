# YT Beats Downloader

Paste a YouTube URL, get a best-quality MP3 ready for sampling. Built for digging — long mixes, rare grooves, whatever you're chopping.

Uses the proven yt-dlp setup:

```
yt-dlp --cookies-from-browser chrome -f "ba/b" -x --audio-format mp3 --audio-quality 0
```

## What it does

- Downloads the best available audio from any YouTube URL (long videos welcome)
- Converts to MP3 at the highest quality setting
- Live progress bar, speed, and ETA
- Saves to `~/Music/yt-beats` by default (change it in the app)

## Setup

1. Install Python 3 (3.9+)
2. Install **ffmpeg** and make sure it's on your PATH:
   - Windows: `winget install Gyan.FFmpeg`
   - Linux Mint: `sudo apt install ffmpeg`
   - macOS: `brew install ffmpeg`
3. Install the Python dependency:
   ```
   pip install -r requirements.txt
   ```
4. Run it:
   ```
   python yt_beats_downloader.py
   ```

No API keys, no accounts, no sign-ups. Everything runs on your machine.

## Web version (use it from your phone)

`web_app.py` runs the same downloader as a mobile-friendly web page.
Host it on your home server, open it from your phone anywhere, and the
MP3 downloads straight to your phone — ready to move into your Drive
samples folder.

```
python web_app.py
# from outside your network:
cloudflared tunnel --url http://localhost:5001
```

- Mobile-first page: paste URL → progress bar → "Save to phone" button
- Uses your Chrome cookies on the server to get past YouTube's bot check
  (Chrome must be installed and logged into YouTube on the server)
- Downloads are cleaned up automatically after 24 hours
- Optional password lock: `YT_BEATS_PASSWORD=secret python web_app.py`
- iPhone tip: Share → Add to Home Screen and it feels like a real app
