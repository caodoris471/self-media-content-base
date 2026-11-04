# 🔥 对标博主视频批量采集 → 逐字稿与改写脚本

> 本目录是 [self-media-content-base](../README.md) 已内置的采集引擎，无需重复安装。下方独立安装方式供单独使用采集 Skill 时参考。

<div align="center">

**定位账号 · 筛选视频 · 下载素材 · 本地转写 · 提炼观点 · 改写脚本 · 统一归档**

给自媒体创作者、编导和内容研究者：提供博主主页、筛选条件与改写风格，让 AI Agent 按流程整理研究材料。

![八平台流程](https://img.shields.io/badge/Platforms-8-blue)
![现有执行环境](https://img.shields.io/badge/Agent-WorkBuddy-6f42c1)
![本地转写](https://img.shields.io/badge/Transcription-local-green)
![转写无需付费API](https://img.shields.io/badge/Transcription-paid_API_not_required-brightgreen)

</div>

> **免责声明：** 本项目仅供学习、内容研究与获得授权的素材整理。请遵守平台规则、访问权限和版权要求；参考选题与表达方法，只借鉴不搬运。AI 转写和改写需要人工核对，下载成功不代表取得转载或商业使用授权。

## 📖 项目简介

把“打开博主主页、逐条找视频、下载、听写、整理、再写一版”串成一套可复用的 Agent 工作流。你给出账号和条件，得到视频清单、源视频与音频、带时间轴的转写、结构化逐字稿和独立改写稿。

这是供 AI Agent 执行的 **Skill + 平台操作参考 + Python 脚本**。现有流程以 WorkBuddy、Windows 和本地工具为基础；在 Codex 或 Claude Code 中使用时，需要先检查命令执行、浏览器、登录与依赖适配。

### 能帮谁

- **自媒体创作者 / 知识博主**：想系统研究对标账号，却没有时间逐条听写、整理观点和改写口播。
- **短视频编导 / 内容运营**：需要按时间、点赞或播放等指标筛选视频，为选题会准备可检索、可回看的案例。
- **跨境内容团队 / 内容研究者**：需要整理国内外博主的视频资料，保留来源、时间轴和原始材料，方便后续研究。

### 解决什么问题

| 以前 | 现在 |
|---|---|
| 一个个打开视频，手动记录标题和数据 | 先列清单，再按时间与平台可返回的互动字段筛选 |
| 下载、抽音频、听写需要来回切工具 | 按平台流程完成采集，再用本地 Whisper 批量转写 |
| 笔记只有一大段文字，找不到原句位置 | 保留 SRT 时间轴和分时段逐字稿，便于回看核对 |
| 各平台文件各放各的，难以复用 | 用统一编号关联视频、转写、逐字稿与改写脚本 |
| 所谓“改写”只是复制或换几个词 | 由 AI 重新组织标题和口播，再做重复度与占位内容检查 |

### 🔧 原理

博主账号 → 获取可访问的视频列表 → 按条件筛选 → 平台工具下载 MP4 / 提取 M4A → faster-whisper 本地转写 → 生成结构化 Markdown → AI 提炼并重写 → 差异检查与归档。小红书、抖音、快手等流程使用 MediaCrawler；其他平台按参考文档调用 yt-dlp 或视频号工具。转写在本地运行，无需付费转写 API；改写使用宿主 Agent 的模型，模型服务、代理或第三方数据服务可能另有费用。

## ✨ 功能特性

| 环节 | 功能 | 状态 |
|---|---|---|
| 账号采集 | 提供 8 个平台的账号列表、下载与登录流程 | ✅ 已有流程与历史案例 |
| 视频筛选 | 按时间范围及实际取得的点赞、播放、评论等字段筛选 | ✅ 依平台返回字段而定 |
| 素材留存 | 保留源视频与音频，统一编号和文件命名 | ✅ |
| 语音转写 | 本地 CPU 转写，输出带时间轴的 SRT 与文本 | ✅ |
| 研究笔记 | 元信息、核心观点、关键点、逐字稿、金句、行动建议 | ✅ 由脚本与 AI 配合完成 |
| 脚本改写 | 单独生成新标题与口播文案，交付前检查差异 | ✅ 需要宿主 AI |
| 实时监控 / 剪辑发布 | 当前 Skill 不提供这两类流程 | 🚧 未提供 |

**采集平台与运行条件：**

| 平台 | 主要流程 | 使用前需要确认 |
|---|---|---|
| 微信视频号 | PC 微信 + 视频号工具 HTTP API + `wx_pipeline.py` | PC 微信已登录并打开过视频号；工具进程与本地服务可用 |
| 小红书 | MediaCrawler + Playwright | 账号登录、视频下载配置与分批采集 |
| 抖音 | MediaCrawler + Playwright | 扫码登录；部分播放数据或视频直链可能不可用 |
| B站 | 搜索页面 / 单视频信息 + yt-dlp | 列表访问与下载画质权限；必要时使用登录态 |
| 快手 | MediaCrawler + Playwright | 登录流程适配、作品列表与视频下载配置 |
| YouTube | yt-dlp + Cookie / JavaScript 运行环境 | 网络可达、登录态以及当前提取器依赖 |
| TikTok | yt-dlp + curl_cffi | 网络可达与可用的浏览器模拟目标 |
| Instagram | 专用浏览器登录 + Cookie + yt-dlp 等 | 登录、可能的双重验证及平台限流 |

以上为仓库 **2026 年 9 月的历史流程与实测记录**，本次说明更新没有重新跑八平台采集。执行前应先验证当前可达性；“全量”指当前账号权限与接口允许枚举的范围，不保证取得删除、私密、受限或平台未返回的视频。各平台也不保证同时提供点赞、播放、收藏、评论等全部字段。细节见各 [平台参考文档](references/)。

## 🚀 快速开始

> 💡 如果这个项目对你有帮助，请给个 ⭐ Star 支持一下！

### 方式一：一句话安装（推荐）

把下面这段发给 Codex / Claude Code；使用 WorkBuddy 时，将安装目录改为它的 `~/.workbuddy/skills/`。这段提示词会先要求 Agent 检查适配，不代表三个宿主已经逐一实测兼容。

```text
帮我从 GitHub 安装这个 Skill：
https://github.com/caodoris471/blogger-video-pipeline
Codex 克隆到 ~/.codex/skills/blogger-video-pipeline；
Claude Code 克隆到 ~/.claude/skills/blogger-video-pipeline。
先检查目录是否已经存在，不覆盖已有修改。
安装后读取 SKILL.md 和 references/，检查 scripts/ 是否齐全，
核实当前宿主的命令执行、浏览器和目标平台登录能力。
本仓库没有统一安装脚本：按目标平台安装依赖、替换脚本里的项目路径，
先做小样本验证，再执行批量任务；先向我说明仍缺的工具或配置。
```

装完说的第一句话：

```text
请使用 blogger-video-pipeline，研究这个小红书博主：<主页链接>。
范围：最近 30 天；筛选：点赞超过 1000；改写语气：干货拆解型。
请先验证能否拿到清单与点赞字段，再做小样本验证。
输出视频清单、MP4/M4A、SRT、结构化逐字稿和独立改写稿。
```

开工前会确认平台与账号、筛选指标、时间范围、改写语言 / 语气，以及登录态是否保留；请求里已经给出的信息可直接沿用。同一博主可以沿用已确认的语气。

### 方式二：手动安装

下面是 Codex 的 PowerShell 示例；Claude Code 将 `.codex` 改成 `.claude`，WorkBuddy 改成 `.workbuddy`。目标目录已存在时先检查，不重复克隆覆盖。

```powershell
$skillPath = Join-Path $env:USERPROFILE '.codex\skills\blogger-video-pipeline'
git clone https://github.com/caodoris471/blogger-video-pipeline.git "$skillPath"
Set-Location -LiteralPath $skillPath
Get-Content -LiteralPath '.\SKILL.md' -Encoding UTF8
# 本仓库没有 install.ps1 / install.py；按下方依赖表和平台参考安装。
# 让 Agent 先替换脚本中的项目路径，再跑小样本，不直接执行带示例路径的脚本。
```

GitHub 或海外平台无法连接时，先确认本机网络和实际可用的代理配置，再让 Git / 下载工具使用该配置。不要套用他人的端口或凭据。详细流程在 [SKILL.md](SKILL.md) 与 [references/](references/)，仓库目前没有独立的 `docs/` 目录。

## 📋 用到的软件和 Skill

| 类别 | 名称 | 用途 | 安装方式 |
|---|---|---|---|
| Skill | [本 Skill](SKILL.md) | 编排采集、转写、改写和验收 | 从本仓库克隆完整目录 |
| 运行环境 | [WorkBuddy](https://www.codebuddy.ai/workbuddy) / 可适配的 Agent | 读取 Skill、执行命令、调用模型 | 按宿主官方说明安装；Codex / Claude Code 先检查适配 |
| 运行环境 | [Python](https://www.python.org/) | 执行配套脚本 | 现有流程使用 Python 3.12；建议使用独立环境 |
| 软件 | [FFmpeg](https://ffmpeg.org/) · [Git](https://git-scm.com/) | 音视频处理、下载仓库 | 官网安装并加入 PATH |
| 软件 | [MediaCrawler](https://github.com/NanmiCoder/MediaCrawler) | 小红书、抖音、快手等采集 | 按目标平台参考与其官方说明部署 |
| 软件 | [视频号下载工具](https://github.com/ltaoo/wx_channels_download) | 视频号列表、下载与解密 | 仅视频号任务需要；按平台参考部署并启动本地服务 |
| Python 包 | [faster-whisper](https://github.com/SYSTRAN/faster-whisper) · [yt-dlp](https://github.com/yt-dlp/yt-dlp) | 本地转写、平台视频下载 | 在选定的 Python 环境中使用 pip 安装 |
| Python 包 | [Playwright](https://playwright.dev/python/) · [curl_cffi](https://github.com/lexiforest/curl_cffi) | 浏览器登录、部分平台请求适配 | 按平台安装；Playwright 另需安装浏览器 |
| 素材 | 自有或获授权的博主视频 | 内容研究、转写和改写参考 | 通过有权访问的账号采集，保留来源 |
| 可选项 | Whisper 模型、[Node.js](https://nodejs.org/)、[yt-dlp-ejs](https://github.com/yt-dlp/ejs) | 模型推理、部分 YouTube 提取流程 | 按脚本与当前平台要求配置 |

本仓库不附带平台登录凭据、Whisper 模型、完整 MediaCrawler 或视频号可执行程序。转写耗时取决于模型、视频时长和电脑性能。

## ⚙️ 需要换成你自己的

仅修改实际会调用的脚本。先复制到任务目录，再替换路径，保留原 Skill 作为模板。

| 文件 | 字段 | 填什么 |
|---|---|---|
| `scripts/collect_videos_*.py` | `BASE_DIR`、源 / 目标目录与索引路径 | 本次项目与下载目录；快手另查 `JSONL_PATH` |
| `scripts/transcribe_with_whisper.py` | `BASE_DIR`、输入 / 输出目录、`MODEL_SIZE`、`language` | 本次素材路径、可用模型、视频实际语言；现有脚本默认 `large-v3` 和 `zh` |
| `scripts/wx_pipeline.py` 的命令参数 | 账号、`--project`、时间与阈值、模型 | 实际视频号与本次任务条件，参数以脚本帮助为准 |
| 对应平台的本地配置 | 账号 ID、下载开关、专用登录态、代理 | 本人有权使用的账号与实际可用配置；不上传 Cookie |

脚本中的示例路径不能直接复用。海外视频转写前要核对语言配置；改写语言与语气按已确认的任务要求执行。

## 🗺️ 完整流程

| # | 节点 | 工具 |
|---|---|---|
| 1 | 确认账号、指标、时间、语言 / 语气和登录态选项 | Agent + 用户任务信息 |
| 2 | 检查平台可达性、字段和小样本下载 | 对应平台参考与采集工具 |
| 3 | 建项目目录，列清单并筛选 | 采集工具 + `collect_videos_*.py` 等 |
| 4 | 下载源视频、提取音频，校验编号关联 | 平台工具 / yt-dlp + FFmpeg |
| 5 | 本地转写，保留 SRT 和文本 | faster-whisper |
| 6 | 生成逐字稿，补齐观点、关键点和行动建议 | `generate_md_timed.py` + AI |
| 7 | 重新组织标题与口播，单独保存改写稿 | AI + 可选的提取脚本 |
| 8 | 检查改写差异、占位内容和文件完整性 | `verify_rewrite_distinct.py` + Agent |

标准产物位于 `01-视频清单/`、`02-Whisper转写/`、`03-逐字稿MD/`、`04-原视频脚本改写/`；`00-操作手册/` 和 `99-生成脚本/` 保存任务说明与本次脚本。视频、转写和稿件使用一致编号。

完整 SOP 见 [SKILL.md](SKILL.md)；平台步骤见 [references/](references/)，视频号优先读 [专用流程](references/platform-wxchannels.md)。交付前执行 `python scripts/verify_rewrite_distinct.py <项目根>`，通过后再交付；差异检查不能代替事实核对和版权判断。

## ❓ 常见问题

- **装好 Skill 就能直接批量跑吗？** 还需要宿主工具、依赖、项目路径和目标平台登录。没有统一安装脚本，先让 Agent 做环境与小样本检查。
- **为什么没有抓到“全部视频”？** 接口、登录权限、限流和账号可见范围都会影响枚举；应报告实际取得的数量、失败项与缺失字段，不把未取到当成不存在。
- **筛选结果为 0 怎么办？** 核对字段是否返回、指标类型和时间范围；需要扩大范围时先确认新条件，不自行降低阈值。
- **海外视频转写成中文或模型下载失败？** 先检查 `language`、模型和本地缓存路径，再按实际网络配置获取模型；不同脚本默认模型并不相同。
- **改写稿还是和逐字稿一样？** 由 AI 重读原稿并重新组织表达，重新跑差异验收；规则脚本产生的骨架不能冒充完成稿。
- **它和自媒体素材库底座怎么选？** 单次账号研究、希望成果保存在本地，选本仓库。需要持续收链接、采资讯、按人设改写并写入飞书，选 [self-media-content-base](https://github.com/caodoris471/self-media-content-base)；后者已内置采集引擎，无需重复安装一套。

## ⭐ 支持项目

觉得有帮助，可以给 [本仓库](https://github.com/caodoris471/blogger-video-pipeline) 点 ⭐ Star。问题和建议请提交到 [Issues](https://github.com/caodoris471/blogger-video-pipeline/issues)，附上平台、执行步骤与脱敏日志。

## 🙏 致谢

[MediaCrawler](https://github.com/NanmiCoder/MediaCrawler) · [yt-dlp](https://github.com/yt-dlp/yt-dlp) · [faster-whisper](https://github.com/SYSTRAN/faster-whisper) · [FFmpeg](https://ffmpeg.org/) · [Playwright](https://playwright.dev/) · [wx_channels_download](https://github.com/ltaoo/wx_channels_download)

## 📄 许可

本仓库当前没有单独的 `LICENSE` 文件，不据此推定任意再分发或商业授权；如需复用，请先向作者确认授权范围。第三方工具各自遵循其许可证；视频、音频和转写涉及原作者权利，使用与再分发前需取得相应授权并遵守平台规则。
