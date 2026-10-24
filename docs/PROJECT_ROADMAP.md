# VibeMix — Roadmap
# Status: LIVING  ·  Updated: 2026-10-24  ·  Owner: any chat in the "DJ Software" project

Plans live here. Facts live in `CLAUDE.md` (it wins on conflict). When a phase completes, both
files update in the same session.

## Phase 0 — Concept ✅ (2026-10-24)
Gemini blueprint (Csound DJ app) reviewed and rejected. Reframed as an arrange-and-render mix
builder with no beatmatching. See DECISIONS.md.

## Phase 1 — v0.1 working app ✅ (2026-10-24)
Engine + single-page UI + Mac/Windows launchers + GitHub Actions build workflow. Tested with
synthetic audio. Delivered as `VibeMix.zip`.

## Phase 3 — Quality-of-life ✅ (2026-10-24, done ahead of Phase 2 under Gabe's blanket pre-approval)
- [x] Waveform strip per song so trims are set by eye (drag handles + click-to-listen)
- [x] "Audition this hand-off": render only ~24 s around one transition for a quick listen
- [x] Save / load named mixes as JSON files in `mixes/`
- [x] Drag-to-reorder
- [x] Extra: transparent peak limiter (quiet songs no longer get turned down), Add songs from the
      browser, MP3 copy, Safari-compatible previews, YouTube-chapter tracklist, arrangement JSON
      saved beside every render, double-launch safe, launchers find Python / explain if missing
- [ ] Optional short reverb tail on Breath — skipped on purpose (one more control; revisit only if
      Breath sounds too abrupt in Phase 2 listening)

## Phase 2 — First real mix (NEXT — the only step Claude can't do)
- [ ] Gabe downloads VibeMix-Mac.zip or VibeMix-Windows.zip from
      https://github.com/gwellsart77/vibemix/releases/latest (no Python needed) — or runs the Drive
      launcher (Python guide: https://claude.ai/artifact/MWEkH3XJYemGx1xBAj6ZYS)
- [ ] Gabe adds 3–5 real Bandcamp tracks, uses "Hear this hand-off" on a couple of
      transitions, then renders a short test
- [ ] Gabe listens and reports by ear: blend lengths, whether Dissolve is too subtle/too much,
      whether Breath's silence is too long, loudness feel, whether the waveform trims are easy
- [ ] Fix whatever that surfaces

## Phase 4 — Packaging ✅ (2026-10-24)
- [x] GitHub repo `gwellsart77/vibemix` created (Gabe clicked Create; Claude pushed via session proxy)
- [x] CI builds VibeMix.app + VibeMix.exe on every push to `main` and publishes the Release
      https://github.com/gwellsart77/vibemix/releases/latest (v0.2: Mac 45 MB, Windows 69 MB)
- [x] Python no longer needs to be installed on either machine
- [ ] Gabe downloads the Release zip on one machine and confirms it launches (Gatekeeper / SmartScreen once)

## Parked / not doing
- Beatmatching, BPM sync, key detection as a requirement — parked indefinitely (see rules).
- Live two-deck mode — not doing.
- Mobile app — not doing.
- Reverb on Breath — parked until Phase 2 feedback says it's needed.

## Chat board
| Workstream | Owning chat | Started | Last handoff |
|------------|-------------|---------|--------------|
| v0.1 build + scaffold | "DJ Software" chat #1 (closed) | 2026-10-24 | HANDOFFS/2026-10-24_v0.1-build.md |
| v0.2 build (Phase 3 + hardening) + Phase 4 packaging | "DJ Software" chat #2 | 2026-10-24 | HANDOFFS/2026-10-24_v0.2-build.md |

## Session notes
### 2026-10-24 — chat #1
Concept reframed; v0.1 built and tested (3 synthetic tracks, all transition types, LUFS verified
at −14.0/−14.1/−13.9); Drive scaffold created; Python install guide published; Csound blueprint
archived. Open: Gabe's first real render.

### 2026-10-24 — chat #2
Gabe gave blanket pre-approval to build and enhance within purpose. Reviewed v0.1, found real
bugs (Safari previews, .m4a listed but unreadable, double-launch crash, whole-song gain reduction
on hot tracks), fixed them, and completed all of Phase 3 plus the extras above. Tested: 4 synthetic
songs at 48k mono / 44.1k stereo / 22k / MP3 with transients → LUFS −14.2/−14.4/−14.2/−14.4,
mix peak 0.67, Breath gap silent, MP3 written, audition + peaks + limiter verified; every API
endpoint exercised; UI driven end to end in headless Chromium. Shipped v0.2 to Drive + zip.
Then Phase 4: Gabe created the GitHub repo (Claude's click was blocked by the safety
classifier); Claude pushed `main`, found tag pushes 403 through the proxy, switched CI to
release-on-push-to-main with the tag read from `app.py`; added `.app`-aware folder location and a
Quit button for the windowless packaged app; first run green on both OSes; Release v0.2 verified
(zips downloaded and inspected). Drive mirror synced; `VibeMix.zip` on Drive retired.
Open: Gabe's first real render (Phase 2) — now from the packaged app or the launcher.

### 2026-10-24 — chat #2, later: real-music automation test → v0.2.1
Gabe asked for a full feature test on real songs. Set up `Desktop/VibeMix` on his PC (exe + 7
Creative-Commons tracks from archive.org netlabels, 31 min, −7.5…−18.2 LUFS spread). Drove the
UI in headless Chromium: waveform-derived trims, drag handles, all three hand-offs (blends 5–25 s),
6 auditions, drag-reorder (verified by synthetic DnD events), save → reload → load, render with
MP3 (28:32, 50 s render), Quit. Zero console errors. Output analysis: every song body lands at
−13.6…−14.4 LUFS, peak 0.98, both Breath gaps silent, MP3 length = WAV length. Dissolve blend
regions measured −17/−22 LUFS; traced to the songs' own quiet intros/fade-outs (incoming heads at
−22 LUFS, outgoing tail −26), NOT the filter — a makeup-gain prototype changed nothing, so Dissolve
was left as is. Fixed: dragged trims saved as floats (32.1399…) → rounded; MP3 with a lying header
listed as 4:48 when it plays 4:26 → list uses decoded length once the waveform is cached. v0.2.1.
