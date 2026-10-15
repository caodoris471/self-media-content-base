# 博主视频全量扒取 Skill

> 把某个博主的全部视频 → 按条件筛选 → 下载 → Whisper 转写 → 逐字稿 MD 的端到端流水线 skill。

## Skill 说明

- **功能**：扒取任意平台博主账号的全部视频，按点赞/播放/评论阈值筛选，下载后用 faster-whisper 本地转写，批量生成 6 模块逐字稿 MD（核心观点 / 3 关键点 / 金句 / 行动）+ 改写脚本。
- **强制流程**：**开工前先问「改写语气」（情感共鸣型 / 犀利观点型 / 干货拆解型 / 人物故事型 / 种草带货型，新博主必问）+ 筛选/时间范围** → 平台可行性评估 → 搭脚手架 → 获取视频 → Whisper 转写 → 生成 MD + AI 提炼 → **AI 亲笔写改写稿（不是复制）** → **跑 `verify_rewrite_distinct.py` 验收（exit=0 才可交付）**。
- **🔴 两条硬闸门（2026-09-14 用户要求写死）**：① 语气必须提前问，不准套默认；② 04 改写稿必须与 03 逐字稿不同，交付前必跑 `scripts/verify_rewrite_distinct.py <项目根>`，FAIL 一票否决。执行细节（装证书/点按钮/跑几步）全自动不问，但**输出语气必须问**。
- **输出**：标准项目目录结构（`00-操作手册` / `01-视频清单` / `02-Whisper转写` / `03-逐字稿MD` / `04-原视频脚本改写` / `99-生成脚本`）。
- **转写引擎**：faster-whisper（本地 CPU int8，约 5-20x 实时；走 hf-mirror 国内镜像）。

## 🚦 v2.6 · 8 平台已打通（2026-09-13）

| 状态 | 平台 | 工具链 | 实测归档 |
|---|---|---|---|
| ✅ | B站 | `search.bilibili.com/all` web 页面 + 单视频 API + yt-dlp 30080+30216 | 3 条「示例博主」 |
| ✅ | 微信视频号 | `wx_channels_download` + 自签证书 | 35 条「品牌出海姐 Rose」 |
| ✅ | 小红书 | `MediaCrawler` + Playwright 持久化登录态 | 29 条「示例博主」 |
| ✅ | 快手 | `MediaCrawler` + `kuaishou/login.py` xpath patch | 17 条「示例博主」 |
| ✅ | YouTube | yt-dlp + 本地代理 + 登录 cookie + yt-dlp-ejs | 2 条「@示例博主」 |
| ✅ | TikTok | yt-dlp + 本地代理 + `--impersonate Chrome-136` + curl_cffi | 9 条「@示例博主」 |
| ✅ | **抖音** | **MediaCrawler + Playwright + PC 扫码登录 + login.py patch（兼容 2025 新版 login-full-panel）** | **2 条「示例博主」** |
| ✅ | **Instagram** | **Playwright Edge 独立 profile + 账号密码 + 2FA → yt-dlp + cookies.txt** | **20 条「@示例博主」** |

> 详细各平台流程见 `references/platform-{xhs,bilibili,ks,youtube,tiktok,douyin,instagram}.md`。

## 📁 项目结构

```
博主视频全量扒取/
├── README.md                          # 本文件（skill 说明 + 里程碑）
├── SKILL.md                           # skill 主文档（开工前问语气 + 7 步流程 + 9 大铁律）
├── references/
│   ├── platform-matrix.md             # 8 平台可行性矩阵 + 决策规则
│   ├── platform-xhs.md                # 小红书 MediaCrawler 全流程
│   ├── platform-bilibili.md           # B站 web search + yt-dlp 组合方案
│   ├── platform-ks.md                 # 快手 MediaCrawler + login.py patch
│   ├── platform-youtube.md            # YouTube 代理 + cookie + yt-dlp 流程
│   ├── platform-tiktok.md             # TikTok 代理 + Chrome-136 impersonate + curl_cffi
│   ├── platform-douyin.md             # 抖音 MediaCrawler + login.py patch（2026-09-13 第 7 平台）
│   ├── platform-instagram.md          # Instagram instaloader + yt-dlp 兜底（v2.4 新增）
│   └── chrome-extension-recovery.md   # Chrome profile 损坏恢复指南
└── scripts/
    ├── collect_videos_xhs.py          # 小红书：从 MediaCrawler videos 归集+重命名
    ├── collect_videos_bilibili.py     # B站：从 yt-dlp raw_downloads 归集+重命名
    ├── collect_videos_ks.py           # 快手：从 MediaCrawler kuaishou videos 归集+重命名
    ├── collect_videos_youtube.py      # YouTube：从 yt-dlp raw_downloads 按 video_id 归集+重命名
    ├── transcribe_with_whisper.py     # Whisper 批量转写（CPU int8，国内镜像）
    ├── generate_md_timed.py           # SRT → 分时段逐字稿 MD（全平台通用）
    └── extract_rewrite_script.py      # 从 03 MD 提取改写脚本到 04 目录
```

## 🚀 开箱即用（卖出去给别人用时的 5 分钟上手）

### 0. 准备依赖（一次性，跨博主复用）

```bash
# Whisper venv（如果还没有）
"<managed python>" -m venv C:/Users/<你的用户名>/.workbuddy/binaries/python/envs/whisper
C:/Users/<你的用户名>/.workbuddy/binaries/python/envs/whisper/Scripts/python.exe -m pip install faster-whisper

# 平台特定依赖
# 小红书：pip install playwright pillow && playwright install chromium
# Instagram：pip install instaloader
# 通用：pip install yt-dlp
```

### 1. 收到用户请求后

```python
# 5 问都用 AskUserQuestion 问（直接复制 SKILL.md 必问问题 1-5 的代码块）
# 平台选「小红书」「B站」「视频号」→ 加载对应 reference 文件
# 平台选其他 → 加载 references/platform-matrix.md 看可达性
```

### 2. 平台特定步骤

| 平台 | 加载 reference | 必跑命令 |
|---|---|---|
| 小红书 | `references/platform-xhs.md` | MediaCrawler 抓取 → `scripts/collect_videos_xhs.py` |
| B站 | `references/platform-bilibili.md` | web search + yt-dlp → `scripts/collect_videos_bilibili.py` |
| 视频号 | `references/platform-wxchannels.md` | `scripts/wx_pipeline.py`（一条命令全自动） |
| 快手 | `references/platform-ks.md` | MediaCrawler 抓取（+ login.py patch）→ `scripts/collect_videos_ks.py` |
| YouTube | `references/platform-youtube.md` | yt-dlp（代理 + cookie）→ `scripts/collect_videos_youtube.py` |

### 3. Whisper + MD + 改写（所有平台通用）

```bash
# Whisper 转写（CPU int8，约 5-20x 实时）
"<whisper venv>/python.exe" "<项目>/99-生成脚本/transcribe_with_whisper.py"

# MD 骨架
"<whisper venv>/python.exe" "<项目>/99-生成脚本/generate_md_timed.py" --srt-dir "<项目>/02-Whisper转写/转写结果" --md-dir "<项目>/03-逐字稿MD" --author "<博主>" --platform "<平台>"

# AI 端填 6 模块 + 04 改写脚本
# （手动或通过 LLM API 批量填，记得更新索引文件）
```

## 🔴 5 大硬铁律速查（v2.4 · 任何平台强制）

| # | 铁律 | 一句话 |
|---|---|---|
| 1 | **浏览器 Profile 保护** | 海外平台登录只能 `项目目录/login_profile/`，**绝对禁止** `--user-data-dir` 指真实 Chrome / NTFS junction（详见 `references/chrome-extension-recovery.md`） |
| 2 | **改写脚本语言匹配原视频** | 海外平台 → 英文；国内平台 → 中文；禁止「（在此填入）」空模板（`extract_rewrite_script.py` 已自动识别 language 字段） |
| 3 | **改写脚本质量** | 改写 ≠ 复制逐字稿，必须有新 Hook / 新口播 / 新 CTA，原文只放 `Original Core Script (Reference)` 区 |
| 4 | **🔴 完整视频双落 mp4+m4a** | `-f "download/..."` 或 `-f "best[ext=mp4]"` 先 mp4、再 `-x --audio-format m4a` 抽音频；**禁只下音频**（2026-09-13 TikTok 教训，二次剪辑必须有 mp4） |
| 5 | **🔴 落盘用绝对路径** | subprocess yt-dlp `-o "xxx.mp4"` 必须 `str(VIDEO_DIR / "xxx.mp4")` 绝对路径 + `cwd=VIDEO_DIR`，否则 mp4 漏到项目根目录（跨项目经验，已加进 `~/.workbuddy/MEMORY.md`） |

## 里程碑

| 版本 | 日期 | 内容 |
|---|---|---|
| v1.0 | 2026-09-04 | 初始版本：支持 6 平台，完成首次端到端试运行（陈述出海视频号，40 条逐字稿） |
| v1.1 | 2026-09-04 | 新增 TikTok + Instagram，扩展到 8 平台；安装 instaloader |
| v2.0 | 2026-09-11 | **三平台已打通**：视频号 35 条 + 小红书 29 条 + B站 3 条 实测通过；新增 cross-platform 一致性铁律 + safe() 统一命名规则 + collect_videos_<platform>.py 归集工具；SKILL.md 加问题5「登录态保留」 |
| v2.1 | 2026-09-11 | **四平台已打通**：+ 快手 17 条「示例博主」实测通过；新增 `references/platform-ks.md` + `scripts/collect_videos_ks.py`；SKILL.md 加快手分支和踩坑 |
| v2.2 | 2026-09-12 | **五平台已打通**：+ YouTube 2 条「@示例博主」实测通过；新增 `references/platform-youtube.md` + `scripts/collect_videos_youtube.py`；SKILL.md / README.md 同步更新 |
| v2.3 | 2026-09-12 | **🔴 两条硬铁律写入**：① 浏览器 Profile 保护（禁止 `--user-data-dir` 指向真实 Chrome User Data / NTFS junction / Playwright launch_persistent_context，违者会清空用户扩展，详见 `references/chrome-extension-recovery.md`）；② 改写脚本语言铁律（YouTube/TikTok/Instagram → 英文，B站/小红书/快手/视频号 → 中文）。SKILL.md / platform-youtube.md / README.md 同步更新 |
| **v2.4** | **2026-09-13** | **🔴 五条硬铁律写齐**：① + ② + ③ 改写脚本质量（改写 ≠ 复制逐字稿）+ ④ 完整视频 mp4 + m4a 双落（TikTok 教训，二次剪辑必须有 mp4）+ ⑤ subprocess 落盘绝对路径（避免 mp4 漏到项目根）。**新增 references/platform-instagram.md**（instaloader + yt-dlp 双路，待首次实测）。SKILL.md / platform-matrix.md / platform-youtube.md / references/chrome-extension-recovery.md / 5 大铁律速查表。TikTok 升级到「已打通」。 |
| **v2.5** | **2026-09-13** | **抖音打通（第 7 平台）**：MediaCrawler + Playwright + PC 端扫码登录 + login.py patch 兼容 2025 新版登录面板 + ffmpeg 抽 m4a。首次命中 1 条「示例博主 136」（近 7 天 + 点赞 > 8000，8171 赞）。**新增 references/platform-douyin.md**（11 项卡点 + login.py patch 教程 + 5 大铁律适配）。SKILL.md / README.md / platform-matrix.md 同步升级。**全平台现状**：✅ 已打通 7 / ⚠️ 待实测 1（Instagram）。 |

## 卖点（卖给别人用时的关键差异点）

| 维度 | 我们怎么做 | 行业常见做法 |
|---|---|---|
| **平台覆盖** | 视频号 + 小红书 + B站 + 快手 + YouTube + TikTok + 抖音 = 7 平台（已打通），待打通 Instagram = 8 平台 | 单平台工具居多 |
| **跨平台一致性** | 目录结构 + 文件命名 + MD 章节完全一致，可统一归档 | 各平台各搞各的 |
| **登录态管理** | 视频号证书/小红书 cookie 可保留，避免每次重扫 | 默认每次重登录 |
| **阈值灵活性** | 阈值变更走「增量补齐」，不全量重跑 | 全量重跑=浪费 |
| **改写脚本** | 04 目录独立产改写脚本，可直接二次创作 | 多数只有逐字稿 |
| **数据铁律** | Whisper 唯一稳定配置：`tiny + cpu + int8 + offline` | 经常卡死/GPU 必须 |
| **分批抓取** | 小红书 ≤30 条/批，超出自动分批 | 一把梭容易被风控 |
