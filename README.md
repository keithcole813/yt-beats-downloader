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
