---
name: 博主视频全量扒取
description: 扒取任意平台博主账号的全部视频，按数据维度筛选（点赞/播放量/评论等阈值），下载后用 faster-whisper 本地转写并批量生成 6 模块逐字稿 MD + 改写脚本。**已打通 8 平台**（截至 2026-09-14）：**微信视频号（🟢 全自动，工具 HTTP API 批量拉 + 直链下载 + decrypt 解密，唯一入口 `scripts/wx_pipeline.py`；已验证：115 条清单/44 条实抓「示例博主」、172 条清单/近 7 天 5 条「示例博主」，见 `references/platform-wxchannels.md`）**/ 小红书（MediaCrawler + 分批抓取，29 条「示例博主」）/ B站（web search + 单视频 API + yt-dlp，3 条「示例博主」）/ 快手（MediaCrawler + login.py patch，17 条「示例博主」）/ YouTube（yt-dlp + 代理 + cookies.txt + yt-dlp-ejs，2 条「@示例博主」）/ TikTok（yt-dlp + Chrome-136 impersonate + 代理 + curl_cffi，9 条「@示例博主」）/ 抖音（MediaCrawler + Playwright + 扫码登录 + login.py patch，2 条「示例博主」）/ **Instagram（Playwright Edge 独立 profile + yt-dlp + cookies.txt，20 条「@示例博主」）**。强制流程：先 5 问（平台+账号 / 筛选维度 / 时间范围 / 脚本语言风格 / 是否需要保留登录态），若命中数为 0 自动建议放大时间范围（不擅自调整）。**🔴 六条硬铁律**：(1) **浏览器 Profile 保护**——任何平台登录只能用项目目录独立 profile，**绝对禁止** `--user-data-dir` 或 Playwright 指向真实 Chrome User Data / NTFS junction（否则会清空用户扩展）；(2) **改写脚本语言**——海外平台（YouTube/TikTok/Instagram）→ 英文，国内平台（B站/小红书/快手/视频号/抖音）→ 中文；(3) **改写脚本质量**——改写 ≠ 复制逐字稿，必须有新 Hook / 新口播 / 新 CTA；(4) **完整视频双落 mp4+m4a**——`-f "download/..."` 或 `-f "best[ext=mp4]"` 先 mp4、再 `-x --audio-format m4a` 抽音频，**禁止只下音频**；(5) **落盘用绝对路径**——subprocess yt-dlp `-o "xxx.mp4"` 必须 `str(VIDEO_DIR / "xxx.mp4")` 绝对路径，并 `cwd=VIDEO_DIR`，否则 mp4 会漏到项目根；(6) **JSON 数字字段转 int**——MediaCrawler jsonl 里 `liked_count`/`play_count` 等是字符串，直接 `int(v.get('k', 0) or 0)` 转 int，否则字符串比较会漏筛（2026-09-13 抖音「示例博主」实测 23,800 点赞被漏的教训）；(7) **视频号必须全自动 + 禁用 md_generator.py**——唯一入口 `scripts/wx_pipeline.py`，**禁止让用户手动点视频/点下载按钮**，MD 一律用 pipeline 内建 `step_md()` 按 SRT 逐段生成（`md_generator.py` 会把逐字稿合并成一坨、错挂博主名、被后台反复覆盖成占位版）。
agent_created: true
---

# 博主视频全量扒取

把某个博主的全部视频 → 按条件筛选 → 下载 → Whisper 转写 → 逐字稿 MD 的端到端流水线。

## TL;DR（30 秒版）

收到请求后：

1. **🔴 开工前必问 2 件事**（AskUserQuestion，一次问完，之后全自动不用再问）：
   - **改写语气类型**（每个新博主必问，不准套默认）：情感共鸣型 / 犀利观点型 / 干货拆解型 / 人物故事型 / 种草带货型
   - **筛选 + 时间范围**：点赞/播放阈值、近 N 天
   - ✅ **不问**：装证书、点按钮、分几步跑、输出目录 —— 这些全自动默认
   - ❌ **不准自作主张**：语气没问就开跑 = 返工
2. **6/7 步**（按序执行，视频号才走第 7 步清理）：
   1. 平台可行性评估 → 给用户看实测结果表
   2. 搭项目脚手架（标准 6 项目录结构）
   3. 获取视频（按平台分路径）
   4. Whisper 转写（CPU int8，约 5-20x 实时）
   5. 生成 MD + AI 提炼（6 模块填满、零 placeholder）
   6. **改写新视频脚本**：基于转写结果，生成同主题/同内容但**全新表达**的视频脚本（新标题 + 新口播文案），独立存放到 `04-原视频脚本改写/`
   7. **（仅视频号）卸载/清理**：跑 `wx_video_download.exe uninstall` + 杀残留进程 + 三态验证

输出位置/形式不问了，直接走「标准项目目录结构」默认值。

> **🔴 视频号任务：收到请求后直接跳 `references/platform-wxchannels.md`，只跑 `scripts/wx_pipeline.py` 一条命令，流程已固化、不得临场改动，也不得让用户手动点任何按钮。**

## 适用边界

- ✅ **适用**：批量扒取某博主某时间段、某数据维度的爆款视频，做内容研究/逐字稿/案例库
- ❌ **不适用**：只想看几个视频（直接打开客户端）；实时监控（属于另一类 skill）；视频二创剪辑（不是本 skill 职责）

## 🚦 八平台分类汇总（截至 2026-09-14 · v2.7）

| 状态 | 平台 | 可达性 | 实测归档 | 文档 |
|---|---|---|---|---|
| ✅ | **微信视频号** | 🟢 **已全自动**（工具 HTTP API 批量拉 + 直链下载 + decrypt 解密） | ✅ **115 条清单 / 44 条实抓「示例博主」；172 条清单 / 近 7 天 5 条「示例博主」** | **`references/platform-wxchannels.md`（唯一标准，不得改流程）** |
| ✅ | 小红书 | 🟡 半封闭 → MediaCrawler | ✅ 29 条「示例博主」 | `references/platform-xhs.md` |
| ✅ | B站 | 🟡 半封闭（web search 兜底） | ✅ 3 条「示例博主」 | `references/platform-bilibili.md` |
| ✅ | 快手 | 🟡 半封闭 → MediaCrawler patch | ✅ 17 条「示例博主」 | `references/platform-ks.md` |
| ✅ | YouTube | 🟡 半封闭（代理 + cookie + yt-dlp-ejs） | ✅ 2 条「@示例博主」 | `references/platform-youtube.md` |
| ✅ | TikTok | 🟡 半封闭（代理 + Chrome-136 impersonate） | ✅ 9 条「@示例博主」 | `references/platform-tiktok.md` |
| ✅ | 抖音 | 🟡 半封闭（MediaCrawler + Playwright + 扫码） | ✅ 2 条「示例博主」 | `references/platform-douyin.md` |
| ✅ | **Instagram** | 🔴 强封闭（必须登录 + 2FA + IG 限流） | ✅ **20 条「@示例博主」** | **`references/platform-instagram.md`** |

**v2.5（2026-09-13 当晚）抖音 + Instagram 双平台跑通，技能集从 7 平台扩展到 8 平台**。详见 `references/platform-matrix.md` 全平台详细决策表与卡点记录。

## 🔴 9 大硬铁律速查（v2.8 · 任何平台强制）

| # | 铁律 | 一句话 |
|---|---|---|
| 1 | **浏览器 Profile 保护** | 海外平台登录只能 `项目目录/login_profile/`，**绝对禁止** `--user-data-dir` 指真实 Chrome / NTFS junction（详见 SKILL.md 段 + `chrome-extension-recovery.md`） |
| 2 | **改写脚本语言匹配原视频** | 海外平台 → 英文；国内平台 → 中文；禁止「（在此填入）」空模板（`extract_rewrite_script.py` 已自动识别 language 字段） |
| 3 | **🔴 改写必须与逐字稿不同（有闸门）** | 改写 ≠ 复制逐字稿，必须有新 Hook / 新口播 / 新 CTA，原文只放 `Original Core Script (Reference)` 区。**纯规则脚本（如 `step_rewrite`）不会改写，只会套模板 + 摘原句，产出的 04 会 100% 复制 03**（2026-09-14「示例博主」教训：04 正文 99-154 行全抄 03，被用户当场指出「和逐字稿一样」）。口播文案**必须由 AI 读逐字稿后亲笔重写**，交付前**必须跑 `python scripts/verify_rewrite_distinct.py <项目根>`**，exit≠0 = 一票否决、重写后才可交付（详见铁律 9） |
| 4 | **🔴 完整视频双落 mp4+m4a** | `-f "download/..."` 或 `-f "best[ext=mp4]"` 先 mp4、再 `-x --audio-format m4a` 抽音频；**禁只下音频**（2026-09-13 TikTok 教训，二次剪辑必须有 mp4） |
| 5 | **🔴 落盘用绝对路径** | subprocess yt-dlp `-o "xxx.mp4"` 必须 `str(VIDEO_DIR / "xxx.mp4")` 绝对路径 + `cwd=VIDEO_DIR`，否则 mp4 漏到项目根目录（跨项目经验，已加进 `~/.workbuddy/MEMORY.md`） |
| 6 | **🔴 JSON 数字字段必须 int 转** | MediaCrawler jsonl 里 `liked_count`/`play_count` 是字符串，直接 `int(v.get('k', 0) or 0)` 转 int；否则字符串比较会漏筛（2026-09-13 抖音「23,800 点赞」被漏的教训） |
| 7 | **🔴 视频号必须全自动，禁用旧版 `md_generator.py`（已废弃，本包不再提供）** | 视频号唯一入口 `scripts/wx_pipeline.py`（搜账号→翻页拉全量→直链下载→decrypt→Whisper→分时段 MD）。**禁止让用户点视频/点下载按钮**（2026-09-14 让用户点了 3 次只拿到 1 条的教训）。**禁止用旧版 `md_generator.py`（已废弃，本包不再提供）**（会把多段 SRT 合并成一坨、头部错挂博主名、还会被后台反复覆盖成占位版）——视频号一律用 pipeline 内建 `step_md()` |
| 8 | **🔴 改写语气必须提前问（不准套默认）** | **下载/转写开工前**用 AskUserQuestion 问一次语气：情感共鸣型 / 犀利观点型 / 干货拆解型 / 人物故事型 / 种草带货型。**每个新博主必问**，同一博主重复扒取沿用上次选择。注意边界：**执行细节（装证书、点按钮、跑几步、输出目录）全自动不问 ≠ 输出语气可以不问**——后者是用户要的结果形态，必须确认（2026-09-14 用户明确要求「语气还是要问的，我指的是下载转写的全过程不用问」） |
| 9 | **🔴 04 交付前必跑差异验收脚本** | `python scripts/verify_rewrite_distinct.py <项目根>`（加 `--strict` 收紧）。判定：整行抄自 03 = 0、最长连续相同字符 ≤15、8-gram 重合 ≤15%、占位话术 = 0、主体 ≥8 行。**exit≠0 一律重写，不许带 FAIL 交付** |

完整规则 + 反例见以下各段（每段都有对应独立小节详细展开）。

## 🔴 浏览器 Profile 保护铁律（最高优先级 · 2026-09-12 事故教训）

**绝对禁止**以下任一操作（违反会触发 Chrome profile 重置，导致用户扩展被清空）：

1. **禁止** `--user-data-dir` 指向真实 Chrome User Data 目录（`C:\Users\<你的用户名>\AppData\Local\Google\Chrome\User Data`）或其 NTFS junction / 符号链接副本
2. **禁止** Playwright `launch_persistent_context(user_data_dir=<真实 Chrome 路径>)`
3. **禁止** 把任何工具/脚本指向 `AppData\Local\Google\Chrome\User Data` 下任何子目录作为持久化目录

**原因**：Chrome 137+ 把这种路径视为损坏/新装 profile，会清空 `Default/Extensions/` 代码目录和 `Secure Preferences` 的 `extensions.settings` 字段，导致用户所有扩展「消失」（虽然 `Local Extension Settings/` 数据还在）。

**正确做法（海外平台登录专用）**：

1. 在项目目录下新建独立 profile 目录，例如：
   ```
   {工作目录}\<项目名>\login_profile\
   ```
2. Playwright / Chrome 只能指向这个**新建空目录**
3. 首次让用户在弹出的窗口中手动登录一次
4. 导出 `cookies.txt` 到项目根目录
5. 后续任务**只复用 `cookies.txt`**，不再启动 Chrome 窗口

**事故案例**：2026-09-12 用 NTFS junction 启动 Playwright 登录 YouTube 窗口，导致 Doris/Default profile 28 个扩展被清到剩 2 个。完整恢复指南见 `references/chrome-extension-recovery.md`。

## 🔴 改写脚本语言铁律（按平台原语言生成）

**改写新视频脚本时，必须用原视频的语言，不是默认中文，且必须是改写而不是复制逐字稿**：

| 平台 | 改写脚本默认语言 | 备注 |
|---|---|---|
| YouTube | **英文** | 海外平台默认英文，即使博主是华人讲中文也要用中文 |
| TikTok | **英文**（或博主口语语言） | 同上 |
| Instagram | **英文**（或博主口语语言） | 同上 |
| B站 | **中文** | 国内平台默认中文 |
| 小红书 | **中文** | 同上 |
| 快手 | **中文** | 同上 |
| 微信视频号 | **中文** | 同上 |

**为什么必须这样做**：扒取海外平台的视频，目的就是为了发到对应海外平台（YouTube/TikTok/Instagram），不是发到中文平台。如果用中文改写，就失去了"在海外社媒重新发布"的价值。

### 改写脚本质量铁律：改写 ≠ 复制逐字稿

**改写脚本的本质是重新组织表达，不是把原视频的 transcript 粘贴一遍**。

| 维度 | 错误做法（禁止） | 正确做法 |
|---|---|---|
| Hook | 复制原视频第一句 | 用新角度/价格/悬念重写，3 秒内抓人 |
| 产品引入 | 照搬原视频对产品名的口误 | 用准确、简洁的口语重新介绍 |
| 卖点展开 | 直接粘贴原视频长句 | 提炼成 3-4 个短句，每句带画面提示 |
| 结尾 CTA | 复制原视频的 "like and subscribe" | 根据目标平台重写互动指令 |
| 语言 | 海外平台用中文占位 | 海外平台用英文，国内平台用中文 |

**交付前必查**：
- 04-改写脚本/ 中的文件**不能直接复制** 03-逐字稿/ 的原文段落
- 必须出现「新标题/新 hook/新口播结构/新 CTA」
- 逐字稿原文只放在 `## 💎 Original Core Script (Reference — do not copy verbatim)` 参考区

**自动识别语言的方法**：
1. 看转写 JSON 的 `language` 字段（Whisper 自动检测）
2. 或读视频元数据的 `language` / `original_language`
3. 或看标题/描述文本的字符集

**铁律**：
- 海外平台（YouTube/TikTok/Instagram）扒取 → **必须**生成**该视频口语语言**的改写脚本初稿（不是「（在此填入）」的空模板）
- `extract_rewrite_script.py` 输出时按平台自动选语言模板
- 04-改写脚本/ 目录下文件命名保持 `{NNN}-{原标题}_改写.md`

## 事实性红线

- 拿不到真实数据（点赞数/发布时间）时，MD 元信息留 `—`，**禁止编造**
- 产出"主题模拟"内容（真实视频还没下载）时，README 和交付说明必须显著标注「模拟内容，待真实视频替换」
- 文件名/编号规则在所有平台固定不变，**禁止**因平台差异改用不同命名

## 标准项目目录结构（固化，不再讨论）

- **输出位置**（不问了）：默认 = 用户当前工作目录下的 `<博主名>视频扒取/` 文件夹
- **输出形式**（不问了）：每个新项目一律按以下结构创建

```
<博主名>视频扒取/
├── README.md              # 总览 + 进度统计 + 索引
├── 00-操作手册.md          # 用户需手动做的步骤（按平台不同）
├── 01-视频清单/
│   ├── README.md           # 命中清单 + 阈值分布
│   └── videos_index.json   # 结构化索引（NNN → {bvid/note_id/video_id, title, ...}）
├── 02-Whisper转写/
│   ├── 视频源文件/         # 放 .mp4（统一命名 {NNN}-{完整标题}.mp4）
│   └── 转写结果/           # .json 输出（{NNN}-{完整标题}_转写.json）
├── 03-逐字稿MD/            # 原始视频的逐字稿 + 6 模块提炼
├── 04-原视频脚本改写/      # 改写后的新视频脚本（独立文件，新标题+新口播）
├── 99-生成脚本/
│   ├── collect_videos_<platform>.py  # 从本 skill scripts/ 拷入（如 xhs/bilibili/wx）
│   ├── transcribe_with_whisper.py   # 从本 skill scripts/ 拷入并改路径
│   ├── generate_md_timed.py           # 从本 skill scripts/ 拷入并改路径（分时段 MD）
│   └── extract_rewrite_script.py    # 从 03 MD 提取改写脚本到 04 目录
├── browser_context/        # （仅小红书）Playwright 登录态
└── models/                          # ASR 模型缓存位置（可选）
```

### 🔴 跨平台一致性铁律（所有平台强制）

**无论视频号、小红书、B站还是 YouTube，最终产出的目录分类、文件命名、MD 结构必须完全一致**——便于跨平台统一归档与二次剪辑。

| 项目 | 统一规范 |
|---|---|
| 目录 | `00-操作手册.md` / `01-视频清单/` / `02-Whisper转写/{视频源文件,转写结果}` / `03-逐字稿MD/` / `04-原视频脚本改写/` / `99-生成脚本/` / `models/`（小红书增 `browser_context/`） |
| 视频标识 | 用项目内连续编号 NNN（`001`/`002`/`...`），不暴露平台 ID 到文件名 |
| 02 视频源文件 | **🔴 必须同时落 mp4（视频） + m4a（音频）**：TikTok/YouTube 等海外平台默认 `-f "download/h264_720p/download"` 下 mp4，转写再补 m4a 或 `-x` 同步抽 |
| 02 转写结果 | `{NNN}-{完整标题}_转写.json`（与视频源文件同名，仅后缀不同） |
| 03 文件名 | `{NNN}-{完整标题}.md`（**连字符 `-` 分隔、用完整标题，不简写、不按下划线**） |
| 04 文件名 | `{NNN}-{完整标题}-改写脚本.md` |
| 03 结构 | `# 标题` + 头部元信息（平台/ID/发布时间/点赞/收藏/评论/时长/来源/转写来源/风格）+ `## 🎯 核心观点（1 句话）` / `## 💡 3 个关键点` / `## 📝 逐字稿`（带 `[HH:MM:SS]` 时间戳）/ `## 🪝 金句摘录` / `## 🔗 我的行动` |
| 04 结构 | `# 🎬 标题（改写版）` + 头部元信息（原始视频链接/博主/时长/数据/改写日期/风格/基础）+ `## 📝 改写内容`（`### 新标题` + `### 新口播文案`）+ `## 🔗 与原视频对比` |
| 对比表分隔行 | `\|------\|--------\|--------\|`（与既有模板严格一致，不要用 `\|---\|---\|---\|`） |
| 编号规则 | **一律按筛选维度降序编号**（点赞为主）：001 = 点赞最高。**不按发布时间、不按抓取顺序** |
| 平台 ID → NNN 映射 | 记录到 `01-视频清单/<platform>_id_to_seq.json`（如 `bvid_to_seq.json`、`note_id_to_seq.json`），便于后续回溯 |

> **🔴 视频文件必须落 mp4（2026-09-13 TikTok 教训）**：之前偷懒只 `-x --audio-format m4a` 抽音频，导致所有海外平台都只有 400KB m4a、没有完整视频，二次剪辑无源。修正后默认 `-f "download/h264_720p/download"` 先落 mp4，再单独抽出 m4a 供 Whisper 用。**任何平台都不能只下音频**。

> **🔴 落盘路径必须用绝对路径（2026-09-13 TikTok 教训）**：subprocess.run yt-dlp 时若 `-o "xxx.mp4"` 用相对路径，会把文件写到 subprocess 继承的 cwd（`项目根目录`），而非预期的 `视频源文件/` 子目录。**强制用绝对路径 `-o str(VIDEO_DIR / "xxx.mp4")`** 或显式传 `cwd=VIDEO_DIR`。

### 🔴 文件命名清洗规则（safe 函数）

所有脚本（generate_md_timed / whisper_transcribe / collect_videos_*.py）共用同一个 `safe()` 函数，逻辑如下：

```python
def safe(name: str, max_len: int = 60) -> str:
    name = re.sub(r'[\\/:*?"<>|]', "-", name or "无标题")  # Windows 非法字符
    name = re.sub(r'[\n\r\t]', " ", name).strip()
    name = re.sub(r'-+', "-", name)                          # 合并连续 -
    name = re.sub(r'\s+', " ", name)
    name = re.sub(r'\.{2,}', '…', name)                     # 连续点合并为 Unicode 省略号
    name = name.strip("-. ")                                 # 去首尾冗余 - . 空格
    if len(name) > max_len:
        name = name[:max_len].rstrip("-.")
    return name

# 拼接后再做一次清理：….mp4 → …mp4
target = re.sub(r'\.{2,}\.mp4$', '.mp4', f"{seq:03d}-{safe_title}.mp4")
```

### 🔴 筛选阈值可由用户中途调整（重要）

用户第一次给的门槛（如「点赞>2000」）**不是终态**——很可能后续追加更低门槛（如「点赞≥500 的也给我」）。处理规则：

1. **先问要不要一次性放低**：拿到任务时若用户只给了一个偏高门槛，主动问一句「是否只要 ≥X，还是先跑高门槛、后续可能补低门槛？」
2. **阈值变更 = 增量补齐，不是重做**：
   - 元数据/视频**已经全量抓到本地**时，不需要重跑爬虫，直接对本地 jsonl 重新筛一遍
   - 只对新纳入的条目补做：归集视频 → Whisper 转写 → 生成 03/04
   - **同时重排全部编号**（因为编号按点赞降序，新条目会插进中间），旧文件按新编号重命名后覆盖
3. **分级阈值命中数先给用户看**：交付前先列一张「阈值 → 条数」分布表（如 ≥2000:7 / ≥1000:17 / ≥500:29），让用户决定停在哪个档
4. **筛选脚本要参数化**：`filter_by_likes.py` 里的阈值写成一个常量，改一处即可；不要硬编码在多处

**交付前必跑的一致性检查**：
- [ ] 03/04 文件名均为 `NNN-完整标题` 格式（连字符）
- [ ] 序号按筛选维度（点赞/播放）**降序**排列，001 为最高
- [ ] 每篇 03 恰好 5 个 `##` section；每篇 04 恰好 2 个 `##` section
- [ ] 序号从 001 起连续无缺口
- [ ] 0 处 `<!--` 占位、0 处重复段落
- [ ] 头部字段顺序 / emoji / 措辞与既有平台项目一致
- [ ] 根目录无散落杂项文件（临时截图、cookie、二维码等一律清理或归入子目录）

> 参考实现：
> - 视频号：`{工作目录}\品牌出海姐Rose视频扒取\`（35 条）
> - 小红书：`{工作目录}\xhs_示例博主\`（29 条）
> - B站：`{工作目录}\示例博主_B站视频扒取\`（3 条）
> - **快手：`{工作目录}\示例博主_快手视频扒取\`（17 条）**

## 流程

### 步骤 1：平台可行性评估

加载 `references/platform-matrix.md` 查各平台详细可达性。简要总览：

| 平台 | 可达性 | 路径 |
|---|---|---|
| B站 | 🟡 半封闭 | 详见 `references/platform-bilibili.md`：`arc/search` 持续 -799 风控，需用 `search.bilibili.com/all` web 页面 + 单视频接口交叉验证；yt-dlp 用 30080+30216 低画质绕登录 |
| YouTube | 🟡 半封闭（代理 + cookie） | yt-dlp 拿列表+元数据+音频；中国大陆需本地代理 + 登录 cookie 绕过 bot 验证 |
| TikTok | 🟡 半封闭 | yt-dlp 抓主页列表；风控严，全量需登录 cookie |
| Instagram | 🟡 半封闭 | instaloader 抓全量 Reels/帖子（需 `pip install instaloader`，登录更稳） |
| 微信视频号 | 🟢 **全自动** | **唯一路径：`scripts/wx_pipeline.py` 一条命令跑完**（搜账号 → 翻页拉全量清单 → 直链下载 → decrypt 解密 → Whisper → 分时段 MD）。用户唯一动作：PC 微信打开过视频号页面。完整标准见 `references/platform-wxchannels.md` |
| 抖音 | 🟡 半封闭 | 需登录态/第三方数据平台（推荐新抖、蝉妈妈，付费） |
| 小红书 | 🟡 → ✅ MediaCrawler | 走 MediaCrawler + Playwright，完整流程见 `references/platform-xhs.md`；**分批抓取 ≤30 条/批** |
| 快手 | 🟡 → ✅ MediaCrawler（patch） | MediaCrawler + patch `kuaishou/login.py` 登录 xpath + 先 navigate 到 profile；分批抓取 ≤30 条/批，完整流程见 `references/platform-ks.md` |

**实测优先**：拿到用户给的账号后，先做一次小规模探测（WebFetch/小脚本），把"实测结果表"（验证项 / 实测结果 / 卡点 / 可行路径 / 需用户配合的事）给用户看，不要臆断可行性。

**小红书任务**：直接跳 `references/platform-xhs.md` 走 MediaCrawler 全流程，无需再 WebFetch 实测。
**B站任务**：直接跳 `references/platform-bilibili.md` 走 API + yt-dlp 组合方案，无需再 WebFetch 实测。
**快手任务**：直接跳 `references/platform-ks.md` 走 MediaCrawler 全流程（与小红书共用同一套 MediaCrawler，仅登录 xpath 不同）。

### 步骤 2：搭项目脚手架

按「标准项目目录结构」创建项目文件夹，从本 skill 的 `scripts/` 拷贝以下脚本到项目 `99-生成脚本/`：

| 脚本 | 何时拷贝 | 来源 |
|---|---|---|
| `collect_videos_<platform>.py` | 视频归集阶段用到 | `scripts/collect_videos_xhs.py` / `scripts/collect_videos_bilibili.py` / `scripts/collect_videos_ks.py` |
| `transcribe_with_whisper.py` | Whisper 转写 | `scripts/transcribe_with_whisper.py` |
| `generate_md_timed.py` | 通用分时段逐字稿 MD（全平台） | `python generate_md_timed.py --srt-dir <转写结果> --md-dir <逐字稿MD> --author <博主> --platform <平台>` |
| `extract_rewrite_script.py` | 改写脚本提取 | `scripts/extract_rewrite_script.py` |
| **`verify_rewrite_distinct.py`** | **🔴 04 vs 03 差异验收闸门（交付前必跑，exit≠0 = 重写）** | `python scripts/verify_rewrite_distinct.py <项目根> [--strict]` |
| **`wx_pipeline.py`** | **视频号一键全自动**（不拷进项目，直接在 skill 目录跑，传 `--project`） | `scripts/wx_pipeline.py` |

每个脚本拷贝后只改头部 `BASE_DIR`、`SRC_DIR`、`DST_DIR` 和 `generate_md()` 里的博主名/来源字段。

> **🔴 视频号任务不走本步骤的脚本拷贝**：直接跑 `scripts/wx_pipeline.py`（带 `--project` 参数），它会自动建好全部目录并跑完 8 步，见 `references/platform-wxchannels.md`。

### 步骤 3：获取视频（按平台分路径）

- **B站**：**完整流程见 `references/platform-bilibili.md`**。`arc/search` 接口持续 -799 风控（WBI 签名机制），必须用 `search.bilibili.com/all` web 页面 + 单视频接口交叉验证；yt-dlp 用 30080+30216 低画质绕登录限制。**视频归集**：下载到 `<项目>/raw_downloads/`，然后跑 `99-生成脚本/collect_videos_bilibili.py` 自动按 BVID/标题匹配并归集到 `02-Whisper转写/视频源文件/`。
- **YouTube**：**完整流程见 `references/platform-youtube.md`**。中国大陆环境下必须同时满足 **本地代理 + 登录 cookie**（`--cookies-from-browser chrome` 或 `--cookies cookies.txt`），否则单视频会触发 Google bot 验证（`Sign in to confirm you’re not a bot`）。先用 `yt-dlp --flat-playlist` 拿列表，再对命中视频单独提取 `view_count`/`upload_date`，最后用 `yt-dlp -f bestaudio` 下载音频。**视频归集**：下载到 `<项目>/raw_downloads/`，然后跑 `99-生成脚本/collect_videos_youtube.py` 按 `video_id` 归集到 `02-Whisper转写/视频源文件/`。
- **TikTok**：`yt-dlp https://www.tiktok.com/@<user>` 抓主页视频列表 + 下载；风控严、点赞数不稳，先小规模实测再定（可引导用户提供登录 cookie）。
- **Instagram**：`instaloader --login <你的账号> --no-pictures profile <目标@user>` 抓全量 Reels/帖子 + 元数据（点赞数）；首次需 `pip install instaloader`。备选 `yt-dlp` 单条下载。
- **微信视频号**：🔴 **按 `references/platform-wxchannels.md` 执行，不要临场发挥**。唯一入口 `scripts/wx_pipeline.py`（一条命令全自动）。**禁止让用户手动点视频/点下载按钮**——这是 2026-09-14 的重大误区，工具自带完整 HTTP API 可批量抓全量。要点：翻页字段 `lastBuffer`、username 在 `infoList[i].contact.username`、直链下载后必须 `POST /api/channels/decrypt?filepath=&key=` 解密、**禁用旧版 `md_generator.py`（已废弃，本包不再提供）**（会把逐字稿合并成一坨 + 错挂博主名）。**视频归集**：不需要，pipeline 直接把 mp4 写到 `02-Whisper转写/视频源文件/`。
- **抖音**：Web 端通常需登录 cookie；可引导用户用第三方平台（新抖/蝉妈妈）导出视频列表 CSV，再走下载链路。
- **小红书**：**完整流程见 `references/platform-xhs.md`**。使用 MediaCrawler（GitHub 50k+ stars）+ Playwright 持久化登录态。**分批抓取 ≤30 条/批**，间隔 60-90s。首次需用户扫码登录（**必须 App 上点"登录"确认**，否则 120s 超时）。**视频归集**：MediaCrawler 把视频下载到 `<MediaCrawler>/data/xhs/videos/<note_id>.mp4`，跑 `99-生成脚本/collect_videos_xhs.py` 按 `note_id_to_seq.json` 归集到 `02-Whisper转写/视频源文件/`。
- **快手**：**完整流程见 `references/platform-ks.md`**。复用小红书 MediaCrawler 方案，但需要 patch `media_platform/kuaishou/login.py`：把 `<p>登录</p>` xpath 改成 `<span class="sidebar-login-button">`，且首次登录需先 `goto("https://www.kuaishou.com/profile/<id>")` 才能看到登录按钮（主页 `/?isHome=1` 不显示）。Whisper 偏好繁体，generate_md.py 加 `pip install zhconv` 后转简体。**视频归集**：下载到 MediaCrawler `data/kuaishou/videos/`，然后跑 `scripts/collect_videos_ks.py` 自动按 photo_id 归集到 `02-Whisper转写/视频源文件/`。

### 步骤 4：Whisper 转写（AI 端全自动）

**已部署场景**（推荐，venv 已存在）：直接用

```bash
C:/Users/<你的用户名>/.workbuddy/binaries/python/envs/whisper/Scripts/python.exe "<项目>/99-生成脚本/transcribe_with_whisper.py"
```

> ⚠️ **注意是 `envs/whisper`，不是 `envs/default`** —— `envs/default` 没装 faster-whisper，用它跑会报
> 「faster-whisper 未安装」（2026-09-14 踩过）。备选：系统 Python 3.12
> `C:/Users/<你的用户名>/AppData/Local/Programs/Python/Python312/python.exe`（已装 faster-whisper + opencc）。

**首次部署场景**（venv 不存在时）：

```bash
"<managed python>" -m venv C:/Users/<你的用户名>/.workbuddy/binaries/python/envs/whisper
C:/Users/<你的用户名>/.workbuddy/binaries/python/envs/whisper/Scripts/python.exe -m pip install faster-whisper
```

脚本内已设 `HF_ENDPOINT=https://hf-mirror.com`，**不要去掉**——huggingface.co 在本机环境被拦，模型必须走国内镜像。

速度参考：CPU int8 约 5-20x 实时，40 条 1 分钟视频 ≈ 10-30 分钟。

### 步骤 5：生成 MD + AI 提炼

```bash
"<managed python>" "<项目>/99-生成脚本/generate_md_timed.py" ^
    --srt-dir "<项目>/02-Whisper转写/转写结果" --md-dir "<项目>/03-逐字稿MD" ^
    --author "<博主>" --platform "<平台>"
```

脚本产出 6 模块骨架后，**AI 必须逐篇补齐**占位段（`<!-- ... -->`），完成标准：

- 🎯 核心观点：1 句话总结
- 💡 3 个关键点：动词开头 + 数字/案例/出处 + 对用户的启示
- 🪝 金句摘录：2 条适合二次传播的原句
- 🔗 我的行动：2 条可勾选清单
- 元信息（点赞/时间/时长）从视频登记表回填
- 最后全量 `grep <!--` 检查残留，必须 0 处

**注意**：03 MD **不含**改写脚本模块。改写脚本是独立产物，在 04 目录（步骤 6）。

### 步骤 6：原视频脚本改写（AI 端全自动，必做）

**为什么必要**：本 skill 不止"扒+转录"，更要"消化再用"。改写后的新视频脚本（同主题/同核心论点，但全新表达 + 全新标题）是本 skill 的核心交付物之一，**独立成文件**存放在 `04-原视频脚本改写/`，不和 03 逐字稿 MD 混在一起。

**输入**：步骤 5 已填满 6 模块的 MD（含逐字稿 + 核心观点 + 3 关键点 + 金句 + 我的行动）

**输出**：在 `04-原视频脚本改写/` 下生成独立文件，每个视频一个 `.md`：
- 文件名：`{序号}-{去标签标题}-改写脚本.md`
- 内容包含：
  - 头部元信息（原始视频路径 / 博主 / 原视频时长 / 原视频点赞 / 改写日期 / 改写风格 / 改写基础）
  - **新标题**：原标题的同主题不同表达（钩子更足 / 角度更新）
  - **新口播文案**：保留原视频核心论点 + 案例 + 数据，但用用户选定的脚本语言风格重写
  - 与原视频对比表（标题/口播/核心论点/风格 4 维度对比）
- 字数建议：与原视频时长对应（1 分钟口播 ≈ 250-300 字）

**🔴 步骤 6 三道强制关卡**：

| 关卡 | 时机 | 要求 |
|---|---|---|
| ① **问语气** | **开工前**（下载之前） | AskUserQuestion 给 5 个命名选项，用户选了才能开始。**没问就开跑 = 违规** |
| ② **AI 亲笔写** | 生成 04 时 | 规则脚本只出骨架，口播文案必须由 AI 读逐字稿后重写，禁止「套模板 + 摘原句」 |
| ③ **跑验收** | 交付前 | `verify_rewrite_distinct.py <项目根>`，exit=0 才可交付 |

**风格约束**：必须严格遵守用户在关卡①选定的语气，**不要默认成情感共鸣/幽默**。

**执行方式**（两种任选）：

**方式 A：先填 03 MD 再提取**（推荐用于 LLM 协助场景）
1. 先在 `generate_md_timed.py` 产出的 03 MD 里追加 `## 🎬 改写新视频脚本` 模块
2. 跑 `generate_md_timed.py` 生成分时段 03 MD（脚本不产生任何占位块）
3. AI 逐篇填改写脚本内容（含核心观点/3 关键点/金句也基于改写脚本回填）
4. 跑 `extract_rewrite_script.py` 把改写脚本段从 03 拆出来，独立保存到 `04-原视频脚本改写/`，并从 03 MD 删除该段
5. 03 MD 最终保留：元信息 / 核心观点 / 3 关键点 / 逐字稿 / 金句 / 我的行动（6 模块）

**方式 B：直接生成 04 文件**（适用于纯 LLM API 批量场景）
1. 直接读逐字稿 + 登记表，批量生成 04 目录下的独立改写脚本 MD
2. 03 MD 不含改写脚本模块

**风格约束检查清单**：
- ✅ 字数与时长匹配（1 分钟 ≈ 250-300 字）
- ✅ 标题必须 `**加粗**`
- ✅ 口播用 `> ` 引用块包裹每段
- ✅ 结构：开头钩子 → 案例铺垫 → 拆解 3-4 个点 → 收尾金句
- ✅ 严格遵守用户选定的脚本风格

### 步骤 7：卸载/清理（仅视频号/小红书平台，按问题 5 答案触发）

视频号用的是 MITM 代理 + 自签证书，小红书用 Playwright 持久化登录态。任务跑完是否清理，按问题 5 答案：

**问题 5 选了「保留」或「不关心」→ 跳过本步骤**（被动等待清理指令）
**问题 5 选了「跑完即清」→ 立即执行对应平台清理**

#### 7.1 视频号清理（按需触发）

视频号用的是 MITM 代理 + 自签证书，跑完任务必须清理（删除证书 + 关闭代理），否则会一直影响其它网络请求。

**触发关键词例**：「帮我删掉视频号的证书」「下次使用的时候我再安装」

**步骤**：

1. **跑工具自带 uninstall 命令**（核心）
   ```bash
   "<工具目录>/wx_video_download.exe" uninstall
   ```
   - 删除初始化时自动安装的 MITM 证书（CurrentUser Root / LocalMachine Root，看当时装的哪个区）
   - **exit=0 即视为成功**，不必纠结有没有输出（无可见 cert 时工具静默退出）

2. **杀掉残留 wx 进程**（必做）
   ```powershell
   Get-Process | Where-Object {$_.ProcessName -like '*wx_video*'} | Stop-Process -Force
   ```
   - 白天跑批量下载时启动的常驻进程可能没自动退出（即使请求都完成了）
   - 这些进程会持有证书锁，**不杀进程就跑 uninstall 可能残留证书**

3. **复跑一次 uninstall 确认**
   ```bash
   "<工具目录>/wx_video_download.exe" uninstall
   ```

3.5 **🔴 关闭系统代理（必做！uninstall 不管这个）**
   ```bash
   # 先记录原值（便于回滚）
   reg query "HKCU\Software\Microsoft\Windows\CurrentVersion\Internet Settings" /v ProxyEnable
   reg query "HKCU\Software\Microsoft\Windows\CurrentVersion\Internet Settings" /v ProxyServer
   # 关闭（保留 ProxyServer 值，只关开关，可逆）
   reg add "HKCU\Software\Microsoft\Windows\CurrentVersion\Internet Settings" /v ProxyEnable /t REG_DWORD /d 0 /f
   ```
   - **为什么必做（2026-09-15 实测）**：`uninstall` 只删证书、不管代理。卸载后 `ProxyEnable` 仍是 `0x1`、`ProxyServer=127.0.0.1:2023`，而 2023 已停止监听 → **浏览器/微信所有走系统代理的流量全部超时**，`netstat` 会看到一堆到 `:2023` 的 `SYN_SENT`
   - 关闭后残留的少量 `SYN_SENT` 是微信进程内缓存，**重启微信即消失**

4. **三态验证**（写到 `cleanup_verify.log`）
   - 证书：`certutil -store root | grep -iE "wx|wechat|weixin|mitm|finder"` 应无匹配
   - 系统代理：`ProxyEnable = 0x0`（**必须主动关，见 3.5**）
   - 进程 + 端口：`tasklist | grep -i wx_video` 应=0；`netstat -ano | grep -E ":(2022|2023)" | grep LISTEN` 应无
   - ⚠️ 若 PowerShell 工具无输出（本环境偶发），直接用上面的 `reg query` / `certutil` / `netstat` 命令行方案

**保留 vs 删除**：
- 工具可执行文件（`wx_video_download.exe`）+ `config.yaml` + `data.db`（含历史任务）：默认**保留**，下次用时直接启动
- 仅在用户明确说"整套都删了"时才连工具目录一起删

**下次使用路径**：直接跳到「步骤 3 视频号路径」重装证书 + 微信扫码登录。

#### 7.2 小红书清理（按需触发，**保留登录态更省事**）

小红书登录态是 MediaCrawler 持久化在 `<MediaCrawler>/browser_context/` 下的 Playwright context，清掉后下次需要重新扫码。

**触发关键词例**：「帮我清掉小红书登录态」「重新登录」

**步骤**：

```bash
rm -rf "<MediaCrawler>/browser_context/"
```

下次跑小红书任务会触发新的扫码流程。

---

## 真实视频回填（产出为"模拟"内容时）

当先有转写产出（来自历史视频/同主题模拟）但用户后来补传了真实视频，需做回填：

1. 把新视频放进 `02-Whisper转写/视频源文件/`，重跑步骤 4 拿到新 SRT
2. 把新 SRT 放进 `02-Whisper转写/转写结果/`
3. 重跑步骤 5，对应 MD 文件**同名覆盖**
4. AI 重读新 SRT，重做"3 关键点 / 2 金句 / 2 行动"的提炼
5. 在 README 顶部把"模拟内容，待真实视频替换"标识改为"✅ 已替换真实视频，日期 YYYY-MM-DD"

## 配套 scripts/ 工具清单（开箱即用）

| 脚本 | 用途 | 调用方式 |
|---|---|---|
| `scripts/collect_videos_xhs.py` | 小红书：从 MediaCrawler videos 目录归集 + 重命名 | `python collect_videos_xhs.py` |
| `scripts/collect_videos_bilibili.py` | B站：从 yt-dlp raw_downloads 归集 + 重命名 | `python collect_videos_bilibili.py` |
| `scripts/collect_videos_ks.py` | 快手：从 MediaCrawler kuaishou videos 目录归集 + 重命名 | `python collect_videos_ks.py` |
| `scripts/collect_videos_youtube.py` | YouTube：从 yt-dlp `raw_downloads/` 按 `video_id` 归集 + 重命名 | `python collect_videos_youtube.py` |
| `scripts/wx_pipeline.py` | **视频号一键全自动流水线**（搜账号→翻页拉全量→直链下载→decrypt→Whisper→分时段 MD→总索引） | `python wx_pipeline.py --nickname "..." --author "..." --spid "..." --project "..." [--days 365\|--all]`（**用 whisper venv 的 python 跑**） |
| `scripts/transcribe_with_whisper.py` | Whisper 批量转写（CPU int8，国内镜像） | `python transcribe_with_whisper.py` |
| `scripts/generate_md_timed.py` | SRT → **分时段**逐字稿 MD（全平台通用，无占位块） | `python generate_md_timed.py --srt-dir ... --md-dir ...` |
| `scripts/wx_pipeline.py` | 视频号一条命令全自动（含内建 `step_md()`） | `python wx_pipeline.py --nickname ... --project ...` |
| `scripts/verify_rewrite_distinct.py` | 改写差异验收闸门（交付前必跑，exit≠0 一票否决） | `python verify_rewrite_distinct.py <项目根>` |
| `scripts/extract_rewrite_script.py` | 从 03 MD 提取改写脚本到 04 目录 | `python extract_rewrite_script.py` |
| **`scripts/verify_rewrite_distinct.py`** | **🔴 改写差异验收（交付前必跑，见铁律 3/9）** | `python verify_rewrite_distinct.py <项目根> [--strict]` |

所有脚本**头部都有 `BASE_DIR` / `SOURCE_DIR` 等常量**，拷到项目 `99-生成脚本/` 后**改 1 个常量即可运行**。

## 配套 references/ 文档清单

| 文档 | 内容 |
|---|---|
| `references/platform-matrix.md` | 8 平台可达性矩阵 + 决策规则 |
| **`references/platform-wxchannels.md`** | **视频号全自动抓取唯一标准（2026-09-14 固化，不得改流程）**：HTTP API 清单 / 翻页 `lastBuffer` / 直链下载 / `decrypt` / 7 大坑 / `--min-likes` / `--rewrite` / 一条命令 |
| `references/platform-xhs.md` | 小红书 MediaCrawler 全流程（已跑通） |
| `references/platform-bilibili.md` | B站 web search + 单视频 API + yt-dlp 组合方案（已跑通） |
| `references/platform-ks.md` | 快手 MediaCrawler 全流程 + login.py 登录 xpath patch（已跑通） |
| `references/platform-youtube.md` | YouTube 代理 + cookie + yt-dlp 抓取流程（已部分验证） |

## 踩坑记录

| 坑 | 解法 |
|---|---|
| `SRT_TIME_PATTERN` 带 `^` 锚定但没开 `re.MULTILINE` → `search()` 永远失败 | 匹配多行文本时用非锚定 pattern 或加 `re.MULTILINE` |
| 改了 .py 不生效 | `__pycache__` 缓存旧 .pyc，跑之前 `find -name __pycache__ -exec rm -rf {} +` |
| HuggingFace 模型下载 502 | 必须走 `HF_ENDPOINT=https://hf-mirror.com` |
| 视频号主页链接 `weixin.qq.com/sph/<id>` 未登录抓不到 | 属正常，视频号强封闭，别浪费轮次重试 |
| 文件名带 Windows 非法字符（`<>:"/\|?*`） | 用统一 `safe()` 函数（见上方说明） |
| 视频文件名与 MD 编号不对应 | 用 `collect_videos_<platform>.py` 在归集阶段就保证 `02`/`03`/`04` 前缀完全一致 |
| venv 路径 | Windows venv 的 python 在 `Scripts/` 下不是 `bin/` 下 |
| Windows 上 Edit 文件报 EBUSY | 文件被占用，稍后重试 |
| 小红书 MediaCrawler 二维码不弹出 | patch `tools/crawler_util.py` 把二维码 PNG 保存到本地 |
| 小红书视频 URL 不在 `consumer.origin_video_key` | patch `store/xhs/__init__.py` 的 `get_video_url_arr`，走 `video.media.stream.h264[0].master_url`（或 EF4 master_url） |
| Whisper `device="cuda"` 沉默挂起 | 改 `device="cpu"` |
| Whisper 报 `IncompleteSnapshotError` | `local_files_only=True` + `HF_HUB_OFFLINE=1`，或用 `tiny` 模型 |
| B站 `arc/search` 持续 -799 | 2024 年起加 WBI 签名；改用 `search.bilibili.com/all` web 页面 |
| B站 yt-dlp 1080P 403 需登录 | 用 `30080+30216/30016/30011` 较低画质 |
| B站 yt-dlp 416 续传失败 | 清理 `.part`/`.tmp`/`.ytdl` 残留 |
| 快手 `//p[text()='登录']` xpath 失效 | patch `kuaishou/login.py` 改 `<span class="sidebar-login-button">` |
| 快手 `/?isHome=1` 主页不显示登录按钮 | 首次登录需 `goto("https://www.kuaishou.com/profile/<id>")` |
| Whisper 倾向识别繁体中文 | `pip install zhconv`，generate_md.py 加 `t2s()` 转简体 |
| YouTube 直连 timeout / reset | 必须走本地代理（v2rayN/Clash），把地址传给 yt-dlp |
| YouTube 单视频 bot 验证 | 加 `--cookies-from-browser chrome` 或 `--cookies cookies.txt` |
| Chrome 运行时无法复制 cookie db | 临时退出 Chrome 再跑；或导出 `cookies.txt` |
| YouTube flat-playlist view_count=NA | 对命中 id 单独跑单视频提取精确播放量 |
| **视频号 feed/list 只拿到 15 条（看起来像博主只有 15 条）** | **翻页字段是 `lastBuffer` 不是 `lastBuff`**；`continueFlag=="0"` 或 `lastBuffer` 为空才停（2026-09-14，误判成只有 1 条的根因） |
| **视频号 `infoList[i].username` 为空** | username 在 `infoList[i].contact.username`（v2_xxx@finder 格式） |
| **视频号直链下载下来播不了** | 文件是加密的（头非 `ftyp`），必须 `POST /api/channels/decrypt?filepath=<abs>&key=<decodeKey>`，**key 必须放 query**，放 body 报 key parameter is required |
| **视频号 MCP 模式全部 context canceled** | 别用 `wx_video_download.exe mcp`，直接 HTTP 打主服务 `/api/channels/*` |
| **`md_generator.py` 把 MD 覆盖成占位版 / 逐字稿合成一坨** | 改用 `generate_md_timed.py` 或 `wx_pipeline.py` 内建 `step_md()`。旧版 `md_generator.py` 已废弃并从本包移除——若外部项目里仍存在，务必禁用（`mv md_generator.py md_generator.py.disabled`） |
| **bash `rm` 删不掉带 `！？｜` 的文件** | 静默失败，改用 Python `Path.unlink()` |
| **Write 工具报 "File has been modified since read"** | 先写到 `99-生成脚本/_stage.md`，再 `mv` 到目标路径 |
