import sys, os, json, math, time
sys.path.insert(0, "../vibemix")
import numpy as np, soundfile as sf, pyloudnorm as pyln
import engine

T = "./tracks"; M = "./mixes"
os.makedirs(T, exist_ok=True); os.makedirs(M, exist_ok=True)

def song(name, sr, ch, secs, freq, amp, loud_burst=False):
    t = np.arange(int(sr*secs))/sr
    sig = amp*np.sin(2*np.pi*freq*t) * (0.6+0.4*np.sin(2*np.pi*0.25*t))   # slow wobble so it's not a pure tone
    sig += 0.3*amp*np.sin(2*np.pi*freq*2.01*t)
    if loud_burst:  # a few hot transients to test the limiter
        for s in np.linspace(5, secs-5, 12):
            i = int(s*sr); sig[i:i+200] = 1.0
    x = np.stack([sig]*ch, axis=1).astype(np.float32)
    sf.write(os.path.join(T, name), x, sr)

song("a_48k_mono.wav", 48000, 1, 40, 220, 0.9)
song("b_44k_stereo.flac", 44100, 2, 35, 330, 0.08)      # quiet "jazz"
song("c_22k.wav", 22050, 1, 30, 165, 0.5, loud_burst=True)
song("d_mp3.mp3", 44100, 2, 30, 440, 0.4)

pl = {"title": "Test mix", "normalize": True, "mp3": True, "tracks": [
    {"file": "a_48k_mono.wav", "trim_start": 3, "trim_end": 2, "transition": "smooth", "blend": 8},
    {"file": "b_44k_stereo.flac", "trim_start": 0, "trim_end": 0, "transition": "dissolve", "blend": 10},
    {"file": "c_22k.wav", "trim_start": 0, "trim_end": 0, "transition": "cut", "blend": 12},
    {"file": "d_mp3.mp3", "trim_start": 0, "trim_end": 0, "transition": "smooth", "blend": 12},
]}
t0 = time.time()
res = engine.render(pl, T, M, progress=lambda p: print("  ", p["message"]))
print("render:", res, f"{time.time()-t0:.1f}s")

data, sr = sf.read(res["wav"]); assert sr == 44100
print("peak:", np.abs(data).max())
meter = pyln.Meter(sr)
# measure loudness of the middle of each song region via tracklist
lines = open(res["tracklist"]).read().splitlines()[2:]
print("\n".join(lines))
def parse(s):
    p = s.split(" ")[0].split(":"); p = [int(x) for x in p]
    return p[-1] + 60*p[-2] + (3600*p[-3] if len(p)==3 else 0)
starts = [parse(l) for l in lines] + [len(data)/sr]
for i in range(4):
    a = int((starts[i]+6)*sr); b = int((starts[i+1]-6)*sr)
    if b > a + sr*3:
        print(f"track {i+1} LUFS: {meter.integrated_loudness(data[a:b]):.1f}")
# breath gap: should be ~1.2s of silence before track 4 start
s4 = int(starts[3]*sr); env = np.abs(data[s4-3*sr:s4+sr]).max(axis=1)
from scipy.ndimage import maximum_filter1d
q = maximum_filter1d(env, size=int(1.15*sr)).min()
print("quietest 1.15s window near breath:", q); assert q < 1e-4
assert os.path.exists(res["mp3"]), res
print("mp3 size:", os.path.getsize(res["mp3"]), "wav size:", os.path.getsize(res["wav"]))
print("json:", json.load(open(res["wav"].replace(".wav","_mix.json")))["title"])

# audition
au = engine.audition(pl["tracks"][1], pl["tracks"][2], T, "./aud.wav")
print("audition:", au)
# peaks
pk = engine.peaks(os.path.join(T, "c_22k.wav"), "./cache")
print("peaks:", len(pk["peaks"]), pk["seconds"], max(pk["peaks"]))

# limiter sanity vs reference loop
x = np.random.default_rng(1).normal(0, 0.3, (44100*3, 2)).astype(np.float32); x[20000:20100] = 3.0
y = engine.limiter(x)
print("limiter peak:", np.abs(y).max(), "untouched ratio:", np.mean(y[:10000]==x[:10000]))
assert np.abs(y).max() <= 0.98 + 1e-6
