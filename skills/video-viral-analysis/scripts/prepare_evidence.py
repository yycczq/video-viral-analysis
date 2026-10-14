#!/usr/bin/env python3
"""Prepare video evidence for Codex; this script does not infer virality."""
import argparse
import hashlib
import json
import math
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
try:
    from PIL import Image, ImageDraw, ImageFont, ImageOps
except ImportError:
    raise SystemExit("Pillow is missing. Install this skill's requirements.txt with your Python interpreter.")


def run(command, timeout=180):
    result = subprocess.run(command, capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=timeout)
    if result.returncode:
        raise ValueError(f"{Path(command[0]).name} failed: {result.stderr[-1600:]}")
    return result


def tool(name, supplied):
    supplied = supplied or os.environ.get(f"VIDEO_VIRAL_{name.upper()}")
    if supplied:
        path = Path(shutil.which(supplied) or supplied).expanduser().resolve()
        if path.is_file() and os.access(path, os.X_OK):
            return str(path)
        raise ValueError(f"Not an executable: {path}")
    found = shutil.which(name)
    if found:
        return str(Path(found).resolve())
    for parent in Path(__file__).resolve().parents:
        path = parent / ".tools/video-analysis" / name / name
        if path.is_file() and os.access(path, os.X_OK):
            return str(path.resolve())
    raise ValueError(f"{name} missing; pass --{name} with an existing executable")


def sha256(path):
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def stamp(seconds):
    ms = round(seconds * 1000)
    return f"{ms // 60000:02d}:{ms // 1000 % 60:02d}.{ms % 1000:03d}"


def seconds(text):
    total = 0.0
    for part in text.replace(",", ".").split(":"):
        total = total * 60 + float(part)
    return total


def load_transcript(filename, duration):
    if not filename:
        return {"status": "not_provided", "segments": []}
    path = Path(filename).expanduser().resolve(strict=True)
    text = path.read_text(encoding="utf-8-sig")
    if path.suffix.lower() in (".srt", ".vtt"):
        pattern = r"(?m)^\s*((?:\d+:)?\d{2}:\d{2}[.,]\d+)\s+-->\s+((?:\d+:)?\d{2}:\d{2}[.,]\d+)[^\n]*\n(.*?)(?=\n\s*\n|\Z)"
        items = [{"start": seconds(m[1]), "end": seconds(m[2]), "text": re.sub(r"<[^>]+>", "", m[3]).strip()} for m in re.finditer(pattern, text, re.S)]
        if not items:
            raise ValueError("No timed SRT/VTT subtitles found")
    elif path.suffix.lower() == ".json":
        raw = json.loads(text)
        if isinstance(raw, dict):
            raw = raw.get("segments", raw.get("words"))
        if not isinstance(raw, list) or not raw or any(not isinstance(i, dict) for i in raw):
            raise ValueError("Transcript JSON needs a nonempty segments/words object list")
        items = [{"start": i.get("start"), "end": i.get("end"), "text": i.get("text", i.get("word", ""))} for i in raw]
    else:
        items = [{"start": None, "end": None, "text": text.strip()}]
    for item in items:
        if not isinstance(item["text"], str) or not item["text"].strip():
            raise ValueError("Empty transcript passage")
        start, end = item["start"], item["end"]
        if start is None and end is None:
            continue
        if any(isinstance(t, bool) or not isinstance(t, (float, int)) or not math.isfinite(t) for t in (start, end)):
            raise ValueError("Transcript timing must be numeric or both null")
        if not 0 <= start <= end <= duration + 0.05:
            raise ValueError("Transcript times exceed selected video duration")
    return {"status": "user_supplied", "source": str(path), "sha256": sha256(path), "segments": items,
            "limitation": "Verify same-video identity and synchronization; transcript alone does not establish sound character."}


def sheets(frames, out):
    font = ImageFont.load_default(size=17)
    names = []
    for offset in range(0, len(frames), 12):
        group = frames[offset:offset + 12]
        image = Image.new("RGB", (1200, math.ceil(len(group) / 4) * 226), "#121822")
        draw = ImageDraw.Draw(image)
        for i, frame in enumerate(group):
            x, y = (i % 4) * 300, (i // 4) * 226
            with Image.open(out / frame["path"]) as source:
                small = ImageOps.contain(source.convert("RGB"), (288, 188))
                image.paste(small, (x + (300 - small.width) // 2, y + (188 - small.height) // 2))
            draw.text((x + 10, y + 194), stamp(frame["seconds"]), font=font, fill="white")
        name = f"contact-{offset // 12 + 1:02d}.jpg"
        image.save(out / name, quality=92)
        names.append(name)
    return names


def times(stderr):
    return [float(x) for x in re.findall(r"\[Parsed_showinfo[^\]]*\]\s+n:\s*\d+.*?pts_time:([\d.eE+\-]+)", stderr)]


def frame_sync_options(ffmpeg):
    # New releases removed -vsync; old releases do not recognize -fps_mode.
    help_text = run([ffmpeg, "-hide_banner", "-h", "full"], 45).stdout
    return ["-fps_mode", "passthrough"] if "-fps_mode" in help_text else ["-vsync", "0"]


def prepare(args):
    source = Path(args.video).expanduser().resolve(strict=True)
    if not source.is_file():
        raise ValueError("Input must be a local video file")
    out = Path(args.out).expanduser().resolve()
    if out.exists():
        raise ValueError("Output already exists; choose a new directory")
    ffmpeg, ffprobe = tool("ffmpeg", args.ffmpeg), tool("ffprobe", args.ffprobe)
    probe = json.loads(run([ffprobe, "-v", "error", "-show_format", "-show_streams", "-of", "json", str(source)], 45).stdout)
    videos = [s for s in probe.get("streams", []) if s.get("codec_type") == "video" and not s.get("disposition", {}).get("attached_pic")]
    if not videos:
        raise ValueError("No video stream found")
    video = videos[0]
    duration = float(probe.get("format", {}).get("duration", video.get("duration", 0)))
    start, end = args.start, duration if args.end is None else args.end
    if not all(math.isfinite(t) for t in (duration, start, end)) or not 0 <= start < end <= duration:
        raise ValueError("Require finite duration and 0 <= start < end <= duration")
    interval = args.every if args.every is not None else max(0.5, (end - start) / 48)
    if not math.isfinite(interval) or interval <= 0:
        raise ValueError("--every must be finite and positive")
    dense_opening = args.every is None and start == 0
    if math.ceil((end - start) / interval) + (6 if dense_opening else 0) > 180:
        raise ValueError("Over 180 samples requested; shorten range or increase --every")
    transcript = load_transcript(args.transcript, duration)
    context = json.loads(Path(args.context).expanduser().read_text(encoding="utf-8-sig")) if args.context else {}
    if not isinstance(context, dict):
        raise ValueError("Context must be a JSON object")
    original_hash = sha256(source)
    sync_options = frame_sync_options(ffmpeg)
    out.mkdir(parents=True)
    try:
        (out / "frames").mkdir()
        step = f"if(lt(t,3),0.5,{interval})" if dense_opening else str(interval)
        select = f"gte(t,{start})*lt(t,{end})*(isnan(prev_selected_t)+gte(t-prev_selected_t,{step}))"
        common = [ffmpeg, "-hide_banner", "-loglevel", "info", "-nostdin", "-i", str(source), "-map", f"0:{video['index']}", "-an"]
        result = run(common + ["-vf", f"setpts=PTS-STARTPTS,select='{select}',scale=640:-2,showinfo", *sync_options, "-frames:v", "180", "-pix_fmt", "yuvj420p", "-q:v", "3", str(out / "frames/frame-%04d.jpg")], max(180, duration * 2))
        sampled = times(result.stderr)
        paths = sorted((out / "frames").glob("*.jpg"))
        if not paths or len(paths) != len(sampled):
            raise ValueError("Decoded frame count and timestamp count differ")
        frames = [{"seconds": t, "path": str(p.relative_to(out))} for t, p in zip(sampled, paths)]
        contacts = sheets(frames, out)
        scene = run(common + ["-vf", f"setpts=PTS-STARTPTS,scale=160:-2,select='gte(t,{start})*lt(t,{end})*gt(scene,0.35)',showinfo", *sync_options, "-f", "null", "-"], max(180, duration * 2))
        audio_streams = [s for s in probe.get("streams", []) if s.get("codec_type") == "audio"]
        audio = {"present": bool(audio_streams), "interpreted": False}
        if audio_streams:
            run([ffmpeg, "-hide_banner", "-loglevel", "error", "-nostdin", "-i", str(source), "-ss", str(start), "-t", str(end - start), "-map", f"0:{audio_streams[0]['index']}", "-vn", "-ac", "1", "-ar", "16000", "-c:a", "pcm_s16le", str(out / "audio.wav")], max(180, duration * 2))
            audio.update({"path": "audio.wav", "source_start_seconds": start})
        if sha256(source) != original_hash:
            raise ValueError("Input changed during preparation; evidence discarded")
        evidence = {"schema": "video-viral-evidence/1", "source": {"path": str(source), "sha256": original_hash, "bytes": source.stat().st_size},
                    "media": {"duration_seconds": duration, "width": video.get("width"), "height": video.get("height"), "avg_frame_rate": video.get("avg_frame_rate")},
                    "coverage": {"start": start, "end": end, "sample_interval_seconds": interval, "opening_dense": dense_opening, "mode": "sampled_frames", "first_sample": sampled[0], "last_sample": sampled[-1]},
                    "frames": frames, "contact_sheets": contacts, "visual_change_candidates": times(scene.stderr), "audio": audio, "transcript": transcript,
                    "context": {"source": "user_supplied" if args.context else "not_provided", "data": context},
                    "tools": {"ffmpeg": run([ffmpeg, "-version"]).stdout.splitlines()[0], "ffprobe": run([ffprobe, "-version"]).stdout.splitlines()[0]},
                    "limitations": ["Sampled frames miss brief events; motion and sound require separate inspection.", "Visual changes are navigation candidates, not semantic edit counts.", "No virality, retention or recommendation metrics are inferred."]}
        (out / "evidence.json").write_text(json.dumps(evidence, ensure_ascii=False, indent=2), encoding="utf-8")
        notes = ["# 视频分析证据", "", f"原文件：`{source}`", f"时长 {duration:.3f} 秒；范围 {start:.3f}–{end:.3f} 秒；提取 {len(frames)} 帧。", "抽样只能用于定位，不能代替完整观看。", "", "## 联系表"]
        notes += [f"\n![时间标注帧]({name})" for name in contacts]
        notes += ["", "## 视觉变化候选", ", ".join(stamp(t) for t in evidence["visual_change_candidates"]) or "没有超过阈值的变化", "", "## 台词证据"]
        for item in transcript["segments"]:
            label = "无时间信息" if item["start"] is None else f"{stamp(item['start'])}–{stamp(item['end'])}"
            notes.append(f"- {label}：{item['text']}")
        if not transcript["segments"]:
            notes.append("没有转录。不得推测台词、语气、音乐或音效。")
        notes += ["", "## 分析状态", "仅完成证据准备；Codex 查看内容后再写 ANALYSIS.md。"]
        (out / "EVIDENCE.md").write_text("\n".join(notes) + "\n", encoding="utf-8")
        print(json.dumps({"output": str(out), "frames": len(frames), "contact_sheets": contacts, "status": "evidence_ready_report_pending"}))
    except BaseException:
        # This directory was created by this invocation; existing outputs are rejected above.
        shutil.rmtree(out, ignore_errors=True)
        raise


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("video")
    parser.add_argument("--out", required=True)
    parser.add_argument("--transcript")
    parser.add_argument("--context")
    parser.add_argument("--start", type=float, default=0)
    parser.add_argument("--end", type=float)
    parser.add_argument("--every", type=float)
    parser.add_argument("--ffmpeg")
    parser.add_argument("--ffprobe")
    try:
        prepare(parser.parse_args())
    except (ValueError, OSError, subprocess.TimeoutExpired, TypeError, KeyError) as error:
        print(f"Error: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
