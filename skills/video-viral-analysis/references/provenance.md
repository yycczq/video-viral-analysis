# Provenance and boundaries

This is an independently written Agent Skill for interpreting the creative choices in a reference video. It was developed by examining [Hypit](https://github.com/hypit-ai/hypit) and its [reference-video workflow](https://github.com/hypit-ai/hypit/blob/main/skills/hypit/references/creation/reference-video.md).

During development, REA 6.4.0 statically inspected the shipped `@hypit/media-local@0.2.0` package: 33 relevant files, 32 JavaScript/declaration files parsed, zero parsing failures. The package exposes media probing, frames, grids and visual-change candidates. Its source explicitly distinguishes evidence preparation from editorial interpretation. Reading the published `@hypit/hypit@0.3.1` entry point and public workflow documentation supplemented that inspection.

The investigation did not execute Hypit's target code, inspect external model implementations, access private platform ranking systems, or establish a validated virality predictor. REA is not a runtime dependency of this skill. Hypit generation, rendering and video-cloning code is not included.

The implementation uses an existing FFmpeg/FFprobe installation and Pillow. No media binaries, sample user videos, accounts, private investigation records or local machine configuration are distributed.

Automated tests exercise frame/time correspondence, visual changes, audio extraction, narrow time ranges, subtitle formats, user context, invalid inputs and preservation of existing output. Development execution has been verified locally on macOS arm64. The Python implementation and CI configuration target Windows, macOS and Linux; a configured matrix is not itself proof that every operating system has passed.

The evidence helper does not call a model or upload videos. Interpretation is performed by the agent and its selected model service, so local media processing does not imply that all subsequent AI processing is offline. There is no bundled speech-recognition model, video downloader or guarantee of video success.
