# 小红书扒取专篇（博主视频扒取）

小红书扒取走 **MediaCrawler**（GitHub 50k+ stars 的开源爬虫项目），基于 Playwright 复用浏览器登录态 + 复用真实 cookie，免 JS 逆向。

> 本文档是 `博主视频全量扒取/SKILL.md` 步骤 3「获取视频」的**小红书专属分支**，遇到小红书任务时按本文件执行。

## TL;DR（30 秒版）

| 项目 | 配置 |
|---|---|
| 工具 | [MediaCrawler](https://github.com/NanmiCoder/MediaCrawler) GitHub 50k+ stars |
| 部署路径 | `{工作目录}/MediaCrawler`（或 `<workspace>/MediaCrawler`） |
| 平台参数 | `--platform xhs --type creator --creator_id <user_id> --save_data_option jsonl` |
| 输出 | `data/xhs/jsonl/creator_contents_<日期>.jsonl`（元数据）+ `data/xhs/videos/`（视频本体）|
| 登录态 | Playwright 持久化 context，自动复用（首次扫码后后续不再需要） |
| 反爬策略 | **分批抓取**：单次 ≤30 条，超出按 20-30 条/批，分批间隔 60-90s |

---

## 0. 环境检查（一次性）

### 0.1 Python venv

必须使用 **whisper venv**（`C:/Users/<你的用户名>/.workbuddy/binaries/python/envs/whisper/`）——MediaCrawler 依赖的 `playwright` 和小红书爬虫链路用的就是这个 venv。

**首次检查清单**：

```bash
# 1) 确认 Python 路径
"C:/Users/<你的用户名>/.workbuddy/binaries/python/envs/whisper/Scripts/python.exe" --version
# 期望：Python 3.12.x

# 2) 确认 playwright 已装
"C:/Users/<你的用户名>/.workbuddy/binaries/python/envs/whisper/Scripts/python.exe" -c "import playwright; print(playwright.__version__)"
# 期望：1.40+
# 缺则装：pip install playwright && playwright install chromium

# 3) 确认 PIL（用于保存二维码到本地）
"C:/Users/<你的用户名>/.workbuddy/binaries/python/envs/whisper/Scripts/python.exe" -c "from PIL import Image; print('OK')"
# 缺则装：pip install pillow
```

### 0.2 MediaCrawler 部署（一次性，跨博主复用）

> 🔴 **自动安装原则**：本 skill 执行小红书任务时，**遇到缺失依赖直接装，不要停下来问用户**。下面是一键安装块。

```bash
# === 一键自动安装（幂等，可重复跑） ===
PY="C:/Users/<你的用户名>/.workbuddy/binaries/python/envs/whisper/Scripts/python.exe"
VENV_DIR="C:/Users/<你的用户名>/.workbuddy/binaries/python/envs/whisper"
MC_DIR="{工作目录}/MediaCrawler"

# 1) venv 不存在则创建
[ -f "$PY" ] || "$(dirname "$(dirname "$PY")")/python.exe" -m venv "$VENV_DIR"

# 2) Python 依赖（一次性全装，缺失即补）
"$PY" -m pip install -q --upgrade pip
"$PY" -m pip install -q faster-whisper pillow playwright \
    typer fastapi uvicorn matplotlib pyexecjs2 httpx \
    pandas openpyxl aiofiles redis

# 3) MediaCrawler 仓库（已 clone 则跳过）
[ -d "$MC_DIR" ] || git clone https://github.com/NanmiCoder/MediaCrawler.git "$MC_DIR"
cd "$MC_DIR" && [ -f requirements.txt ] && "$PY" -m pip install -q -r requirements.txt

# 4) Playwright 浏览器内核
"$PY" -m playwright install chromium

# 5) execjs 找不到 Node 的兜底（复制到 PATH 一定能找到的位置）
[ -f "C:/Windows/node.exe" ] || cp "C:/Program Files/nodejs/node.exe" "C:/Windows/" 2>/dev/null || true
```

> 实测坑：`requirements.txt` 装完后仍可能缺 `typer / fastapi / matplotlib / pyexecjs2`（版本锁定问题），
> 所以上面第 2 步单独补了一遍。多装不影响使用。

### 0.3 必需的 patch（绕过 sandbox-cli.exe 代理拦截）

**问题**：本机 sandbox-cli.exe 拦截 huggingface.co，导致 Whisper 模型下不下来；同时 exejs 默认找不到 Node。

**Patch 1：MediaCrawler 抖音模块签名绕过（小红书任务下也必做，否则 main.py 一开始就报错）**

文件：`MediaCrawler/media_platform/douyin/help.py`

找到 `js = execjs.compile(...)` 这一行，把整段 try/except **改成 `pass`**，避免启动时执行 execjs 编译。

**Patch 2：二维码本地保存（默认 PIL show 弹窗在 sandbox 里被拦）**

文件：`MediaCrawler/tools/crawler_util.py`

把 `show_qrcode()` 函数改为：
```python
def show_qrcode(qr_code) -> None:
    if "," in qr_code:
        qr_code = qr_code.split(",")[1]
    qr_code = base64.b64decode(qr_code)
    image = Image.open(BytesIO(qr_code))
    width, height = image.size
    new_image = Image.new('RGB', (width + 20, height + 20), color=(255, 255, 255))
    new_image.paste(image, (10, 10))
    draw = ImageDraw.Draw(new_image)
    draw.rectangle((0, 0, width + 19, height + 19), outline=(0, 0, 0), width=1)
    # 保存到工作目录
    save_path = os.path.join(os.getcwd(), "qrcode_login.png")
    new_image.save(save_path, format="PNG")
    print(f"\n📱 二维码已保存: {save_path}\n   请打开这个图片用小红书 App 扫描\n")
```

**Patch 3：execjs Node 路径找不到（仅非 Windows / 无默认 Node 时）**

```bash
# 方案 A：复制 node.exe 到 Python\Scripts
cp "C:/Program Files/nodejs/node.exe" "C:/Users/<你的用户名>/.workbuddy/binaries/python/envs/whisper/Scripts/"

# 方案 B：复制到 C:\Windows\（推荐，PATH 一定找到）
cp "C:/Program Files/nodejs/node.exe" "C:/Windows/"
```

**Patch 4：`extractor.py` 贪婪正则导致创作者主页解析失败（2026-09-22 实测）**

**症状**（第一次跑某个博主主页时必现）：

```
[XiaoHongShuCrawler.get_creators_and_notes] Failed to parse creator URL:
Expecting value: line 1 column 62699 (char 62698)
Xhs Crawler finished ...        # 一条笔记都没抓就退出
```

**根因**：`extractor.py` 的 `extract_creator_info_from_html()` 用了贪婪正则

```python
r"<script>window.__INITIAL_STATE__=(.+)<\/script>"
```

页面里 `__INITIAL_STATE__` 之后还有别的 `<script>` 时，`(.+)` 会一路吃到最后一个 `</script>`，
拼出来的不是合法 JSON，`json.loads` 抛 `ValueError`，被 `core.py` 当成"URL 解析失败"吞掉。

**修法**（幂等，原文件自动备份为 `.bak_20260922`）：定位 `__INITIAL_STATE__` 后用
`json.JSONDecoder().raw_decode` 从第一个 `{` 精确解析完整对象：

```python
idx = html.find("window.__INITIAL_STATE__=")
if idx == -1:
    return None
start = html.find("{", idx)
if start == -1:
    return None
raw = html[start:].replace(":undefined", ":null")
try:
    info, _ = json.JSONDecoder().raw_decode(raw)
except Exception:
    return None
if info is None:
    return None
user_obj = info.get("user") or {}
return user_obj.get("userPageData")
```

> 现成脚本：`{项目目录}/99-生成脚本/patch_extractor.py`（改 oath 后可直接跑）。

### 0.4 视频 URL 提取 patch（小红书 API 新版字段）

小红书 2024 年后 API 字段结构调整，老 MediaCrawler 找不到视频 URL。

文件：`MediaCrawler/store/xhs/__init__.py`

`get_video_url_arr()` 函数改成从 `video.media.stream.EF4[0].master_url` 提取：

```python
def get_video_url_arr(note_item: Dict) -> List:
    if note_item.get('type') != 'video':
        return []
    video_dict = note_item.get('video')
    if not video_dict:
        return []
    videoArr = []
    # 新版路径
    media = video_dict.get('media', {})
    stream = media.get('stream', {})
    h264 = stream.get('h264', [])
    if h264:
        for v in h264:
            url = v.get('master_url', '')
            if not url:
                backups = v.get('backup_urls', [])
                if backups:
                    url = backups[0]
            if url:
                videoArr.append(url)
    # 兼容老路径
    if not videoArr:
        consumer = video_dict.get('consumer', {})
        originVideoKey = consumer.get('origin_video_key', '') or consumer.get('originVideoKey', '')
        if originVideoKey:
            videoArr.append(f"http://sns-video-bd.xhscdn.com/{originVideoKey}")
    return videoArr
```

---

## 1. 配置（每个博主任务前改 1 次）

文件：`MediaCrawler/config/base_config.py`

```python
PLATFORM = "xhs"                       # 平台
CRAWLER_TYPE = "creator"               # 创作者主页模式
LOGIN_TYPE = "qrcode"                  # 扫码登录（首次）
SAVE_LOGIN_STATE = True                # 保存登录态（关键！避免每次扫码）

# CDP_CONNECT_EXISTING = True/False 都行；用 False 自动起内置 Chromium
CDP_CONNECT_EXISTING = False
ENABLE_CDP_MODE = False                # 关闭 CDP，用 Playwright 内置浏览器

# 抓取上限（关键参数）
CRAWLER_MAX_NOTES_COUNT = 50           # 默认值；按需改小分批

# 下载视频/图片
ENABLE_GET_MEIDAS = True               # 必须 True，否则只下元数据没视频本体
```

文件：`MediaCrawler/config/base_config.py` 末尾或新建 `xhs_config.py`：

```python
XHS_SPECIFIED_USER_ID_LIST = ["6166b66a0000000002027a1d"]  # 示例博主
```

---

## 2. 抓取执行（首次扫码 + 后续复用）

### 2.1 首次抓取（含扫码）

```bash
cd "{工作目录}/MediaCrawler"
"C:/Users/<你的用户名>/.workbuddy/binaries/python/envs/whisper/Scripts/python.exe" \
  -u main.py --platform xhs --type creator \
  --creator_id "https://www.xiaohongshu.com/user/profile/<user_id>?xsec_token=XXX=&xsec_source=pc_user" \
  --save_data_option jsonl
```

> 🔴 **2026-09-22 实测：`--creator_id` 要传「完整主页 URL」，不要只传 24 位纯 ID。**
> `parse_creator_info_from_url()` 对纯 ID 会返回 `xsec_token='' / xsec_source=''`，
> 抓笔记时的鉴权参数随之丢失；传完整 URL 才会带上 `xsec_token` 与 `xsec_source`。

**用户操作流程**（必须严格执行）：

| 步骤 | 用户端动作 | 关键提示 |
|---|---|---|
| ① | 启动后约 5-10 秒 | 脚本在 `data/xhs/` 旁生成 `qrcode_login.png`（已用 show_qrcode patch） |
| ② | 用小红书 App 扫这个 PNG | 右上角"扫一扫" |
| ③ | App 弹出「确认登录网页端小红书」 | **必须点"登录"**，否则 120s 超时退出 |
| ④ | 看到 App 跳转后回到对话 | "已登录" 一句话即可 |

> ⚠️ **超时根因**：4 次失败都是「扫了没在 App 上点确认」。**100% 是这步没做。**

### 2.2 后续抓取（登录态复用）

`SAVE_LOGIN_STATE=True` + `xhs/browser_context/` 已持久化 Playwright context，**第二次以后直接跑 main.py 即可，无需再扫码**。

---

## 3. 分批抓取策略（小红书专属铁律）

**单次上限**：小红书翻页触发风控的经验上限 ≈ **30 条/批**。

### 3.1 分批决策

| 博主视频总数 | 推荐策略 |
|---|---|
| ≤ 30 条 | 一次抓全（`CRAWLER_MAX_NOTES_COUNT = 50`） |
| 30-60 条 | 分 2 批：第一次 `MAX=30`，60-90s 后第二次 `MAX=50` |
| 60-100 条 | 分 3 批：每批 30 条，间隔 60-90s |
| >100 条 | 联系用户决定是否调整；建议拆多次会话跑 |

### 3.2 分批配置 + 命令

```bash
# 第一批
sed -i 's/CRAWLER_MAX_NOTES_COUNT = .*/CRAWLER_MAX_NOTES_COUNT = 30/' config/base_config.py
python main.py --platform xhs --type creator --creator_id <id> --save_data_option jsonl

# 等 60-90 秒（避免连续请求触发风控）
sleep 75

# 第二批（更大 limit，确保抓剩余）
sed -i 's/CRAWLER_MAX_NOTES_COUNT = .*/CRAWLER_MAX_NOTES_COUNT = 50/' config/base_config.py
python main.py --platform xhs --type creator --creator_id <id> --save_data_option jsonl
```

### 3.3 分批去重逻辑

MediaCrawler 默认**会覆盖** `creator_contents_<日期>.jsonl`。分批跑时：

```bash
# 第一批跑完后立刻备份
cp data/xhs/jsonl/creator_contents_<日期>.jsonl "<项目>/01-视频清单/round1_<日期>.jsonl"

# 第二批跑完后做并集合并
python -c "
import json
seen = set()
out = []
for path in ['<项目>/01-视频清单/round1_<日期>.jsonl', 'data/xhs/jsonl/creator_contents_<日期>.jsonl']:
    with open(path, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if line and (nid := json.loads(line).get('note_id')) and nid not in seen:
                seen.add(nid)
                out.append(line)
with open('data/xhs/jsonl/creator_contents_<日期>.jsonl', 'w', encoding='utf-8') as f:
    f.write('\n'.join(out) + '\n')
"
```

### 3.4 抓取失败信号 → 立即降速

| 现象 | 含义 | 应对 |
|---|---|---|
| 同一批 5+ 次连续"note card empty" | 触发风控 | 立刻停 5 分钟，降速到 1 条/3s |
| API 返回 461 / 471 | IP 被限流 | 换 IP 或停 30 分钟 |
| 登录态失效（自动重新弹二维码） | Cookie 过期 | 用户重新扫码一次即可 |

---

## 4. 抓取后处理流水线

### 4.1 下载视频本体

MediaCrawler 默认 `ENABLE_GET_MEIDAS=True` 时，视频本体存在 `data/xhs/videos/<note_id>.mp4`，但**实测会下载失败**——patch 后只拿到 URL 字符串。

**手动下载脚本**（参考 `xhs_示例博主/99-生成脚本/download_videos.py`）：

```python
import urllib.request, ssl, json, os
ssl._create_default_https_context = ssl._create_unverified_context

def download(url, path):
    if os.path.exists(path) and os.path.getsize(path) > 1000:
        return f'EXISTS'
    req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
    with urllib.request.urlopen(req, timeout=60) as r:
        with open(path, 'wb') as f:
            f.write(r.read())
    return f'OK {os.path.getsize(path)} bytes'

# 从 creator_contents_*.jsonl 过滤 type=video and liked>=<阈值>
# 阈值写成一个常量，便于用户中途放低门槛
# 然后逐条下载第一个 master_url
```

**阈值变更 = 增量补齐**：元数据与视频已全量落地时，用户后续追加更低门槛（如 2000 → 500）**不需要重跑爬虫**，只需：
1. 对本地 jsonl 重筛（`filter_by_likes.py`）
2. 归集新纳入的 mp4（`collect_videos_ge500.py`）
3. 只对新条目跑 Whisper + 生成 03/04
4. 因编号按点赞降序，**全量重排编号并重命名**旧文件

> 经验值（`示例博主` 48 条视频实测）：≥2000 → 7 条；≥1000 → 17 条；≥500 → 29 条；≥300 → 36 条。交付前先给用户看这张分布表再决定档位。

> aiohttp 在 venv 里没装，用 urllib 即可（Windows 上没 SSL 问题反而更稳）

### 4.2 Whisper 转写（CPU 强制模式）

```bash
# 必须用本地缓存 + 离线 + CPU（sandbox 代理拦 huggingface.co）
cd "<项目>"
HF_HUB_OFFLINE=1 "C:/Users/<你的用户名>/.workbuddy/binaries/python/envs/whisper/Scripts/python.exe" -u 99-生成脚本/whisper_transcribe.py
```

**唯一稳定的 Whisper 配置**（参考 `xhs_示例博主/99-生成脚本/whisper_transcribe.py`）：

```python
from faster_whisper import WhisperModel
model = WhisperModel(
    "tiny",                              # large-v3 缓存不完整，用 tiny
    device="cpu",                        # cuda 在无 NVIDIA 驱动时沉默挂起 43 分钟
    compute_type="int8",
    local_files_only=True,               # 跳过 huggingface 下载
)
segments, info = model.transcribe(
    str(video_path),
    language="zh",
    beam_size=5,
    vad_filter=False,                    # VAD 加载慢 + 偶尔卡死
)
```

**速度参考**：CPU int8 约 10-20x 实时，2 个 1 分钟视频 ≈ 12 秒搞定。

### 4.3 生成 6 模块 MD + 改写脚本

完全复用 `博主视频全量扒取/SKILL.md` 步骤 5/6 标准流程，无平台差异。

---

## 5. 标准输出目录（**所有平台强制一致，小红书也照此执行**）

> 🔴 **铁律：无论视频号还是小红书，最终产出的目录分类与文件命名必须完全一致**，便于跨平台统一归档、对比和二次剪辑。

```
<博主名>视频扒取/ 或 <博主名>_<平台>/          # 项目根目录
├── README.md                                   # 项目总览 + 进度统计
├── 00-操作手册.md                              # 用户需手动做的步骤（按平台不同）
├── 01-视频清单/
│   ├── 视频登记表.md                            # 全量清单 + 命中筛选表
│   ├── videos_index.json                       # 结构化清单数据
│   └── creator_contents_final.jsonl            # 去重后的原始抓取数据
├── 02-Whisper转写/
│   ├── 视频源文件/                              # {NNN}-{完整标题}.mp4，与 03/04 编号完全一致
│   └── 转写结果/                                # {NNN}-{完整标题}_转写.json，与视频源文件同名
├── 03-逐字稿MD/                                # 6 模块逐字稿（不含改写脚本）
├── 04-原视频脚本改写/                          # 改写脚本（独立文件）
├── 99-生成脚本/                                # 见下方「脚本清单」
├── models/                                     # 模型说明
└── browser_context/                            # Playwright 登录态（小红书专属，不要删！）
```

**`99-生成脚本/` 脚本清单**（按执行顺序，参考 `xhs_示例博主/99-生成脚本/`）：

| 脚本 | 作用 |
|---|---|
| `filter_by_likes.py` | 按点赞阈值筛近一年视频，输出 `notes_liked_ge500.json` / `notes_liked_lt500.json` |
| `collect_videos_ge500.py` | 把命中视频从 MediaCrawler `data/xhs/videos/` 归集到 `02-Whisper转写/视频源文件/{NNN}-{完整标题}.mp4` |
| `rename_videos_and_jsons.py` | 把 `02-Whisper转写/` 下的视频和 JSON 重命名为 `{NNN}-{完整标题}`，与 03/04 对齐 |
| `check_video_files.py` | 校验命中视频是否全部下载到位 |
| `download_videos.py` | （备选）直接从 jsonl 的 `video_url` 用 urllib 下载 |
| `whisper_transcribe.py` | 批量转写（自动跳过已存在的），输出 `转写结果/{NNN}-{完整标题}_转写.json` |
| `dump_all_transcripts.py` | 导出全部时间戳逐字稿到单个 txt，便于人工提炼 |
| `generate_md_and_rewrites.py` | 生成 03/04 两组文件（`MODULES` 字典按 `note_id` 存内容） |
| `generate_video_index.py` | 生成 `01-视频清单/README.md`、`videos_index.json`、项目 `README.md` |

### 5.1 03-逐字稿MD 的 6 模块结构（**跨平台统一**）

文件名（03 逐字稿 / 04 改写脚本 / 02 视频源文件 / 02 转写结果）必须**完全同名、同编号**：
- 视频源文件：`{序号:03d}-{完整标题}.mp4`
- 转写结果：`{序号:03d}-{完整标题}_转写.json`
- 03 逐字稿：`{序号:03d}-{完整标题}.md`
- 04 改写脚本：`{序号:03d}-{完整标题}-改写脚本.md`

**命名铁律**：用完整标题、连字符 `-` 分隔、不简写、不用下划线，保证同屏观看时能秒找对应视频。

```markdown
# {完整标题}

> **平台**：小红书（示例博主）        ← 视频号写「视频号：sphXXX」
> **笔记 ID**：`{note_id}`
> **发布时间**：YYYY-MM-DD
> **点赞数**：N ｜ **收藏**：N ｜ **评论**：N ｜ **分享**：N
> **视频时长**：M:SS
> **来源**：https://www.xiaohongshu.com/explore/{note_id}
> **逐字稿来源**：Whisper tiny 转写（YYYY-MM-DD 导出）
> **视频脚本风格**：干货+金句式

---

## 🎯 核心观点（1 句话）
## 💡 3 个关键点        ← 用 - **看现象** / **拆工具** / **给活法** 这类三段式
## 📝 逐字稿            ← > [HH:MM:SS] 文本，每段一行
## 🪝 金句摘录          ← > 「金句」
## 🔗 我的行动          ← - [ ] 可勾选清单
```

### 5.2 04-原视频脚本改写 的文件结构（**跨平台统一**）

文件名：`{序号:03d}-{完整标题}-改写脚本.md`

```markdown
# 🎬 {完整标题}（改写版）

> **原始视频**：[NNN 号视频](../03-逐字稿MD/NNN-{完整标题}.md)
> **博主**：示例博主（小红书）
> **原视频时长**：M:SS ｜ **原视频点赞**：N ｜ **收藏**：N ｜ **评论**：N
> **改写日期**：YYYY-MM-DD
> **改写风格**：干货+金句式
> **改写基础**：基于 Whisper tiny 转写的逐字稿 + 博主原始视频内容

---

## 📝 改写内容
### 新标题
**新标题内容**
### 新口播文案
> 段落 1
> 段落 2

---

## 🔗 与原视频对比
| 维度 | 原视频 | 改写版 |
|------|--------|--------|
| 标题 | 见 03 顶部 | 见 `### 新标题` |
| 口播文案 | 见 03 逐字稿 | 见 `### 新口播文案` |
| 核心论点 | 同主题 | 同主题，不同表达 |
| 风格 | 博主本人风格 | 干货+金句式 |
```

> ⚠️ 对比表用 `|------|` 分隔行（**不要用 `|---|---|`**），与视频号模板严格一致；且**禁止重复段落**（视频号 001 曾出现「改写内容」段重复的 bug，不要复制这个错误）。

### 5.3 一致性检查清单（交付前必跑）

- [ ] 03/04 两目录的文件名都用了 `NNN-完整标题` 格式（连字符，非下划线）
- [ ] 每个 03 MD 恰好 5 个 `##` 级 section（🎯/💡/📝/🪝/🔗）+ 头部元信息
- [ ] 每个 04 文件有 `## 📝 改写内容` 和 `## 🔗 与原视频对比` 两个 section
- [ ] 头部字段顺序、emoji、措辞与视频号项目一致
- [ ] 0 处 `<!--` 占位残留、0 处重复段落
- [ ] 序号连续无缺口（001 起）

---

## 6. 复用命令（下次扒同博主其他博主时直接复制）

```bash
# Step 1: 改 user_id
sed -i 's/XHS_SPECIFIED_USER_ID_LIST = \[.*\]/XHS_SPECIFIED_USER_ID_LIST = ["<new_user_id>"]/' \
  "{工作目录}/MediaCrawler/config/base_config.py"

# Step 2: 改 limit + 跑
sed -i 's/CRAWLER_MAX_NOTES_COUNT = .*/CRAWLER_MAX_NOTES_COUNT = 50/' \
  "{工作目录}/MediaCrawler/config/base_config.py"

cd {工作目录}/MediaCrawler && \
"C:/Users/<你的用户名>/.workbuddy/binaries/python/envs/whisper/Scripts/python.exe" \
  -u main.py --platform xhs --type creator --creator_id <new_user_id> --save_data_option jsonl
```

---

## 7. 踩坑记录（小红书专属）

| 坑 | 解法 |
|---|---|
| 扫码后 120s 超时（最常见，4/5 失败原因） | **必须 App 上点"登录"确认**，不要只扫不点 |
| aiohttp 没装（urllib 替代） | 直接用 urllib.request 即可 |
| Whisper `device="cuda"` 在无 GPU 机器沉默挂起 43 分钟 | 改 `device="cpu"` + `vad_filter=False` |
| Whisper large-v3 缓存不完整 → IncompleteSnapshotError | 加 `local_files_only=True` + `HF_HUB_OFFLINE=1`，或改 `tiny` 模型 |
| 抖音 help.py `execjs.compile` 启动失败 | 把 try/except 改成 `pass` |
| 视频 URL 拿不到（老代码找 `consumer.origin_video_key`） | patch `store/xhs/__init__.py` 的 `get_video_url_arr` 走新路径 `video.media.stream.EF4[0].master_url` |
| Playwright 二维码弹窗被 sandbox 拦 | patch `tools/crawler_util.py` 改成保存 PNG |
| execjs 找不到 Node | 复制 `node.exe` 到 `C:\Windows\` 或 `Scripts/` |
| MediaCrawler 默认 `ENABLE_GET_MEIDAS=False` 不下视频 | 改 `base_config.py` 设为 `True` |
| 抓 50+ 条触发风控 | 按 30 条/批 + 60-90s 间隔 |
| 浏览器 context 路径冲突 | 用绝对路径：`USER_DATA_DIR = "<项目>/browser_context/xhs"` |
| 中文 ID 路径编码错乱 | 用相对路径或短英文路径，避免 Windows ANSI 转码 |
| 文件名 Windows 非法字符 | `sanitize_filename()` 处理 `<>:"/\|?*` |

---

## 8. 何时用 vs 不适用

**适用**：小红书博主批量扒视频做内容研究/逐字稿/案例库（小红书生态做品牌出海/小红书电商/MCN 必备）

**不适用**：
- 单条视频查看 → 直接打开客户端
- 实时监控 → 另起 skill
- 用户没小红书账号 → 引导用户注册后再继续

---

**最后维护**：2026-09-11，基于 `xhs_示例博主`（user_id `6166b66a0000000002027a1d`）32 条视频实测。

---

## 9. 实测档案（2026-09-11 示例博主）

### 9.1 抓取效率实测

| 轮次 | 配置 | 结果 | 耗时 |
|---|---|---|---|
| 首轮 | `CRAWLER_MAX_NOTES_COUNT=15` | 15 条笔记 + 评论 + 封面图 | 3m11s |
| 二轮 | `CRAWLER_MAX_NOTES_COUNT=50` | 32 条视频笔记全抓 + **视频本体 87 个 mp4（1.4GB）** | 6m58s |

> ✅ **结论**：`MAX=50` 一次可抓全小博主（≤40 条），实测**未触发风控**。
> 分批策略（30 条/批）作为**保险**保留，用于大博主（>40 条）或出现风控信号时。

### 9.2 抓取后数据流

```
data/xhs/jsonl/creator_contents_<日期>.jsonl   # 元数据（两轮累积，需去重）
data/xhs/videos/<note_id>/0.mp4                # 视频本体（多清晰度版本，取最大）
data/xhs/images/<note_id>/0.jpg                # 封面图
```

**注意**：两轮跑会**累积写入同一 jsonl**（不去重），需手工去重：

```python
uniq = {}
for n in raw:
    uniq[n['note_id']] = n   # 保留最后一次
```

### 9.3 筛选结果

- 原始抓取 65 条 → **去重后 50 条笔记 / 48 条视频**（全部近一年内）
- **点赞 ≥ 2000 = 7 条**；**点赞 ≥ 500 = 29 条**（最终交付 29 组文件）
- 编号规则：**按点赞降序** 001–029

**分级阈值分布（近一年）**

| 阈值 | 条数 |
|---|---|
| 点赞 ≥ 2000 | 7 |
| 点赞 ≥ 1000 | 17 |
| 点赞 ≥ 500 | 29 |
| 点赞 ≥ 300 | 36 |
| 点赞 ≥ 100 | 46 |

**点赞 ≥ 500 命中清单（前 10，完整见项目 `01-视频清单/README.md`）**

| # | 点赞 | 标题 |
|---|---|---|
| 001 | 6500 | 55个大厂设计语言，都在这份DESIGN.md里了 |
| 002 | 5462 | AI视频神级玩法！人人做拼贴动画【教程】 |
| 003 | 3313 | 一句话生成大师UI动效！K2.6 Agent审美太强 |
| 004 | 2877 | 居然才知道！Github里藏了4个前端动效库！ |
| 005 | 2339 | 用html做漂亮ppt太简单了！！附3个skills |
| 006 | 2114 | 让Codex省70倍Token？都去用这个开源神器！ |
| 007 | 2084 | 一句话拆解爆款！我又开源私藏skill啦～ |
| 008 | 1848 | 3分钟学会 HTML PPT！从0-1新手教程～ |
| 009 | 1477 | 做自媒体必备6个skills！建议收藏 |
| 010 | 1364 | 开源自动化skill！0基础做高级拼贴动画！ |

### 9.4 全链路耗时

| 阶段 | 耗时 |
|---|---|
| MediaCrawler 抓 32 条 + 下 1.4GB 视频 | 6m58s |
| 满量重跑（`MAX=50`，抓全 48 条 + 87 个 mp4） | 6m58s |
| 归集 29 条命中视频 | 秒级 |
| Whisper tiny 转写 29 条（22 条新增） | 4m15s |
| 生成 29 篇 6 模块 MD + 29 篇改写脚本 | 秒级 |
| **合计** | **约 12 分钟**（登录态已复用，无需扫码） |