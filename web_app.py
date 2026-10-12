#!/usr/bin/env python3
"""
YT Beats Downloader — web version.

Run this on your home server (Linux Mint box), open it from your phone's
browser, paste a YouTube URL, and the MP3 downloads straight to your phone.

Same proven settings as the desktop app:
  yt-dlp --cookies-from-browser chrome -f "ba/b" -x --audio-format mp3 --audio-quality 0

Setup:
  pip install -r requirements.txt
  python web_app.py            # serves on port 5001

  # from outside your network, in another terminal:
  cloudflared tunnel --url http://localhost:5001

Optional:
  YT_BEATS_PASSWORD=yourpassword python web_app.py   # lock it with a password
"""
import glob
import os
import threading
import time
import uuid

from flask import Flask, jsonify, render_template_string, request, send_file
from yt_dlp import YoutubeDL

PORT = int(os.environ.get("PORT", 5001))
BASE_DIR = os.path.expanduser("~/Music/yt-beats-web")
PASSWORD = os.environ.get("YT_BEATS_PASSWORD", "")
MAX_AGE = 24 * 3600  # downloads older than this get cleaned up

os.makedirs(BASE_DIR, exist_ok=True)

app = Flask(__name__)
jobs = {}
jobs_lock = threading.Lock()


PAGE = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0, viewport-fit=cover">
<title>YT Beats</title>
<style>
  * { margin:0; padding:0; box-sizing:border-box; }
  body { background:#0b0f1a; color:#f1f5f9;
         font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,sans-serif;
         min-height:100vh; display:flex; flex-direction:column; align-items:center;
         padding:2.5rem 1.25rem; }
  h1 { font-size:1.8rem; margin-bottom:.3rem; }
  .sub { color:#94a3b8; margin-bottom:2rem; font-size:.95rem; text-align:center; }
  .box { width:100%; max-width:480px; }
  label { display:block; font-size:.85rem; font-weight:600; color:#cbd5e1; margin:0 0 .35rem; }
  input { width:100%; background:#141b2e; border:1px solid #26314d; border-radius:12px;
          color:#f1f5f9; padding:1rem; font-size:1rem; margin-bottom:1rem; }
  input:focus { outline:none; border-color:#f0cd6e; }
  #go { width:100%; background:#f0cd6e; color:#0b0f1a; border:none; border-radius:12px;
        font-size:1.15rem; font-weight:800; padding:1.1rem; margin-top:.25rem; }
  #go:disabled { opacity:.5; }
  #prog-wrap { margin-top:1.5rem; display:none; }
  .bar { height:14px; background:#141b2e; border-radius:999px; overflow:hidden; border:1px solid #26314d; }
  .bar > div { height:100%; width:0%; background:#f0cd6e; border-radius:999px;
               transition:width .3s; }
  #status { margin-top:.7rem; color:#94a3b8; font-size:.95rem; text-align:center; }
  #title { margin-top:.4rem; color:#f1f5f9; font-weight:600; text-align:center;
           word-break:break-word; }
  #save { display:none; margin-top:1.2rem; width:100%; background:#10b981; color:#06281c;
          text-align:center; text-decoration:none; font-weight:800; font-size:1.15rem;
          padding:1.1rem; border-radius:12px; }
  #err { display:none; margin-top:1rem; color:#f87171; font-size:.9rem; text-align:center;
         word-break:break-word; }
  .hint { margin-top:2.5rem; color:#475569; font-size:.8rem; text-align:center; line-height:1.7; }
</style>
</head>
<body>
  <h1>&#127335; YT Beats</h1>
  <p class="sub">Grab the set. Chop it later.</p>
  <div class="box">
    <label for="url">YouTube URL</label>
    <input id="url" type="url" placeholder="https://youtu.be/…" autocomplete="off">
    <div id="pw-row" style="display:none">
      <label for="pw">Password</label>
      <input id="pw" type="password" placeholder="••••••••">
    </div>
    <button id="go">Download MP3</button>
    <div id="prog-wrap">
      <div class="bar"><div id="fill"></div></div>
      <div id="status">Starting…</div>
      <div id="title"></div>
    </div>
    <a id="save" href="#">&#11015; Save to phone</a>
    <div id="err"></div>
    <p class="hint">Best-quality MP3, straight to your phone.<br>Move it to your Drive samples folder whenever.</p>
  </div>
<script>
const $ = id => document.getElementById(id);
let pwRequired = false;

async function init() {
  try {
    const cfg = await (await fetch('/api/config')).json();
    pwRequired = cfg.password_required;
    if (pwRequired) {
      $('pw-row').style.display = 'block';
      $('pw').value = localStorage.getItem('ytb_pw') || '';
    }
  } catch(e) {}
}
init();

$('go').onclick = async () => {
  const url = $('url').value.trim();
  if (!url) { showErr('Paste a YouTube URL first.'); return; }
  const password = pwRequired ? $('pw').value : '';
  if (pwRequired) localStorage.setItem('ytb_pw', password);
  $('go').disabled = true; hideErr();
  $('save').style.display = 'none';
  $('prog-wrap').style.display = 'block';
  $('fill').style.width = '0%';
  $('title').textContent = '';
  setStatus('Starting…');
  try {
    const r = await fetch('/api/start', {
      method:'POST', headers:{'Content-Type':'application/json'},
      body: JSON.stringify({url, password})
    });
    const data = await r.json();
    if (!r.ok) throw new Error(data.error || 'Could not start download.');
    poll(data.job_id);
  } catch(e) { showErr(e.message); $('go').disabled = false; }
};

function setStatus(t){ $('status').textContent = t; }
function showErr(t){ const e=$('err'); e.textContent=t; e.style.display='block'; }
function hideErr(){ $('err').style.display='none'; }

async function poll(jobId) {
  try {
    const j = await (await fetch('/api/status/' + jobId)).json();
    if (j.state === 'downloading') {
      $('fill').style.width = j.progress.toFixed(1) + '%';
      setStatus('Downloading… ' + j.progress.toFixed(0) + '%');
    } else if (j.state === 'converting') {
      $('fill').style.width = '100%';
      setStatus('Converting to MP3…');
    } else if (j.state === 'done') {
      $('fill').style.width = '100%';
      setStatus('Done.');
      if (j.title) $('title').textContent = j.title;
      const s = $('save');
      s.href = '/api/file/' + jobId;
      s.style.display = 'block';
      $('go').disabled = false;
      return;
    } else if (j.state === 'error') {
      showErr('Download failed: ' + (j.error || 'unknown error'));
      $('prog-wrap').style.display = 'none';
      $('go').disabled = false;
      return;
    }
    setTimeout(() => poll(jobId), 1000);
  } catch(e) { setTimeout(() => poll(jobId), 2000); }
}
</script>
</body>
</html>
"""


def set_state(job_id, **kw):
    with jobs_lock:
        if job_id in jobs:
            jobs[job_id].update(kw)


def download_worker(job_id, url):
    job_dir = os.path.join(BASE_DIR, job_id)
    os.makedirs(job_dir, exist_ok=True)

    def hook(d):
        st = d.get("status")
        if st == "downloading":
            total = d.get("total_bytes") or d.get("total_bytes_estimate") or 0
            done = d.get("downloaded_bytes", 0)
            pct = (done / total * 100) if total else 0
            set_state(job_id, state="downloading", progress=pct)
        elif st == "finished":
            set_state(job_id, state="converting", progress=100)

    ydl_opts = {
        "format": "ba/b",
        "cookiesfrombrowser": ("chrome",),
        "postprocessors": [{
            "key": "FFmpegExtractAudio",
            "preferredcodec": "mp3",
            "preferredquality": "0",
        }],
        "outtmpl": os.path.join(job_dir, "%(title)s.%(ext)s"),
        "progress_hooks": [hook],
        "quiet": True,
        "no_warnings": True,
    }
    try:
        with YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
        mp3s = glob.glob(os.path.join(job_dir, "*.mp3"))
        if not mp3s:
            raise RuntimeError("conversion produced no MP3 file")
        path = max(mp3s, key=os.path.getmtime)
        set_state(job_id, state="done", progress=100,
                  path=path,
                  filename=os.path.basename(path),
                  title=(info or {}).get("title", ""))
    except Exception as e:
        set_state(job_id, state="error", error=str(e)[:300])


@app.route("/")
def index():
    return render_template_string(PAGE)


@app.route("/api/config")
def config():
    return jsonify({"password_required": bool(PASSWORD)})


@app.route("/api/start", methods=["POST"])
def start():
    data = request.get_json(force=True) or {}
    if PASSWORD and data.get("password") != PASSWORD:
        return jsonify({"error": "Wrong password."}), 403
    url = (data.get("url") or "").strip()
    if not url or not (url.startswith("http://") or url.startswith("https://")):
        return jsonify({"error": "That doesn't look like a URL."}), 400
    job_id = uuid.uuid4().hex[:12]
    with jobs_lock:
        jobs[job_id] = {"state": "starting", "progress": 0,
                        "created": time.time()}
    threading.Thread(target=download_worker, args=(job_id, url),
                     daemon=True).start()
    return jsonify({"job_id": job_id})


@app.route("/api/status/<job_id>")
def status(job_id):
    with jobs_lock:
        job = jobs.get(job_id)
        if not job:
            return jsonify({"error": "unknown job"}), 404
        job = dict(job)
    job.pop("path", None)
    return jsonify(job)


@app.route("/api/file/<job_id>")
def get_file(job_id):
    with jobs_lock:
        job = jobs.get(job_id)
    if not job or job.get("state") != "done" or not job.get("path"):
        return jsonify({"error": "not ready"}), 404
    return send_file(job["path"], as_attachment=True,
                     download_name=job.get("filename", "audio.mp3"))


def cleanup_loop():
    while True:
        time.sleep(1800)
        now = time.time()
        with jobs_lock:
            stale = [jid for jid, j in jobs.items()
                     if now - j.get("created", now) > MAX_AGE]
            for jid in stale:
                jobs.pop(jid, None)
        for jid in stale:
            d = os.path.join(BASE_DIR, jid)
            if os.path.isdir(d):
                import shutil as _sh
                _sh.rmtree(d, ignore_errors=True)


if __name__ == "__main__":
    threading.Thread(target=cleanup_loop, daemon=True).start()
    # NOTE: front this with cloudflared for outside access; keep it on localhost.
    app.run(host="127.0.0.1", port=PORT)
