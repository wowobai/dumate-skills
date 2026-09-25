# weihai_travel_skill_V2（云端化）

## 功能
每日威海旅游新闻全流程自动化：搜索新闻 → 去重 → 配图下载 → PPT生成 → 公众号HTML → 公众号草稿创建（秒哒服务器）。
**V2核心变更：由 local 模式（绑定Windows设备Bai1112）改造为 cloud 模式，电脑不开机也能运行，与 HOT_NEWS 云端架构对齐。**

### V1 → V2 变更摘要

| 维度 | V1（本地Windows） | V2（云端cloud） |
|------|-----|-----|
| 运行模式 | local，依赖设备Bai1112在线 | **cloud，云端沙箱定时触发，不依赖任何本地设备** |
| 模板引擎 | `D:\dumate\skills\weihai_travel_news\run_weihai_travel_template.py` | **`weihai_travel_runner.py`（从GitHub拉取，3合1）** |
| 环境变量 | PowerShell读Windows用户环境变量 | **环境变量缺失时从同目录 hot_news_runner.py 提取凭据（复用既有凭据载体）** |
| PPT引擎 | import `D:\dumate\skills\weihai_travel_news\gen_ppt.py` | **runner内置动态布局引擎（蓝色系 #1A56DB）** |
| 依赖安装 | 依赖本机已装包 | **runner内置ensure_dependencies()自动pip安装** |
| 产出目录 | `D:\dumate\旅游新闻\{yyyyMMdd}威海旅游\` | **`{workdir}/{yyyyMMdd}威海旅游/`（云端工作目录）** |
| 邮件 | SMTP 163必发 | **有SMTP授权码才发（缺失跳过，不阻塞草稿）** |
| 草稿标题 | 固定"威海旅游新闻"（main_title） | **不变：固定"威海旅游新闻"（main_title），严禁混用其他主题标题** |
| 配图 | 百度acjson降级链 | **websearch image_count=5优先 + PIL预筛 + curl HTML备选** |

## 触发条件
- 每日定时触发（18:00，cloud模式）或用户手动要求"运行"
- 前置条件：前一日产出目录存在（用于去重）
- **运行规则：无需用户审批任何权限，直接执行**

## 版本获取规则

### 自动获取最新版
1. **禁止使用 `git clone`**（易超时），改用 `curl -sL` 从 GitHub raw 下载
2. **动态获取最新SKILL文件名**：
   ```bash
   curl -sL "https://api.github.com/repos/wowobai/dumate-skills/contents/weihai-travel-brief" | \
     python3 -c "import json,sys; files=[f['name'] for f in json.load(sys.stdin) if f['name'].startswith('weihai_travel_skill_SKILL_V')]; files.sort(); print(files[-1])"
   ```
3. Runner脚本固定文件名：`weihai_travel_runner.py`
4. 用 GitHub API 检查最新commit：`https://api.github.com/repos/wowobai/dumate-skills/commits?path=weihai-travel-brief&per_page=3`
5. 读取runner.py头部注释确认版本号
6. **每次运行都必须拉取最新版，不使用本地缓存旧版本**

### 权限规则
- **全程无权限确认**：不向用户请求任何权限审批
- 直接执行所有步骤：GitHub拉取、新闻搜索、配图下载、脚本运行、公众号草稿创建
- 不展示授权提示，不等待用户确认

## 环境判断

| 环境 | 判定方式 | 产出目录 | 公众号草稿 |
|------|---------|---------|----------|
| 沙箱 | `os.name == 'posix'` 且工作目录含 `ses_` | `{workdir}/{yyyyMMdd}威海旅游/` | **走秒哒代理** |
| 其他环境 | 未适配 | - | 跳过草稿 |

## 工作流程

### 步骤0：获取最新版本
```bash
LATEST_SKILL=$(curl -sL "https://api.github.com/repos/wowobai/dumate-skills/contents/weihai-travel-brief" | \
  python3 -c "import json,sys; files=[f['name'] for f in json.load(sys.stdin) if f['name'].startswith('weihai_travel_skill_SKILL_V')]; files.sort(); print(files[-1])")

mkdir -p {workdir}/{yyyyMMdd}威海旅游/images
curl -sL --connect-timeout 15 --max-time 30 -o {workdir}/{yyyyMMdd}威海旅游/weihai_travel_runner.py "https://raw.githubusercontent.com/wowobai/dumate-skills/main/weihai-travel-brief/weihai_travel_runner.py"
curl -sL --connect-timeout 15 --max-time 30 -o /tmp/${LATEST_SKILL} "https://raw.githubusercontent.com/wowobai/dumate-skills/main/weihai-travel-brief/${LATEST_SKILL}"

# 关键：同时下载 hot_news_runner.py 到产出目录，作为公众号凭据载体（runner运行时会从其中提取WX/SUPABASE凭据）
curl -sL --connect-timeout 15 --max-time 30 -o {workdir}/{yyyyMMdd}威海旅游/hot_news_runner.py "https://raw.githubusercontent.com/wowobai/dumate-skills/main/hot-news-brief/hot_news_runner.py"

head -5 {workdir}/{yyyyMMdd}威海旅游/weihai_travel_runner.py  # 确认版本号
```
**注意**：runner.py 内置 `ensure_dependencies()`，启动时自动安装缺失的Python依赖包。公众号凭据读取顺序：环境变量 → 同目录 hot_news_runner.py 源码提取（步骤0已下载，无需手动配置）；hot_news_runner.py 仅作凭据载体，不会被运行。

### 步骤1：搜索新闻 + 去重
1. 用 `memory_search` 搜索前1-2日选题记录用于去重
2. **并行5次websearch**（一轮发出，不等单次完成）：
   - `"威海 旅游 新闻 {yyyy年M月}"`
   - `"威海 文旅 景区 活动 {yyyy年M月}"`
   - `"威海 文旅局 政策 出行 {yyyy年M月}"`
   - `"威海 入境游 航线 高铁 {yyyy年M月}"`
   - `"山东 文旅 涉及威海 {yyyy年M月}"`
3. **仅从搜索摘要提取信息**，禁止webfetch逐条打开原文（节省token）
4. **信息源红线（L1优先）**：
   - L1：威海新闻网、威海日报、威海广播电视台、Hi威海客户端、文旅威海等官方本地媒体
   - L2：山东省文旅厅官网、山东文旅官方账号
   - L3：央视新闻/新华社/文旅部等全国权威
   - L4：新浪/网易/澎湃等主流媒体
   - **黑名单：百家号（baijiahao.baidu.com）一律禁止**
5. **新闻选材**：威海本地旅游新闻为主（至少3条威海本地/直接相关），可含山东或其他涉及威海游客/航线的动态；优先景区活动、文旅政策、旅游数据、交通出行、文旅项目、入境游、节庆活动
6. 筛选5条不与前一日重复的新闻，每条须有2个以上消息来源；无法验证的标"待确认"

### 步骤2：生成 news_data.json
在产出目录下创建 `news_data.json`：
```json
{
  "date": "20260925",
  "date_display": "2026.09.25",
  "news": [
    {
      "id": "1",
      "tag": "景区活动",
      "title": "新闻标题（完整陈述核心事实）",
      "summary": "正文梗概（150-200字，涵盖谁做了什么+关键数字+关键动作）",
      "impact": "旅程看点/影响分析（100-150字，基于单条新闻自身逻辑）",
      "source": "威海新闻网/威海日报",
      "img_keyword": "关键词（2-3词，从正文提取具体事件/景点名）",
      "kpi1": "▲ 关键指标1",
      "kpi2": "▲ 关键指标2"
    }
  ]
}
```
**注意**：summary和impact中严禁使用英文双引号 `"`，用中文引号 `\u201c\u201d` 替代。

### 步骤3：搜索配图 + 下载
**配图获取优先级**：
1. **首选：websearch image_count=5** - 用新闻关键词搜索图片
2. **次选：curl从新闻原文HTML提取**（过滤logo/icon/avatar/business/transform/kandian/w180h180等URL）
3. **兜底：百度图片API** `https://image.baidu.com/search/acjson`

**配图文件名规则（强制）**：`news_1.jpg` ~ `news_5.jpg`（带下划线）。

**下载与处理**：
1. `curl -sL -o images/news_{id}.jpg "URL"`
2. **PIL程序化预筛**：min_dim<200 或 文件<10KB 则丢弃换源
3. PIL压缩：max 1200px宽，quality=85，P/LA/RGBA/ARGB转RGB
4. **视觉验证**：压缩后用read工具逐张查看，确认与新闻标题匹配；严禁带台词/字幕/文字图片

### 步骤4：运行统一脚本 weihai_travel_runner.py
```bash
python -X utf8 weihai_travel_runner.py news_data.json
```
脚本自动执行（3合1）：
1. **自动依赖安装**：requests/Pillow/python-pptx
2. **PPT生成**：蓝色系（#1A56DB），8页（封面+目录+5详情+尾页），5张配图，文件名 `威海旅游新闻热点TOP5.pptx`
3. **公众号HTML**：蓝色系主题，文件名 `wechat_article.html`
4. **公众号草稿**（仅沙箱环境）：POST到秒哒Supabase Edge Function，payload带 `main_title:"威海旅游新闻"`
5. **验证**：内置verify_all()检查所有产出（PPT>100KB/8页/5图、HTML存在、draft_id非空）

### 步骤5：统一验证
- PPT文件存在且 >100KB，8页，5张图
- HTML文件存在
- 公众号草稿（如执行）：draft_id非空、标题含「威海旅游新闻」
- 配图一致性：每次运行必须用 read 工具逐张查看 images/news_{1-5}.jpg，确认视觉内容与新闻标题匹配

## 公众号草稿 - 秒哒代理方案

### 架构
```
沙箱(DuMate) ──POST news_data.json + 5张图──> 秒哒应用(固定IP) ──> 微信API
                                                          <──draft_id──
```

### 秒哒应用信息
- 应用名：公众号草稿自动创建工具
- appId：`app-dbhlf1n9e3up`
- 线上URL：`https://app-dbhlf1n9e3up.appmiaoda.com`
- 后端：Supabase Edge Function，URL: `https://backend.appmiaoda.com/projects/supabase340340166944145408/functions/v1/create-draft`
- 秒哒服务器IP：`106.13.244.120`（已加入公众号白名单）
- **草稿标题固定规则**：payload中 `main_title:"威海旅游新闻"`，秒哒函数生成标题 `{date_chinese||date_display} 威海旅游新闻`
- **严禁**出现"热点社会新闻"/"热点文娱新闻"字样——不同主题任务标题不得混用

### 沙箱调用方式
脚本内置 `gen_wechat_draft()` 函数，自动POST multipart/form-data到秒哒Supabase Edge Function，包含Bearer+apikey双认证头。凭据优先从环境变量读取，缺失时从同目录 hot_news_runner.py 源码提取（复用既有凭据载体，不硬编码入新文件）。

## 选题规则（威海旅游）
- 威海本地旅游为主（至少3条本地/直接相关），聚焦：景区活动、文旅政策、旅游数据、交通出行、文旅项目、入境游、节庆活动
- 只选发布当天或前一日发生的新闻，超过2天的旧闻一律排除；须区分"突发新闻事件"与"持续性话题/数据更新"
- 固定5条新闻，不多不少
- 去重：运行前用memory_search搜索前1-2日选题；本地用前一日 `{前一日}威海旅游/news_data.json` 比对
- 来源须2个以上；严禁百家号

## 写作规范
- summary完整陈述核心事实（谁做了什么+关键数字+关键动作），150-200字
- impact基于单条新闻自身逻辑，100-150字旅程看点，不跨事件嫁接因果关系
- body/analysis中严禁英文双引号，用中文引号

## 文件分发规则
每次更新SKILL版本时，**必须**同步上传：
1. **GitHub**：`wowobai/dumate-skills` 仓库 `weihai-travel-brief/` 目录（SKILL + runner）
2. **本地**：通过file_export保存到用户指定路径

## 关键文件

| 文件 | 用途 |
|------|------|
| `weihai_travel_runner.py` | **统一脚本**（PPT+HTML+公众号草稿，3合1，含自动依赖安装） |
| `news_data.json` | 每日新闻数据文件（JSON格式） |
| `images/news_{1-5}.jpg` | 5张配图（压缩后，文件名带下划线） |

## 版本历史

| 版本 | 日期 | 核心变更 |
|------|------|---------|
| V1 | 2026-09-16 | 初始版本：local模式，依赖Windows设备Bai1112，模板引擎+gen_ppt.py，邮件必发 |
| V2 | 2026-09-25 | **云端化改造**：cloud模式定时触发（电脑不开机也能运行）；runner自包含（3合1，内置依赖安装与动态布局引擎）；凭据复用hot_news_runner.py载体；邮件降级为可选；配图优先websearch+PIL预筛；草稿标题仍固定"威海旅游新闻" |

## 依据
本SKILL V2 对齐 HOT_NEWS V18 云端架构（自动版本拉取、秒哒草稿链路、依赖自安装、PIL配图预筛），保留 weihai_travel_news V1 的信息源红线与草稿标题固定规则。公众号凭据来源见 hot-news-brief/hot_news_runner.py。
