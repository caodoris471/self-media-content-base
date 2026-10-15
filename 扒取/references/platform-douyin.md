# 抖音（douyin.com）扒取指南

> ⚠️ **首次实战教程**：本文档基于 2026-09-13 「示例博主」首次跑通的实战经验整理。

## 路径速查

| 项 | 值 |
|---|---|
| 工具 | **MediaCrawler**（`NanmiCoder/MediaCrawler`，GitHub） |
| 安装路径 | `{工作目录}/tools/MediaCrawler/` |
| 输出路径 | `{工作目录}/tools/MediaCrawler/data/douyin/{jsonl,videos}/` |
| 登录态 | `browser_data/dy_user_data_dir/`（持久化） |
| 转写 | `faster-whisper tiny/cpu/int8 + HF_HUB_OFFLINE=1` |
| 改写脚本语言 | **中文**（国内平台） |
| 改写风格 | **财经/口播** 干货+金句 |

## 与其他海外平台差异

| 维度 | 抖音 | TikTok | 小红书 | YouTube |
|---|---|---|---|---|
| **工具** | MediaCrawler | yt-dlp | MediaCrawler | yt-dlp |
| **登录强制** | ✅ 必须扫码（首次） | ❌ 代理+impersonate | ✅ 必须扫码（首次） | ⚠️ 可选 cookie |
| **CDN 403 率** | ⚠️ 约 50% | 低 | 低 | 极低 |
| **视频源** | MP4（CDN 403 多） | MP4（download 格式） | MP4/M3U8 | MP4/WebM |
| **元数据完整度** | ✅ 全 | ✅ 全 | ✅ 全 | ✅ 全 |
| **改写语言** | 中文 | 英文 | 中文 | 英文 |

## 关键技术栈

### 1. MediaCrawler 配置（5 处必改）

**`config/base_config.py`**：
```python
PLATFORM = "dy"
CRAWLER_TYPE = "creator"          # ⚠️ 默认 "search" 必须改！
LOGIN_TYPE = "qrcode"
ENABLE_CDP_MODE = False            # ⚠️ 默认 True 必须改（铁律 1：禁止连真实 Chrome）
ENABLE_GET_MEIDAS = True           # 开启视频下载
CRAWLER_MAX_NOTES_COUNT = 500      # 博主全量
```

**`config/dy_config.py`**：
```python
DY_CREATOR_ID_LIST = [
    "MS4wLjABAAAA...",  # 博主 sec_uid（不是 URL）
]
```

### 2. login.py Patch（必须）

抖音 2025 年改版后登录面板 ID 是 `login-full-panel-xxxx`（随机后缀），MediaCrawler 旧版还在等 `login-panel-new`，会一直超时。**用 `contains()` 模糊匹配**：

```python
# 改前
dialog_selector = "xpath=//div[@id='login-panel-new']"
# 改后
dialog_selector = "xpath=//div[contains(@id, 'login-full-panel')]"
```

### 3. 启动 + 扫码流程

```bash
cd {工作目录}/tools/MediaCrawler
C:/Users/<你的用户名>/AppData/Local/Programs/Python/Python312/python.exe main.py
```

PC 端会弹出抖音登录窗口 + 二维码。用户**拿手机抖音 App 扫一下**（10s 动作），cookie 自动持久化。

✅ **下次跑无需重新扫码**，直接复用 `dy_user_data_dir/`。

## 已知卡点（11 项验证清单）

| # | 卡点 | 症状 | 解决方案 |
|---|---|---|---|
| 1 | CRAWLER_TYPE 默认 "search" | 日志显示「Begin search douyin keywords」抓错数据 | 改成 `"creator"` |
| 2 | ENABLE_CDP_MODE 默认 True | 会尝试连真实 Chrome（破坏 Doris profile） | 改成 `False` |
| 3 | 抖音新版登录面板 ID 带随机后缀 | login.py 超时等不到面板 | 用 `contains(@id, 'login-full-panel')` |
| 4 | 视频 CDN 403 | `v26-web.douyinvod.com` 拒绝 MediaCrawler 下载 | 重试或用 yt-dlp 兜底 |
| 5 | 抖音 web 端风控严 | 直连 curl 返回 0 字节 | 必须用 Playwright + 登录态 |
| 6 | sec_uid 转 UID 复杂 | MediaCrawler 直接用 sec_uid，无需转换 | 填 `DY_CREATOR_ID_LIST` 用 sec_uid |
| 7 | 视频时长 ≠ 视频文件大小 | 4 分钟视频约 24MB（高码率） | 不影响转写，m4a 4MB 已够 |
| 8 | 数据分散在 `jsonl` 和 `videos/` | 需自行 merge 逻辑 | `99-生成脚本/generate_md_and_rewrites.py` 自动 merge |
| 9 | 视频下载失败但元数据完整 | 命中视频无 mp4 文件 | 用 yt-dlp 重试或项目目录空缺 |
| 10 | 抖音 web 端 CSRF token 严格 | 切勿高频请求 | MediaCrawler 默认带 sleep，无需额外处理 |
| 11 | 抖音「示例博主」等财经口播 | 4-5 分钟长视频，转写慢 | Whisper tiny 已实测 31s/4min ✅ |

## 改写脚本适配（v2.4 铁律）

抖音是**国内平台**，改写脚本**必须是中文**（铁律 2）。

**改写 ≠ 复制逐字稿**（铁律 3）：
- ✅ 新 Hook（不是「央行数据 1700 万亿」开场）
- ✅ 新结构（5 段式 vs 原视频线性论证）
- ✅ 新 CTA（评论区互动 vs 原视频订阅引导）

**改写风格推荐**：
- **财经类**：干货+金句（数据 + 反转 + 共鸣）
- **情感类**：故事+金句（叙事弧线 + 情绪高潮）
- **带货类**：痛点 + 卖点 + 信任背书
- **段子类**：反转 + 包袱 + 互动

## 5 大硬铁律同步

| # | 铁律 | 抖音适配 |
|---|---|---|
| 1 | 🔴 浏览器 Profile 保护 | 抖音 web 必须用 Playwright 自带 Chromium + `dy_user_data_dir/` 项目内独立目录（**绝对禁止** ENABLE_CDP_MODE=True） |
| 2 | 🔴 改写脚本语言匹配原视频 | 抖音（国内）→ **中文** |
| 3 | 🔴 改写脚本质量 | 必须新 Hook / 新结构 / 新 CTA |
| 4 | 🔴 完整视频双落 mp4 + m4a | MediaCrawler 自带 mp4 → `ffmpeg -vn -acodec copy -map 0:a` 抽 m4a |
| 5 | 🔴 落盘用绝对路径 | subprocess ffmpeg 必须 `str(Path)` 绝对路径，避免 Git Bash 中文路径编码问题 |

## 实战预备

### 首次跑抖音（强烈建议）

1. **用 MediaCrawler 已跑通的 1 个博主**（如「示例博主」）做 5 条视频小规模实验
2. 验证：扫码 → 元数据全 → 视频下载 → Whisper 转写 → MD → 改写稿 全链路通畅
3. 验证：登录态持久化（第二次跑无需扫码）

### 后续扩展

- **同博主跑更多视频**：直接改 `CRAWLER_MAX_NOTES_COUNT` 即可
- **换博主**：改 `DY_CREATOR_ID_LIST` + 重新扫码（除非 cookie 仍在有效期内）
- **跑新博主**：用 `{工作目录}/{博主名}_抖音视频扒取/` 标准项目结构

## 跨项目经验沉淀

- 抖音爬虫是「最严风控」平台，建议首次跑前先评估 ROI（投入 10-15 分钟 vs 产出 5-50 条视频）
- 适合「精准号」（< 500 条视频、内容垂直）而非「大号」（> 1000 条）
- 视频下载 403 率高，但元数据完整度高（元数据可二次利用下载其他平台版本）