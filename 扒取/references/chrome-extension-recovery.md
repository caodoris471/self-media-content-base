# Chrome 扩展恢复指南（2026-09-12 事故用）

## 事故背景

**触发动作**：用 NTFS junction 指向真实 Chrome User Data 启动 Playwright，被 Chrome 137+ 视为损坏 profile，清空了 `Default/Extensions/` 代码目录。

**实际后果**（实测）：Doris（Default）profile 原本 **28 个扩展** → 被清到剩 **2 个**（AutoGLM + IDM Integration Module）。

**保留的数据**（硬盘实测完整）：
- `Default/Local Extension Settings/` —— 28 个扩展的配置/数据完整保留（**134MB**）
- `Default/IndexedDB/chrome-extension_*/` —— 6 个扩展的 IndexedDB 完整
- `Default/Sync Extension Settings/` —— 14 个扩展处于 Chrome Sync 状态
- `Default/Extension Scripts/` + `Extension Rules/` —— 完整
- `Default/Bookmarks.bak` —— 完整

**被清空的数据**：
- `Default/Extensions/` —— 28 个扩展代码包全没了（只剩 2 个）
- `Default/Preferences` + `Secure Preferences` 的 `extensions.settings` 字段被重置

## 28 个扩展 ID 完整清单（按存储大小排序）

| # | Extension ID | Local Settings 大小 | Sync |
|---|---|---|---|
| 1 | hjbfbllnfhppnhjdhhbmjabikmkfekgf | 104900 KB | ✅ |
| 2 | hoklmmgfnpapgjgcpechhaamimifchmp | 7102 KB | ✅ |
| 3 | lghnjiiijkmgpgafgehpahncpcpfmkbp | 4206 KB | ✅ |
| 4 | bpoadfkcbjbfhfodiogcnhhhpibjhbnh | 4180 KB | ✅ |
| 5 | lnbmbgocenenhhhdojdielgnmeflbnfb | 3983 KB | |
| 6 | knbeilbpfnelpbeoofhnkfbfcldpfehn | 3654 KB | |
| 7 | fchbhcjlkcdchcaklpkdofllfoimelgb | 2526 KB | |
| 8 | penohjgblobinadflplocjekaclnoemh | 827 KB | |
| 9 | ibdfeimkglcmdejppabkaidpippniiob | 823 KB | |
| 10 | oldceeleldhonbafppcapldpdifcinji | 630 KB | ✅ |
| 11 | cofdbpoegempjloogbagkncekinflcnj | 433 KB | ✅ |
| 12 | dhdgffkkebhmkfjojejmpbldmpobfkfo | 189 KB | |
| 13 | glglcllfanaonpfinaldiiehbabhmhpe | 286 KB | |
| 14 | amdfepljcddfmbgdnkkkfgkflgakbgjm | 169 KB | |
| 15 | pachckjkecffpdphbpmfolblodfkgbhl | 169 KB | ✅ |
| 16 | elglapmnjgilhlbfjogkgfledogdkmol | 143 KB | ✅ |
| 17 | hbapdpeemoojbophdfndmlgdhppljgmp | 54 KB | ✅ |
| 18 | peaiabjigdmcjiigljknblkdmllgmklp | 29 KB | |
| 19 | bdmhpdilnolofapjphhfigjdclgmdhpf | 29 KB | |
| 20 | akdgnmcogleenhbclghghlkkdndkjdjc | 24 KB | |
| 21 | hehggadaopoacecdllhhajmbjkdcmajg | 9 KB | |
| 22 | bclaoecbblljmooanbbhcdadmhcejhdm | 6 KB | |
| 23 | leokjncneiocjfkalljjokhomjnpolkk | 5 KB | ✅ |
| 24 | pmafjeghchhihekeniifdnagkiagijbn | 2 KB | ✅ |
| 25 | dalllmjfhfikljcgpfnfhcaepefgnahm | 2 KB | ✅ |
| 26 | jilgamolkonoalagcpgjjijaclacillb | 1 KB | |
| 27 | dpfmkbcoaddghkkhebjcjaoaiaefigln | 1 KB | |
| 28 | gjjabgpgjpampikjhjpfhneeoapjbjaf | 1 KB | |

## 重建顺序（从最稳到最差）

### 路径 1：Chrome Sync 自动恢复（首选，0 操作）

如果用户 Doris 账号登录了 Google Chrome：

1. 打开 Chrome，地址栏输入 `chrome://settings/syncSetup`
2. 确保「扩展程序」同步开关打开
3. Chrome 应自动从云端同步所有扩展列表 → 触发 Web Store 重新安装
4. 大部分扩展几秒到几十秒恢复，配置数据从 `Local Extension Settings/` 自动关联

### 路径 2：批量 CRX 下载安装（推荐，无登录态要求）

用 Chrome Web Store 的官方 CRX 下载端点（无需登录）：

```
https://clients2.google.com/service/update2/crx?response=redirect&prodversion=130.0&acceptformat=crx3&x=id%3D<id>%26installsource%3Dondemand%26uc
```

**Python 批量脚本示例**：

```python
import urllib.request, zipfile, os, shutil, json

ids = [
    'hjbfbllnfhppnhjdhhbmjabikmkfekgf',  # 102MB 最大
    'hoklmmgfnpapgjgcpechhaamimifchmp',
    # ... 其他 26 个
]

ext_base = r'C:\Users\<你的用户名>\AppData\Local\Google\Chrome\User Data\Default\Extensions'

for eid in ids:
    url = f'https://clients2.google.com/service/update2/crx?response=redirect&prodversion=130.0&acceptformat=crx3&x=id%3D{eid}%26installsource%3Dondemand%26uc'
    req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
    with urllib.request.urlopen(req, timeout=30) as r:
        data = r.read()
    
    # 解压 CRX 到目标目录
    with zipfile.ZipFile(io.BytesIO(data)) as z:
        # 读 manifest 拿 version
        mf = json.loads(z.read('manifest.json'))
        ver = mf['version']
        out_dir = os.path.join(ext_base, eid, ver)
        os.makedirs(out_dir, exist_ok=True)
        z.extractall(out_dir)
    print(f'OK: {eid} v{ver}')
```

下载后还需要在 `Secure Preferences` 的 `extensions.settings.<id>` 字段加上 `"state": 1`，或者直接重启 Chrome 让它自动扫描 `Extensions/` 目录。

### 路径 3：Chrome Web Store 手工装（最慢，但最稳）

每个 ID 在 `https://chromewebstore.google.com/detail/<id>` 自动跳转到对应扩展页，逐个点「添加至 Chrome」。

## 铁律（必须遵守）

❌ **绝对禁止**用 `--user-data-dir` 指向真实 Chrome User Data 或其 NTFS junction
❌ **绝对禁止**用 Playwright `launch_persistent_context(user_data_dir=<真实 Chrome 路径>)`
✅ 如果必须用真实 profile，先把整个 `User Data/` 复制到独立目录再用

## 用户当前环境

- Windows 11 + Chrome 152.0.7977.83
- 4 个 profile：Doris (Default, 主账号) / NailLover (Profile 2) / USA (Profile 22) / 熹 (Profile 9)
- Doris 账号原本 28 个扩展，被清到剩 2 个
- 三个其他 profile **未受影响**
- 已确认 Doris 是当前活跃 profile（`Local State.last_active_profiles = ["Default"]`）
- `Local State.backup_20260912_130612` 保留为安全备份

## 相关路径

- Chromium: `C:\Program Files\Google\Chrome\Application\chrome.exe`
- Chrome 主目录: `C:\Users\<你的用户名>\AppData\Local\Google\Chrome\User Data\`
- 用户主项目: `{工作目录}\`
