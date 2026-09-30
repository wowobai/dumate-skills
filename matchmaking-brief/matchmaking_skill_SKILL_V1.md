# matchmaking_skill_V1（威海红娘新闻·婚介资讯·云端化）

## 功能
每日婚介/婚恋/相亲领域资讯全流程自动化：搜索新闻 → 去重 → 配图下载 → 公众号HTML → 公众号草稿创建（秒哒服务器）。
仿照 weihai_travel_skill_V2（威海旅游新闻）云端架构，**不生成PPT**，只产出公众号HTML与草稿。
**核心定位：以威海本地相亲/婚介资讯为主体、婚恋行业宏观动态为头条的每日资讯聚合，面向公众号发布。**
**草稿标题恒为「{date_chinese} 威海红娘新闻」**（main_title 固定"威海红娘新闻"）。

## 触发条件
- 每日定时触发（**08:00**，cloud模式）或用户手动要求"运行"
- 前置条件：前一日产出目录存在（用于去重）
- **运行规则：无需用户审批任何权限，直接执行**

## 选题结构（固定5条，强制顺序）

| 位置 | 要求 |
|------|------|
| 第1条（头条） | **宏观类资讯，尽量有数据支撑**（tag建议：宏观动态/行业观察）：如民政部婚姻登记数据、全国结婚率/初婚年龄/婚介市场规模、婚介行业监管政策、婚俗改革新规、彩礼治理等 |
| 第2-4条 | **尽量贴近威海相亲相关资讯**（tag建议：威海相亲/相亲故事/婚介所动态/婚姻趣闻）：威海本地相亲活动、青年联谊、婚介机构运营动态、婚姻家庭趣事；**若威海本地资讯不足，可选用其他省份的相亲新闻或趣味资讯兜底** |
| 第5条（最后一条） | **威海婚介所相关新闻优先**（如威海本地婚介机构动态、红娘服务、婚介所活动）；**如无婚介所资讯，则选威海相亲相关新闻**（tag固定：威海婚介所/威海相亲） |

**严禁改变顺序**：宏观头条必须在第1条，威海本地（婚介所优先）新闻必须在最后一条。中间3条可调顺序但不越位。

## 版本获取规则

### 自动获取最新版
1. **禁止使用 `git clone`**（易超时），改用 `curl -sL` 从 GitHub raw 下载
2. **动态获取最新SKILL文件名**：
   ```bash
   curl -sL "https://api.github.com/repos/wowobai/dumate-skills/contents/matchmaking-brief" | \
     python3 -c "import json,sys; files=[f['name'] for f in json.load(sys.stdin) if f['name'].startswith('matchmaking_skill_SKILL_V')]; files.sort(); print(files[-1])"
   ```
3. Runner脚本固定文件名：`matchmaking_runner.py`
4. 用 GitHub API 检查最新commit：`https://api.github.com/repos/wowobai/dumate-skills/commits?path=matchmaking-brief&per_page=3`
5. 读取runner.py头部注释确认版本号
6. **每次运行都必须拉取最新版，不使用本地缓存旧版本**

### 权限规则
- **全程无权限确认**：不向用户请求任何权限审批
- 直接执行所有步骤：GitHub拉取、新闻搜索、配图下载、脚本运行、公众号草稿创建
- 不展示授权提示，不等待用户确认

## 环境判断

| 环境 | 判定方式 | 产出目录 | 公众号草稿 |
|------|---------|---------|----------|
| 沙箱 | `os.name == 'posix'` 且工作目录含 `ses_` | `{workdir}/{yyyyMMdd}威海红娘新闻/` | **走秒哒代理** |
| 其他环境 | 未适配 | - | 跳过草稿 |

## 工作流程

### 步骤0：获取最新版本
```bash
LATEST_SKILL=$(curl -sL "https://api.github.com/repos/wowobai/dumate-skills/contents/matchmaking-brief" | \
  python3 -c "import json,sys; files=[f['name'] for f in json.load(sys.stdin) if f['name'].startswith('matchmaking_skill_SKILL_V')]; files.sort(); print(files[-1])")

mkdir -p {workdir}/{yyyyMMdd}威海红娘新闻/images
curl -sL --connect-timeout 15 --max-time 30 -o {workdir}/{yyyyMMdd}威海红娘新闻/matchmaking_runner.py "https://raw.githubusercontent.com/wowobai/dumate-skills/main/matchmaking-brief/matchmaking_runner.py"
curl -sL --connect-timeout 15 --max-time 30 -o /tmp/${LATEST_SKILL} "https://raw.githubusercontent.com/wowobai/dumate-skills/main/matchmaking-brief/${LATEST_SKILL}"

# 关键：同时下载 hot_news_runner.py 到产出目录，作为公众号凭据载体（runner运行时会从其中提取WX/SUPABASE凭据）
curl -sL --connect-timeout 15 --max-time 30 -o {workdir}/{yyyyMMdd}威海红娘新闻/hot_news_runner.py "https://raw.githubusercontent.com/wowobai/dumate-skills/main/hot-news-brief/hot_news_runner.py"

head -5 {workdir}/{yyyyMMdd}威海红娘新闻/matchmaking_runner.py  # 确认版本号
```
**注意**：runner.py 内置 `ensure_dependencies()`，启动时自动安装缺失的Python依赖包。公众号凭据读取顺序：环境变量 → 同目录 hot_news_runner.py 源码提取（步骤0已下载，无需手动配置）；hot_news_runner.py 仅作凭据载体，不会被运行。

### 步骤1：搜索新闻 + 去重
1. 用 `memory_search` 搜索前1-2日选题记录用于去重
2. **并行5次websearch**（一轮发出，不等单次完成）：
   - `"婚恋 婚姻登记 数据 政策 {yyyy年M月}"`（头条宏观，找有数据支撑的资讯）
   - `"威海 相亲 青年联谊 婚恋 {yyyy年M月}"`（2-4条威海相亲优先）
   - `"威海 婚介所 红娘 婚介机构 {yyyy年M月}"`（第5条威海婚介所优先）
   - `"相亲 婚恋 趣事 新闻 {yyyy年M月}"`（外省相亲资讯/趣事兜底）
   - `"婚介 行业 整治 婚托 规范 {yyyy年M月}"`（行业动态补充）
3. **仅从搜索摘要提取信息**，禁止webfetch逐条打开原文（节省token）
4. **信息源红线（L1优先）**：
   - L1：民政部官网、全国婚恋婚介官方机构、威海本地官方媒体（威海新闻网、威海日报、Hi威海客户端等）
   - L2：省市民政/妇联/共青团官方账号
   - L3：央视新闻/新华社/人民日报等全国权威
   - L4：新浪/网易/澎湃等主流媒体
   - **黑名单：百家号（baijiahao.baidu.com）一律禁止**
5. **新闻选材**：按"选题结构"固定5条——第1条宏观头条（有数据支撑），第2-4条威海相亲优先（外省兜底），第5条威海婚介所优先（无则威海相亲）
6. 筛选5条不与前一日重复的新闻，每条须有2个以上消息来源；无法验证的标"待确认"

### 步骤2：生成 news_data.json
在产出目录下创建 `news_data.json`：
```json
{
  "date": "20260930",
  "date_display": "2026.09.30",
  "news": [
    {
      "id": "1",
      "tag": "宏观动态",
      "title": "新闻标题（第1条须为宏观类资讯，尽量含数据支撑，如全国结婚登记/初婚年龄等）",
      "summary": "正文梗概（150-200字，涵盖谁做了什么+关键数字+关键动作）",
      "impact": "影响分析（100-150字，基于单条新闻自身逻辑）",
      "source": "民政部官网/人民日报",
      "img_keyword": "关键词（2-3词，从正文提取具体事件/机构名）",
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

### 步骤4：运行统一脚本 matchmaking_runner.py
```bash
python -X utf8 matchmaking_runner.py news_data.json
```
脚本自动执行（2合1，**无PPT**）：
1. **自动依赖安装**：requests/Pillow
2. **公众号HTML**：蓝色系主题，文件名 `wechat_article.html`
3. **公众号草稿**（仅沙箱环境）：POST到秒哒Supabase Edge Function，payload带 `main_title:"威海红娘新闻"`
4. **验证**：内置verify_all()检查所有产出（HTML存在、draft_id非空）

### 步骤5：统一验证
- HTML文件存在
- 公众号草稿（如执行）：draft_id非空、标题含「威海红娘新闻」
- 选题结构校验：news[0]为宏观头条（有数据支撑）、news[-1]为威海（婚介所优先/相亲兜底）
- 配图一致性：每次运行必须用 read 工具逐张查看 images/news_{1-5}.jpg，确认视觉内容与新闻标题匹配

## 公众号草稿 - 秒哒代理方案

### 架构
```
沙箱(DuMate) ──POST news_data.json + 5张图──> 秒哒应用(固定IP) ──> 微信API
                                                          <──draft_id──
```

### 秒哒应用信息
- 应用名：公众号草稿自动创建工具
- 后端：Supabase Edge Function，URL: `https://backend.appmiaoda.com/projects/supabase340340166944145408/functions/v1/create-draft`
- 秒哒服务器IP：`106.13.244.120`（已加入公众号白名单）
- **草稿标题固定规则**：payload中 `main_title:"威海红娘新闻"`，秒哒函数生成标题 `{date_chinese||date_display} 威海红娘新闻`
- **严禁**出现"威海旅游新闻"/"热点社会新闻"/"婚介资讯"等字样——标题恒为「*年*月*日威海红娘新闻」，不同主题任务标题不得混用

### 沙箱调用方式
脚本内置 `gen_wechat_draft()` 函数，自动POST multipart/form-data到秒哒Supabase Edge Function，包含Bearer+apikey双认证头。凭据优先从环境变量读取，缺失时从同目录 hot_news_runner.py 源码提取（复用既有凭据载体，不硬编码入新文件）。

## 信息源红线（婚介领域）
- 婚介政策类：民政部官网、全国人大/国务院官网、地方民政部门官微（L1/L2优先）
- 婚介行业类：婚介行业协会、主流媒体深度报道
- 威海本地类：威海新闻网、威海日报、Hi威海客户端、威海广播电视台
- **黑名单：百家号（baijiahao.baidu.com）一律禁止**
- 每条新闻须2个以上消息来源

## 写作规范
- summary完整陈述核心事实（谁做了什么+关键数字+关键动作），150-200字
- impact基于单条新闻自身逻辑，100-150字影响分析，不跨事件嫁接因果关系
- body/analysis中严禁英文双引号，用中文引号
- 第1条宏观头条的summary应突出数据（如登记对数、结婚率、市场规模、同比增长）与政策/事件要点
- 2-4条威海相亲资讯应突出本地信息（时间/地点/主办方）；外省资讯兜底时保持相亲/婚恋主题相关
- 第5条威海婚介所新闻应突出机构名称/活动/服务内容；无婚介所资讯时选威海相亲新闻兜底

## 文件分发规则
每次更新SKILL版本时，**必须**同步上传：
1. **GitHub**：`wowobai/dumate-skills` 仓库 `matchmaking-brief/` 目录（SKILL + runner）
2. **本地**：通过file_export保存到用户指定路径

## 关键文件

| 文件 | 用途 |
|------|------|
| `matchmaking_runner.py` | **统一脚本**（HTML+公众号草稿，2合1，无PPT，含自动依赖安装） |
| `news_data.json` | 每日新闻数据文件（JSON格式） |
| `images/news_{1-5}.jpg` | 5张配图（压缩后，文件名带下划线） |

## 版本历史

| 版本 | 日期 | 核心变更 |
|------|------|---------|
| V1 | 2026-09-30 | 初始版本：仿照 weihai_travel_skill_V2 云端架构；无PPT，仅公众号HTML+草稿；选题结构固定（第1条宏观头条有数据支撑、2-4条威海相亲优先外省兜底、第5条威海婚介所优先无则威海相亲）；草稿标题恒为「*年*月*日威海红娘新闻」；每日08:00定时触发 |

## 依据
本SKILL V1 对齐 weihai_travel_skill_V2 / HOT_NEWS 云端架构（自动版本拉取、秒哒草稿链路、依赖自安装、PIL配图预筛），按婚介领域定制选题结构与信息源红线。公众号凭据来源见 hot-news-brief/hot_news_runner.py。