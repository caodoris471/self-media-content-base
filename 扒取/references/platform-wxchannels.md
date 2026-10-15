# 微信视频号 · 全自动抓取（固化流程 v1.0 · 2026-09-14 起不再变动）

> **🔴 本文件是视频号任务的唯一执行标准。任何视频号任务，只跑 `scripts/wx_pipeline.py`，不要现场造脚本、不要改流程、不要让用户手动点下载。**

---

## 0. 一句话结论

**视频号不需要人工点下载。** `wx_channels_download` 自带完整 HTTP API，可以全自动：
搜索账号 → 翻页拉全部视频清单（含直链 + 解密密钥）→ 直链下载 → 调 API 解密 → Whisper 转写 → 分时段 MD。

**唯一的一次性人工动作**：PC 微信已登录，且**打开过任意视频号页面**（让工具 WebSocket 连上）。
之后几十上百条全部自动，**用户不需要逐个点视频、点下载按钮**。

> 历史教训：2026-09-14 之前一直误以为「必须人工点下载按钮」，让用户反复点了 3 次只拿到 1 条。
> 实际是工具 API 没被用起来。**今后再出现「让用户点下载按钮」的行为 = 违规。**

---

## 1. 前置检查（每次任务开工必做）

### 1.0 🔴 先问改写语气（新博主必问，在跑任何命令之前）

用 AskUserQuestion 问一次，**拿到答案才开始下载**：

> 这个博主的改写脚本要用哪种语气？（选项：情感共鸣型 / 犀利观点型 / 干货拆解型 / 人物故事型 / 种草带货型）

- **每个新博主必问一次**；同一博主重复扒取沿用上次选择
- 已确认的默认：示例博主（`{视频号sph_id}`，人生/婚姻/低谷类）→ **情感共鸣型**
- ❌ 不准跳过、不准自作主张套默认（2026-09-14 用户明确要求写死这条）
- ✅ 但**下载/转写/清理全过程仍然不问**，全自动跑完

### 1.1 工具与 API

```bash
# 1) 工具进程在不在
tasklist | grep -i wx_video
# 不在就后台启动
"{工作目录}/tools/wx_channels_download/wx_video_download.exe"

# 2) API 通不通
curl -sS http://127.0.0.1:2022/api/channels/status
# 期望：data.available = true
```

- `available: false` → **引导用户在 PC 微信打开博主视频号主页**，然后重跑
- API 不通（Connection refused）→ 启动工具后等 5 秒再试
- 启动后证书丢失属正常（工具每次启动自签）；证书只影响 PC 微信侧抓包，不影响 API 调用

**注意**：`config.yaml` 的 `download.dir` **与本文流程无关**（我们走直链下载 + 调 API 解密，不依赖工具的下载目录）。不要再去改它。

---

## 2. 一条命令跑完全流程

```bash
"C:/Users/<你的用户名>/AppData/Local/Programs/Python/Python312/python.exe" \
  "C:/Users/<你的用户名>/.codex/skills/博主视频全量扒取/scripts/wx_pipeline.py" \
  --nickname "示例博主" \
  --author  "示例博主" \
  --spid    "{视频号sph_id}" \
  --project "{工作目录}/{视频号sph_id}_视频号视频扒取" \
  --days 7 \
  --min-likes 100 \
  --rewrite
```

| 参数 | 必填 | 说明 |
|---|---|---|
| `--nickname` | ✅ | 视频号搜索关键词（能搜到该账号的名字片段） |
| `--author` | 建议 | 博主显示名，写进 MD 头部 |
| `--spid` | 建议 | 视频号 ID，写进 MD 头部 |
| `--project` | ✅ | 项目根目录，不存在自动建 |
| `--days` | 默认 365 | 只抓最近 N 天 |
| `--all` | — | 抓全部（不加时间过滤） |
| `--min-likes` | 默认 0 | 只保留点赞数 ≥ N 的视频 |
| `--model` | 默认 tiny | whisper 模型；large-v3 在 hf-mirror 常 401 |
| `--rewrite` | — | 同步生成 `04-改写脚本/` |
| `--skip-download` | — | mp4 已下好，只跑转写 + MD |
| `--skip-transcribe` | — | 只下载不转写 |

**Python 环境要求**：必须用已安装 `faster-whisper` + `opencc-python-reimplemented` 的 Python 执行。当前实测可用环境：
`C:/Users/<你的用户名>/AppData/Local/Programs/Python/Python312/python.exe`
（managed venv `envs/default` 未装 faster-whisper，会报错）。
安装命令：
```bash
C:/Users/<你的用户名>/AppData/Local/Programs/Python/Python312/python.exe -m pip install faster-whisper opencc-python-reimplemented
```

---

## 3. 流水线内部 8 步（已写死在脚本里，不要改）

| # | 步骤 | 接口 / 做法 |
|---|---|---|
| 1 | 检查页面连接 | `GET /api/channels/status` → `data.available` |
| 2 | 搜账号拿 username | `GET /api/channels/contact/search?keyword=<kw>` → `data.data.infoList[i].contact.username`（**v2_xxx@finder 格式**） |
| 3 | 翻页拉全量清单 | `GET /api/channels/contact/feed/list?username=<un>&next_marker=<lastBuffer>` |
| 4 | 时间过滤 | `createtime >= now - N days` |
| 5 | 直链下载加密文件 | `media[0].url + media[0].urlToken`，带 Referer `https://channels.weixin.qq.com/` |
| 6 | 解密 | `POST /api/channels/decrypt?filepath=<绝对路径>&key=<decodeKey>` |
| 7 | Whisper 转写 | faster-whisper，tiny/int8/CPU，`language="zh"` |
| 8 | 重建 MD + 总索引 | 按 SRT **逐段**生成 `[HH:MM:SS]` 分时段稿，繁转简 |

**产物**：
```
01-视频清单/account_videos.json   全量清单（含直链 + decodeKey）
01-视频清单/逐字稿总索引.md        按日期倒序的总入口
02-Whisper转写/视频源文件/         N 个 mp4
02-Whisper转写/转写结果/           N 个 srt + txt
03-逐字稿MD/                       N 篇分时段逐字稿（繁转简）
04-改写脚本/                       N 篇改写稿（🔴 必须 AI 亲笔写口播文案，见铁律 I）
```

**04 交付标准（缺一不可）**：
```
## 🎯 新标题备选      ≥3 个
## 🪝 Hook           1 句实际写出来的开场白（不是「直接抛出…」）
## 🎙️ 口播文案        4 段实际写出来的口播，可直接照读
## 🎞️ 画面/字幕同步表  4 行
## ✨ 金句            提炼改写后的句子（不是原文照抄）
## 📝 原稿参考区       折叠块，放 03 逐字稿全文
```
> **验收命令**（改写主体抄自原稿的行数必须为 0）：
> ```python
> main4 = t4.split('<details>')[0]   # 参考区之前
> # 统计 main4 中出现在 03 逐字稿里的行数 → 必须为 0
> ```

---

## 4. 🔴 七个已踩过的坑（硬约束，务必遵守）

### 坑 1：翻页字段是 `lastBuffer`，不是 `lastBuff`
- 写错 → 只能拿到第一页（15 条），看起来像「博主只有 15 条」
- 正确：`inner.get("lastBuffer")`；`continueFlag == "0"` 或 `lastBuffer` 为空 → 停

### 坑 2：username 藏在 `contact` 嵌套里
- `infoList[i].username` 是空的
- 正确：`infoList[i].contact.username`

### 坑 3：视频直链下载下来是**加密**的
- 文件头不是 `ftyp`，直接播不了
- 必须 `POST /api/channels/decrypt` 解密（原地覆盖）

### 坑 4：decrypt 的 key 必须放 **query 参数**
- 放 body → 报 `key parameter is required`
- 正确：`?filepath=<abs>&key=<int>`（key 在 `objectDesc.media[0].decodeKey`）

### 坑 5：MCP 模式全废，别用
- `wx_video_download.exe mcp` 的 tools/call 全部 `context canceled`
- **直接 HTTP 打主服务 `http://127.0.0.1:2022` 的 `/api/channels/*`**
- `POST /api/v1/download_task/create` 传 `{tasks:[{url}]}` 报 400「没有传入要下载的内容」→ 放弃这条路

### 坑 6：旧版 `md_generator.py` **禁止使用**（已废弃并从本包移除）
- 它会把多段 SRT **合并成一坨**（丢掉时间戳）
- 头部还会错挂上一个项目的博主名 / 视频号 ID
- 且被后台任务反复调用，把正确 MD 覆盖成 `<!-- AI 提炼 -->` 占位版
- **视频号一律用 `wx_pipeline.py` 内建的 `step_md()`**；若外部项目里仍残留 `md_generator.py`，直接 `mv md_generator.py md_generator.py.disabled`

### 坑 7：Python 环境必须含 `faster-whisper` + `opencc`
- managed venv `C:/Users/<你的用户名>/.workbuddy/binaries/python/envs/default` 未装 faster-whisper，直接跑会报：`faster-whisper 未安装`
- **解决方案**：使用系统 Python 3.12，并安装依赖：
  ```bash
  C:/Users/<你的用户名>/AppData/Local/Programs/Python/Python312/python.exe -m pip install faster-whisper opencc-python-reimplemented
  ```
- 不要临场创建新的 whisper venv，除非确认其中已装好上述两个包

---

## 5. 补充铁律

| # | 铁律 | 说明 |
|---|---|---|
| A | **不用用户点任何按钮** | 违反 = 返工。唯一人工动作是「PC 微信打开过视频号页面」 |
| B | **进度用 API 结果验证，不靠用户口述** | 拉完清单打印 `total` 条数；下载完打印成功/失败数 |
| C | **清理文件用 Python `Path.unlink()`** | bash `rm` 对含 `！？｜` 等特殊字符的文件名会**静默失败** |
| D | **写 MD 时若 Write 工具报 "File has been modified since read"** | 先写到 `99-生成脚本/_stage.md`，再 `mv` 到目标路径 |
| E | **Whisper tiny 会输出繁体** | 装 `opencc-python-reimplemented`，用 `OpenCC("t2s")` 转简体 |
| F | **large-v3 在 hf-mirror 常 401** | 默认 `tiny`；tiny 错字多但可用，需要精校时再换模型 |
| G | **下载 4GB 约 10 分钟，转写 45 条约 15 分钟** | 用后台任务跑，别前台等 |
| H | **🔴 开工前必须先问「改写语气」，不准套默认** | **下载/转写之前**就用 AskUserQuestion 问一次，给 5 个命名选项：情感共鸣型 / 犀利观点型 / 干货拆解型 / 人物故事型 / 种草带货型。**每个新博主必问一次**（同一博主重复扒取沿用上次选择，可不再问）。边界（2026-09-14 用户原话）：「语气还是要问的，我指的是下载的转写的全过程不用问」——**执行细节全自动 ≠ 输出语气可以不问** |
| I | **🔴🔴 04 改写稿必须 AI 亲笔写口播文案，脚本只出骨架** | `wx_pipeline.py --rewrite` 的 `step_rewrite()` **只能生成框架模板，它不是交付物**。纯规则脚本不会改写，只会「套模板 + 摘原句」，产出的 04 会 100% 复制 03 逐字稿（2026-09-14「示例博主」实测：04 正文 99-154 行全部原样抄自 03，真正新写的只有 14 行模板占位话术，被用户当场指出「和逐字稿一样」）。**正确做法**：AI 读 03 逐字稿 → 按 H 已确认的语气亲笔重写 Hook/口播/CTA/金句 → 用 `99-生成脚本/ai_rewrite_fill.py` 模式批量落盘（参考区仍放原稿全文） |
| J | **🔴 交付前必跑 `verify_rewrite_distinct.py`，exit≠0 一票否决** | 命令见上文「04 交付标准」段。脚本已做过反向测试：喂复制品会判 FAIL（抄 4 行 / LCS 23 / 8gram 52.6% / 占位 1），喂真改写会判 PASS。**没跑过脚本的 04 一律视为未验收** |
| K | **🔴 清理时 `uninstall` 不会关系统代理，必须手动关** | 卸载后 `ProxyEnable` 仍=1、`ProxyServer=127.0.0.1:2023` 但端口已停 → 全网超时（2026-09-15 实测）。必跑：`reg add "HKCU\Software\Microsoft\Windows\CurrentVersion\Internet Settings" /v ProxyEnable /t REG_DWORD /d 0 /f` |

---

## 6. 已验证战绩

| 博主 | 视频号 ID | 清单 | 实抓 | 成功率 |
|---|---|---|---|---|
| 示例博主 | `{视频号sph_id}` | 115 条（与主页显示吻合） | 近一年 44 条 / 4.1GB | **100%，零失败** |
| 示例博主 | `{视频号sph_id}` | 172 条 | 近 7 天 5 条 / 660MB（点赞≥100） | **100%，零失败** |

耗时参考：
- 示例博主：下载 10 分钟 + 转写 15 分钟 → 47 个 srt → 45 篇分时段 MD（2519 段）。
- 示例博主：下载 2 分钟 + 转写 2 分钟 → 5 个 srt → 5 篇 MD + 5 篇改写稿（610 段）。

---

## 7. 任务收尾

- 默认**保留**工具进程 + 证书（用户偏好「跑一次装一次、不主动清理」）
- 用户说「删证书 / 清掉视频号」才执行清理：见 SKILL.md 步骤 7.1
