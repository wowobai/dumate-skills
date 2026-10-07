# hot_news_skill_article_V20

## 功能
每日热点文娱新闻全流程自动化：搜索新闻 → 去重 → 配图下载 → PPT生成 → 新闻稿docx生成 → 公众号草稿创建（秒哒服务器）。

**V19核心优化：三条硬性选题规则固化 — 同事件合并单条报道 + 头条40岁以下明星 + 末条文娱行业新闻（不含票房）。**
**V20核心优化：运行成本记录与效率复盘强制闭环 — 每次运行必须记录积分快照与token统计、运行结束写成本复盘、沉淀更高效率方法与浪费token教训；下载路径统一为GitHub API、新增版本自检、补齐错误复盘闭环（对齐威海旅游V3）。**

### V19 → V20 变更摘要

| 维度 | V19 | V20 |
|------|-----|-----|
| 成本可见性 | 无成本记录，消耗不可查 | **运行前记录积分快照（余额）+ 运行后记录token统计/耗时；产出目录写 cost_report.md（运行成本复盘文档）** |
| 效率复盘 | 无 | **每次运行结束强制复盘：①发现更高效率的方法→写入SKILL经验库；②复盘浪费token的错误做法→定改进方案；③成本与教训沉淀入 cost_report.md** |
| 下载路径 | SKILL用GitHub API，runner仍用raw易超时 | **runner也改用GitHub API base64下载，raw仅注释保留** |
| 版本同步 | SKILL与runner版本漂移无自检 | **新增版本自检：下载后核对SKILL文件名版本与runner头注释版本，不一致必须记录并注明执行基线** |
| 错误闭环 | 仅有"一次成功运行设计"，无纠错回流 | **补齐"错误复盘与Skill自我改进"强制闭环（四层根因分析+防复发），对齐威海旅游V3** |

### V18 → V19 变更摘要

| 维度 | V18 | V19 |
|------|-----|-----|
| 同事件报道 | 可能因人物/视角不同拆分成多条新闻 | **同一事件的新闻不管涉及多少人物和视角，必须集中为一条新闻，禁止拆分多条** |
| 头条要求 | 仅要求非票房总结类新闻 | **头条必须是40岁以下明星的热点新闻** |
| 末条要求 | 无行业规则 | **末条必须是文娱行业相关的新闻（公司/平台/行业动态），且不含票房信息** |
| 规则执行 | 依赖执行者自觉 | **搜索新闻后、生成news_data.json前必须逐条对照校验三条规则** |

## 触发条件
- 每日定时触发（11:20）或用户手动要求"运行"
- 前置条件：前一日产出目录存在（用于去重）
- **运行规则：无需用户审批任何权限，直接执行**

## 版本获取规则

### 自动获取最新版
1. **禁止使用 `git clone`**（易超时），改用 `curl -sL` 从 GitHub API 下载（raw.githubusercontent.com 可能超时，优先用 API 的 base64 content）
2. **动态获取最新SKILL文件名**（V18修复，不再硬编码V13）：
   ```bash
   # 用GitHub API列出目录，自动找最高版本号的SKILL文件
   curl -sL "https://api.github.com/repos/wowobai/dumate-skills/contents/hot-news-brief" | \
     python3 -c "import json,sys; files=[f['name'] for f in json.load(sys.stdin) if f['name'].startswith('hot_news_skill_article_SKILL_V')]; files.sort(); print(files[-1])"
   ```
   得到最新文件名后，用 GitHub API（非 raw.githubusercontent.com）下载 base64 content 并解码保存
3. Runner脚本固定文件名：`hot_news_runner.py`
4. 用 GitHub API 检查最新commit：`https://api.github.com/repos/wowobai/dumate-skills/commits?path=hot-news-brief&per_page=3`
5. 读取runner.py头部注释确认版本号（如 `V17`、`V18`等）
6. **每次运行都必须拉取最新版，不使用本地缓存旧版本**

### 权限规则
- **全程无权限确认**：不向用户请求任何权限审批
- 直接执行所有步骤，包括GitHub拉取、新闻搜索、配图下载、脚本运行、公众号草稿创建
- 不展示授权提示，不等待用户确认

## 当前用户偏好（强制保留）

- 浅色主题 PPT
- 双源交叉验证（两个以上网站或官方来源）
- 单源新闻不采用
- 推荐职位真实性验证（如适用）

## 环境判断

| 环境 | 判定方式 | 产出目录 | 脚本路径 | 公众号草稿 |
|------|---------|---------|---------|----------|
| 沙箱 | `os.name == 'posix'` 且工作目录含 `ses_` | `{workdir}/{yyyyMMdd}热点新闻/` | 同目录 | **走秒哒代理** |
| 本地Windows | `os.name == 'nt'` | `D:\dumate\娱乐新闻\{yyyyMMdd}热点新闻\` | `D:\dumate\skills\news_script\` | 直调微信API |
| 秒哒服务器 | 秒哒应用内执行 | 平台临时目录 | 应用内置 | 直调微信API |

## 一次成功运行设计原则（V18新增，V19沿用）

本SKILL的设计目标是在云端沙箱环境中**一次成功运行**，不需要人工介入或重试。为实现这一目标：

1. **依赖零手动安装**：runner.py启动时自动检测并安装缺失的Python包（requests/Pillow/python-pptx/python-docx）
2. **配图高成功率**：websearch图片搜索作为主要配图来源（成功率约80%），curl HTML提取仅作为备选
3. **配图程序化预筛**：下载后先用PIL检查尺寸和宽高比，自动过滤logo/截图/小缩略图，减少视觉验证失败率
4. **失败时保留文件**：runner仅在验证通过时清理散落文件，失败时保留所有文件供调试

## 工作流程

### 步骤0：获取最新版本
```bash
# 1. 动态获取最新SKILL文件名（V18修复，不再硬编码V13）
LATEST_SKILL=$(curl -sL "https://api.github.com/repos/wowobai/dumate-skills/contents/hot-news-brief" | \
  python3 -c "import json,sys; files=[f['name'] for f in json.load(sys.stdin) if f['name'].startswith('hot_news_skill_article_SKILL_V')]; files.sort(); print(files[-1])")

# 2. 下载SKILL和runner（用GitHub API base64方式，raw可能超时）
curl -sL --connect-timeout 15 --max-time 30 "https://api.github.com/repos/wowobai/dumate-skills/contents/hot-news-brief/${LATEST_SKILL}" | \
  python3 -c "import json,sys,base64; d=json.load(sys.stdin); open('/tmp/'+d['name'],'w').write(base64.b64decode(d['content']).decode('utf-8'))"
# 3. 下载runner（V20：统一GitHub API base64，raw易超时已废弃；obj=runner, ref=main）
curl -sL --connect-timeout 15 --max-time 30 "https://api.github.com/repos/wowobai/dumate-skills/contents/hot-news-brief/hot_news_runner.py?ref=main" |   python3 -c "import json,sys,base64; d=json.load(sys.stdin); open('/tmp/hot_news_runner.py','w').write(base64.b64decode(d['content']).decode('utf-8'))"

# 4. 版本自检(V20新增)：SKILL文件名版本 vs runner头注释版本
head -5 /tmp/hot_news_runner.py  # 确认版本号，如与SKILL版本不一致须记录并注明执行基线

# 5. 创建产出目录并复制
mkdir -p {workdir}/{yyyyMMdd}热点新闻/images
cp /tmp/hot_news_runner.py {workdir}/{yyyyMMdd}热点新闻/
cp /tmp/${LATEST_SKILL} {workdir}/{yyyyMMdd}热点新闻/
```

**注意**：runner.py V17+ 内置 `ensure_dependencies()` 函数，启动时自动安装缺失的Python依赖包，无需手动pip install。

### 步骤0.5：运行成本记录（V20新增，强制）
**每次运行前必须执行，禁止跳过：**
1. 记录运行前积分快照：`console.bce.baidu.com/api/dumate/points/overview` 的当前余额（或运行前最近一次已知余额）；**仅此一次调用积分接口，运行中不得反复查询**
2. 记录启动时间与SKILL版本号（${LATEST_SKILL}）
3. 将以上信息写入产出目录 `cost_report.md`（若产出目录尚未创建则先创建）

### 步骤6：运行成本复盘与效率改进（V20新增，强制）

**运行结束后（验证产出时一并执行），在产出目录 `cost_report.md` 追加以下内容并随交付提交：**

1. **成本快照**：运行前余额 → 运行后余额（或本次消耗的估算积分），差值即本次运行成本
2. **token 统计**：本次运行的主要步骤耗时与大致 token 消耗（搜索/配图/生成/验证各环节），能取到准确值用准确值，取不到写估算值并标注
3. **效率经验**：本次运行中发现的更高效率做法（如某类搜索词更快命中、某来源配图质量更高），**必须**写入 SKILL「经验沉淀」区或本文件的改进建议，供下次运行参考
4. **浪费复盘**：本次运行中浪费 token 的错误做法（重复搜索、无效验证、超时重试、上下文重复注入等），逐条记录现象与根因，制定改进方案
5. **改进落地**：改进方案直接写入 SKILL（版本+1 按「错误复盘与Skill自我改进」流程执行）或登记为待下版落实项

**成本核算不阻塞产出交付，但必须记录；连续两次运行不写 cost_report.md 视为流程违规。**

### 步骤1：搜索新闻 + 去重 + 三条硬性选题规则（V19强化）

**三条硬性选题规则（V19固化，必须全部满足，逐条校验）：**

1. **同事件合并规则**：同一事件的新闻，不管涉及多少人物和视角，都必须集中在一条新闻里报道，**严禁**按人物/视角拆分成若干条新闻。例如某晚会被多位明星吐槽的争议事件，只能作为一条新闻，不得拆成"XXX回应""YYY吐槽""ZZZ发声"多条。
2. **头条规则**：第一条新闻（头条）必须是**40岁以下明星**的热点新闻（指明星本人年龄在40岁以下，包括但不限于90后、00后艺人）。
3. **末条规则**：最后一条新闻（第5条）必须是**文娱行业相关新闻**——即关于娱乐公司、平台、产业、行业政策、从业人员生态等行业层面动态，**不得是票房相关**的信息（票房数据、票房预测、票房排名等一律排除）。

搜索流程：
1. 用 `memory_search` 搜索前1-2日选题记录用于去重
2. **并行5次websearch**（一轮发出，不等单次完成）：
   - `"今日热点文娱新闻 {yyyy年M月d日}"`
   - `"最新电影票房 综艺 明星新闻 {yyyy年M月}"`
   - `"娱乐圈热点 演艺圈动态 {yyyy年M月d日}"`
   - `"微博热搜 娱乐 {yyyy年M月d日}"`（V18新增，补充微博热点）
   - `"{昨日具体热点事件} 最新进展 {yyyy年M月d日}"`（V18新增，追踪延续性新闻）
3. **仅从搜索摘要提取信息**，禁止webfetch逐条打开原文（节省~40000 token）
4. **禁止百家号**：跳过 `baijiahao.baidu.com` 作为来源
5. **非百家号的正规媒体均可采纳**：新浪、搜狐、网易、腾讯、封面新闻、IT之家、快科技、中国新闻网等
6. 筛选5条不与前一日重复的新闻，每条须有2个以上消息来源
7. **筛选后必须执行V19三条规则校验**：①确认无拆分同一事件的重复报道；②头条明星年龄<40岁；③末条为行业新闻且不含票房信息。不满足则重新筛选直至满足

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
**注意**：body和analysis中严禁使用英文双引号 `"`，用中文引号 `“”` 替代。

### 步骤3：搜索配图 + 下载（V18重构）

**配图获取优先级（V18重构）**：
1. **首选：websearch image_count=5** - 用新闻关键词搜索图片，从返回结果中挑选合适的图片URL
   - 优点：返回的图片已经过搜索引擎筛选，是实际新闻照片的概率高（约80%）
   - 操作：`websearch(query="{新闻关键词}", image_count=5)` 获取图片URL列表
2. **次选：curl从新闻原文HTML提取** - 用 `curl -sL` 获取新闻原文页面，`grep -oP` 提取 `<img>` 标签中的图片URL
   - 适用场景：websearch无图片结果或图片不匹配时
   - 注意：需过滤掉 logo、icon、avatar、business/transform 等非新闻图片URL
3. **兜底：百度图片API** - `https://image.baidu.com/search/acjson` 接口

**配图文件名规则（强制）**：
- 文件名必须为 `news_1.jpg`、`news_2.jpg`、...、`news_5.jpg`（**带下划线**）
- **禁止**使用 `news1.jpg`（无下划线），否则runner无法识别导致图片未嵌入

**配图URL过滤规则（V18新增，程序化预筛）**：
下载前检查URL，以下URL模式直接跳过（不是新闻照片）：
- 包含 `logo`、`icon`、`avatar`、`favicon` 的URL
- 包含 `business/transform` 的URL（新浪通用缩略图）
- 包含 `w180h180`、`w200h200`、`w85h85` 等极小尺寸标记的URL
- 包含 `kandian` 的URL（新浪看点logo）
- 文件扩展名为 `.png` 且URL含 `default` 的URL

**下载与处理**：
1. `curl -sL -o images/news_{id}.jpg "URL"` 下载
2. **PIL程序化预筛（V18新增）**：下载后立即用PIL检查，不满足条件的直接丢弃换源：
   ```python
   from PIL import Image
   img = Image.open(path)
   w, h = img.size
   min_dim = min(w, h)
   # 拒绝条件：最小边<200px、文件<10KB（可能是logo/icon）
   if min_dim < 200 or os.path.getsize(path) < 10240:
       # 丢弃，换源重新搜索
   ```
3. PIL压缩：max 1200px宽，quality=85，P/LA/RGBA/ARGB模式转RGB
4. **视觉验证**：配图压缩后必须用read工具逐张查看，确认视觉内容与新闻标题匹配
5. **URL日期检查**：下载前检查配图URL路径中日期是否与新闻事件日期匹配
6. 配图规则：严禁带台词/字幕/文字的图片，优先人物照片/新闻现场照/颁奖照/写真照

### 步骤4：运行统一脚本 hot_news_runner.py
```bash
python -X utf8 hot_news_runner.py news_data.json
```
脚本自动执行（4合一）：
1. **自动依赖安装**（V17+）：检测并安装缺失的requests/Pillow/python-pptx/python-docx
2. **PPT生成**：蓝色系，8页（封面+目录+5详情+尾页），5张配图
3. **新闻稿docx**：中文数字日期，每条≤200字，5张配图
4. **公众号HTML**：内联style，可直接粘贴公众号编辑器
5. **公众号草稿**（仅沙箱环境）：POST到秒哒代理应用
6. **验证**：内置verify_all()检查所有产出
7. **清理**：仅在验证通过时清理散落文件（V17+改进，失败时保留供调试）

### 步骤5：统一验证
脚本内置 `verify_all()` 函数，一次检查：
- PPT文件存在且 >100KB，8页，5张图
- docx文件存在且 >100KB，5条新闻，5张图，中文数字日期
- HTML文件存在
- 公众号草稿（如执行）：draft_id非空

## 错误复盘与 Skill 自我改进（V20新增，强制闭环）

**任何一次运行发现错误（新闻数据错误、来源违规、配图不符、草稿标题错误、验证失败、成本异常等），必须执行以下闭环，禁止只修本次产物了事（对齐威海旅游V3）：**

1. **记录错误事实**：日期、受影响的条目/字段、错误现象（截图或描述）
2. **四层根因分析**（逐层排查）：
   - 流程层：SKILL 规则是否有可操作的判定标准？哪里缺失或含糊？
   - 脚本层：runner 校验是否覆盖该错误维度？
   - 来源层：配图/数据来源是否有约束漏洞（泛图替代、单源信息）？
   - 闭环层：此错误是否源自以往错误未沉淀？
3. **更新 Skill**：将防错规则写入 SKILL.md 对应步骤 + 更新 runner.py 校验逻辑（含反例入库）
4. **升级版本**：SKILL 版本号 +1（如 V19→V20），在版本历史表登记变更，**执行后必须填写成本复盘段落**
5. **推回 GitHub**：SKILL.md 与 runner.py 同步上传 `wowobai/dumate-skills` 仓库 `hot-news-brief/` 目录
6. **归档复盘**：在产出目录写复盘文档（根因分析+改进说明+预防机制），并随交付提交

**防复发要求**：
- 同一类型错误不得第二次出现（反例库机制）
- 类似/衍生错误在写规则时一并覆盖
- 每次 Skill 更新必须同步更新 runner 版本号与 SKILL 版本历史，保证远端自洽

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
- **硬性约束：公众号草稿必须包含5张配图**（该接口强制要求恰好5张图，少于5张会创建失败）

### 沙箱调用方式
脚本内置 `gen_wechat_draft()` 函数，自动POST multipart/form-data到秒哒Supabase Edge Function，包含Bearer+apikey双认证头。

## 新闻稿规则

### 选题规则（V16保留 + V17补充 + V18保留 + V19三条硬规则）
- 必须严格核对事件发生日期与发布日期的间隔，只选发布当天或前一日发生的新闻
- 超过2天的旧闻一律排除
- 第一条新闻不得是票房总结类新闻
- **第一条新闻（头条）必须是40岁以下明星的热点新闻（V19新增）**
- **最后一条新闻必须是文娱行业相关新闻（公司/平台/产业/行业动态），且不含票房相关信息（V19新增）**
- **同一条事件的新闻必须合并为一条报道，禁止按人物或视角拆分（V19新增）**
- 必须区分"突发新闻事件"与"持续性话题/数据更新"
- 选题必须去重：运行前用memory_search搜索前1-2日的选题
- 选题必须有足够的话题热度和大众关注度
- **来源不限百家号以外的正规媒体均可采纳**（V17放宽）

### 配图规则
- **文件名必须为 news_1.jpg 格式（带下划线）**（V17强制强调）
- **配图搜索优先用websearch image_count=5**（V18重构，替代curl HTML提取为主）
- **下载后先PIL程序化预筛再视觉验证**（V18新增，减少无效图片进入验证环节）
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
| `hot_news_runner.py` | **统一脚本**（PPT+docx+HTML+公众号草稿，4合一，V17+含自动依赖安装） |
| `news_data.json` | 每日新闻数据文件（JSON格式，~50行） |
| `images/news_{1-5}.jpg` | 5张配图（压缩后，文件名带下划线） |

## 版本历史

| 版本 | 日期 | 核心变更 |
|------|------|---------|
| V13 | 2026-07 | 三合一统一脚本 + 秒哒公众号代理 + token精简 |
| V14 | 2026-07-29 | 公众号草稿改直调Supabase Edge Function + 双认证头 |
| V15 | 2026-07-29 | 单篇草稿模式(5合1) |
| V16 | 2026-08-07 | 配图校验增强 + 去重提醒 + URL日期检查 + 视觉验证 |
| V17 | 2026-08-09 | 自动拉取最新版(curl替代git clone) + 无权限审批 + 配图获取增强 + 配图文件名强制规则 + 非百家号多源采纳 |
| V18 | 2026-08-14 | **一次成功运行设计**：runner自动依赖安装 + 配图搜索优先级重构(websearch优先) + 配图URL程序化预筛 + SKILL下载URL动态获取(修复V13硬编码) + 清理逻辑改为仅成功时执行 + 新闻搜索5次并行 |
| V19 | 2026-09-22 | **三条硬性选题规则固化**：同事件合并为单条报道(禁止拆分) + 头条必须为40岁以下明星热点新闻 + 末条必须为文娱行业新闻且不含票房信息；三条规则在筛选后逐条校验 |
| V20 | 2026-10-07 | **运行成本记录与效率复盘强制闭环**：运行前积分快照 + 运行后cost_report成本复盘（效率经验/浪费token复盘/改进落地）；runner下载统一GitHub API；新增版本自检；补齐错误复盘与Skill自我改进闭环（对齐威海旅游V3）；**显式保留用户偏好（浅色主题PPT/双源交叉验证/单源不采用）** |