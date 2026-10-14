"""Portable tests with generated media; never require a private video or model API."""
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
import wave

from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "skills/video-viral-analysis/scripts/prepare_evidence.py"
spec = importlib.util.spec_from_file_location("prepare_evidence", SCRIPT)
helper = importlib.util.module_from_spec(spec)
spec.loader.exec_module(helper)


class SubtitleTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name)

    def tearDown(self):
        self.temporary.cleanup()

    def load(self, name, content):
        path = self.root / name
        path.write_text(content, encoding="utf-8")
        return helper.load_transcript(path, 6)

    def test_srt_and_vtt_preserve_times_and_text(self):
        srt = self.load("captions.srt", "1\n00:00:00,000 --> 00:00:01,500\n中文 <b>caption</b>\n\n2\n00:00:02,000 --> 00:00:04,000\nSecond line\n")
        self.assertEqual(srt["segments"], [{"start": 0, "end": 1.5, "text": "中文 caption"}, {"start": 2, "end": 4, "text": "Second line"}])
        vtt = self.load("captions.vtt", "WEBVTT\n\n00:00.000 --> 00:01.500 align:start\nHello\n")
        self.assertEqual(vtt["segments"][0]["end"], 1.5)

    def test_words_and_untimed_text_have_distinct_semantics(self):
        words = self.load("words.json", json.dumps({"words": [{"start": 0, "end": .5, "word": "Hello"}]}))
        self.assertEqual(words["segments"][0]["text"], "Hello")
        text = self.load("plain.txt", "No speech timing available.")
        self.assertIsNone(text["segments"][0]["start"])
        self.assertEqual(helper.load_transcript(None, 6)["status"], "not_provided")

    def test_malformed_or_out_of_video_subtitles_are_rejected(self):
        cases = [{"start": 0, "end": 7, "text": "Wrong video"}, {"start": 2, "end": 1, "text": "Reversed"},
                 {"start": 0, "end": None, "text": "Missing end"}, {"start": True, "end": 1, "text": "Boolean"},
                 {"start": 0, "end": 1, "text": None}, {"start": 0, "end": float("nan"), "text": "NaN"}]
        for item in cases:
            with self.subTest(item=item), self.assertRaises(ValueError):
                self.load("bad.json", json.dumps({"segments": [item]}))


class MediaTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        try:
            cls.ffmpeg = helper.tool("ffmpeg", None)
            cls.ffprobe = helper.tool("ffprobe", None)
        except ValueError as error:
            raise unittest.SkipTest(str(error))
        cls.temporary = tempfile.TemporaryDirectory()
        cls.root = Path(cls.temporary.name)
        cls.fixture = cls.root / "测试 video.mp4"
        command = [cls.ffmpeg, "-hide_banner", "-loglevel", "error", "-nostdin", "-f", "lavfi", "-i", "color=c=red:s=180x320:d=2:r=12",
                   "-f", "lavfi", "-i", "color=c=blue:s=180x320:d=2:r=12", "-f", "lavfi", "-i", "color=c=green:s=180x320:d=2:r=12",
                   "-f", "lavfi", "-i", "sine=frequency=440:duration=6", "-filter_complex", "[0:v][1:v][2:v]concat=n=3:v=1:a=0[v]",
                   "-map", "[v]", "-map", "3:a", "-c:v", "libx264", "-pix_fmt", "yuv420p", "-c:a", "aac", "-shortest", str(cls.fixture)]
        result = subprocess.run(command, capture_output=True, text=True, timeout=60)
        if result.returncode:
            cls.temporary.cleanup()
            raise RuntimeError(result.stderr)

    @classmethod
    def tearDownClass(cls):
        cls.temporary.cleanup()

    def prepare(self, name, *arguments, source=None, success=True):
        output = self.root / name
        command = [sys.executable, str(SCRIPT), str(source or self.fixture), "--out", str(output), "--ffmpeg", self.ffmpeg, "--ffprobe", self.ffprobe, *arguments]
        result = subprocess.run(command, capture_output=True, text=True, timeout=60)
        self.assertEqual(result.returncode == 0, success, result.stderr)
        return output

    def test_frames_match_source_times_cuts_and_audio(self):
        out = self.prepare("whole")
        evidence = json.loads((out / "evidence.json").read_text(encoding="utf-8"))
        self.assertEqual(evidence["visual_change_candidates"], [2.0, 4.0])
        for frame in evidence["frames"]:
            with Image.open(out / frame["path"]) as image:
                rgb = image.getpixel((image.width // 2, image.height // 2))
            dominant = 0 if frame["seconds"] < 2 else 2 if frame["seconds"] < 4 else 1
            self.assertGreater(rgb[dominant], max(v for i, v in enumerate(rgb) if i != dominant) + 60)
        with wave.open(str(out / "audio.wav")) as audio:
            self.assertEqual(audio.getframerate(), 16000)
            self.assertEqual(audio.getnchannels(), 1)
            self.assertAlmostEqual(audio.getnframes() / 16000, 6, delta=.1)
        self.assertEqual(evidence["source"]["sha256"], helper.sha256(self.fixture))
        self.assertEqual(evidence["transcript"]["status"], "not_provided")
        self.assertFalse((out / "ANALYSIS.md").exists())

    def test_dense_range_preserves_context_and_previous_output(self):
        captions = self.root / "captions.srt"
        captions.write_text("1\n00:00:01,750 --> 00:00:02,250\nTest\n", encoding="utf-8")
        context = self.root / "context.json"
        context.write_text(json.dumps({"views": 123, "completion_rate": None, "audience": "中文用户"}, ensure_ascii=False), encoding="utf-8")
        out = self.prepare("dense", "--start", "1.75", "--end", "2.5", "--every", ".25", "--transcript", str(captions), "--context", str(context))
        original = (out / "evidence.json").read_bytes()
        evidence = json.loads(original)
        self.assertEqual([f["seconds"] for f in evidence["frames"]], [1.75, 2, 2.25])
        self.assertEqual(evidence["context"]["data"], {"views": 123, "completion_rate": None, "audience": "中文用户"})
        self.assertEqual(evidence["audio"]["source_start_seconds"], 1.75)
        self.prepare("dense", success=False)
        self.assertEqual((out / "evidence.json").read_bytes(), original)

    def test_invalid_ranges_and_audio_only_leave_no_output(self):
        for name, args in [("zero", ["--every", "0"]), ("nan", ["--start", "nan"]), ("reverse", ["--start", "3", "--end", "2"]), ("too-many", ["--every", ".001"])]:
            with self.subTest(name=name):
                out = self.prepare(name, *args, success=False)
                self.assertFalse(out.exists())
        audio = self.root / "audio.wav"
        subprocess.run([self.ffmpeg, "-hide_banner", "-loglevel", "error", "-i", str(self.fixture), "-vn", str(audio)], check=True, capture_output=True, timeout=30)
        out = self.prepare("audio-only", source=audio, success=False)
        self.assertFalse(out.exists())

    def test_environment_tool_paths(self):
        variable = "VIDEO_VIRAL_FFMPEG"
        previous = os.environ.get(variable)
        os.environ[variable] = self.ffmpeg
        try:
            self.assertEqual(helper.tool("ffmpeg", None), self.ffmpeg)
        finally:
            if previous is None:
                os.environ.pop(variable, None)
            else:
                os.environ[variable] = previous

    def test_output_path_with_unicode_and_spaces(self):
        out = self.prepare("中文 result", "--start", "0", "--end", "1", "--every", ".5")
        self.assertEqual(len(json.loads((out / "evidence.json").read_text(encoding="utf-8"))["frames"]), 2)


if __name__ == "__main__":
    unittest.main()
