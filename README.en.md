# Viral Video Analysis

[中文](README.md) · [Skill](skills/video-viral-analysis/SKILL.md) · [MIT License](LICENSE)

**Give an AI agent a video and get a timestamped explanation of what could make viewers stop, keep watching, comment, save or share.**

An Agent Skill for creators, marketers, editors and learners. Local tools prepare visual and subtitle evidence; an image-capable agent interprets it and writes the report. It studies hooks, suspense, payoffs, emotions, audiovisual pacing and sharing motives.

## Output

- A one-sentence account of the video's strongest attraction.
- Three to five supported explanations, each tied to a time span and observed evidence.
- A compact timeline and useful creative techniques.
- Unknowns and questions that would improve confidence.
- A complete `ANALYSIS.md` report.

Without audience or distribution data, these are content-level hypotheses, not proven causes of actual virality.

## Install in Codex

Ask Codex:

```text
Use $skill-installer to install:
https://github.com/yycczq/video-viral-analysis/tree/main/skills/video-viral-analysis
```

Alternatively, clone this repository and copy `skills/video-viral-analysis` into your project's `.agents/skills/`. Open Codex in that project. If the skill does not appear, restart Codex. See the [official skill documentation](https://learn.chatgpt.com/docs/build-skills).

Other Agent Skills hosts may use their own installation convention. They need file access, image understanding and command execution; client compatibility beyond the local Codex workflow has not been individually verified.

## Dependencies

Python 3.10+, Pillow 10.1+, FFmpeg and FFprobe:

```sh
python3 -m pip install -r skills/video-viral-analysis/requirements.txt
ffmpeg -version
ffprobe -version
```

Use the same Python interpreter for installation and execution. Windows may use `python` or `py`. Install the media tools using your operating system's package manager or [FFmpeg's download page](https://ffmpeg.org/download.html). No binaries are bundled or automatically installed.

## Use the skill

```text
Use $video-viral-analysis to explain why /path/to/video.mp4 might attract attention and spread.
Give timestamps and evidence for the hook, continued viewing, emotions and sharing motives.
Write the report in English.
```

For a stronger reading, supply same-video subtitles and publishing / metric context. Supported subtitle inputs: SRT, VTT, plain text, JSON `segments` or `words`. Unknown context fields may remain `null`; see [the context example](examples/context.json).

Links work only when your agent already has an authorized way to read or download them. The skill does not bundle a downloader.

## Evidence helper

From the repository root:

```sh
python3 skills/video-viral-analysis/scripts/prepare_evidence.py video.mp4 \
  --out video-analysis-results/first \
  --transcript subtitles.srt --context examples/context.json
```

Omit optional transcript/context flags when unavailable. For a close look:

```sh
python3 skills/video-viral-analysis/scripts/prepare_evidence.py video.mp4 \
  --out video-analysis-results/opening --start 0 --end 3 --every 0.25
```

Select a new output directory; existing work is never overwritten. End time must not exceed video duration. Use `--ffmpeg` / `--ffprobe` or `VIDEO_VIRAL_FFMPEG` / `VIDEO_VIRAL_FFPROBE` when tools are not on PATH.

The helper writes `evidence.json`, `EVIDENCE.md`, timestamped `contact-*.jpg` sheets, individual frames and an `audio.wav` file when audio exists. **Running the helper alone does not generate a semantic report.** Ask the agent to inspect those files using the skill and produce `ANALYSIS.md`.

## Limits

There is no bundled speech recognition model. The agent needs an existing audio-understanding capability or supplied subtitles to interpret speech. Sparse frames can miss short events; revisit important sequences. No viral probability, revenue forecast or video-success guarantee is provided. Video generation and cloning are outside scope.

Evidence preparation is local and performs no model calls or uploads. Subsequent interpretation follows the agent's chosen model service; local preparation does not imply that all AI processing is offline.

## Tests and contributions

```sh
python3 -m unittest discover -s tests -v
```

Media tests generate temporary fixtures and require FFmpeg/FFprobe; they explicitly skip when tools are missing. Local execution has been verified on macOS arm64. Other operating system results should be judged from actual CI runs.

Issues and pull requests are welcome. Include a minimal reproducible example without account settings or private user media.

## Attribution

Inspired by [Hypit's reference-video workflow](https://github.com/hypit-ai/hypit). REA was used during development to inspect a shipped media package. This independently written implementation requires neither Hypit nor REA. See [provenance](skills/video-viral-analysis/references/provenance.md).

Released under the [MIT License](LICENSE).
