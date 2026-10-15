# -*- coding: utf-8 -*-
"""{作者}稿件自动审稿机（QA Gate）

用法:
  python qa_check.py <md_path> --type article|koubo|brand [--json]

退出码: 0 = 通过 / 1 = 存在阻塞级问题 / 2 = 用法错误

三条产出路径的前提规则（2026-10-10 用户最终定稿）:
  文章  -> 原文文字稿 + 改写长文稿 + 口播稿
  视频  -> 只口播稿（不做逐字稿、不做长文）
  图文  -> 口播稿 + 说明文字（不做长文）
  访谈  -> 不处理（本脚本不介入）
  文章+栏目=品牌剖析 -> 五维品牌营销全景拆解模板
"""
import argparse, json, re, sys

sys.stdout.reconfigure(encoding="utf-8")

# ---------- 词表 ----------
# 允许出现的英文/标识符（工具名、协议名、字段名、产品名）
WHITELIST = set("""
AI AIGC AGI API HTML CSS JS JSON XML PDF URL MPC MCP MVP SaaS App APP Token Tokens
Skill Skills WorkBuddy Workbuddy ChatCut Obsidian SnapEdit Notion Gemini Claude Codex
GitHub Github Git RSS Excel Word Chrome Edge Edge SKU GMV ROI ROI KOL TikTok Shop
Reddit YouTube Instagram Facebook Amazon VK X Yahoo Bing SEO SEM CPC CTR CTR GMV
TikTok抖音 Douyin TikTok WhatsApp Telegram Zoom Slack Debian Ubuntu Python Node npm
Markdown MD TXT CSV SMTP HTTP HTTPS REST UI UX UI PaaS SaaS Figma Hemingway
CTA CTA Hook Hook Brief Brief Part Step Parts Tips Note Notes Tips P0 P1 SOP QA ROI KPI OK

# 抖音素材工具名（2026-10-14）
HypeIt ClapCat Ghost Cut Hot Video Recreate Chatcut ChatCut howto Howto HowTo

# 跨境电商运营术语（2026-10-10 跨境资讯链路补入）
FBA FBM ACOS ASIN BSR DSP LD BD SP Woot Vine Listing Listings Feedback Review Reviews
Rating Ratings Deal Deals Coupon Coupons Prime Seller Central Minishop Lazada Shopee Ozon
Wildberries Coupang Mercado Temu Shein AliExpress eBay Walmart Best Buy Home Depot Newegg
Costco Target Wayfair Etsy KOC DTC B2B B2C Pixel Events CVR CPM CPA ROAS CTR

# 品牌营销全景拆解框架 v2 术语（2026-10-14 补入）
AA ACC ATT CPS DOTD DealNews Slickdeals Kinja SimilarWeb TrafficWiser Ahrefs Shopify
EDM GEO LTV UGC PR CPC SB SD A+ 旗舰店 混货 FB IG
# 关键词与外媒专名（2026-10-14）
bike bag frame mountain pedals bikepacking Top vs Exploring Singletracks Shimano ROCKBROS
SURI trysuri discoversuri ELFBAR Lost Mary VEEV SKE PayPal Trustpilot
Casetify Casetagram Colette BTS dbrand JerryRigEverything
Oodie Davie Fogarty Pinterest
RITM PacPac Behance Ritual Persona
COCOLAB Cocofloss Scrub Daddy Inc floss Nitecore SUREFIRE Supreme UTMB EDC GFS Govee GOOJODOQ FastMoss

# 本批品牌 / 工具 / 数据源专名（2026-10-10）
Cozyla GOOJODOQ JisuLife MLILY EGO HOME GOKOCO GFS025 Calendar Neo Plus InsMark
Fastmoss Metric VideoAktiv Osmo Pocket TF Maxcolchon Matratzen Concord MOR Furniture
LazVogue LazShadesofStyle LazLive Vogue Crying Center FPA VERAFIED GAM MVK AULA
MOVESPEED KTC Mina Adams Kayy Nas TellezJoanna preetyomahs Outlook Google Apple Lenovo
CES TIME Forbes

# 跨境资讯链路品牌 / 站点 / 数据源专名（2026-10-11 跨境日报补入）
Wavytalk OVIOS DREO SellerSprite Ulta Phia OptiMonk Growjo Indiegogo Erewhon Tesco
Waitrose Ocado Woolworths Whole Foods Simon Griffiths Danny Alexander Jehan Ratnatunga
Melbourne Coupang FastMoss Similarweb Technavio Shopify VOC ABA Hugh K Beauty LevenDry
Cloud Couch Boneless Chaise Lounge Oversized Real Life Styled
Who Gives Crap LeadIQ Morketing Causeartist City AM Instagram

# AI 资讯链路专名（2026-10-10 AI 资讯日报补入）
Bug Bugs Demo Demos PPT IDE SOLO Code Coding Work View Window and
TRAE TraeCode TraeWork Cursor Minecraft Notch Chests Levers TeamDesk FeedbackDesk
Agent Agents AgentOS Agentic Hub WorkSwarm SystemAgent Jiuwen openJiuwen agentos-enterprise
Anthropic OSS Scanner Mythos CVD PR Fuzz QbitAI HC OSS-Fuzz openJiuwen-ai
Doubao Seedream Flash Lite Turbo Pro atomgit github com

# AI 资讯日报 2026-10-11 专名（ds bot / TeamAI / Qoder / 元宝桌宠 / Claude 工作流 / Edge 155 / Nano Banana 2.1）
DeepSeek DeepSeek-Bot DSH Bot Bots Grok Muse FeiZhuLulu FeiZ Harness Web
ds ds-bot pnpm Apache License Session Sessions
Settings Usage Beta PC Main BTW ID IDs Hook Tencent Oct Jan Feb Mar Apr Jun Jul Aug Sep Nov Dec
TeamAI ClawPro CodeBuddy Qoder Fast Performance Ultimate Auto Credits CN Yuanbao workday
Managed Workflow Microsoft Chromium unload HDR JPEG XL wav mp3 webm
Nano Banana Arena Veo Flow Adobe Studio Christopher Fryant Heather Cooper Zane Stav
Zilbershtein snow Qwen TypeSafe Jev Clef omni
AIStudio GeminiAPP gemini-nano-banana gemini-nano-banana- ChatGPT GPT
Image Images Max Buff Case

# AI 资讯日报 2026-10-12 专名（论文工具 / 上下文扩容 / 企鹅微单）
OpenAI Academic Paper Gen GLM LaTeX BibTeX RIS DOI Ctrl Key OpenAlex Crossref Scholar arXiv
Zcode Highspeed Rosalind Decart Keep Grok VISTA Harness

# AI 资讯日报 2026-10-13 专名（千问Go / Copilot Notebooks / Step5 / 智能UI）
Meta Personal Dots Astra DevDay Instinct Corner handle battle Go GPT-
Copilot Notebooks Frontier MoE Sora Teams Step5Preview Step5
Notebook NotebookLM Office PowerPoint Word Excel
Analysis Artificial OpenRouter Preview Trending

# 网页汇报 Skill 专名（2026-10-10 HTML skill 清单批次）
Frontend Slides Huashu Design Visual Explainer Studio Editable Bento deck Deck
KB MB GB npx add global agent theme Theme Stars Star Slides Show share mac win
bash sh shell text list main yes tree plugins weekly table chart timeline report
latest frontend huashu visual explainer editable slides zarazhangrui alchaincyf
nicobailon lewislulu archlizheng

# 跨境资讯链路 2026-10-12 批次专名（沃尔玛广告 / Costway / 领英 / 亚马逊广告 / Shopee /
# 网红归因 / 美客多 / Suboo / 付费邀评 / 品牌授权 / Birdfy / 大健云仓 / P+ / Google Ads /
# Shark / 广交会工具 / SmallRig）
Action Brand Call Hero Item Logo Now Portal SB SV to gt nbsp
Costway Haoya Babyjoy portable DIY Ocean PatPat WIS Carlos CCremodeling My Projects Official
Boolean Buyer Sourcing Procurement Purchasing Manager managers Chain Supply Company companies Current
Industry Locations Headline Experience People Purchasing Directors Decision-makers responsible importing
retailers equipment outdoor furniture packaging food gas oil Saudi Arabia UAE Mexico Germany France
ABC at for in my nd network or the connections degree
SD AMS ERP FBS LFF VMI SLS PF PingPong MCN Hello Kitty FDA GDP Video Live
Aspire Cirqle CreatorIQ GDPR Grin Group NeoReach North Northbeam Nox Points Rockerbox SocialBook
Statista The UTM University Upfluence Vilnius eMarketer cookie
Bluetooth Earbuds Headphones Wireless Noise Reduction Cheap Sale Catalog Clips EAN UPC GTIN Brand Yiju
Suboo Damien Darin Desordre Dion Lee Alice McCall Sneakerboy Veronika Maine Cue Clothing Co Pty Ltd
Rent Runway Harry the
Requests
Alexa approved brand comes from or xx BRAND XX Product Sourced Wilson Box
Birdfy Netvue Feeder Duo Bath Pro Wild Birds Unlimited American Birding Biggest Week Stephen Moss
Chewy PetSmart Petco Roku Sam's Kohl's Club MAP MediaMarkt EN Wi-Fi cookie smart bird feeder IFA
COO GIGA NFM Nebraska Mart New Classic Colony TALLDESI MONTARY The nfm www
Bullet Dawn checklist
AMC AdX Ads Audience Data Direct Manager Open Publisher Seven Signals alexa
MOQ OEM ISO Tag Assistant GA automotive certified construction custom factory food industrial inverter
manufacturer manufacturing metal packaging processing pump solar supplier water wholesale
EchoTik Shark
Europages ImportYeti OpenCorporates Maps Automotive Lighting Hardware Tools Phone accessories screen
protector mobile importer wholesaler distributor Distributor Importer Owner President General Angeles
Los USA Ac cantonf cantonfair hg smtso sories linkedin europages importyeti opencorporates maps
fasteners industrial
AirTag Anyway Boulanger Fnac IBC IFA POV Patagonia REBOUND SmallRig Vlog vivo IT IP

# 跨境资讯链路 2026-10-13 批次专名（日本疗愈消费 / Kaufland 西班牙站 / Nex Playground
# 儿童体感游戏机 / 广交会客户开发网站清单）
Qoo10 Others Recovery Relax Rakuten Mercari ZOZOTOWN LINE Yahoo Japan Tokyo Osaka Kyoto
Kaufland Schwarz Lidl Ahold Delhaize Mercadona Esselunga Sainsbury Carrefour EPR Marketplace
Spain Germany Netherlands Poland Czech Slovakia Austria France Italy Europe ES Global
Nex Playground Kalodata Nintendo Xbox PlayStation Wii Switch Active Bundle Sensor Camera
Canton Cantonfair Kompass Thomasnet Yellowpages ZoomInfo Hunter RocketReach Snovio Lusha
Clearbit Alibaba Made-in-China GlobalSources Wholesale Exporter Buyer Trade Import Export

# 跨境资讯链路 2026-10-14 批次专名（蓝标传媒x中国国航亚马逊广告 / Amazon Ads Agent /
# SHEIN 年末大促 / 美国鞋履 Circana / 恒诺家具破产 / Meoky 保温杯 / Morpho UV 打印机 /
# 德国进口简报 / Liquid I.V.）
BlueMedia Air China AirChina Programmatic Optimization Award Winner Partner unBoxed unboxed
IMDb Prime Fire Tablet Dentsu Jason MacLean Kelly Amit Bhattacharyya Beijing Shanghai Guangzhou
DSP AMC ROAS Ads Console Agent Agents Full-Funnel Campaigns DVA Brand Performance Console
SHEIN Shein Haul KA P4P RTS Levanta Renpho INNO100 Owen Guetschow Gugu Rocky Liang
Circana FDRA POS Lifestyle Running Occupational Safety Training Hiking Sandals Outdoor Water
Sneakers Athletic Footwear Sport Consumers Retail Tracker Import Boots Casual Fashion
Wayfair Hengnuo Zhejiang Hangzhou Xiaoshan Court Bankruptcy OEM ODM Furniture Leather
Meoky Stanley YETI Tumbler Insulated Stainless Steel Leakproof Iced Coffee Mackaron Macaron
Tumblers Cup Cups Bottle TikTok Shop US UK North America
Morpho DJI Kickstarter Maker Makers UV Printer Printing Desktop Engraving Resin Curing
Wang Mingyu 3D Printer Printers Backer Backers Pledge Campaign Indiegogo
Liquid Unilever Wellbeing Electrolytes Hydration Costco Sugar-Free Vitamins Powder
TOTWOO Shenzhen Carlson Nicholas Yulan Huang Fenqiang Xu Xinbenchuang Capybara Jewelry
Bracelet Bracelets Wearable Smart Bluetooth App iOS Android Gift Couple Couples Long-distance
Deutschland Berlin Hamburg Munich Hamburg Paris Rotterdam Antwerp Customs Parcel Parcels
Tiny Minitype De Minimis Textiles Apparel Plastics Rubber Footwear Headwear
""".split())

EN_WORD = re.compile(r"[A-Za-z][A-Za-z\-']{1,}")

NAV_GARBAGE = [
    "预览时标签不可点", "微信扫一扫", "关注该公众号", "轻点两下取消赞", "轻点两下取消在看",
    "使用小程序", "使用完整服务", "小程序", "分享", "留言", "收藏", "听过", "不喜欢",
    "知道了", "取消", "允许", "×分析",
]

AD_WORDS = [
    "扫码领取", "扫码即可免费领取", "后台回复", "课程详情", "咨询课程", "加送",
    "资料包", "领取资料", "关注本公众号", "免费领取", "立即领取", "进群",
]

CTA_HINTS = ["今晚", "评论区", "去试试", "动手", "跑一遍", "挑一条", "现在就", "截图发我"]


def strip_code(md: str) -> str:
    """去掉围栏代码块（按行首 ``` 成对开关，兼容 ```bash 这类带语言的开始标记）。
    旧实现 re.sub(r'```.*?```') 在多个带语言标记的代码块之间会错位配对，
    把正文当代码删掉、同时把 'bash' / 'latest' 等围栏标记残片留在正文里。"""
    out, in_code = [], False
    for ln in md.split("\n"):
        if ln.lstrip().startswith("```"):
            in_code = not in_code
            continue
        if not in_code:
            out.append(ln)
    return "\n".join(out)


def split_sections(md: str):
    """返回 [(level, title, body), ...]"""
    out = []
    lines = md.split("\n")
    cur = None
    buf = []
    for ln in lines:
        m = re.match(r"^(#{1,6})\s+(.*)$", ln)
        if m:
            if cur:
                out.append((cur[0], cur[1], "\n".join(buf).strip()))
            cur = (len(m.group(1)), m.group(2).strip())
            buf = []
        else:
            buf.append(ln)
    if cur:
        out.append((cur[0], cur[1], "\n".join(buf).strip()))
    return out


def cjk_len(s: str) -> int:
    return len(re.findall(r"[\u4e00-\u9fff]", s))


def ngrams(s: str, n=4):
    s = re.sub(r"\s+", "", s)
    return {s[i:i + n] for i in range(max(0, len(s) - n + 1))}


def jaccard(a: str, b: str, n=4) -> float:
    A, B = ngrams(a, n), ngrams(b, n)
    if not A or not B:
        return 0.0
    return len(A & B) / len(A | B)


def find_body(sections, keywords, exclude=None):
    """取到关键词标题下【含全部下级子章节】的完整正文"""
    for idx, (lv, title, body) in enumerate(sections):
        t = title + body[:50]
        if all(k in t for k in keywords):
            if exclude and any(x in t for x in exclude):
                continue
            parts = [body]
            for lv2, t2, b2 in sections[idx + 1:]:
                if lv2 <= lv:
                    break
                head = "#" * lv2 + " " + t2
                parts.append(head + "\n" + b2)
            return "\n".join(p for p in parts if p)
    return None


def body_wo_source(md: str, src_words=("原文文字稿", "原文", "逐字稿")):
    """去掉原文/逐字稿段落后的正文（用于查引流词，原文里出现不算问题）"""
    lines = md.split("\n")
    out, skip = [], False
    for ln in lines:
        m = re.match(r"^(#{1,6})\s+(.*)$", ln)
        if m:
            lv, title = len(m.group(1)), m.group(2)
            if lv <= 2:
                skip = any(w in title for w in src_words)
        if not skip:
            out.append(ln)
    return "\n".join(out)


def check(md: str, typ: str, sub: str = "img"):
    issues = []
    secs = split_sections(md)
    plain = strip_code(md)
    titles = [t for _, t, _ in secs]


    def block(msg):
        issues.append({"level": "block", "msg": msg})

    def warn(msg):
        issues.append({"level": "warn", "msg": msg})

    # 1. 结构
    if typ == "article":
        need = ["原文文字稿", "改写长文稿", "口播稿"]
        for k in need:
            if not any(k in t for t in titles):
                block("缺少章节：%s" % k)
        long_body = find_body(secs, ["改写长文稿"]) or ""
        n = cjk_len(long_body)
        if n < 2200:
            block("长文稿中文字数不足：%d 字（要求 ≥2200）" % n)
        else:
            issues.append({"level": "info", "msg": "长文稿字数 %d 字 ✅" % n})
    elif typ == "koubo":
        # 图文/视频轻量稿：说明文字 + 口播稿，两段封顶（2026-10-10 用户：太长，砍掉原文要点）
        # 2026-10-10 用户定稿：图文 说明~150 / 口播~250；视频再短一档
        if sub == "video":
            cap_desc, desc_lo = 120, 60
            cap_lo, cap_hi = 100, 200
        else:
            cap_desc, desc_lo = 200, 120
            cap_lo, cap_hi = 230, 300
        if any(("原文要点" in t or "原文文字稿" in t or "逐字稿" in t) for t in titles):
            block("图文/视频轻量稿不许出现「原文要点 / 原文文字稿 / 逐字稿」章节，只要说明文字 + 口播稿")
        if not any("说明文字" in t for t in titles):
            block("缺少章节：说明文字")
        if not any("口播稿" in t for t in titles):
            block("缺少章节：口播稿")
        if any("改写长文稿" in t or "长文稿" in t for t in titles):
            block("图文/视频类型不允许出现长文稿章节")
        desc = find_body(secs, ["说明文字"]) or ""
        dn = cjk_len(desc)
        if dn > cap_desc:
            block("说明文字 %d 字，超过上限 %d 字（%s）" % (dn, cap_desc, sub))
        elif dn < desc_lo:
            warn("说明文字仅 %d 字，目标 ~%d 字（要点：为什么值得抄 + 可抄的结构 + 一条落地提醒）" % (dn, 150 if sub == "img" else 100))
        kb_all_t = find_body(secs, ["口播稿"]) or ""
        n = cjk_len(kb_all_t)
        if n < cap_lo:
            block("口播稿 %d 字，低于下限 %d 字" % (n, cap_lo))
        elif n > cap_hi:
            block("口播稿 %d 字，超过上限 %d 字（%s）" % (n, cap_hi, sub))
        else:
            issues.append({"level": "info",
                           "msg": "口播稿 %d 字（约 %d 秒）/ 说明文字 %d 字 ✅" % (n, round(n / 5.0), dn)})
    elif typ == "brand":
        need = ["原文文字稿", "品牌营销全景拆解", "可抄的动作清单", "改写长文稿", "口播稿"]
        long_body = find_body(secs, ["改写长文稿"]) or ""
        n = cjk_len(long_body)
        if n < 2000:
            block("品牌剖析长文字数不足：%d 字（要求 ≥2000）" % n)
        # v2 框架（2026-10-14）：拆解章节开头必须先判型 → 再定详略权重
        # 仅 warn，不阻塞（存量 37 条旧五维稿豁免，新增必须有）
        audit_body = find_body(secs, ["品牌营销全景拆解"]) or md
        if not any(t in audit_body for t in ("亚马逊主导型", "DTC 型", "DTC型", "双轨型")):
            warn("未见品牌判型结论（亚马逊主导型 / DTC 型 / 双轨型）——v2 框架要求"
                 "拆解章节开头先判型，再按权重表定详略（详写最多 2-3 个维度）")

    # 2. 原文段的网页导航垃圾
    src = find_body(secs, ["原文文字稿"]) or ""
    hit_nav = [w for w in NAV_GARBAGE if len(w) >= 3 and w in src]
    if hit_nav:
        warn("原文段疑似残留网页导航词：%s" % "、".join(hit_nav[:6]))

    # 3. 广告引流词（只看改写正文，原文段里出现不算）
    hit_ad = [w for w in AD_WORDS if w in strip_code(body_wo_source(md))]
    if hit_ad:
        block("残留推广引流词：%s" % "、".join(hit_ad))

    # 4. 中英混杂
    words = EN_WORD.findall(plain)
    bad = sorted({w for w in words if w.lower() not in {x.lower() for x in WHITELIST}})
    if len(bad) > 8:
        block("疑似中英混杂过多（%d 个白名单外英文词）：%s" % (len(bad), "、".join(bad[:12])))
    elif bad:
        warn("白名单外英文词 %d 个：%s（若是产品名请确认）" % (len(bad), "、".join(bad[:12])))

    # 5. Hook / CTA
    kb_all = find_body(secs, ["口播稿"]) or ""
    if "[Hook" not in kb_all:
        block("口播稿缺少 [Hook｜x-y 秒] 分段标记")
    if "[CTA" not in kb_all:
        block("口播稿缺少 [CTA｜] 分段标记")
    tail = kb_all[-260:]
    if not any(h in tail for h in CTA_HINTS):
        warn("CTA 不像具体动作（缺今晚/评论区/跑一遍等），建议改成可执行动作")

    # 6. 抄袭检测：长文 vs 原文 4-gram 重叠
    if typ in ("article", "brand"):
        long_body = find_body(secs, ["改写长文稿"]) or ""
        if src and long_body:
            j = jaccard(long_body, src)
            issues.append({"level": "info", "msg": "长文与原文 4-gram 重叠度 %.1f%%" % (j * 100)})
            if j > 0.30:
                block("长文与原文重叠 %.1f%% > 30%%，判定为改写不足（疑似复制）" % (j * 100))
            elif j > 0.20:
                warn("长文与原文重叠 %.1f%%，偏高，建议进一步重构句式" % (j * 100))

    # 7. 标题
    h1 = next((t for lv, t, _ in secs if lv == 1), None)
    if not h1:
        block("缺少一级标题（应等于原标题）")

    return issues


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("md")
    ap.add_argument("--type", default="article", choices=["article", "koubo", "brand"])
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--sub", default="img", choices=["img", "video"])
    a = ap.parse_args()

    try:
        md = open(a.md, encoding="utf-8").read()
    except Exception as e:
        print(json.dumps({"ok": False, "error": str(e)}, ensure_ascii=False))
        return 2

    issues = check(md, a.type, a.sub)
    blocks = [i for i in issues if i["level"] == "block"]
    warns = [i for i in issues if i["level"] == "warn"]

    if a.json:
        print(json.dumps({"ok": not blocks, "blocks": blocks, "warns": warns,
                          "issues": issues}, ensure_ascii=False, indent=1))
    else:
        print("审阅：%s（%s）" % (a.md, a.type))
        for i in issues:
            mark = {"block": "🔴", "warn": "🟡", "info": "⚪"}[i["level"]]
            print("  %s %s" % (mark, i["msg"]))
        print("结论：%s（阻塞 %d / 警告 %d）" % ("通过" if not blocks else "不通过", len(blocks), len(warns)))

    return 0 if not blocks else 1


if __name__ == "__main__":
    sys.exit(main())
