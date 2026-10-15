# TikTok 抓取完整指南（博主视频全量扒取）

> 状态：✅ 已跑通（2026-09-13 实测 9 条 @示例博主）
> 关键依赖：`yt-dlp + --impersonate Chrome-136 + curl_cffi 0.16 + socks5 代理`

## 路径速查

| 阶段 | 命令 |
|---|---|
| 列表抓取 | `yt-dlp --proxy socks5://127.0.0.1:10808 --flat-playlist --no-warnings --dump-json --skip-download "https://www.tiktok.com/@<user>"` |
| 单视频音频 | `yt-dlp --proxy socks5://127.0.0.1:10808 --impersonate Chrome-136 -x --audio-format m4a -o "<seq>-<title>.%(ext)s" "<video_url>"` |
| **单视频 mp4 + m4a（🔴 推荐）** | `yt-dlp --proxy socks5://127.0.0.1:10808 --impersonate Chrome-136 -f "download/h264_720p/download" -o "<abs_path>.mp4" "<video_url>"` 后 `-x --audio-format m4a` 同名抽音频 |
| Whisper 转写 | `HF_HUB_OFFLINE=1 python transcribe_with_whisper.py`（项目内脚本） |

## 已验证实测结论（2026-09-13）

| 验证项 | 结果 |
|---|---|
| 直连 `tiktok.com/@<user>` | ❌ TCP timeout（IP 段屏蔽） |
| 经 socks5 代理 `127.0.0.1:10808` | ✅ 可达 |
| `yt-dlp --flat-playlist` 主页列表 | ✅ 拿 id/title/view_count/timestamp |
| `yt-dlp` 单视频（**无 impersonate**） | ❌ `Unexpected response from webpage request` |
| `yt-dlp --impersonate Chrome-136` 单视频 | ✅ 完整下载（视频/音频均可） |
| Whisper tiny/cpu/int8 转写 | ✅ 完成（9/9） |
| 多语种检测（en/pt） | ✅ Whisper 自动识别 |

## 关键卡点与解决方案

### 卡点 1：单视频下载必须 impersonate

**症状**：`ERROR: [TikTok] <id>: Unexpected response from webpage request`

**根因**：TikTok 2024 年起对新会话做 JA3/JA4 指纹 + 行为特征检测，非浏览器特征一律拒绝。

**解决**：
```bash
# 1. 装 curl_cffi（必须在 yt-dlp 用的 Python 上，3.12）
"C:/Users/<你的用户名>/AppData/Local/Programs/Python/Python312/python.exe" -m pip install curl_cffi

# 2. 加 --impersonate Chrome-136（其他可用：Edge-101 / Firefox-133）
yt-dlp --impersonate Chrome-136 ...
```

**注意事项**：
- `curl_cffi` 必须装在 yt-dlp 用的解释器（`yt-dlp.exe` 默认 Python 3.12）
- 如果之前装在 3.13，`yt-dlp --list-impersonate-targets` 会显示「unavailable」
- `pip install` 看到路径是 `Python313` 而不是 `Python312` 就装错了

### 卡点 2：Whisper 模型 `HF_HUB_OFFLINE`

**症状**：`faster_whisper` 报「无法连接 huggingface.co」或「未找到 tiny 模型」

**解决**：跑转写前 **必须** `set HF_HUB_OFFLINE=1`（或 export `HF_HUB_OFFLINE=1`），否则会卡在联网校验模型。

模型本地路径：`C:\Users\<你的用户名>\.cache\huggingface\hub\models--Systran--faster-whisper-tiny`

### 卡点 3：内容特征决定改写策略

**实测发现**：TikTok 猫猫类账号 90%+ 是 **15 秒纯视觉 + 背景音乐 + 字幕** 类，**几乎没有口播**。

改写策略必须从「口播脚本」调整为「**视觉规律拆解 + 字幕多语种策略**」：
- Hook：用视觉悬念替代口播钩子
- Body：拆解 hashtag 套路 + 字幕多语种策略 + 选音频策略
- CTA：让评论区驱动（不强行收口）

### 卡点 4：🔴 视频 + 音频必须双落（2026-09-13 教训）

**症状**：早期实现为了"省空间"，只下 `-x --audio-format m4a`（400KB/条），结果没有任何完整视频可供二次剪辑 / 参考画面 / 平台再发布。

**修正**：默认下完整视频 mp4（TikTok `download` 单文件最稳），同时保留 m4a 供 Whisper 转写：

```bash
# 1. 下完整 mp4
yt-dlp --proxy socks5://127.0.0.1:10808 \
       --impersonate Chrome-136 \
       -f "download/h264_720p/download" \
       -o "<abs_path>.mp4" \
       "<video_url>"

# 2. 再抽 m4a 供 Whisper（不下载视频流）
yt-dlp --proxy socks5://127.0.0.1:10808 \
       --impersonate Chrome-136 \
       -x --audio-format m4a \
       -o "<abs_path>.%(ext)s" \
       "<video_url>"
```

**根因**：TikTok 视频短（15-60s）+ 质量本就 720p，单条 mp4 1-2MB，9 条总共 ~10MB —— 跟 400KB×9 的音频比也就多 7MB，**这个开销完全可接受**。**禁止**再走"只下音频"路径。

### 卡点 5：🔴 `-o` 必须用绝对路径（2026-09-13 教训）

**症状**：批量 9 条显示"[download] 100%"成功，目录却找不到 mp4。最后发现 8 个视频**全部漏到项目根目录**（subprocess 继承父 cwd）而不是 `视频源文件/` 子目录。

**修正**：

```python
import subprocess
from pathlib import Path

VIDEO_DIR = Path("/d/.../02-Whisper转写/视频源文件")
out_abs = str(VIDEO_DIR / "001-xxx.mp4")  # 绝对路径

subprocess.run([
    "yt-dlp", ...,
    "-o", out_abs,  # ✅ 绝对路径
    video_url
], cwd=str(VIDEO_DIR))  # ✅ 显式 cwd 双保险
```

**根因**：Python `subprocess.run()` 默认继承父 cwd，若父 cwd 不是视频目录，相对路径 `-o "001.mp4"` 就会写到默认 cwd（项目根）。所有爬虫脚本都用这个 pattern 写。

## 已知账号适配

| 账号 | 内容类型 | 改写策略 |
|---|---|---|
| @示例博主 | AI 猫猫视觉 + 多语种字幕 | 视觉规律 + 多语种字幕策略 |

## 反爬升级应对

| 升级 | 应对 |
|---|---|
| TikTok JA3/JA4 指纹变化 | 升级 `yt-dlp` 到最新版 + 切更高版本 impersonate |
| 数据中心 IP 被封 | 换 v2rayN 节点（住宅 IP 更稳） |
| 列表能抓但单视频 403 | 加 `--cookies-from-browser <browser>`（注意 Chrome profile 保护铁律） |
| 整体 block | 改用第三方数据平台（飞瓜 / 新榜 TikTok 板块，付费） |

## 跨平台一致性

所有产出仍走标准结构（见 SKILL.md「🔴 跨平台一致性铁律」）：
- `01-视频清单/selected_videos.json` + `README.md`
- `02-Whisper转写/视频源文件/{NNN}-{title}.mp4`（🔴 **完整视频，2026-09-13 修正**）+ 同名 `.m4a` 音频 + `转写结果/{NNN}-{title}_转写.json`
- `03-逐字稿MD/{NNN}-{title}.md`
- `04-改写脚本/{NNN}-{title}_改写.md`（英文）
- `99-生成脚本/{download_videos,transcribe_with_whisper,generate_md_timed}.py`（🔴 `generate_md_timed.py` 替代已废弃的 `md_generator.py`）

唯一差异：TikTok 抓取脚本不复用 `collect_videos_<platform>.py`（MediaCrawler 类不适用），而是独立的 `download_videos.py` 内嵌 `yt-dlp` 调用（MD 一律用 `generate_md_timed.py`）。