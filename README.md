# 爆款视频分析 · Viral Video Analysis

[English](README.en.md) · [技能说明](skills/video-viral-analysis/SKILL.md) · [MIT License](LICENSE)

**给 AI 助手一个视频，得到带时间点和具体证据的分析：什么让人停下来、继续看、评论、收藏或转发。**

这是一个可安装的 Agent Skill。媒体工具整理画面、时间轴、声音和字幕，AI 助手理解内容并完成报告。它专注于解释视频的吸引力与传播动机。

## 适合谁用

- 内容创作者：拆解热门短视频的钩子、悬念、兑现和节奏，找到值得学习的表达方式。
- 营销与电商团队：分析广告或产品视频怎样传递价值、激发情绪与互动。
- 编导与剪辑师：把笼统的“节奏好”转成有时间位置的视听解释。
- 学习者与研究者：区分视频里观察到的事实、传播机制假设和真实平台数据。

可分析抖音、TikTok、Reels、Shorts、B 站等平台的可读视频文件。直接分析链接取决于你使用的助手是否已有合适的下载或读取能力。

## 会得到什么

1. 一句话概括视频最强的吸引力。
2. 三到五条主要原因，每条包含“时间片段 → 证据 → 观众可能的反应 → 传播机制”。
3. 开头、推进、兑现、结尾的时间线表。
4. 值得参考的表达方式，以及仍需验证的关键问题。
5. 保存为 `ANALYSIS.md` 的完整报告。

证据不足时少写原因，并明确标注部分分析。没有播放、留存、投放等数据时，输出的是内容层面的走红因素假设，不把算法推荐或观众行为当成已证实的因果。

## 安装技能

需要能够读取文件、查看图片并运行本地命令的 AI 助手。本项目已在 Codex 本地验证；其他支持 Agent Skills 的助手可以按自己的技能安装方式使用，尚未逐一验证。

### 方法一：让 Codex 安装

在 Codex 中发送：

```text
用 $skill-installer 安装这个 GitHub 技能：
https://github.com/yycczq/video-viral-analysis/tree/main/skills/video-viral-analysis
```

安装后使用 `$video-viral-analysis` 调用。如果技能没有出现在列表里，重启 Codex。安装和发现规则见 [OpenAI 官方技能文档](https://learn.chatgpt.com/docs/build-skills)。

### 方法二：手动放进自己的项目

macOS / Linux：

```sh
git clone https://github.com/yycczq/video-viral-analysis.git
mkdir -p /path/to/your-project/.agents/skills
cp -R video-viral-analysis/skills/video-viral-analysis /path/to/your-project/.agents/skills/
```

Windows PowerShell：

```powershell
git clone https://github.com/yycczq/video-viral-analysis.git
New-Item -ItemType Directory -Force -Path "C:\your-project\.agents\skills"
Copy-Item -Recurse "video-viral-analysis\skills\video-viral-analysis" "C:\your-project\.agents\skills\"
```

将示例目录改成自己的项目目录，在该项目中打开 Codex。

## 准备本地工具

需要 **Python 3.10+、Pillow、FFmpeg 和 FFprobe**。技能不会附带二进制，也不会自动安装工具或调用付费模型。

用运行分析脚本的同一个 Python 安装依赖。以下路径以克隆后的仓库为例；若技能安装到别处，用实际技能路径：

```sh
python3 -m pip install -r skills/video-viral-analysis/requirements.txt
ffmpeg -version
ffprobe -version
```

Windows 通常使用 `python` 或 `py`。如果系统需要虚拟环境，先创建并启用环境再安装。FFmpeg/FFprobe 应在 PATH 中；也可以在执行时明确指定路径。FFmpeg 安装入口见 [官方网站](https://ffmpeg.org/download.html)。

## 如何使用

最简单的请求：

```text
用 $video-viral-analysis 分析这个视频为什么可能会火：/path/to/video.mp4
给出具体时间点，解释开头钩子、观看动力、情绪和转发动机。
```

有字幕和数据时：

```text
用 $video-viral-analysis 分析 video.mp4。
字幕是 subtitles.srt，发布背景和指标在 context.json。
区分观察、推测和指标证据，把报告保存为 ANALYSIS.md。
```

只想研究开头：

```text
用 $video-viral-analysis 重点分析前 3 秒为什么能吸引人。
放大检查关键画面，说明证据；不推测未知的声音内容。
```

也可以提供视频链接，但本技能没有内置下载器；助手无法读取链接时需要本地文件。

### 单独运行证据工具

在仓库根目录运行：

```sh
python3 skills/video-viral-analysis/scripts/prepare_evidence.py video.mp4 \
  --out video-analysis-results/first
```

添加字幕和背景信息：

```sh
python3 skills/video-viral-analysis/scripts/prepare_evidence.py video.mp4 \
  --out video-analysis-results/with-context \
  --transcript subtitles.srt --context examples/context.json
```

局部加密取帧：

```sh
python3 skills/video-viral-analysis/scripts/prepare_evidence.py video.mp4 \
  --out video-analysis-results/opening --start 0 --end 3 --every 0.25
```

`--end` 不得超过视频时长。输出目录必须是新目录，已有结果不会覆盖。若工具不在 PATH 中，增加 `--ffmpeg /path/to/ffmpeg --ffprobe /path/to/ffprobe`，或设置 `VIDEO_VIRAL_FFMPEG` / `VIDEO_VIRAL_FFPROBE` 环境变量。

脚本产生：

| 文件 | 用途 |
| --- | --- |
| `evidence.json` | 原视频摘要、实际帧时间、覆盖范围和证据边界 |
| `EVIDENCE.md` | 联系表和台词证据索引 |
| `contact-*.jpg` | 带时间标签的画面概览 |
| `frames/` | 可单独放大的抽样画面 |
| `audio.wav` | 视频有声音时提取的单声道音轨 |

**单独运行脚本只准备证据，不会自动得到“为什么会火”的报告。** 把结果交给已安装该技能的 AI 助手，实际查看画面与字幕后才会生成 `ANALYSIS.md`。

字幕支持 SRT、VTT、无时间纯文本，或 `{"segments":[{"start":0,"end":1.5,"text":"台词"}]}` / `words` JSON。字幕必须来自同一视频。示例背景文件中的未知指标保留 `null` 即可。

## 能力边界

- 没有内置语音识别；语音内容需要助手已有的音频能力或同视频字幕。
- 抽样可能漏掉短暂动作，需要对关键片段加密检查。
- 不预测爆款概率，不保证播放量，也不生成或复制视频。
- 证据准备在本地完成，不调用模型或上传视频；后续 AI 分析的处理方式由你的助手和模型服务决定。

## 测试与贡献

```sh
python3 -m unittest discover -s tests -v
```

媒体测试需要 FFmpeg/FFprobe，找不到时会明确跳过。测试使用临时生成的素材，不依赖用户视频。已在 macOS arm64 验证；其他平台的实际结果以 CI 为准。

欢迎通过 Issue 或 Pull Request 提供问题、跨平台反馈与改进。请提供可复现的最小样例，避免提交自己的账号配置或用户素材。

## 来源与许可

工作流受到 [Hypit](https://github.com/hypit-ai/hypit) 的参考视频分析方法启发，开发时用 REA 检查过其发布媒体模块。这里的实现独立编写，使用时不需要 Hypit 或 REA。详细说明见 [来源与边界](skills/video-viral-analysis/references/provenance.md)。

[MIT License](LICENSE) 允许使用、修改和分发本项目。
