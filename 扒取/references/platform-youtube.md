# YouTube 抓取流程（yt-dlp）

> **状态**：🟡 半封闭 —— 视频元数据和下载均依赖 yt-dlp，但中国大陆环境下必须同时满足 **代理 + 登录 cookie** 才能绕过 Google 的 bot 验证。
>
> **实测时间**：2026-09-12（代理已验证可用，列表可拿，单视频因 bot 验证待 cookie）

## 前置条件

| 项 | 要求 | 说明 |
|---|---|---|
| 代理 | ✅ 必须 | 本地 socks5/http 代理，例：`socks5://127.0.0.1:10808`；直连 YouTube IP 段会被 reset |
| yt-dlp | ✅ 必须 | `pip install yt-dlp`，建议 2026.08+ |
| 登录 cookie | ⚠️ 通常需要 | 用 `--cookies-from-browser chrome` 或 `--cookies cookies.txt`；否则单视频触发「Sign in to confirm you’re not a bot」 |
| JS runtime | ⚠️ 推荐 | yt-dlp 新版会提示 `No supported JavaScript runtime`，可忽略或加 `--js-runtimes node:<node路径>` |

## 账号格式

YouTube 博主主页常见形式：

- `@handle`：`https://www.youtube.com/@示例博主`
- `@handle/shorts`：`https://www.youtube.com/@示例博主/shorts`
- `@handle/videos`：`https://www.youtube.com/@示例博主/videos`
- channel ID：`https://www.youtube.com/channel/UC6xsUYK3eJyrCvw3kkDCifA`
- playlist：`https://www.youtube.com/playlist?list=PL...`

> **Shorts + 长视频都要**：建议分别抓 `/shorts` 和 `/videos`（或 `/streams`），再合并去重。

## 步骤 1：获取 cookie

### 🔴 铁律：绝对禁止 `--user-data-dir` / Playwright 指向真实 Chrome profile

**绝对禁止**以下三种做法（违反会导致用户 Chrome 扩展被清空，详见 `references/chrome-extension-recovery.md`）：

1. ❌ `chrome.exe --user-data-dir="C:\Users\<你的用户名>\AppData\Local\Google\Chrome\User Data"`
2. ❌ 用 NTFS junction 把真实 User Data 软链到项目目录再启动 Chrome
3. ❌ Playwright `launch_persistent_context(user_data_dir=<真实 Chrome 路径>)`

**唯一安全做法**：在项目目录下新建独立 profile 目录（如 `login_profile/`），用专用 Playwright 窗口让用户登录一次，导出 `cookies.txt`，后续只复用 cookies.txt。

### 方式 A：专用 Playwright 登录窗口导出 cookies.txt（✅ 推荐）

完整脚本见 `scripts/youtube_login.py`。流程：

1. 在项目目录下新建空 `login_profile/`
2. Playwright 启动 Chrome 指向 `login_profile/`（**不是**真实 User Data）
3. 弹窗 → 用户手动登录 YouTube
4. 脚本自动检测登录态（cookie 数量变化）→ 导出 `youtube_cookies.txt`
5. 关闭浏览器窗口
6. 后续 yt-dlp 只用 `youtube_cookies.txt`，不再启动 Chrome

### 方式 B：Chrome 扩展导出 cookies.txt

Chrome 安装扩展 **Get cookies.txt LOCALLY**，导出 `youtube.com` 的 Netscape cookies.txt 到项目目录，然后：

```bash
yt-dlp --proxy "socks5://127.0.0.1:10808" \
  --cookies "<项目>/youtube_cookies.txt" \
  ...
```

### 方式 C：yt-dlp 直接读取 Chrome cookie（Chrome 必须关闭 + App-Bound Encryption 风险）

```bash
yt-dlp --proxy "socks5://127.0.0.1:10808" \
  --cookies-from-browser chrome \
  --print "%(id)s|%(title)s|%(view_count)s|%(upload_date)s|%(duration)s|%(webpage_url)s" \
  "https://www.youtube.com/shorts/<VIDEO_ID>"
```

**注意**：Chrome 137+ App-Bound Encryption 会让 `--cookies-from-browser` 失败，必须用方式 A 或 B 替代。

> cookies.txt 属于敏感文件，用完建议删除或移入 `99-生成脚本/` 子目录，不要散落在项目根目录。

## 步骤 2：抓取视频列表（flat-playlist）

```bash
PROXY="socks5://127.0.0.1:10808"
CHANNEL="@示例博主"

yt-dlp --proxy "$PROXY" --cookies-from-browser chrome \
  --flat-playlist --lazy-playlist \
  --print "%(id)s|%(title)s|%(view_count)s|%(upload_date)s|%(duration)s|%(webpage_url)s" \
  "https://www.youtube.com/${CHANNEL}/shorts" > shorts_list.txt

yt-dlp --proxy "$PROXY" --cookies-from-browser chrome \
  --flat-playlist --lazy-playlist \
  --print "%(id)s|%(title)s|%(view_count)s|%(upload_date)s|%(duration)s|%(webpage_url)s" \
  "https://www.youtube.com/${CHANNEL}/videos" > videos_list.txt
```

> `--flat-playlist` 下 `view_count` 和 `upload_date` 有时为 `NA`，需要下一步对每个视频单独提取。

## 步骤 3：精确提取元数据 + 筛选

把步骤 2 的 id 列表去重后，对每个 id 跑单视频提取：

```bash
for id in $(cat all_ids.txt); do
  yt-dlp --proxy "$PROXY" --cookies-from-browser chrome \
    --print "%(id)s|%(title)s|%(view_count)s|%(upload_date)s|%(duration)s|%(like_count)s|%(webpage_url)s" \
    "https://www.youtube.com/watch?v=$id" 2>/dev/null
done
```

筛选示例（近 30 天 + 播放 > 3 万）：

```python
from datetime import datetime, timedelta
threshold_date = (datetime.now() - timedelta(days=30)).strftime("%Y%m%d")
# 保留 upload_date >= threshold_date 且 view_count >= 30000 的条目
```

## 步骤 4：下载命中视频（🔴 mp4 + m4a 双落）

**绝对禁止只下 bestaudio**（2026-09-13 TikTok 教训，二次剪辑 / 平台再发布必须有完整视频）。

**🔴 必须用绝对路径 `-o`** 或显式 `cwd=RAW_DIR`（subprocess 路径错位会漏到项目根目录）：

```bash
PROXY="socks5://127.0.0.1:10808"
RAW_DIR="./raw_downloads"
ABS_RAW_DIR="$(realpath "$RAW_DIR")"   # 绝对路径，subprocess 必备
COOKIES="youtube_cookies.txt"

# 1. 下载完整视频 mp4（必须先）
yt-dlp --proxy "$PROXY" --cookies "$COOKIES" \
  -f "best[height<=720][ext=mp4]/best[height<=720]/best" \
  --output "${ABS_RAW_DIR}/%(id)s - %(title)s.%(ext)s" \
  -a video_ids.txt

# 2. 再抽 m4a 音频供 Whisper 转写（同名同源）
yt-dlp --proxy "$PROXY" --cookies "$COOKIES" \
  -x --audio-format m4a \
  --output "${ABS_RAW_DIR}/%(id)s - %(title)s.%(ext)s" \
  -a video_ids.txt
```

如果习惯用 Python 调用 yt-dlp（推荐用，方便后续归集）：

```python
import subprocess
from pathlib import Path

RAW_DIR = Path("/d/proj/02-Whisper转写/raw_downloads")  # 绝对路径
video_id = "dQw4w9WgXcQ"

# ✅ 完整模板
out_abs = str(RAW_DIR / "%(id)s - %(title)s.%(ext)s")
subprocess.run([
    "yt-dlp", "--proxy", "socks5://127.0.0.1:10808",
    "--cookies", "youtube_cookies.txt",
    "-f", "best[height<=720][ext=mp4]/best",
    "-o", out_abs,        # ← 绝对路径
    f"https://www.youtube.com/watch?v={video_id}"
], cwd=str(RAW_DIR))      # ← 双保险
```

> 若出现 403，优先检查 cookie 是否过期（24h 内必查）；若出现 416 续传失败，清理 `.part` / `.tmp` / `.ytdl` 后重试。

## 步骤 5：归集到项目 02 目录

下载完成后，运行 `99-生成脚本/collect_videos_youtube.py`（从本 skill `scripts/` 拷入），脚本会读取 `01-视频清单/videos_index.json` 中的 `video_id` 映射，把 `raw_downloads/` 中的文件重命名为 `{NNN}-{完整标题}.mp4` 并复制到 `02-Whisper转写/视频源文件/`。

## 步骤 6：Whisper 转写 + MD 生成

同其他平台：

```bash
"<whisper venv>/python.exe" "<项目>/99-生成脚本/transcribe_with_whisper.py"
"<whisper venv>/python.exe" "<项目>/99-生成脚本/generate_md_timed.py" --srt-dir "<项目>/02-Whisper转写/转写结果" --md-dir "<项目>/03-逐字稿MD" --author "<博主>" --platform "YouTube"
```

YouTube 视频语言多为英文，Whisper 默认 `auto` 语言检测通常准确；若目标博主固定英文，可在 `transcribe_with_whisper.py` 中显式指定 `language="en"` 提升速度。

## 踩坑记录

| 坑 | 现象 | 解法 |
|---|---|---|
| 直连 YouTube timeout | TCP 无法建立 | 必须开本地代理（v2rayN/Clash 等），并把地址传给 yt-dlp |
| 单视频 403 / bot 验证 | `Sign in to confirm you’re not a bot` | 加 `--cookies-from-browser chrome` 或 `--cookies cookies.txt` |
| Chrome 运行时无法复制 cookie db | `Could not copy Chrome cookie database` | 临时退出 Chrome 再跑；或导出 cookies.txt |
| 没有 JS runtime | 警告 `No supported JavaScript runtime` | 可忽略；若格式缺失则加 `--js-runtimes node:<node路径>` |
| flat-playlist view_count=NA | 列表页拿不到播放量 | 对命中 id 单独跑单视频提取 |
| `/shorts` 分页 403 | `UC... page N: Unable to download API page: HTTP Error 403` | 减少分页深度，或改用 channel 主页 `/videos` + 手动过滤 Shorts |
| 下载到 `.webm` | 音频/视频格式为 webm | Whisper 一般能读，如需 mp4 用 ffmpeg 转封装：`ffmpeg -i input.webm -c copy output.mp4` |
| 标题含 `…` / 连续点 | 文件名生成 `….mp4` | 用统一 `safe()` 函数处理：连续点合并为 `…`，拼接后再清理 `….mp4` |

## 与 B站 / 小红书的差异

| 项 | YouTube | B站 | 小红书 |
|---|---|---|---|
| 列表 API | yt-dlp flat-playlist | `search.bilibili.com/all` | MediaCrawler 创作者 API |
| 登录要求 | 通常需要 cookie | 下载 1080P+ 需要 | 必须扫码登录 |
| 代理要求 | 必须 | 非必须 | 非必须 |
| 视频格式 | webm/mp4 | flv/mp4 | mp4 |
| 播放量字段 | `view_count` | `stat.view` | `interact_info.liked_count` |

## 输出规范

无论 YouTube 原语言是什么，项目目录、文件命名、MD 结构**必须**与视频号/小红书/B站/快手完全一致：

- `01-视频清单/videos_index.json`：含 `video_id`、`title`、`view_count`、`upload_date`、`duration`
- `02-Whisper转写/视频源文件/{NNN}-{完整标题}.mp4`
- `02-Whisper转写/转写结果/{NNN}-{完整标题}_转写.json`
- `03-逐字稿MD/{NNN}-{完整标题}.md`
- `04-原视频脚本改写/{NNN}-{完整标题}-改写脚本.md`
- 编号按筛选维度降序（播放高 → 001）
