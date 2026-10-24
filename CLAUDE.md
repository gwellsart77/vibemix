# VibeMix — Project State
# Status: LIVING  ·  Updated: 2026-10-24 (v0.2, Phase 4 done)  ·  Owner: any chat in the "DJ Software" project

> **Division of truth:** this file owns FACTS (what is true right now). `PROJECT_ROADMAP.md`
> owns PLANS. When they disagree, this file wins and the roadmap gets corrected. Decisions
> go to `DECISIONS.md` the day they're made. Work moving between chats gets a brief in `HANDOFFS/`.

## What this is (30 seconds)
VibeMix is Gabe's personal, subscription-free **mix builder**. He arranges 30–90 minutes of
music (rock, hip-hop, alternative, modern jazz — lyric-driven, NOT house/techno), picks how each
song hands off to the next, and renders one long WAV plus a timestamped tracklist. The mix plays
in the studio while he paints on camera; the audio is synced to the painting video afterwards.

It is deliberately **not a DJ app**: no decks, no live performance, no beatmatching. Beat-sync
is wrong for this material (singers go out of time, drummers swing, songs change tempo).
Transitions are about mood and energy, not BPM. Think late-night radio DJ, not club DJ.

## Who Gabe is, for this project
Artist and "vibe coder": gives vision and decisions, Claude does architecture and code. He is not
an audio engineer and doesn't want to become one. Every feature must pass: *would a non-technical
person understand this control on first sight?* Fewer controls beats more. Plain words in the UI
("Smooth / Dissolve / Breath"), never DSP jargon.

## Where the code lives (Phase 4, 2026-10-24)
- **GitHub is the source of truth:** https://github.com/gwellsart77/vibemix (public, `main`).
- **Every push to `main`** builds `VibeMix-Mac.zip` + `VibeMix-Windows.zip` on GitHub Actions
  (~6 min) and publishes/updates the Release tagged `v<VERSION>` (VERSION read from `app.py`):
  https://github.com/gwellsart77/vibemix/releases/latest — no Python needed on Gabe's machines.
- Drive `vibemix/` is a mirror Claude keeps in sync by hand (Gabe runs the script version from it);
  `VibeMix.zip` on Drive is retired — the Release is the download.
- To ship a new version: bump `VERSION` in `app.py`, push to `main`. That's it.
- The session git proxy **cannot push tags** (403) — that's why the release is cut from a push to
  `main`, not from a `v*` tag. Don't "fix" this by switching back to tag-triggered releases.

## Architecture (v0.2, shipped 2026-10-24)
```
vibemix/
  app.py              local HTTP server on 127.0.0.1:8765, opens the browser, JSON API, byte-range audio streaming
  engine.py           all audio: load → trim → loudness-level + limiter → hand-off → stream to WAV (+ optional MP3)
  index.html          the whole UI, one page, no build step, arrangement in localStorage + named saves on disk
  requirements.txt    numpy scipy soundfile>=0.12 pyloudnorm
  Start VibeMix (Mac).command / Start VibeMix (Windows).bat   one-click launchers (make .venv-mac / .venv-win on first run
                      so one Drive-synced folder works from both machines;
                      find python3.x / py -3 / python; friendly message if Python is missing)
  .github/workflows/build.yml   on push to main: PyInstaller (--windowed --onefile) builds VibeMix.app + VibeMix.exe,
                      bundles them with tracks/ mixes/ README (+ Gatekeeper note on Mac), publishes the Release
  .gitignore          venvs, caches, tracks/*, mixes/* (keeps the .keep files)
  tracks/             Gabe's songs (WAV / FLAC / MP3 / AIFF / OGG natively; M4A/AAC only if ffmpeg is on the PATH)
  mixes/              rendered output + `<name>.vibemix.json` saved arrangements
  .cache/             waveform peak cache + last audition clip (safe to delete)
```
- One codebase, runs on both Gabe's Mac and Windows PC. Packaged builds exist (see above), so Python
  is only needed for the script/launcher version. Packaged app: folders are created next to
  `VibeMix.app` / `VibeMix.exe`; there's no console, so a **Quit** button in the header stops it.
- Audio reading via libsndfile (soundfile ≥ 0.12 bundles MP3 read AND write). Everything resampled
  to 44.1 kHz stereo; output is 16-bit PCM WAV. MP3 copy via ffmpeg if present, else libsndfile.
- Render **streams to disk** track by track — a 90-minute mix never sits in RAM.
- Second launch while already running just re-opens the browser (no port crash).

## The three hand-offs (the whole product, really)
| UI name  | What the engine does |
|----------|----------------------|
| Smooth   | equal-power crossfade, 3–40 s (slider "Blend") |
| Dissolve | same crossfade, but the outgoing song runs through a low-pass filter sweeping 18 kHz → 250 Hz (log curve) so it "sinks underwater" |
| Breath   | 2 s fade out → 1.2 s silence → 1.5 s fade in. For hard mood changes. |
Plus: per-song "skip first / skip last" set by dragging gold lines on a waveform (or typing);
every song levelled to **−14 LUFS** (YouTube's target) then through a transparent lookahead peak
limiter (0.98 ceiling) — v0.1 turned the whole song down instead, which made quiet songs quieter;
final song gets a 4 s fade. Tracklist timestamps mark the midpoint of each blend (start of the
incoming song for Breath) and are written as `0:00 Title` lines = YouTube chapter format.

## v0.2 features beyond v0.1
- Waveform strip per song with draggable trim handles; click the waveform to listen from there.
- **▶ Hear this hand-off**: renders 8 s + hand-off + 8 s of one transition in a few seconds.
- Drag ≡ to reorder. **Add songs…** copies files into `tracks/` from the browser.
- Save / load / delete named mixes (`mixes/*.vibemix.json`). Every render also writes
  `<name>_mix.json` (exact arrangement) next to the WAV and tracklist.
- Optional MP3 copy checkbox (for phone/speaker playback; WAV stays the master for the video edit).
- Previews work in Safari now (server supports HTTP Range requests).

## Rules (don't re-litigate without a DECISIONS.md entry)
1. No beatmatching / time-stretch / BPM detection in the core product.
2. No subscriptions, no cloud, no accounts. Runs locally, free forever.
3. UI stays one HTML file; engine stays plain Python. No frameworks unless a feature truly needs one.
4. Prefer Bandcamp lossless purchases as source material. (OBS-ripping streams breaks platform
   ToS and compressed audio degrades under processing — documented in `_archive/` blueprint.)
5. YouTube Content ID is NOT a safe harbor: some rightsholders block or mute rather than
   monetize. Treat each track's reuse policy as a per-artist question.

## Known gaps / failure modes
- Gabe runs the app straight from the Drive-synced `vibemix/` folder (a `.venv`, `__pycache__`,
  `tracks/` and `mixes/` appeared there at 12:32 local on 2026-10-24, so the v0.1 launcher ran at
  least once on one machine; `tracks/` was still empty). No real-audio listening test yet (Phase 2).
- Because of that, v0.2's launchers use `.venv-mac` / `.venv-win` instead of `.venv`, so the Mac
  and PC don't fight over one synced venv. First v0.2 launch re-installs (~1 min). The old `.venv`
  folder can be deleted. Drive syncing a venv is wasteful but harmless; the packaged builds
  (Phase 4) remove the need for it entirely.
- macOS Gatekeeper may block the `.command` on first run: right-click → Open once.
- `Dissolve` on very short blends (<4 s) sweeps too fast to be audible as a sweep.
- Smooth/Dissolve blends overlap vocals for the whole blend length; for two lyric-heavy songs
  a shorter blend (4–8 s) or Breath will usually sound better. This is for Gabe's ear to decide.
- Browser localStorage holds the *current* arrangement; named saves are on disk and survive.
- Packaged apps are unsigned: Mac shows the Gatekeeper warning once (right-click → Open); Windows
  SmartScreen may show "More info → Run anyway" once. Code signing costs money; not doing it.
- Packaged builds verified only by inspecting the zips' contents (app bundle + exe + folders
  present). Not yet launched on Gabe's real machines.
- Peak limiter is per-song, applied before blending; the crossfade itself is equal-power so the
  sum stays under the ceiling in practice (tested), but there is no final master limiter.

## Key files
| File | Role |
|------|------|
| `CLAUDE.md` | this — facts |
| `PROJECT_ROADMAP.md` | plans, phases, chat board, session notes |
| `DECISIONS.md` | append-only decision log |
| `HANDOFFS/` | dated briefs between chats |
| GitHub `gwellsart77/vibemix` | **source of truth** + Releases with packaged apps |
| `vibemix/` (Drive) | mirror of the repo; Gabe can run the script version from here |
| `_archive/Csound_DJ_App_Blueprint.md` | the original Gemini concept — superseded, kept for history |

## How to work in this project
- Read this file, then the roadmap's chat board, before building anything.
- Changes to the engine: test with synthetic tones at mixed sample rates (48k mono / 44.1k
  stereo / 22k) and verify LUFS per region with pyloudnorm before shipping. v0.2's test script
  is `docs/HANDOFFS/test_engine_v0.2.py` (drops synthetic songs, renders all three hand-offs, checks
  LUFS, the Breath silence gap, MP3, audition, peaks, limiter). UI was verified with headless
  Chromium (playwright) — zero console errors.
- Ship = push to `main` on GitHub (Release builds itself) **and** mirror the changed files to Drive
  `vibemix/`, then a roadmap session note. Use the session's `add_repo` (push access) + `git push`;
  tag pushes fail through the proxy, branch pushes work.
- Gabe's response format: short "Gabriel's View" in plain English + collapsible "AI Notes".
