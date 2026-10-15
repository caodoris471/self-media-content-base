# 平台可行性矩阵（博主视频扒取）

各平台扒取可达性实测/经验结论。执行第 1 步可行性评估时按此表选路径。

> **六平台已跑通**（2026-09-13 实测）：B站 ✅ / 微信视频号 ✅ / 小红书 ✅ / 快手 ✅ / YouTube ✅ / **TikTok ✅**
> **二平台待实测**：Instagram（⚠️ instaloader / yt-dlp + 登录态）/ 抖音（⚠️ 风控严 + 第三方平台分流）

## 主表（按可达性 + 实测状态排序）

| 平台 | 数据可达性 | 视频列表 | 点赞/播放数据 | 视频下载 | 推荐路径 | 实测状态 |
|---|---|---|---|---|---|---|
| **B站** | 🟡 半封闭 | ⚠️ `arc/search` API 持续 -799 风控（WBI 签名机制 2024 年起）；✅ 用 `search.bilibili.com/all` web 页面（不限速）+ 单视频接口交叉验证 | ✅ 单视频接口返回完整字段（播放/点赞/收藏/分享/评论 + 发布日期） | ✅ yt-dlp 30080+30216 低画质绕登录 | **详见 `references/platform-bilibili.md`**：web search + 单视频接口 + yt-dlp 组合方案 | ✅ 3 条「示例博主」2026-09-11 |
| **小红书** | 🟡 半封闭 → ✅ MediaCrawler | ✅ 创作者主页 API 翻页 | ✅ 点赞/收藏/评论全可见 | ⚠️ 需 patch 视频 URL 字段（新版 API：`video.media.stream.h264[0].master_url`） | **MediaCrawler**（详见 `references/platform-xhs.md`）：Playwright 持久化登录态 + 脚本批量翻页，**分批抓取 ≤30 条/批** | ✅ 29 条「示例博主」2026-09-11 |
| **微信视频号** | 🔴 强封闭 | ❌ 无公开 API，无公开 Web 端 | ❌ 未登录连主页都看不到 | ⚠️ 需 PC 微信 + `wx_channels_download`（github.com/ltaoo/wx_channels_download）拦截下载 | 半自动：用户 PC 端下载视频 + 肉眼登记点赞数；AI 端做转写和 MD | ✅ 35 条「品牌出海姐Rose」2026-09-07 |
| **快手** | 🟡 半封闭 → ✅ MediaCrawler（patch） | ✅ 创作者主页 + 个人作品列表 API | ✅ 点赞/播放/评论全可见 | ⚠️ 需 patch `kuaishou/login.py` 登录 xpath；视频 URL 走 `photoUrl` | **MediaCrawler**（详见 `references/platform-ks.md`）：与小红书共用 MediaCrawler，仅登录 xpath 不同；**分批抓取 ≤30 条/批** | ✅ 17 条「示例博主」2026-09-11 |
| **YouTube** | 🟡 半封闭（代理 + cookie + yt-dlp-ejs） | ✅ yt-dlp `--flat-playlist` 可拿频道列表 | ✅ 登录后 view_count/like_count 完整 | ✅ yt-dlp `-f "best[ext=mp4]"` mp4 + `-x --audio-format m4a` 同名抽音频（🔴 必须双落 mp4 + m4a） | **yt-dlp + 本地代理 + 登录 cookie + yt-dlp-ejs**；详见 `references/platform-youtube.md` | ✅ 2 条「@示例博主」2026-09-12 |
| **TikTok** | 🟡 半封闭 → ✅ impersonate + 代理 | ✅ yt-dlp `--flat-playlist` 可拿主页列表 | ✅ view_count 完整 | ✅ yt-dlp `--impersonate Chrome-136` + `-f "download/h264_720p/download"`（**必须 mp4 + m4a 双落**，单音频不够剪辑） | **yt-dlp + 本地代理 + Chrome-136 impersonate + curl_cffi + `-o` 绝对路径**；详见 `references/platform-tiktok.md` | ✅ 9 条「@示例博主」2026-09-13 |
| **Instagram** | 🟡 半封闭 | ✅ `instaloader --login <user>` 可抓主页全量 Reels/帖子 + Stories + 帖子图片；⚠️ Cookie 24h 失效，需重新登录；✅ yt-dlp `--username :--password` 备选 | ✅ 登录后点赞数/评论数可见（`likes`/`comments` JSON 字段） | ✅ instaloader `--fast-update` 或 yt-dlp | **两条路**：① instaloader（Reels 视频 + 帖子图片都能下） ② yt-dlp（仅 Reels 视频但更稳）。首次必须 `--login` 扫一次码，后续复用 session 文件；详见 `references/platform-instagram.md` | ⚠️ 待实测 |
| **抖音** | 🟡 半封闭 → ✅ MediaCrawler | ✅ MediaCrawler `creator` 模式可拿博主全量视频（sec_uid 即可） | ✅ 登录后点赞数完整，播放数部分缺失 | ⚠️ MP4 下载 ~50% 成功（CDN 403）但元数据完整 | **MediaCrawler + Playwright + PC 端扫码登录 + login.py patch**；详见 `references/platform-douyin.md` | ✅ 1 条「示例博主」2026-09-13 |

## B站专项卡点（2026-09-11 实测 ✅）

| 验证项 | 结果 |
|---|---|
| `api.bilibili.com/x/space/acc/info?mid=<UID>` | ✅ 正常 |
| `api.bilibili.com/x/space/arc/search`（列表 API） | ❌ 持续 -799 风控 / HTTP 412，2024 年起加 WBI 签名 |
| `api.bilibili.com/x/web-interface/view?bvid=BVxxx`（单视频） | ✅ 正常 |
| `search.bilibili.com/all?keyword=...&order=click`（web 页面） | ✅ 不限速，HTML 内含 BV 号 + 播放量 |
| `yt-dlp` 列表页 | ❌ 412 风控 |
| `yt-dlp` 单视频 30080+30216 低画质 | ✅ 稳定 |
| `yt-dlp` 单视频 1080P+ 高码率 | ❌ 403 要求登录大会员 |
| `yt-dlp` 503 新视频 CDN 没分配好 | ⚠️ 等 30s + 清理残留后重试 |

## 小红书专项卡点（2026-09-11 实测 ✅）

| 验证项 | 结果 |
|---|---|
| `MediaCrawler` GitHub clone | ✅ https://github.com/NanmiCoder/MediaCrawler 50k+ stars |
| 创作者主页 API 翻页 | ✅ 默认配置即可，支持 `--type creator --creator_id <user_id>` |
| Playwright 扫码登录 | ✅ 必须 App 上点「登录」确认（否则 120s 超时） |
| Playwright context 持久化 | ✅ 第二次跑直接复用（不重扫） |
| `ENABLE_GET_MEIDAS=True` 下载视频 | ⚠️ 默认 `False`，需改 `base_config.py` |
| 视频 URL 解析（`consumer.origin_video_key`） | ❌ 老代码找不到，**新结构在 `video.media.stream.h264[0].master_url`** |
| `aiohttp` 依赖 | ⚠️ 有时没装，用 `urllib` 兜底即可 |
| `execjs` 抖音 help 编译失败（即使只跑 xhs） | ⚠️ try/except 跳过即可 |

## 微信视频号专项卡点（2026-09-07 实测 ✅）

| 验证项 | 结果 |
|---|---|
| `https://weixin.qq.com/sph/<视频号ID>` 直接抓取 | ❌ 返回"此内容暂时无法播放" |
| 视频号官方 API `getfinderattrbyappid` | ❌ 需 access_token（仅视频号主本人或授权第三方可拿） |
| 搜索引擎索引视频号内容 | ❌ 仅公众号文章/播客转载，无视频号视频与点赞数 |
| 视频号 PC Web 端 | ❌ 不存在，只能在微信客户端内查看 |
| `wx_channels_download.exe` 工具 | ✅ GitHub 开源，需要管理员运行装证书 |
| 证书卸载 `wx_video_download.exe uninstall` | ✅ exit=0 视为成功 |

## 快手专项卡点（2026-09-11 实测 ✅）

| 验证项 | 结果 |
|---|---|
| `https://www.kuaishou.com/profile/<id>` 直接 curl | ⚠️ HTML 含 SPA 脚手架但不渲染视频数据，需 JS 执行 |
| `www.kuaishou.com/?isHome=1` 主页 | ⚠️ 不显示登录按钮（顶栏动态加载） |
| `m.kuaishou.com/profile/<id>` 移动端 | ⚠️ 直接返回"找不到该页面"（UA 不匹配） |
| 无 cookie GraphQL `visionProfilePhotoList` | ⚠️ 返回 `result:2` = 需要登录 |
| MediaCrawler `kuaishou/login.py` xpath `//p[text()='登录']` | ❌ 已失效（实际是 `<span class="sidebar-login-button">`） |
| MediaCrawler 主页直接抓 | ⚠️ 找不到登录按钮（主页 `/?isHome=1` SPA 时序问题） |
| MediaCrawler `goto("https://www.kuaishou.com/profile/<id>")` | ✅ 顶栏显示登录按钮 |
| MediaCrawler Playwright 持久化登录态 | ✅ 第二次跑直接复用（cookie 不重扫）|
| MediaCrawler `ENABLE_GET_MEIDAS=True` 下载视频 | ⚠️ 默认 `False`，需改 `base_config.py`（同上小红书） |
| Whisper 倾向识别繁体 | ⚠️ 需 `pip install zhconv`，generate_md.py 转简体 |
| 分批抓取 | ⚠️ 同小红书，**≤30 条/批**，超过分 2 批（间隔 60-90s） |
| 视频本体跳过下载（变成 0 字节） | ⚠️ 视频下载需打开 `ENABLE_GET_MEIDAS=True`（同上小红书坑） |

## YouTube 专项卡点（2026-09-12 实测 ✅）

| 验证项 | 结果 |
|---|---|
| 直连 `youtube.com` | ❌ TCP timeout / reset（IP 段被屏蔽） |
| 经本地 socks5 代理 `127.0.0.1:10808` 访问 | ✅ 可达 |
| `yt-dlp --flat-playlist @示例博主/shorts` | ✅ 可拿 id + title |
| `yt-dlp` 单视频元数据（无 cookie） | ❌ `Sign in to confirm you’re not a bot` |
| `yt-dlp --cookies-from-browser chrome`（Chrome 运行中） | ❌ `Could not copy Chrome cookie database` |
| 专用 Playwright 窗口登录 YouTube → 导出 `cookies.txt` | ✅ 导出 43 个 YouTube/Google cookie |
| `yt-dlp --cookies youtube_cookies.txt` 单视频元数据 | ✅ 需额外安装 `yt-dlp-ejs` + Node 24 权限参数 |
| `yt-dlp -f bestaudio` 下载 | ✅ 2 条 Shorts 音频下载成功 |
| Whisper tiny/cpu/int8 英文转写 | ✅ 完成 |
| 6 模块 MD + 改写脚本生成 | ✅ 完成 |

## TikTok 专项卡点（2026-09-13 实测 ✅）

| 验证项 | 结果 |
|---|---|
| 直连 `tiktok.com/@<user>` | ❌ TCP timeout |
| 经本地 socks5 代理 `127.0.0.1:10808` | ✅ 可达 |
| `yt-dlp --flat-playlist @示例博主` | ✅ 拿 27 条 id/title/view_count/timestamp |
| `yt-dlp` 单视频元数据（无 impersonate） | ❌ `Unexpected response from webpage request` |
| `pip install curl_cffi` 默认装到 Python 3.13（yt-dlp 不用） | ❌ `--list-impersonate-targets` 全 unavailable |
| `pip install curl_cffi` 装到 Python 3.12 | ✅ Chrome-136/Edge-101/Firefox-133 等 12 个目标可用 |
| `yt-dlp --impersonate Chrome-136` 单视频下载 | ✅ 完整下载音频 |
| Whisper tiny/cpu/int8 转写 | ✅ 完成 9/9 |
| 多语种检测（en/pt/it） | ✅ Whisper 自动识别 |
| 6 模块 MD + 改写脚本生成 | ✅ 完成（特殊：猫猫类视觉驱动而非口播驱动） |

## Instagram 专项卡点（2026-09-13 预备 · ⚠️ 待实测）

**核心难点**：Instagram 反爬强度高于 YouTube，cookie 时效短（24h 失效），必须依赖登录态。

| 验证项 | 预估结果 | 备注 |
|---|---|---|
| 直连 `instagram.com/<user>` | ❌ 严格风控 / TCP reset 大概率 | 类 YouTube 情况，需本地代理 |
| 经本地 socks5 代理 `127.0.0.1:10808` 访问 | ✅ 可达（同 YouTube / TikTok 节点） | 复用 v2rayN 同节点 |
| `instaloader --login` 首次扫码 | ⚠️ App 二维码扫描 + 输入验证码 | 流程类似小红书 MediaCrawler |
| `instaloader` 持久化 session 文件 | ✅ 24h 内复用免重扫 | 文件路径 `~/.config/instaloader/session-<username>` |
| `instaloader <user>` 主页全量 Reels 列表 | ✅ 含发布日期 + 点赞数 + 评论数 + 播放数 | 帖子图片也会一并下（必要时过滤） |
| `yt-dlp https://www.instagram.com/reel/<id>/` | ✅ 单 Reel 下载（登录态 cookie 文件） | 对 profiles 全量自动生成 video meta |
| Cookie 过期处理 | ⚠️ 24h 后重跑会要重新扫码 | 必须保存 session 文件 + 监控失效 |
| 公开账号 Reels 直连下载 | ⚠️ 部分账号允许匿名拉取 | 多数热门博主需要登录 |
| 海外 IP 必查 | ❌ 大陆直连 95% 概率会弹登录墙 | 走代理才行 |
| Whisper 转写 | ✅ 同其他平台 | 多数 Reels 是英文 / 偶尔博主母语 |

**🔴 与海外平台相同铁律**：
1. 浏览器 Profile 必须独立建在项目目录 `login_profile/`，禁止 `--user-data-dir` 指向真实 Chrome
2. 改写脚本默认英文（绝大多数 Instagram Reels 是英文）
3. 视频 + 音频双落（`instaloader --` 下视频 + 单独 `-x` 抽音频；或 yt-dlp 双调用）
4. subprocess 路径必须用绝对路径

**两条工具链对比**：

| 项 | instaloader | yt-dlp |
|---|---|---|
| 依赖安装 | `pip install instaloader` | yt-dlp 已自带 |
| 抓主页列表 | ✅ `--profile <user>` | ✅ `yt-dlp --flat-playlist https://www.instagram.com/<user>/` |
| 抓 posts + comments | ✅ 带评论和 metadata 完整 | ⚠️ 仅基本信息 |
| 抓 stories | ✅ `--stories` 参数 | ❌ 不支持 |
| 下载 Reels 视频 | ✅ 直接 `.mp4` 文件 | ✅ 同 |
| 下载帖子图片 | ✅ | ❌ |
| Cookie 失效报错 | 显式 `Login required` | 同 |
| 推荐场景 | 学术研究 / 完整数据 | 仅需要视频时 |

## 第三方数据平台备选（付费）

| 平台 | 覆盖 | 成本 | 说明 |
|---|---|---|---|
| 新榜/新视 | 视频号 | 年费几百-几千 | 结构化数据（点赞/播放），但小博主可能未收录 |
| 新抖/蝉妈妈 | 抖音 | 同上 | 同上 |
| 飞瓜数据 | 抖音/快手/小红书 | 同上 | 同上 |
| 灰豚数据/飞瓜快手 | 视频号+快手 | 同上 | 同上 |

拿到的是数据表，视频源文件仍需另行下载。

## 决策规则

1. 平台 🟢（YouTube / Instagram 登录后）→ 直接全自动，先拿列表按阈值筛选，**输出筛选结果让用户确认**再下载。
2. 平台 🔴（视频号）→ 立刻给用户"半自动路径"说明（PC 工具 + 登记表），不要反复尝试在线抓取。
3. 平台 🟡（抖音/小红书/快手/TikTok/Instagram 未登录）→ 先做一次 WebFetch 实测，把结果摆给用户，让用户选：登录态自动化 / 手动采集 / 付费平台。
4. 平台 ✅（已跑通的 6 个）→ 直接加载对应 `references/platform-<name>.md`，按文档执行即可。

## 视频下载的统一归集工具

无论 yt-dlp / instaloader / MediaCrawler / wx_channels_download 下载到哪里，**最终归集到 `<项目>/02-Whisper转写/视频源文件/{NNN}-{完整标题}.mp4` 的工作用对应 `scripts/collect_videos_<platform>.py`** 完成。

跨平台统一文件名规则（safe() 函数）见 SKILL.md「🔴 文件命名清洗规则」章节。
