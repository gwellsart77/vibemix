# Decisions — VibeMix
Append-only. Newest first. Never edit an old entry — supersede it with a new one.

## 2026-10-24 — GitHub is the source of truth; Release built on every push to main
- **Decision:** `github.com/gwellsart77/vibemix` (public) holds the code. CI builds packaged Mac/Windows apps on every push to `main` and publishes a Release tagged `v<VERSION>` from `app.py`. Drive `vibemix/` is a mirror; `VibeMix.zip` on Drive is retired.
- **Why:** The session's git proxy allows branch pushes but returns 403 on tag pushes, so tag-triggered releases can't be cut from Claude. Release-on-push also makes shipping one step (bump VERSION, push). Public repo = unlimited Actions minutes (macOS runners cost 10× on private) and nothing in the code is secret.
- **Who:** Gabe (approved Phase 4 with full permission), Claude (mechanics).
- **Supersedes:** "Drive folder is the source of truth until a GitHub repo exists".

## 2026-10-24 — Unsigned builds; Gatekeeper/SmartScreen warning accepted
- **Decision:** No Apple Developer ID / Windows code-signing certificate. Mac users right-click → Open once; Windows "More info → Run anyway" once.
- **Why:** Signing costs ~$99/yr (Apple) and more for Windows, for a single-user personal tool. A one-time click is fine.
- **Who:** Claude.
- **Supersedes:** —

## 2026-10-24 — Phase 3 built before Phase 2, under blanket pre-approval
- **Decision:** Build all of Phase 3 (waveform trims, audition, saved mixes, drag reorder) plus hardening (limiter, Range streaming, upload, MP3 copy) before Gabe's first real listen, instead of waiting for feedback.
- **Why:** Gabe: "I'm giving you full autonomy and preapproval to build this and complete it… if you see things that you need to add to make this better, please do." Audition-one-hand-off makes his first listening session faster and more useful, and none of these change the three-hand-off model his feedback is about.
- **Who:** Gabe (mandate), Claude (scope).
- **Supersedes:** roadmap ordering "Phase 3 after Phase 2 feedback".

## 2026-10-24 — Transparent peak limiter instead of whole-song gain reduction
- **Decision:** After levelling to −14 LUFS, run a lookahead peak limiter (2 ms lookahead, 80 ms release, 0.98 ceiling) that only touches the moments that would clip.
- **Why:** v0.1 scaled the entire song down when any peak exceeded 0.98, so a dynamic track ended up quieter than its neighbours — the opposite of what levelling is for. Verified: four test songs land at −14.2 to −14.4 LUFS.
- **Who:** Claude.
- **Supersedes:** v0.1 peak-scaling in `normalize()`.

## 2026-10-24 — No reverb tail on Breath (for now)
- **Decision:** Skip the "optional reverb on Breath" roadmap item.
- **Why:** Adds a control a non-technical user has to understand, for a benefit only ears can judge. Revisit only if Phase 2 listening says Breath feels abrupt.
- **Who:** Claude.
- **Supersedes:** —

## 2026-10-24 — WAV stays the master; MP3 is an optional copy
- **Decision:** The video edit syncs to the WAV. The MP3 checkbox exists purely for studio playback from a phone/speaker.
- **Why:** Lossless master for the edit; a 90-min 16-bit WAV is ~950 MB, which is fine for a video editor but awkward on a phone.
- **Who:** Claude.
- **Supersedes:** —

## 2026-10-24 — M4A/AAC supported only when ffmpeg is present
- **Decision:** libsndfile can't read AAC; VibeMix reads M4A/AAC/WMA through ffmpeg if it's on the PATH, otherwise shows "can't read" with a hint to convert.
- **Why:** v0.1 listed .m4a as supported and would have crashed on it. ffmpeg is a one-line install and keeps the app dependency-free for everyone else.
- **Who:** Claude.
- **Supersedes:** v0.1's AUDIO_EXT list.

## 2026-10-24 — Drive folder is the source of truth until a GitHub repo exists
- **Decision:** `AI Projects/DJ Software/vibemix/` on Google Drive holds the canonical source; `VibeMix.zip` is re-cut from it on every ship.
- **Why:** Gabe wants any chat to pick up where the last left off.
- **Who:** Gabe (ask), Claude (structure).
- **Supersedes:** —

## 2026-10-24 — No skill for this project (for now)
- **Decision:** No custom skill. `CLAUDE.md` + roadmap carry the context; the app is a one-off build, not a repeating procedure.
- **Why:** Skills earn their keep when the same multi-step procedure recurs across chats. Nothing here recurs yet. Revisit if "render a mix from a list" becomes a routine Claude performs.
- **Who:** Claude, on Gabe's question.
- **Supersedes:** —

## 2026-10-24 — Runs on both Mac and Windows from one codebase
- **Decision:** Python + single HTML page, launcher scripts per OS, GitHub Actions builds packaged apps.
- **Why:** "I wanna be able to use this on both my Mac and my PC." — Gabe
- **Who:** Gabe (requirement), Claude (stack).
- **Supersedes:** —

## 2026-10-24 — No beatmatching. Transitions are about mood, not tempo.
- **Decision:** Drop time-stretch, BPM detection and sync entirely. Three hand-offs: Smooth, Dissolve, Breath.
- **Why:** Material is rock / hip-hop / alternative / jazz with vocals — "I'm not mixing house music… something more introspective and laid-back and have playing in the background." — Gabe. Tempo-syncing that material sounds wrong.
- **Who:** Claude proposed, Gabe confirmed by describing the music.
- **Supersedes:** the Csound blueprint's beatmatching requirement.

## 2026-10-24 — Arrange-and-render, not a live DJ app
- **Decision:** Build a mix *builder* (timeline → render one WAV), not a two-deck performance tool.
- **Why:** The real need is a 30–90 min audio file to paint to; performance features are ~80% of a DJ app's complexity and 0% of the need. Gabe chose "Arrange & render" in the questionnaire.
- **Who:** Gabe.
- **Supersedes:** —

## 2026-10-24 — Not using Csound
- **Decision:** Python (numpy / scipy / soundfile / pyloudnorm) instead of Csound.
- **Why:** Csound is a research-grade audio language with no friendly UI path; the Gemini doc's "CsoundCode / CsoundCodeWork" appears to be a garbled "Claude Code / Cowork". Python gets the same DSP with a fraction of the effort.
- **Who:** Claude.
- **Supersedes:** Csound_DJ_App_Blueprint.md §2 (archived).
