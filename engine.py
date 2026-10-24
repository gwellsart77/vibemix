"""
VibeMix engine — arrange tracks, blend them, render one long WAV.

No beatmatching on purpose: this is for lyric-driven rock / hip-hop / jazz,
where tempo-syncing makes things sound wrong. Transitions are about mood.

Playlist JSON shape (what the UI sends):
{
  "title": "Saturday studio mix",
  "tracks": [
    {"file": "01 - song.wav", "trim_start": 0.0, "trim_end": 0.0,
     "transition": "smooth", "blend": 12.0}
  ],
  "normalize": true,
  "mp3": false
}
transition = how THIS track hands off to the NEXT one:
  smooth   — equal-power crossfade over `blend` seconds
  dissolve — crossfade + the outgoing track sinks under a low-pass filter
  cut      — outgoing fades fast, short breath of silence, next track fades in
"""
import os, json, math, time, shutil, subprocess, hashlib
import numpy as np
import soundfile as sf
from scipy.signal import resample_poly, butter, sosfilt, sosfilt_zi
from scipy.ndimage import maximum_filter1d

SR = 44100
TARGET_LUFS = -14.0          # YouTube's loudness target
CEILING = 0.98               # peak ceiling after levelling (never clip)
AUDIO_EXT = (".wav", ".flac", ".mp3", ".aiff", ".aif", ".ogg", ".opus", ".m4a", ".aac", ".wma")
NATIVE_EXT = (".wav", ".flac", ".mp3", ".aiff", ".aif", ".ogg", ".opus")   # libsndfile reads these

BREATH_OUT = 2.0             # "cut" (Breath) hand-off: seconds of fade-out on the outgoing song
BREATH_GAP = 1.2             #                        seconds of silence
BREATH_IN = 1.5              #                        seconds of fade-in on the next song
FINAL_FADE = 4.0             # gentle fade on the last song
PREVIEW_PAD = 8.0            # audition: seconds of song heard before and after the hand-off


# ---------- loading ----------

def ffmpeg_path():
    return shutil.which("ffmpeg")


def can_read(path):
    ext = os.path.splitext(path)[1].lower()
    return ext in NATIVE_EXT or (ext in AUDIO_EXT and ffmpeg_path() is not None)


def _decode_ffmpeg(path):
    """Fallback for AAC / M4A / WMA etc. — only used when ffmpeg is on the PATH."""
    cmd = [ffmpeg_path(), "-v", "error", "-i", path, "-f", "f32le", "-ac", "2", "-ar", str(SR), "-"]
    raw = subprocess.run(cmd, capture_output=True, check=True).stdout
    data = np.frombuffer(raw, dtype=np.float32).reshape(-1, 2)
    return data.copy(), SR


def load_track(path):
    """Return float32 stereo array (n, 2) at 44.1k."""
    ext = os.path.splitext(path)[1].lower()
    if ext in NATIVE_EXT:
        data, sr = sf.read(path, dtype="float32", always_2d=True)
    else:
        data, sr = _decode_ffmpeg(path)
    if data.shape[1] == 1:
        data = np.repeat(data, 2, axis=1)
    elif data.shape[1] > 2:
        data = data[:, :2]
    if sr != SR:
        g = math.gcd(sr, SR)
        data = resample_poly(data, SR // g, sr // g, axis=0).astype(np.float32)
    return np.ascontiguousarray(data, dtype=np.float32)


def track_info(path):
    ext = os.path.splitext(path)[1].lower()
    if ext in NATIVE_EXT:
        info = sf.info(path)
        return {"file": os.path.basename(path), "seconds": round(info.duration, 1),
                "samplerate": info.samplerate, "channels": info.channels}
    if ffmpeg_path() is None:
        raise RuntimeError("needs ffmpeg installed to read this format (or convert it to WAV/FLAC/MP3)")
    out = subprocess.run([shutil.which("ffprobe") or ffmpeg_path().replace("ffmpeg", "ffprobe"),
                          "-v", "error", "-show_entries", "format=duration",
                          "-of", "default=nw=1:nk=1", path], capture_output=True, text=True)
    secs = float(out.stdout.strip() or 0)
    return {"file": os.path.basename(path), "seconds": round(secs, 1), "samplerate": None, "channels": None}


def _cache_key(path):
    st = os.stat(path)
    return hashlib.md5(f"{os.path.basename(path)}|{st.st_size}|{int(st.st_mtime)}".encode()).hexdigest()


def peaks(path, cache_dir=None, n=900):
    """Waveform outline for the UI: n values in 0..1 (max |sample| per bucket), plus length."""
    if cache_dir:
        os.makedirs(cache_dir, exist_ok=True)
        cpath = os.path.join(cache_dir, _cache_key(path) + ".json")
        if os.path.isfile(cpath):
            return json.load(open(cpath))
    audio = load_track(path)
    mono = np.max(np.abs(audio), axis=1)
    edges = np.linspace(0, len(mono), n + 1, dtype=int)
    vals = [float(mono[a:b].max()) if b > a else 0.0 for a, b in zip(edges[:-1], edges[1:])]
    out = {"peaks": [round(v, 3) for v in vals], "seconds": round(len(audio) / SR, 2)}
    if cache_dir:
        json.dump(out, open(cpath, "w"))
    return out


# ---------- loudness ----------

def measure_lufs(audio):
    import pyloudnorm as pyln
    return pyln.Meter(SR).integrated_loudness(audio)


def limiter(audio, ceiling=CEILING, lookahead_ms=2.0, release_ms=80.0):
    """Transparent peak limiter: only touches the moments that would clip, instead of
    turning the whole song down (which is what v0.1 did and what makes quiet songs quieter)."""
    peak = np.abs(audio).max(axis=1)
    if peak.max() <= ceiling:
        return audio
    la = max(int(SR * lookahead_ms / 1000), 1)
    env = maximum_filter1d(peak, size=2 * la + 1)                 # look ahead so the gain is down before the peak
    need = np.minimum(1.0, ceiling / np.maximum(env, 1e-9))      # gain needed at each sample
    # smooth release: gain drops instantly but recovers slowly (avoids pumping / zipper noise).
    # m[i] = max(d[i], coef*m[i-1]) with d = 1-need, done vectorised chunk by chunk:
    # m[i] = coef^i * cummax(d[j] / coef^j).
    coef = math.exp(-1.0 / (SR * release_ms / 1000))
    d = 1.0 - need
    m = np.empty_like(d)
    chunk = SR
    carry = 0.0
    for s in range(0, len(d), chunk):
        seg = d[s:s + chunk]
        k = np.arange(len(seg))
        up = coef ** (-k)
        c = np.maximum.accumulate(np.maximum(seg * up, carry * coef))   # carry recovers one step then rides along
        m[s:s + chunk] = c * (coef ** k)
        carry = m[s + len(seg) - 1]
    g = 1.0 - m
    out = audio * g[:, None]
    return np.clip(out, -ceiling, ceiling).astype(np.float32)


def normalize(audio, target_lufs=TARGET_LUFS):
    """Bring every track to the same perceived loudness (hip-hop vs jazz problem)."""
    try:
        lufs = measure_lufs(audio)
        gain = 10 ** ((target_lufs - lufs) / 20) if math.isfinite(lufs) else 1.0
    except Exception:
        rms = np.sqrt(np.mean(audio ** 2)) + 1e-9
        gain = (10 ** (target_lufs / 20)) / rms * 0.3
    out = (audio * min(gain, 8.0)).astype(np.float32)
    return limiter(out)


# ---------- curves & filters ----------

def equal_power(n):
    """Fade-out and fade-in curves that keep loudness constant through the blend."""
    t = np.linspace(0.0, 1.0, max(n, 1), dtype=np.float32)
    return np.cos(t * np.pi / 2)[:, None], np.sin(t * np.pi / 2)[:, None]


def lowpass_sweep(audio, start_hz=18000.0, end_hz=250.0, block=1024):
    """Outgoing track sinks underwater: cutoff slides down over the whole segment."""
    out = np.empty_like(audio)
    n = len(audio)
    zi = None
    for i in range(0, n, block):
        frac = i / max(n - 1, 1)
        hz = start_hz * (end_hz / start_hz) ** frac          # log sweep sounds natural
        sos = butter(2, min(hz / (SR / 2), 0.99), btype="low", output="sos")
        if zi is None:
            zi = np.stack([sosfilt_zi(sos) * audio[0, c] for c in range(2)], axis=-1)
        seg = audio[i:i + block]
        y, zi = sosfilt(sos, seg, axis=0, zi=zi)
        out[i:i + block] = y
    return out


def apply_trim(audio, trim_start, trim_end):
    a = int(max(float(trim_start or 0), 0) * SR)
    b = len(audio) - int(max(float(trim_end or 0), 0) * SR)
    a = min(a, max(len(audio) - SR, 0))
    return audio[a:max(b, a + SR)]


# ---------- the hand-off, shared by render() and audition() ----------

def split_tail(audio, head_len, mode, blend):
    """Cut a track into (body, tail): the tail is what blends into the next song."""
    avail = max(len(audio) - head_len, 0)
    if mode == "cut":
        tail_len = min(int(BREATH_OUT * SR), avail)
    else:
        blend = max(2.0, min(float(blend or 12.0), 60.0))
        tail_len = min(int(blend * SR), max(avail - SR, min(avail, SR)))
    tail_len = max(tail_len, 0)
    body = audio[head_len:len(audio) - tail_len]
    tail = audio[len(audio) - tail_len:].copy()
    if mode == "cut" and len(tail):
        fo, _ = equal_power(len(tail))
        tail *= fo
    return body, tail


def handoff(tail, head, mode):
    """Blend the previous song's tail into the start of the next one.
    Returns (block_to_write, offset_of_next_song_start_within_block, head_samples_consumed)."""
    if mode == "cut":
        gap = np.zeros((int(BREATH_GAP * SR), 2), np.float32)
        h = min(int(BREATH_IN * SR), len(head))
        _, fi = equal_power(h)
        inc = head[:h] * fi
        block = np.concatenate([tail, gap, inc])
        return block, len(tail) + len(gap), h
    n = min(len(tail), len(head))
    fo, fi = equal_power(n)
    outgoing = tail[:n]
    if mode == "dissolve":
        outgoing = lowpass_sweep(outgoing)
    block = outgoing * fo + head[:n] * fi
    return block, n // 2, n            # tracklist marks the midpoint of a blend


def prepare(entry, tracks_dir, do_norm, report=None):
    audio = load_track(os.path.join(tracks_dir, entry["file"]))
    audio = apply_trim(audio, entry.get("trim_start", 0), entry.get("trim_end", 0))
    if do_norm:
        if report: report(f"Levelling {entry['file']}")
        audio = normalize(audio)
    return audio


# ---------- rendering ----------

def safe_name(title):
    s = "".join(c if c.isalnum() or c in " -_" else "_" for c in (title or "")).strip()
    return s or "mix"


def fmt_stamp(samples):
    m, sec = divmod(int(samples / SR), 60)
    h, m = divmod(m, 60)
    return f"{h}:{m:02d}:{sec:02d}" if h else f"{m}:{sec:02d}"


def render(playlist, tracks_dir, out_dir, progress=None):
    """Stream the mix to disk so a 90-minute WAV never has to sit in memory."""
    tracks = playlist["tracks"]
    if not tracks:
        raise ValueError("Playlist is empty")
    title = playlist.get("title") or "mix"
    safe = safe_name(title)
    stamp = time.strftime("%Y-%m-%d_%H%M")
    base = os.path.join(out_dir, f"{safe}_{stamp}")
    wav_path, txt_path, json_path = base + ".wav", base + "_tracklist.txt", base + "_mix.json"
    do_norm = playlist.get("normalize", True)
    want_mp3 = bool(playlist.get("mp3", False))
    total_steps = len(tracks) + (1 if want_mp3 else 0)

    def report(i, msg):
        if progress:
            progress({"step": i, "total": total_steps, "message": msg})

    writer = sf.SoundFile(wav_path, "w", samplerate=SR, channels=2, subtype="PCM_16")
    written = 0           # samples committed to disk
    tail = None           # end of the previous track still waiting to blend
    tail_mode = "smooth"
    starts = []

    def write(block):
        nonlocal written
        if len(block):
            writer.write(np.clip(block, -1.0, 1.0))
            written += len(block)

    try:
        for idx, t in enumerate(tracks):
            report(idx, f"Loading {t['file']}")
            audio = prepare(t, tracks_dir, do_norm, lambda m: report(idx, m))

            if tail is None:
                head_len = 0
                starts.append(0)
            else:
                block, start_off, head_len = handoff(tail, audio, tail_mode)
                starts.append(written + start_off)
                write(block)

            mode = t.get("transition", "smooth")
            is_last = idx == len(tracks) - 1
            if is_last:
                body = audio[head_len:].copy()
                n = int(FINAL_FADE * SR)
                if len(body) > n:                       # gentle ending on the final track
                    fo, _ = equal_power(n)
                    body[-n:] *= fo
                write(body)
                tail = None
            else:
                body, tail = split_tail(audio, head_len, mode, t.get("blend", 12.0))
                write(body)
            tail_mode = mode
            report(idx + 1, f"Blended {t['file']}")
    finally:
        writer.close()

    with open(txt_path, "w", encoding="utf-8") as f:
        f.write(f"{title}\n\n")
        for s, t in zip(starts, tracks):                # "0:00 Title" lines — paste into a YouTube description for chapters
            f.write(f"{fmt_stamp(s)} {os.path.splitext(t['file'])[0]}\n")
    json.dump(playlist, open(json_path, "w"), indent=2)

    result = {"wav": wav_path, "tracklist": txt_path, "seconds": round(written / SR, 1)}
    if want_mp3:
        report(len(tracks), "Making the MP3 copy")
        try:
            result["mp3"] = to_mp3(wav_path)
        except Exception as e:
            result["mp3_error"] = str(e)
    return result


def to_mp3(wav_path):
    """MP3 copy for phone / speaker playback in the studio. WAV stays the master for the video edit."""
    mp3_path = os.path.splitext(wav_path)[0] + ".mp3"
    if ffmpeg_path():
        subprocess.run([ffmpeg_path(), "-v", "error", "-y", "-i", wav_path, "-b:a", "256k", mp3_path], check=True)
        return mp3_path
    if "MP3" not in sf.available_formats():
        raise RuntimeError("no MP3 encoder available")
    with sf.SoundFile(wav_path) as src, sf.SoundFile(mp3_path, "w", samplerate=src.samplerate,
                                                     channels=src.channels, format="MP3") as dst:
        for block in src.blocks(blocksize=SR * 10, dtype="float32"):
            dst.write(block)
    return mp3_path


def audition(a, b, tracks_dir, out_path, do_norm=True, progress=None):
    """Render only the hand-off between two songs (PREVIEW_PAD s before and after) for a quick listen."""
    rep = (lambda m: progress({"step": 0, "total": 1, "message": m})) if progress else None
    A = prepare(a, tracks_dir, do_norm, rep)
    B = prepare(b, tracks_dir, do_norm, rep)
    mode = a.get("transition", "smooth")
    body, tail = split_tail(A, 0, mode, a.get("blend", 12.0))
    pad = int(PREVIEW_PAD * SR)
    pre = body[-pad:]
    block, start_off, consumed = handoff(tail, B, mode)
    post = B[consumed:consumed + pad].copy()
    if len(post) > SR:
        fo, _ = equal_power(SR)
        post[-SR:] *= fo
    out = np.concatenate([pre, block, post])
    sf.write(out_path, np.clip(out, -1, 1), SR, subtype="PCM_16")
    return {"file": out_path, "seconds": round(len(out) / SR, 1),
            "handoff_at": round((len(pre) + start_off) / SR, 1)}


if __name__ == "__main__":
    import sys
    pl = json.load(open(sys.argv[1]))
    print(render(pl, sys.argv[2], sys.argv[3], progress=lambda p: print(p["message"])))
