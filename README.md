# VibeMix

A tiny, subscription-free mix builder. Put songs in a folder, order them,
pick how each one hands off to the next, hit Render, get one long WAV
plus a tracklist with timestamps.

No beatmatching, on purpose — built for rock, hip-hop, jazz and anything
with vocals, where tempo-syncing sounds wrong. Transitions are about mood.

## Run it

1. Install Python 3 (python.org) if you don't have it.
2. Mac: double-click `Start VibeMix (Mac).command`
   (first time on a Mac: right-click → Open if it says it's from an unknown developer)
   Windows: double-click `Start VibeMix (Windows).bat`
3. Your browser opens at http://127.0.0.1:8765
4. Use **Add songs…** (or drop WAV / FLAC / MP3 files in the `tracks` folder).

Mixes land in the `mixes` folder. Use the **Quit** button (top right) or close the black window to quit.

## What you can do

- Click songs to add them, drag the ≡ grip to reorder.
- Each song shows its waveform. Drag the gold lines to skip a long intro or outro,
  or click anywhere on the waveform to listen from there.
- Every hand-off between two songs has a style:
  - **Smooth** — equal-power crossfade, 3–40 seconds.
  - **Dissolve** — crossfade while the outgoing song slides under a low-pass filter.
  - **Breath** — quick fade out, a beat of silence, fade in. For hard mood changes.
- **▶ Hear this hand-off** renders just that transition (8 s before, 8 s after) so
  you can tune it in seconds instead of rendering the whole mix.
- **Save** keeps the arrangement under a name; load it from the dropdown later.
- Every song is levelled to -14 LUFS (YouTube's own loudness target) with a
  transparent peak limiter, so a quiet jazz track and a loud hip-hop track sit at
  the same volume without squashing either.
- Tick **MP3 copy** to also get a small file for your phone / speaker. The WAV
  stays the master for the video edit.

Each render writes three files: the WAV, a `_tracklist.txt` whose lines are in
YouTube-chapter format (paste into the description), and a `_mix.json` with the
exact arrangement so you can reproduce it.

## Formats

WAV, FLAC, MP3, AIFF, OGG read natively. M4A / AAC need `ffmpeg` on the system
(`brew install ffmpeg` on Mac); otherwise convert them to WAV first.

## Packaged apps (no Python needed)

Every push to `main` builds `VibeMix-Mac.zip` and `VibeMix-Windows.zip` on GitHub and
attaches them to a Release (see `.github/workflows/build.yml`). Unzip, double-click
VibeMix, done. The app looks for `tracks` and `mixes` folders next to itself.
Mac first run: right-click VibeMix.app → Open (unsigned app).
