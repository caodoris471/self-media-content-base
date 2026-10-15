# 真实飞书字段映射

读取日期：2026-09-22；修订号：761。本次为表头和样例读取，不代表已清洗或改写历史素材。

- 标题：{作者}自媒体素材库
- 入口：https://<你的飞书域名>.feishu.cn/wiki/{知识库父节点token}
- 底层类型：电子表格 Sheets，不是多维表格 Base。
- spreadsheet_token：{spreadsheet_token}

## 工作表

| 表名 | sheet_id | 已有表头（按列顺序） |
|---|---|---|
| 可复制笔记-自整理 | {素材表ID} | 序号、账号归属、平台、类型、内容栏目、标题、链接、口播逐字稿、口播改写、是否符合改写、迫切程度、完成情况、发布情况、备注 |
| 对标博主视频扒取-复刻 | {周采集表ID} | 视频扒取日期、账号归属、平台、博主ID、视频链接/截图、视频标题、视频逐字稿/文案、改写口播稿/改写文案、完成情况 |
| 对标博主 | {对标博主表ID} | 序号、账号归属、平台、ID、主页链接、对标标签、备注 |
| Ai资讯热点 | {AI资讯表ID} | 新闻日期、新闻链接、新闻内容、选题方向、文字稿、口播稿、完成情况 |
| 跨境资讯热点 | {跨境资讯表ID} | 新闻日期、新闻链接、新闻内容、选题方向、文字稿、口播稿、完成情况 |

表头后还有空白列，但空表头不代表整列无内容。新增字段前检查完整目标范围。

## 已读取的笔记表下拉项（B2:M2 样例）

- 账号归属：{作者}（多账号各自复制底座，各自的表里写各自的账号归属）。
- 平台：小红书、公众号；如接视频号、B站等，需在部署时扩展相应验证规则，不能把视频号伪填成公众号。
- 类型：图文、视频、文章。
- 内容栏目：理财、Ai工具、Ai知识科普、人生感悟、品牌剖析、亚马逊、TK、独立站。
- 是否符合改写：符合、不符合。🔴 **助理（自动化）收录的条目一律写「符合」**，不做内容筛选；只有用户手动录入且明确说不改写时才可写「不符合」（2026-10-10 用户定稿）。
- 迫切程度：P00、P0、P1、P2。🔴 **自动化一律留空，由用户手动打**；不改用户已填的值（2026-10-08 首次、2026-10-10 再确认）。
- 完成情况（**下拉选项**，支持多选，`enable_highlight=true` 带色高亮）：`已改成图文`（`#c3dd40`）、`已改成视频`（`#ad82f7`）、`已改成文章`（`#b1e8fc`）、`已改写待审核`（`#ff8800` 橙色）。**稿件生成阶段统一打「已改写待审核」**（2026-10-09 用户指定），不要填「纯文字稿」（不在选项内、无颜色）。这些是生产状态标签，不等同于程序的转写/改写状态；仅生成稿件不能标记已制作视频/图文/文章。
- 发布情况：已发布、未发布。生成草稿不等于发布。

## MVP 建议新增字段（尚未写入在线表）

| 目标 | 建议新增 |
|---|---|
| 四张内容结果表 | 素材唯一键、处理状态、失败原因、采集时间、稿件文档链接 |
| 两张热点表 | 账号归属（避免两人稿件混在一起） |
| 对标视频结果表 | 发布时间、播放量、点赞量、指标采集时间 |
| 对标博主表 | 是否启用、时间窗、播放阈值、点赞阈值、条件逻辑、最后成功水位 |

技术状态可以先放本地任务账本，但角色和文稿必须在飞书可读。未增加唯一键前，可用角色+平台+原链接/解析后的内容 ID 判重；禁止仅凭标题判重。

## 已实测命令（2026-10-08 复核）

读：

```powershell
lark-cli sheets +workbook-info --url 'https://<你的飞书域名>.feishu.cn/wiki/{知识库父节点token}' --as user
lark-cli sheets +csv-get --spreadsheet-token {spreadsheet_token} --sheet-id {素材表ID} --range A1:AA8 --as user
```

写（子命令是 **`+csv-put`**，不是 `+csv-set`；后者不存在）：

```powershell
# 短文本
printf 'a,b,c\n' | lark-cli sheets +csv-put --spreadsheet-token {spreadsheet_token} --sheet-id <id> --range A1:C1 --csv - --as user

# 长文本（逐字稿/口播稿）必须用 stdin，--csv @file 拒绝 allowlist 外路径
cat payload.csv | lark-cli sheets +csv-put --spreadsheet-token {spreadsheet_token} --sheet-id <id> --range A5:I5 --csv - --as user
```

临时 sheet 用于验证写权限（用完必删）：

```powershell
lark-cli sheets +sheet-create --spreadsheet-token <token> --title "_wb_writetest" --as user
lark-cli sheets +sheet-delete --spreadsheet-token <token> --sheet-id <临时id> --yes --as user
```

**写权限已实测通过**（2026-10-08）：建临时 sheet → `+csv-put` → 回读一致 → 删除，revision 919→921，表结构未受影响。此后再验证不必重复此流程。

写入前读取安装环境中 lark-sheets 的相关 reference/CLI help，确认表头、实际数据末行和样式；追加后回读。

## 运行环境（2026-10-08 实测）

| 依赖 | 状态 | 说明 |
|---|---|---|
| lark-cli | ✅ 1.0.97 | 读 + 写均已验证 |
| ffmpeg | ✅ 9.0.1 | 抽 m4a |
| Python | ⚠️ **必须用 3.12** | `C:\Users\<你的用户名>\AppData\Local\Programs\Python\Python312\python.exe` 有 faster_whisper / requests / playwright / cv2 |
| Python 3.13.12 | ❌ 缺依赖 | faster_whisper、requests、playwright 全部 MISSING，**不要用** |
| 采集引擎 | ✅ | **已内置在本包 `扒取/` 子目录**（含 SKILL.md / scripts 9 个 / references），无需另外 clone |
| MediaCrawler | ✅ | `{工作目录}\MediaCrawler` |
