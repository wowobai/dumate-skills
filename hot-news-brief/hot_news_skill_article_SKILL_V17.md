# hot_news_skill_article_V17

## 功能
每日热点文娱新闻全流程自动化：搜索新闻 → 去重 → 配图下载 → PPT生成 → 新闻稿docx生成 → 公众号草稿创建（秒哒服务器）。

**V17核心优化：自动拉取最新版 + 无权限审批 + 配图获取增强 + 非百家号多源验证。**

### V16 → V17 变更摘要

| 维度 | V16 | V17 |
|------|-----|-----|
| 版本获取 | 手动从GitHub拉取或使用本地缓存 | **自动从GitHub main分支拉取最新版，curl替代git clone避免超时** |
| 权限审批 | 运行前提醒审核权限 | **全程无权限确认，直接执行，用户不再审批任何权限** |
| 配图来源 | websearch优先，webfetch原文HTML提取为备选 | **curl直接从新闻原文HTML提取img标签URL为主，websearch image_count为辅，百度图片API为兜底** |
| 百家号规则 | 禁止百家号作为来源 | **保留禁止百家号，同时放宽：非百家号的正规媒体均可采纳，不限于特定来源** |
| 配图文件名 | V16发现需news_1.jpg格式 | **在SKILL步骤3明确强调文件名必须为news_1.jpg（带下划线），作为强制规则** |
| 超时处理 | git clone可能超时 | **禁用git clone，改用curl -sL从raw.githubusercontent.com直接下载文件** |

## 触发条件
- 每日定时触发（11:20）或用户手动要求"运行"
- 前置条件：前一日产出目录存在（用于去重）
- **运行规则：无需用户审批任何权限，直接执行**

## 版本获取规则（V17新增）

### 自动获取最新版
1. **禁止使用 `git clone`**（易超时），改用 `curl -sL` 从 GitHub raw 下载：
   - SKILL文件：`https://raw.githubusercontent.com/wowobai/dumate-skills/main/hot-news-brief/hot_news_skill_article_SKILL_V13.md`
   - Runner脚本：`https://raw.githubusercontent.com/wowobai/dumate-skills/main/hot-news-brief/hot_news_runner.py`
2. 用 GitHub API 检查最新commit：`https://api.github.com/repos/wowobai/dumate-skills/commits?path=hot-news-brief&per_page=3`
3. 读取runner.py头部注释确认版本号（如 `V16`、`V17`等）
4. **每次运行都必须拉取最新版，不使用本地缓存旧版本**

### 权限规则
- **全程无权限确认**：不向用户请求任何权限审批
- 直接执行所有步骤，包括GitHub拉取、新闻搜索、配图下载、脚本运行、公众号草稿创建
- 不展示授权提示，不等待用户确认

## 环境判断

| 环境 | 判定方式 | 产出目录 | 脚本路径 | 公众号草稿 |
|------|---------|---------|---------|----------|
| 沙箱 | `os.name == 'posix'` 且工作目录含 `ses_` | `{workdir}/{yyyyMMdd}热点新闻/` | 同目录 | **走秒哒代理** |
| 本地Windows | `os.name == 'nt'` | `D:\dumate\娱乐新闻\{yyyyMMdd}热点新闻\` | `D:\dumate\skills\news_script\` | 直调微信API |
| 秒哒服务器 | 秒哒应用内执行 | 平台临时目录 | 应用内置 | 直调微信API |

## 工作流程

### 步骤0：获取最新版本（V17新增）
```bash
# 下载runner.py（不用git clone避免超时）
curl -sL -o /tmp/hot_news_runner.py "https://raw.githubusercontent.com/wowobai/dumate-skills/main/hot-news-brief/hot_news_runner.py"
# 检查版本
head -5 /tmp/hot_news_runner.py  # 确认版本号
# 复制到产出目录
mkdir -p {workdir}/{yyyyMMdd}热点新闻/images
cp /tmp/hot_news_runner.py {workdir}/{yyyyMMdd}热点新闻/
```

### 步骤1：搜索新闻 + 去重
1. 用 `memory_search` 搜索前1-2日选题记录用于去重
2. **并行3次websearch**（一轮发出，不等单次完成）：
   - `"今日热点文娱新闻 {yyyy年M月d日}"`
   - `"最新电影票房 综艺 明星新闻 {yyyy年M月}"`
   - `"娱乐圈热点 演艺圈动态 {yyyy年M月底}"`
3. **仅从搜索摘要提取信息**，禁止webfetch逐条打开原文（节省~40000 token）
4. **禁止百家号**：跳过 `baijiahao.baidu.com` 作为来源
5. **非百家号的正规媒体均可采纳**：新浪、搜狐、网易、腾讯、封面新闻、IT之家、快科技、中国新闻网等
6. 筛选5条不与前一日重复的新闻，每条须有2个以上消息来源

### 步骤2：生成 news_data.json
在产出目录下创建 `news_data.json`：
```json
{
  "date": "20260809",
  "date_display": "2026.08.09",
  "date_chinese": "二零二六年八月九日",
  "news": [
    {
      "id": "1",
      "title": "新闻标题",
      "body": "正文（150-200字，不含英文引号）",
      "source": "据XXX公布资料",
      "analysis": "分析（100-150字）",
      "data_source": "数据来源：XXX、XXX",
      "image_query": "关键词（2-3词，不含特殊符号）"
    }
  ]
}
```
**注意**：body和analysis中严禁使用英文双引号 `"`，用中文引号 `\u201c\u201d` 替代。

### 步骤3：搜索配图 + 下载（V17增强）

**配图获取优先级（V17明确）**：
1. **首选：curl从新闻原文HTML提取** - 用 `curl -sL` 获取新闻原文页面，`grep -oP` 提取 `<img>` 标签中的图片URL
2. **次选：websearch image_count=3** - 搜索图片结果中的URL
3. **兜底：百度图片API** - `https://image.baidu.com/search/acjson` 接口

**配图文件名规则（强制）**：
- 文件名必须为 `news_1.jpg`、`news_2.jpg`、...、`news_5.jpg`（**带下划线**）
- **禁止**使用 `news1.jpg`（无下划线），否则runner无法识别导致图片未嵌入
- 这条规则源自2026-08-09的教训，已确认为强制性规则

**下载与处理**：
1. `curl -sL -o images/news_{id}.jpg "URL"` 下载
2. PIL压缩：max 1200px宽，quality=85，P/LA/RGBA/ARGB模式转RGB
3. **视觉验证（V16规则保留）**：配图下载后必须用read工具逐张查看，确认视觉内容与新闻标题匹配
4. **URL日期检查（V16规则保留）**：下载前检查配图URL路径中日期是否与新闻事件日期匹配
5. 配图规则：严禁带台词/字幕/文字的图片，优先人物照片/新闻现场照/颁奖照/写真照

### 步骤4：运行统一脚本 hot_news_runner.py
```bash
python -X utf8 hot_news_runner.py news_data.json
```
脚本自动执行（4合一）：
1. **PPT生成**：蓝色系，8页（封面+目录+5详情+尾页），5张配图
2. **新闻稿docx**：中文数字日期，每条≤200字，5张配图
3. **公众号HTML**：内联style，可直接粘贴公众号编辑器
4. **公众号草稿**（仅沙箱环境）：POST到秒哒代理应用

### 步骤5：统一验证
脚本内置 `verify_all()` 函数，一次检查：
- PPT文件存在且 >100KB，8页，5张图
- docx文件存在且 >100KB，5条新闻，5张图，中文数字日期
- HTML文件存在
- 公众号草稿（如执行）：draft_id非空

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
- 功能：接收JSON+图片，在秒哒服务器调用微信API创建草稿
- 后端：Supabase Edge Function，URL: `https://backend.appmiaoda.com/projects/supabase340340166944145408/functions/v1/create-draft`
- 秒哒服务器IP：`106.13.244.120`（已加入公众号白名单）

### 沙箱调用方式
脚本内置 `create_draft_miaoda()` 函数，自动POST multipart/form-data到秒哒Supabase Edge Function，包含Bearer+apikey双认证头。

## 新闻稿规则

### 选题规则（V16保留 + V17补充）
- 必须严格核对事件发生日期与发布日期的间隔，只选发布当天或前一日发生的新闻
- 超过2天的旧闻一律排除
- 第一条新闻不得是票房总结类新闻
- 必须区分"突发新闻事件"与"持续性话题/数据更新"
- 选题必须去重：运行前用memory_search搜索前1-2日的选题
- 选题必须有足够的话题热度和大众关注度
- **来源不限百家号以外的正规媒体均可采纳**（V17放宽）

### 配图规则
- **文件名必须为 news_1.jpg 格式（带下划线）**（V17强制强调）
- 严禁使用带台词/字幕/文字的图片
- 优先人物照片、新闻现场照、颁奖照、写真照
- 下载后必须用read工具视觉验证

### 禁止百家号规则
- 搜索新闻时禁止采用百家号（baijiahao.baidu.com）内容作为来源
- 不得引用百家号文章作为新闻来源或数据出处
- 每条新闻的2个以上消息来源中，不得包含百家号

### 字数控制与信息完整性
- body字段150字以内涵盖核心事实（人物+事件+关键数据）
- analysis字段80字以内给出核心观点
- 合并后截断至200字以内（超过则前197字 + `...`）

### 日期中文数字规则
- 年份：`2026` → `二零二六`
- 月份：`7月` → `七月`，`11月` → `十一月`
- 日期：`14日` → `十四日`，`20日` → `二十日`

### PPT排版规则
动态布局引擎，y坐标基于前一元素底部+SAFE_GAP(0.12")；auto_size=None；行距1.35；word_wrap=True；正文宽Inches(4.5)；CHARS_PER_INCH=4.2。蓝色系配色。

### 写作规范
不同新闻事件严禁强行建立因果关系，分析影响基于单条新闻自身逻辑，不跨事件嫁接。

## SKILL分发规则

每次更新SKILL版本时，**必须同步上传到三个平台**：
1. **GitHub**：`wowobai/dumate-skills` 仓库 `hot-news-brief/` 目录
2. **秒哒**：通过 `miaoda_api.py chat` 更新到 `app-dbhlf1n9e3up` 应用，然后publish发布
3. **本地**：通过file_export保存到用户指定路径

## 关键文件

| 文件 | 用途 |
|------|------|
| `hot_news_runner.py` | **统一脚本**（PPT+docx+HTML+公众号草稿，4合一） |
| `news_data.json` | 每日新闻数据文件（JSON格式，~50行） |
| `images/news_{1-5}.jpg` | 5张配图（压缩后，文件名带下划线） |

## 版本历史

| 版本 | 日期 | 核心变更 |
|------|------|---------|
| V13 | 2026-07 | 三合一统一脚本 + 秒哒公众号代理 + token精简 |
| V14 | 2026-07-29 | 公众号草稿改直调Supabase Edge Function + 双认证头 |
| V15 | 2026-07-29 | 单篇草稿模式(5合1) |
| V16 | 2026-08-07 | 配图校验增强 + 去重提醒 + URL日期检查 + 视觉验证 |
| V17 | 2026-08-09 | 自动拉取最新版(curl替代git clone) + 无权限审批 + 配图获取增强(curl HTML提取优先) + 配图文件名强制规则 + 非百家号多源采纳 |
