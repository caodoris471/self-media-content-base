# 快手 (kuaishou) 平台扒取指南

> **状态**：✅ 已跑通（2026-09-11 示例博主项目，17 条 ≥30 天 + 点赞 ≥1000）
> **工具**：MediaCrawler + Playwright + 持久化登录态

---

## TL;DR

| 探测项 | 结果 |
|---|---|
| 主站 Web SPA | ❌ 纯 JavaScript 脚手架，HTML 不含视频数据 |
| 移动端 `m.kuaishou.com` | ❌ 用户主页返回"找不到该页面" |
| 公开 GraphQL `visionProfilePhotoList` | ❌ 返回 `result:2` = 需要登录 |
| B站相似 search web 页 | ❌ 快手**无对应公开 search** |
| yt-dlp profile 页 | ❌ `Unsupported URL`，需 photo_id |
| **MediaCrawler (`PLATFORM=ks`)** | **✅ 跑通**，复用小红书同一套 Playwright 持久化登录态 |

**结论**：快手本质跟小红书同一类——半封闭平台，靠 **MediaCrawler + Playwright 持久化登录态** 解决。

---

## 一、账号探测（不需要登录态）

```bash
# 主页 URL: https://www.kuaishou.com/profile/<user_id>
curl -sL -A "Mozilla/5.0 ..." \
  "https://www.kuaishou.com/profile/{快手sec_uid}" \
  -o profile.html
```

页面是 324KB 的 SPA 脚手架——无视频数据，预热用。

---

## 二、MediaCrawler 配置（3 处必改）

### 1. 切换平台：`base_config.py`

```python
# 改前
PLATFORM = "xhs"

# 改后（快手平台）
PLATFORM = "ks"
```

### 2. 配置 creator_id：`config/ks_config.py`

```python
KS_CREATOR_ID_LIST = [
    "{快手sec_uid}",  # 示例博主
]
```

### 3. 浏览器数据目录：`base_config.py`

```python
USER_DATA_DIR = "{工作目录}/<你的项目目录>/browser_context/%s"
```

> ⚠️ 中文路径下 CDP 模式偶尔报错 `WinError 123`，**自动 fallback standard mode**，无需手动处理。

---

## 三、🔴 必须 patch 的代码（2026-09 实测）

### patch 1：登录按钮 xpath（`media_platform/kuaishou/login.py`）

**老代码失效**：
```python
login_button_ele = self.context_page.locator(
    "xpath=//p[text()='登录']"  # ❌ 网页结构改了
)
```

**修复后**：
```python
login_button_ele = self.context_page.locator(
    "xpath=//span[contains(@class, 'sidebar-login-button')]"
)
```

**根因**：快手 2026 年改版，登录按钮从 `<p>登录</p>` 变成 `<span role="button" class="...sidebar-login-button">` 嵌套 `<span>立即\n登录</span>`。

### patch 2：导航到 profile 而非 home（`media_platform/kuaishou/login.py`）

**老代码**：
```python
await self.context_page.goto("https://www.kuaishou.com")
```

**修复后**：
```python
await self.context_page.goto(f"https://www.kuaishou.com/profile/{user_id}")
```

**根因**：快手主页 `/` 不显示顶栏登录按钮（动态加载），profile 页直接展示侧栏登录按钮。

---

## 四、扫码登录流程

```bash
cd "{工作目录}/MediaCrawler" && \
"C:/Users/<你的用户名>/.workbuddy/binaries/python/envs/whisper/Scripts/python.exe" -u main.py \
  --platform ks --type creator --creator_id <USER_ID> --save_data_option jsonl
```

**关键：用户必须在 App 上点"登录"确认**，否则 10 分钟超时。

---

## 五、数据落盘路径

```
MediaCrawler/data/kuaishou/
├── jsonl/
│   └── creator_contents_2026-09-11.jsonl  # 全部视频元数据
└── videos/                                  # 视频本体下载（playUrl）
    └── <video_id>/
```

---

## 六、爬虫跑完后清单

| 数据 | 字段 |
|---|---|
| `video_id` | 唯一 ID（如 `3xdtecgp3x5kuhk`）|
| `title` + `desc` | 标题/描述（带话题 tag）|
| `create_time` | 毫秒时间戳 |
| `liked_count` | 点赞数（注意：有时是字符串，含"万"）|
| `viewd_count` | 播放数（同样可能含"万"）|
| `video_url` | `https://www.kuaishou.com/short-video/<video_id>` |
| `video_play_url` | **直接 mp4/m3u8 URL（带 token，可直接下载）** |
| `video_cover_url` | 封面图 URL |

---

## 七、下载 18 条视频实战策略

### ❌ 不推荐：让爬虫跑完 + 让他下视频本体
- 爬虫会下 320 条视频（creator 全量），其中大部分没用
- 浪费带宽 + 时间

### ✅ 推荐：只下需要的 18 条

```python
# 伪代码
with open('jsonl/creator_contents_2026-09-11.jsonl') as f:
    for line in f:
        rec = json.loads(line)
        if filter(rec):  # 按你的阈值过滤
            url = rec['video_play_url']
            download(url, dest_path)
```

**play_url 自带 token，2-5MB/秒，~10 分钟下完 18 条**。

完整脚本：`scripts/collect_videos_ks.py`（项目里 `99-生成脚本/filter_and_download.py`）。

---

## 八、🔴 jsonl 重复记录处理

**实测发现**：MediaCrawler 偶尔**同一条视频抓两次**（不同 `video_id` 但 mp4 内容字节级相同）。

**校验方法**：
```python
size_a, dur_a = os.path.getsize(mp4_a), duration_a
size_b, dur_b = os.path.getsize(mp4_b), duration_b
if size_a == size_b and dur_a == dur_b:
    # 同一视频重复
    os.remove(mp4_b)
```

**风险**：删错会丢真视频。
**保险**：先看 `md5(mp4_a) == md5(mp4_b)`，再删。

---

## 九、Whisper 识别繁体的处理

快手台湾腔博主念字幕时，**Whisper tiny 倾向识别为繁体**。

```python
import zhconv
text_simp = zhconv.convert(text_trad, 'zh-cn')
```

`zhconv` 不是 faster_whisper 自带，需 `pip install zhconv`。

---

## 十、SKILL.md 进度

| 状态 | |
|---|---|
| 视频号 | ✅ 35 条「品牌出海姐 Rose」 |
| 小红书 | ✅ 29 条「示例博主」 |
| B站 | ✅ 3 条「示例博主」 |
| **快手** | ✅ **17 条「示例博主」（本轮新增）** |

---

## 十一、复用命令速查

```bash
# 1. 三处配置
sed -i 's/PLATFORM = ".*"/PLATFORM = "ks"/' .../base_config.py
sed -i 's/KS_CREATOR_ID_LIST = \[.*\]/KS_CREATOR_ID_LIST = ["<id>"]/' .../ks_config.py
sed -i 's|USER_DATA_DIR = .*|USER_DATA_DIR = "<新项目路径>/browser_context/%s"|' .../base_config.py

# 2. 启动
cd MediaCrawler && python -u main.py --platform ks --type creator --creator_id <id> --save_data_option jsonl

# 3. 筛+下（用户自选阈值）
cd <项目目录> && python -u 99-生成脚本/filter_and_download.py

# 4. Whisper
HF_HUB_OFFLINE=1 python -u 99-生成脚本/whisper_transcribe.py

# 5. MD（自动繁转简）
python -u 99-生成脚本/generate_md.py
```

完整命令见项目 `00-操作手册.md`。
