---
name: video-reverse
description: Reverse engineer ANY video - take it apart and rebuild a copy that looks 100% the same, in code. Downloads the video, finds every cut, grabs frames into contact sheets, reads the on-screen text and the spoken script, measures the sound, then writes a recipe and rebuilds the film with HyperFrames and scores the copy against the original until it matches. Use when the user says "reverse engineer this video", "remake this exactly", "copy this video", or "make one just like this".
---

# video-reverse: take any video apart, rebuild it 100% the same

GOAL: the copy must look the SAME as the original - same cuts at the same times,
same words on screen, same colours, same motion, same sound level. Not "same style" -
the same video, rebuilt in code so it can be re-rendered and changed.

Two halves:
- **Measured half** (scripts do it): download, cuts, frames, script, sound. Exact numbers.
- **Eye half** (you do it): read the contact sheets to see art, colours, captions, camera.
Then you WRITE the recipe, BUILD the copy, and SCORE it until it matches.

## Tools in this skill (`scripts/`)

| Script | Job | Out |
|---|---|---|
| `teardown.py` | Pull the video apart (steps 1-5) | `teardown.json`, `frames/`, `contact-sheet-*.jpg`, `script.txt` |
| `compare.py` | Score the copy vs the original (step 9) | `compare.json`, `compare-sheet-*.jpg` |

Needs: `ffmpeg` at `C:\ffmpeg\bin`, `python -m yt_dlp` (install once: `python -m pip install -U yt-dlp pillow`).
Rebuild uses the video-automation skills (HyperFrames). All paths absolute on Windows.

## The route

### 1-5. Tear it apart (one command)
```
python C:\Users\Ahmad\.kiro\crew\skills\video-reverse\scripts\teardown.py <url-or-file> ^
  --out C:\Users\Ahmad\.kiro\crew\workspace\videos\<name>\_ref --name ref --sps 1
```
- URL -> yt-dlp downloads the MP4 + English subtitles.
- Local file -> pass the full path; a sibling `ref.srt` is picked up if present.
- Prints: aspect + fps + duration, shot count + avg/min/max shot length,
  script word count + words-per-minute, LUFS + true peak, how many contact sheets.
- `--sps 2` for fast-cut videos (2 frames/sec); `--scene 0.2` makes cut detection more sensitive.

### 6. Read the sheets with your EYES (the part only you can do)
Open each `contact-sheet-*.jpg` with the image tool. For the whole video note:
- **Format**: 2D cartoon / 3D / stickman / map / real footage / slides. (Picks the rebuild skill.)
- **Palette**: the 4-6 main colours (background, ink, accent). Pull exact hexes.
- **Captions**: font look, size, position, colour, one line or more, karaoke or not.
- **Camera**: still, slow push, zoom, pan, cuts vs continuous. Does it ever cut hard?
- **Repeats**: recurring character, logo, lower-third, intro/outro card.
- **Per shot**: what is on screen in each shot from the shot list in `teardown.json`.
Write what you SEE, with the frame number. A thumbnail can't tell you motion - the
sheets are sampled 1/sec, so open a short frame range if you must judge a move.

### 7. Write the recipe `recipe.md`
In `videos\<name>\recipe.md`. Two parts, so another run can rebuild without the chat:
- **Rules** (whole film): aspect, fps, palette hexes, caption style, camera rules,
  voice gender + wpm, music mood, target LUFS (copy the measured one).
- **Scene plan** (one row per shot from `teardown.json`): shot #, start-end, what's on
  screen, the exact on-screen text, the spoken line (from `script.txt`), the camera move.
Exact text and exact times are what make it 100%, not a vibe.

### 8. Build the copy
Route by the format you saw to the right skill (see `video-automation\SKILL.md`):
cartoon/history -> `stickman-history-video`; how-it-works -> `3d-explainer-video`;
news/doc -> `ai-news-video`; map -> `map-video`; intro -> `3d-motion-video`.
Feed it the recipe: same script text, same shot times, same palette, same captions,
same aspect, same target LUFS. Make the copy the same LENGTH first - that's the easy 50%.

### 9. Score it, then loop
```
python C:\Users\Ahmad\.kiro\crew\skills\video-reverse\scripts\compare.py ^
  --orig C:\Users\Ahmad\.kiro\crew\workspace\videos\<name>\_ref ^
  --copy C:\Users\Ahmad\.kiro\crew\workspace\videos\<name>\renders\<name>.mp4 ^
  --out  C:\Users\Ahmad\.kiro\crew\workspace\videos\<name>\_cmp --sps 1
```
Prints an overall match %, plus colour / brightness / layout %, the duration delta,
and the exact seconds that scored below 80%. Open each `compare-sheet-*.jpg`
(original on top, copy on the bottom) and fix the weak seconds:
- colour low -> fix palette hexes / background.
- layout low -> move the element to where the original has it; match the camera framing.
- bright low -> match exposure / darkness of the shot.
- duration delta -> re-time shots / trim the script.
Rebuild, score again. **Stop when overall >= 90% and no second below 80%,** or after
4 loops (then report the best score and what still differs). Good enough for "100%"
to the eye is layout + colour + timing all matching; pixel-identical is impossible
when assets are redrawn, so the score is the honest measure.

## Rules
- You can't WATCH a video or hear it; you read frames (sheets) and the subtitle text,
  and you MEASURE sound with ffmpeg. Say "measured", never "I heard it".
- Don't bypass a login / paywall / CAPTCHA to download. If yt-dlp is blocked, ask for a file.
- Copying a video 1:1 is for learning / a private remake. Don't re-publish someone else's
  video as your own, and keep any logo/character the original owns out of a copy you post -
  rebuild the STYLE, swap the owned assets. Flag this if the user wants to publish.
- Everything the scripts can't see (motion feel, art, captions) you must read off the
  sheets with your eyes before you claim the copy matches.

## Tested
<!-- fill after first real run: original title, match %, loops, LUFS orig vs copy -->
