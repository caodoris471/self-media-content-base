# Instagram 抓取流程（Playwright 登录 + yt-dlp 下载）

> **状态**：✅ 已跑通（2026-09-13 实战 @示例博主 20 Reels）  
> **关键依赖**：`Playwright + Edge 独立 profile`（登录态）→ `yt-dlp + cookies.txt`（下载 + caption）

---

## 路径速查（实战版）

| 阶段 | 工具 | 命令 / 操作 |
|---|---|---|
| 装依赖 | pip | `pip install playwright pysocks instaloader yt-dlp` |
| Playwright Chromium | shell | `playwright install chromium`（Edge 用系统自带） |
| **登录拿 IG session** | Playwright Edge | `99-生成脚本/ig_login_helper.py`（弹独立 profile，账号密码 + 2FA） |
| 导出 Netscape cookies | Python | `99-生成脚本/ig_cookies.json` → `99-生成脚本/ig_cookies.txt` |
| **批量下载 Reels** | yt-dlp | `99-生成脚本/ig_yt_dlp_scraper.py` |
| Whisper 转写 | faster-whisper | `99-生成脚本/transcribe_ig_with_whisper.py` |
| MD + 改写稿 | Python | `99-生成脚本/ig_generate_md.py` |

---

## 与其他海外平台的差异（实战版）

| 项 | Instagram | YouTube | TikTok |
|---|---|---|---|
| 必须代理 | ✅ socks5://127.0.0.1:10808 | ✅ | ✅ |
| 必须登录 cookie | ✅ **强制** | ✅ | ❌（impersonate 已够） |
| Cookie 失效时长 | 🟡 数天-数周 | 🟢 1-3 月 | 🟢 1-2 周 |
| 工具链首选 | **yt-dlp + cookies.txt** | yt-dlp | yt-dlp |
| 反爬强度 | 🔴 **最高** | 🟡 中 | 🟡 中 |
| 公开账号免登录 | ❌ 完全不行 | ❌ 极少 | ❌ 几乎不 |
| HTML 抓取能否拿到数据 | ❌（数据埋 React state） | ✅ | ✅ |
| API 端点是否限流 | 🔴 **429 严重**（10 分钟窗口） | 🟡 | 🟢 |

---

## 已验证结论（2026-09-13 @示例博主 实战）

### ✅ 已验证

| 项 | 结果 |
|---|---|
| Playwright Edge 独立 profile 登录 IG | ✅ sessionid/csrf/ds_user_id 全获取 |
| IG 2FA challenge (auth_platform/codeentry) | ✅ 自动检测 + 用户手动输入 |
| Playwright + socks5://127.0.0.1:10808 | ✅ Edge 走代理 `--proxy-server` 参数有效 |
| Playwright 抓主页 HTML | ✅ HTTP 200，但数据埋 React state（HTML 无 og:image/og:description） |
| Playwright 抓详情页 + og:meta | ✅ caption + likes + 缩略图都拿到 |
| instaloader API（web_profile_info/GraphQL）| ❌ HTTP 429，限流 10 分钟 |
| instaloader 走 Playwright cookies 注入 | ⚠️ 装包能注入但仍 429（IG 限 IP+session） |
| requests + IG cookies + Referer | ❌ CDN 403（裸 requests 被拒） |
| **yt-dlp + cookies.txt + socks5 代理** | ✅ **终极方案**，完整 mp4 + caption + likes |
| yt-dlp 最高画质 | 1080x1920 (mp4) + 128kbps (m4a) |
| Whisper 转写 (tiny/cpu/int8) | ✅ 17/20 成功（3 个 m4a 缺失因 yt-dlp postprocess 失败）|
| MD + 改写稿生成 | ✅ 17/17 完成 |

### ❌ 失败方案

| 方案 | 失败原因 |
|---|---|
| instaloader 匿名 + socks5 | IG API 触发 429 限流（10 分钟窗口） |
| instaloader + Playwright 注入 cookies | 仍然 429（IG 限 session）|
| requests 抓 og:image URL | IG CDN 403（需 Playwright 浏览器栈带 session） |
| Playwright `<video>` src | IG Reel 用 blob: URL（浏览器内编码），不是 http URL |
| Playwright 抓详情页 DOM 点赞数 | selector 不稳，og:description 解析反而更可靠 |

---

## 完整实战流水线（推荐顺序）

### Step 1：装依赖（一次性）

```bash
"C:/Users/<你的用户名>/.workbuddy/binaries/python/versions/3.13.12/python.exe" -m pip install playwright pysocks instaloader yt-dlp
# 首次启动 Playwright 自带的 Chromium（实际用 Edge 不用装）
# playwright install chromium   # 仅在 Edge 不通时备用
```

### Step 2：登录拿 cookies（每个账号一次）

```bash
cd "{工作目录}/<项目>/99-生成脚本"
python ig_login_helper.py
# 1. Edge 弹出独立 profile（项目 login_profile/）
# 2. 用户输入 IG 账号密码 + 2FA
# 3. 自动检测 sessionid 出现 → 导出 ig_cookies.json
```

### Step 3：转 Netscape cookies.txt（一次性）

```python
# 99-生成脚本 任意 .py 中加：
import json
data = json.loads(open('ig_cookies.json', encoding='utf-8').read())
out_lines = ['# Netscape HTTP Cookie File', '']
for c in data['all_cookies']:
    domain = c['domain']
    flag = 'TRUE' if domain.startswith('.') else 'FALSE'
    secure = 'TRUE' if c.get('secure', False) else 'FALSE'
    expires = int(c.get('expires', 0) or 0)
    if expires < 0: expires = 0
    out_lines.append(f'{domain}\t{flag}\t{c.get("path","/")}\t{secure}\t{expires}\t{c["name"]}\t{c["value"]}')
open('ig_cookies.txt', 'w', encoding='utf-8').write('\n'.join(out_lines))
```

### Step 4：抓主页列表（可选）

如果需要列表（点赞数过滤等），用 Playwright 抓主页：

```python
# 99-生成脚本/ig_browser_scraper.py 已实现
# 1. 启动 Playwright Edge（独立 profile）
# 2. 访问 profile 页 → 滚动 → DOM 提取 a[href*='/p/'] / a[href*='/reel/']
# 3. 逐个详情页 → 解析 og:description（"X likes, Y comments"）和 og:image
# 4. 不下载（让 yt-dlp 来）
```

### Step 5：批量下载（yt-dlp）

```python
# 99-生成脚本/ig_yt_dlp_scraper.py 已实现
import subprocess
for item in selected:
    cmd = [
        "yt-dlp",
        "--proxy", "socks5://127.0.0.1:10808",
        "--cookies", "ig_cookies.txt",
        "--no-warnings", "--no-playlist", "--no-part",
        "-f", "dash-2236899033823391v+dash-2236750723838222a/best",  # 1080p DASH + audio
        "--write-info-json",   # 写 video.info.json sidecar
        "--write-description", # 单独写 video.description
        "-o", str(mp4_abs_path),
        item["url"],
    ]
    subprocess.run(cmd, cwd=str(folder), timeout=120)
```

### Step 6：Whisper 转写

```bash
cd "{工作目录}/<项目>/99-生成脚本"
"C:/Users/<你的用户名>/.workbuddy/binaries/python/envs/whisper/Scripts/python.exe" transcribe_ig_with_whisper.py
```

### Step 7：MD + 改写稿

```bash
python ig_generate_md.py
```

---

## 🔴 Step 7.5：内容类型分流（2026-09-14 新增 · 必做）

**Instagram ≠ 纯视频平台。转写前先分 Reels 类型，图文帖单独走 carousel 流水线。**

### A. Reels 分类（口播型 vs 视觉驱动型）

**判定方法**：Whisper 转写词密度 = 总词数 ÷ 视频秒数

| 词密度 | 分类 | 处理 |
|---|---|---|
| ≥ 2.0 词/秒 | 🎤 口播型 | 正常逐字稿 MD + 口播改写稿 |
| 1.0 - 2.0 | 看文本 | 歌词=BGM-only（归视觉）；教学讲解=口播型 |
| < 1.0 或空 | 👁️ 视觉驱动型 | **不硬做逐字稿** |

**视觉驱动型细分**：
- **无声发布**：yt-dlp `--dump-json` 查所有格式 `acodec=none` → IG 原生无声（MD 标注「无口播，转写为空是正常现象」）
- **BGM-only**：Whisper 抓到的是背景音乐歌词 → MD 中标注为 BGM 参考，不作口播

**视觉驱动型 Reels 处理（`ig_visual_rebuild.py`）**：
1. ffmpeg 场景检测（`select='gt(scene,0.25)'`）→ 真实切镜时间轴 + 平均镜头时长 + 节奏判定（快<1.5s/中1.5-3s/慢>3s）
2. ffmpeg 关键帧拼图（`fps=1/N,tile=6x4`）→ `00N-*/关键帧拼图.jpg` 供人工查看
3. caption + hashtag 词库匹配 → 产品清单（35 品牌 + 25 品类词库）
4. 生成 MD 结构：⚠️ 无口播声明 → TL;DR → Caption → 视觉拆解 → 节奏分析（真实数据表）→ 产品清单 → 二创建议
5. 改写稿 = 视觉复刻框架（镜头映射表 + BGM 建议 + 产品植入位 + 字幕 CTA），**非口播脚本**

### B. 图文帖 Carousel（`ig_carousel_scraper.py`）

IG 是图文+视频混合平台，profile grid 上 `/p/` = 图文（含 carousel 多图）、`/reel/` = 视频：

1. Playwright 打开 profile → 滚动全 grid → 收集 `a[href*='/p/']`（区别于 `/reel/`）
2. 逐个打开 `/p/` 详情页 → 点右箭头翻 carousel → 收集全部 `<img>` src（原图 CDN URL）
3. requests + SOCKS5 代理 + Referer 头下载 `image1.jpg ... imageN.jpg`
4. 产出：`05-图文Posts/00N-标题/` + metadata.json + 图文笔记 MD

**注意**：`@示例博主` 实测 33 条全 Reels、0 图文——**先扫 grid 确认有没有 /p/ 帖再决定是否跑 carousel 流水线**（脚本已建好备用）。

### C. 下载后必验音轨

```python
# yt-dlp 下载后 ffprobe 验证（2026-09-14 教训：003/009/011 首次下载为纯视频流，3 条漏转写）
ffprobe -v error -show_streams -of json video.mp4
# 检查 streams 里有没有 codec_type=audio，无音轨 → 先 --dump-json 查格式列表
# 全部 acodec=none → 该 Reel 原生无声，归视觉驱动型
```

---

## 关键卡点与解决方案（实战版）

### 卡点 1：必须登录 + 2FA

**症状**：Playwright Edge 打开 IG login 页 → 输入账号密码 → IG 跳到 `auth_platform/challengepicker/` 或 `auth_platform/codeentry/` → 需要 2FA 验证码。

**解决**：
1. `ig_login_helper.py` 已实现：自动检测 `auth_platform/codeentry` URL，等 sessionid 出现才算成功
2. 用户在 Edge 窗口中：
   - 输入账号密码
   - IG 弹 2FA 选择页（短信 / 邮件 / 认证器）→ 选一个
   - 输入 6 位验证码
   - 跳到 IG 首页 → sessionid 出现
3. 整个流程最长 10 分钟（脚本 timeout 600s）

**经验**：IG 经常在「异地登录」时强制 2FA，所以**新 profile 第一次登录必须走完整 2FA**。后续 session 复用即可（session 有效期通常数天-数周）。

### 卡点 2：Cookie 文件格式转换

**症状**：Playwright 导出的是 JSON，需要给 yt-dlp 用 Netscape cookies.txt。

**解决**：Step 3 Python 脚本已实现，关键字段：
- `sessionid`：登录凭证
- `csrftoken`：CSRF token
- `ds_user_id`：用户 ID
- `mid`：设备 ID
- `ig_did`：IG 设备 ID

### 卡点 3：Playwright Edge socks5 代理

**症状**：Edge 默认不走 socks5 代理（环境变量 HTTP_PROXY 不生效）。

**解决**：用 Playwright launch 时的 args 传：
```python
args=["--proxy-server=http://127.0.0.1:10808"]  # Edge 也吃 socks5 + http 协议
```

**注意**：`--proxy-server=socks5://127.0.0.1:10808` 也能工作，但建议用 http:// 前缀（Edge 实现更稳）。

### 卡点 4：socket.socket monkey-patch 破坏 asyncio

**症状**：用 `socks.set_default_proxy() + socket.socket = socks.socksocket` 全局 patch 后，Playwright 的 asyncio 报 `ConnectionError: Unexpected peer connection`（socket.socketpair() 被破坏）。

**解决**：
1. **不要全局 patch socket.socket**
2. 用 requests 的 `proxies={'http': 'socks5://...', 'https': 'socks5://...'}` 参数
3. 或者 urllib3 自带 SOCKS 支持（装 PySocks）

### 卡点 5：IG CDN 403（裸 requests）

**症状**：requests 直接 GET `https://scontent-lax3-1.cdninstagram.com/...jpg` → 403。

**原因**：IG CDN 用 cookie + 签名验证请求来源，裸 requests 没浏览器指纹。

**解决**：
1. 用 Playwright 浏览器栈下载（page.goto(url) + response.body()）
2. 或者 **yt-dlp 自带签名处理**，所以 yt-dlp 下载 OG image 直接 OK

### 卡点 6：Whisper m4a 缺失

**症状**：yt-dlp 下载后 `audio.m4a` 缺失（但 `video.mp4` 完整）。

**原因**：yt-dlp 抽音频时 ffprobe 报 `unable to obtain file audio codec`，postprocess 失败。

**解决**：
1. **优先级 1**：用 `ffmpeg -i video.mp4 -vn -acodec copy -map 0:a audio.m4a` 从 mp4 抽音轨（不重新编码，最快）
2. **优先级 2**：yt-dlp 单独再跑 `-x --audio-format m4a`（可能还是失败）
3. **优先级 3**：Whisper 直接转 mp4（faster-whisper 支持任意音视频格式）

### 卡点 7：Windows NTFS 不支持部分 unicode（emoji）路径

**症状**：含 emoji 的目录名（`001-DcwA_auxL_J-Everyone's_talking_about...🤎...`）→ 创建目录失败或文件写入失败。

**解决**：sanitize 函数过滤：
```python
import re
def sanitize(name):
    name = re.sub(r'[\\/:*?"<>|\n\r]', '_', name)  # Windows 保留字符
    name = re.sub(r'[\U00010000-\U0010FFFF]', '_', name)  # emoji 范围
    name = re.sub(r'\s+', '_', name)  # 空格
    return name.strip('_')[:50]
```

### 卡点 8：m4a 抽 audio 失败导致 Whisper 漏转

**症状**：Whisper 转写时跳过了 m4a 不存在的目录（17/20 完成而非 20/20）。

**解决**：`transcribe_ig_with_whisper.py` 用 `audio.m4a` glob，没有就跳过。后续可改为 fallback 到 `video.mp4`。

---

## 改写脚本语言规则（IG → 国内平台）

| 原 Reel 语言 | 改写目标平台 | 改写语言 |
|---|---|---|
| 英文 (default) | 抖音 / 视频号 / 小红书 | **中文** |
| 英文 (default) | TikTok 海外 / YouTube Shorts | **英文**（保留原声） |
| 中文/日文/韩文 | 同语种平台 | **原文**（只改结构） |

**特殊**：
- 纯视觉驱动 Reels（化妆前后对比 / 视觉特效）→ 拆解视觉规律而非口播脚本
- 含 BGM 热门音乐 → 标注音乐名（避免版权问题）
- 含产品链接 → 替换为国内平台同款（淘宝/小红书店铺）

---

## 实战脚本清单（99-生成脚本/）

| 脚本 | 作用 |
|---|---|
| `ig_login_helper.py` | Playwright Edge 独立 profile 登录 IG，导出 cookies.json |
| `ig_browser_scraper.py` | Playwright 抓主页 + 详情页 og:meta（生成 selected_posts.json） |
| `ig_cookies_to_netscape.py` | cookies.json → Netscape cookies.txt（yt-dlp 格式） |
| `ig_yt_dlp_scraper.py` | yt-dlp 批量下载 mp4 + m4a + info.json sidecar |
| `ig_post_process.py` | caption 修正 + 目录重命名 + 删除冗余文件 |
| `transcribe_ig_with_whisper.py` | faster-whisper tiny/cpu/int8 转写所有 audio.m4a |
| `ig_generate_md.py` | 生成 03-逐字稿MD/ + 04-改写脚本/（IG 视觉驱动 vs 口播双模板） |

---

## 已跑通案例

### @示例博主（波士顿 MUA，20 Reels，2026-09-13）

| 维度 | 数据 |
|---|---|
| 账号粉丝 | 17.2K（公开账号，商业号） |
| Posts 总数 | 145+ |
| 近 30 天 Reels | 20 条命中 |
| 点赞区间 | 41 - 937（IG 常态，非抖音级别） |
| 下载成功率 | 20/20 mp4 ✅ + 17/20 m4a（3 个 yt-dlp postprocess 失败） |
| Whisper 成功率 | 17/17 ✅ |
| MD + 改写稿 | 17/17 ✅ |
| 类型分布 | 11 视觉驱动 + 6 口播+视觉 |
| 主题 | 美妆教程（Hailey/Kylie 化妆技巧 + 婚礼妆容） |
| Hashtag | #makeupartist #concealer #haileybieber #kyliejenner 等 |

---

## 已知限制

1. **下载 20 条/批**（避免 IG 反爬触发限流），更多分批跑 + 中间 sleep 60-120s
2. **Cookie 数天-数周失效**（IG 风控），失效后重新跑 ig_login_helper.py
3. **Whisper tiny 英文准确度 80-90%**（推荐 medium/large for production）
4. **yt-dlp DASH format 不固定**（IG 经常改 format_id），用 `best` fallback
5. **CDN 签名 URL 几小时失效**（不要缓存 → 必须现下）

---

## 常见错误排查

| 错误 | 原因 | 解决 |
|---|---|---|
| `chromium-error://chromewebdata/` | 网络层不通（DNS / 代理 / 防火墙） | 测 `--proxy-server=http://127.0.0.1:10808` 是否生效 |
| `Page.goto: net::ERR_HTTP_RESPONSE_CODE_FAILURE` | IG 风控拒绝（headless 标识） | 加 `--disable-blink-features=AutomationControlled` + `--ignore-default-args=["--enable-automation"]` |
| `JSON Query to api/v1/users/web_profile_info/: 429` | IG API 限流 | 改用 yt-dlp + cookies.txt（绕过 API） |
| `ConnectionError: Unexpected peer connection` | socket.socketpair 被 monkey-patch 破坏 | 去掉 `socket.socket = socks.socksocket`，改用 `proxies` 参数 |
| `ModuleNotFoundError: No module named 'socks'` | PySocks 没装 | `pip install pysocks` |
| yt-dlp `ERROR: Postprocessing: WARNING: unable to obtain file audio codec` | m4a 抽音失败 | 用 ffmpeg 从 mp4 抽 m4a 兜底 |
| Windows emoji 路径失败 | NTFS 不支持 | sanitize 函数过滤 emoji（详见卡点 7） |

---

## 后续待办

- [ ] **Stories 支持**（24h 限时 + Highlights）：需 instaloader `--stories` + `--highlights` 参数
- [ ] **Carousel 图集下载**（多图 Post）：yt-dlp 已支持，需测试
- [ ] **批量账号 + 账号池**：避免单账号被风控
- [ ] **图片 Post vs 视频 Post 自动识别**：当前默认 Reels（视频），需适配图片 Post
- [ ] **Whisper large-v3 for IG 英文**（tiny 准确度不够）
- [ ] **Instagram 限流智能退避**：429 自动等待 + 重试

---

**最后更新**：2026-09-13 实战 @示例博主 20 Reels 跑通