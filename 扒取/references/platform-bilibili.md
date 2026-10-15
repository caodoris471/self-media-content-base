# B站扒取专篇（博主视频扒取）

B站扒取**走 API + yt-dlp 组合方案**——单视频接口 + web search 页面绕开 WBI 风控 + yt-dlp 用低画质避开登录限制。

> 本文档是 `博主视频全量扒取/SKILL.md` 步骤 3「获取视频」的 **B站专属分支**，遇到 B站任务时按本文件执行。

## TL;DR（30 秒版）

| 项目 | 配置 |
|---|---|
| **账号信息** | `api.bilibili.com/x/space/acc/info?mid=<UID>` |
| **视频列表** | ❌ `arc/search` 持续 -799 风控；✅ 用 `search.bilibili.com/all` web 页面（不限速） |
| **单视频元数据** | ✅ `api.bilibili.com/x/web-interface/view?bvid=BVxxx`（最稳） |
| **下载视频** | ✅ `yt-dlp -f "30080+30216/30016/30011"`（低画质绕登录） |
| **播放量 / 点赞 / 时长 / 发布时间** | 单视频接口返回的 `data.stat.view/like/duration/pubdate` |
| **ASR** | Whisper tiny + cpu + int8 + offline（参考小红书章节 4.2） |

---

## 0. 账号信息探测

```bash
curl -A "Mozilla/5.0" "https://api.bilibili.com/x/space/acc/info?mid=<UID>"
```

返回字段：`name`（昵称）、`mid`（UID）、`sign`（签名）、`fans`（粉丝数）、`archive_count`（视频总数）。

---

## 1. 视频列表获取（**关键：API 全风控，必须用 web search 兜底**）

### 1.1 ❌ 失败路径：传统 API

```bash
curl "https://api.bilibili.com/x/space/arc/search?mid=<UID>&pn=1&ps=50&order=pubdate"
```

返回：`{"code":-799,"message":"请求过于频繁，请稍后再试"}`（HTTP 200 但业务错误）

**根因**：B站 2024 年起对 `arc/search` 接口加了 **WBI 签名机制**——必须在 URL 加 `w_rid` 和 `wts` 两个参数（值由复杂 MD5+二次混淆生成）。光有 cookie 不够，必须实现签名算法。详见 `https://github.com/SocialSisterYi/bilibili-API-collect`。

### 1.2 ✅ 推荐路径：web search 页面 + 单视频接口交叉验证

```bash
# Step 1: WebFetch 抓 search web 页面（不限速）
# URL: https://search.bilibili.com/all?keyword=<UP主昵称>&order=click&page=1
# 返回 HTML，包含前 ~50 条视频的 BVID + 标题 + 播放量

# Step 2: 用单视频接口批量验证精确播放量 + 发布日期
for bvid in "BV1xxx" "BV1yyy" ...; do
  curl "https://api.bilibili.com/x/web-interface/view?bvid=$bvid"
done
```

**实测耗时**：search web 页面 1 次 WebFetch + 10 个 BV 验证 ≈ 1 分钟。

### 1.3 单视频接口返回字段

```json
{
  "code": 0,
  "data": {
    "bvid": "BV1d1vUBUE54",
    "title": "【示例博主】我们做了台魔法钢琴…",
    "pubdate": 1767261600,         // 发布时间戳（秒）
    "duration": 851,               // 时长（秒）
    "stat": {
      "view": 24996664,            // 播放量
      "like": 1746886,             // 点赞数
      "favorite": 300000,          // 收藏
      "share": 50000,              // 分享
      "comment": 22602             // 评论
    }
  }
}
```

---

## 2. 视频下载（yt-dlp 实战）

### 2.1 推荐画质选择

```bash
yt-dlp -f "30080+30216/30016/30011" \
  --merge-output-format mp4 \
  --no-part --no-warnings --no-playlist \
  -o "<目标路径>.mp4" \
  "https://www.bilibili.com/video/BVxxx/"
```

**为什么用 30080+30216**：
- 4K 超高清 / 1080P 高码率要求登录大会员
- 30080 = 720P 视频流（约 30-60MB/分钟）
- 30216 = 64kbps 音频流（足够 Whisper）
- Whisper tiny 转写 **不需要 1080P+**

### 2.2 常见错误 + 解决方案

| 现象 | 原因 | 解决方案 |
|---|---|---|
| `HTTP Error 412: Precondition Failed` | 列表页风控 | 直接用单 BV 跳过列表页 |
| `HTTP Error 416: Requested Range Not Satisfiable` | 续传残留文件 | 清理 `.part`/`.tmp`/`.ytdl` 后重新下载 |
| `HTTP Error 503: Service Unavailable` | 新视频 CDN 没分配好 | 单条重试 + 间隔 30s + 清理残留 |
| `Format(s) 4K 超高清, 1080P 高码率 are missing; you have to become a premium member` | 高码率要求登录 | 改用 30080+30216 低画质 |
| `Got error: HTTP Error 403: Forbidden` | IP 被 B 站临时拉黑 | 等 60-300s 后重试 |

### 2.3 完整下载脚本模板

```python
import subprocess
cmd = [
    "yt-dlp",
    "-f", "30080+30216/30016/30011",
    "--merge-output-format", "mp4",
    "--no-part",
    "--no-warnings",
    "--no-playlist",
    "-o", target_path,
    f"https://www.bilibili.com/video/{bvid}/",
]
subprocess.run(cmd, timeout=1800)
```

参考实现：`示例博主_B站视频扒取/99-生成脚本/download_bili_videos.py`

---

## 3. Whisper 转写

完全复用 `references/platform-xhs.md` 第 4.2 节"Whisper 转写（CPU 强制模式）"的**唯一稳定配置**：

```python
from faster_whisper import WhisperModel
model = WhisperModel(
    "tiny",                              # large-v3 缓存不完整，用 tiny
    device="cpu",                        # cuda 沉默挂起
    compute_type="int8",
    local_files_only=True,
)
segments, info = model.transcribe(
    str(video_path),
    language="zh",
    beam_size=5,
    vad_filter=False,                    # VAD 加载慢
)
```

启动命令：
```bash
HF_HUB_OFFLINE=1 "C:/Users/<你的用户名>/.workbuddy/binaries/python/envs/whisper/Scripts/python.exe" \
  -u 99-生成脚本/whisper_transcribe.py
```

**速度参考**：CPU int8 约 10-20x 实时，14 分钟视频 ≈ 1 分钟转完。

---

## 4. 标准输出目录（**所有平台强制一致，B站也照此执行**）

完全复用跨平台一致性铁律。详见 `SKILL.md` 第 142-178 行：

- 视频源：`02-Whisper转写/视频源文件/{NNN}-{完整标题}…mp4`
- 转写 JSON：`02-Whisper转写/转写结果/{NNN}-{完整标题}…_转写.json`
- 03 逐字稿：`03-逐字稿MD/{NNN}-{完整标题}…md`
- 04 改写脚本：`04-原视频脚本改写/{NNN}-{完整标题}…-改写脚本.md`

参考实现：`示例博主_B站视频扒取/`（3 条命中完整流程）

---

## 5. 阈值变更 = 增量补齐（铁律）

跟小红书一样：用户中途放低门槛（如 1000万 → 500万）**不需要重跑爬虫**，只需：
1. 重新跑 `search.bilibili.com/all` 拿全量播放量数据
2. 重筛 jsonl + 单视频接口验证
3. 只对新条目跑 yt-dlp + Whisper + 生成 MD/改写
4. **编号按播放量降序重排，旧文件按新编号重命名后覆盖**

---

## 6. 复用命令（下次扒同平台其他 UP 主时直接复制）

```bash
# Step 1: 探测账号
curl -A "Mozilla/5.0" "https://api.bilibili.com/x/space/acc/info?mid=<UID>"

# Step 2: 用 WebFetch 拿视频列表
# WebFetch "https://search.bilibili.com/all?keyword=<UP主昵称>&order=click&page=1"

# Step 3: 单视频接口批量验证精确数据
for bvid in BV1xxx BV1yyy ...; do
  curl "https://api.bilibili.com/x/web-interface/view?bvid=$bvid"
done

# Step 4: yt-dlp 下载（低画质）
yt-dlp -f "30080+30216/30016/30011" \
  --merge-output-format mp4 --no-part --no-warnings --no-playlist \
  -o "<目标路径>.mp4" "https://www.bilibili.com/video/BVxxx/"
```

---

## 7. 踩坑记录（B站专属，2026-09-11 实测）

| 坑 | 解法 |
|---|---|
| `arc/search` 持续 -799 风控 | 改用 `search.bilibili.com/all` web 页面 |
| WBI 签名机制（HTTP 200 + code=-799） | 不实现签名算法，用 web 端绕过 |
| `yt-dlp` 412 列表页风控 | 单 BV 跳列表页直接下载 |
| `yt-dlp` 403 高码率下载需登录 | 用 30080+30216 较低画质 |
| `yt-dlp` 416 续传失败 | 清理 `.part`/`.tmp`/`.ytdl` 残留 |
| `yt-dlp` 503 新视频 CDN 没分配 | 单条重试 + 清理残留 |
| 视频/转写/MD/改写文件名不对齐 | 统一 safe() 函数：`{2,}` 个 `.` → `…`，末尾 strip `-` 和 `.` |
| 文件名末尾 `….mp4` vs `…mp4` 不一致 | safe() 加 `strip('-.\')` + 拼接后再 strip |
| WebFetch 拿到的 BV 用 os.listdir 在某些环境下找不到（编码问题） | 转写脚本用**绝对路径 + 显式文件列表**硬编码 |
| `search.bilibili.com/all` 排序只有"综合/最新/播放"，无"按时间倒序全量" | 翻 page=1, 2, 3 + 单视频接口批量验证 |

---

## 8. 何时用 vs 不适用

**适用**：
- B站 UP 主批量扒视频做内容研究/逐字稿/案例库
- B站顶流 UP 主（千万粉级）按时间筛 + 播放量筛
- 历史视频归档（已过版权保护期）

**不适用**：
- 单条视频查看 → 直接打开客户端
- 实时监控 → 另起 skill
- 用户没 B站账号 → 引导用户注册

---

**最后维护**：2026-09-11，基于 `示例博主_B站视频扒取`（UID {B站UID}）3 条命中实测。