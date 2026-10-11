# matchmaking_skill_V2（威海红娘新闻·婚介资讯·云端化·积分精简版）

## 功能
每日婚介/婚恋/相亲领域资讯全流程自动化：搜索新闻 → 去重 → 配图下载 → 公众号HTML → 公众号草稿创建（秒哒服务器）。
**不生成PPT**，只产出公众号HTML与草稿。
**核心定位：以威海本地相亲/婚介资讯为主体、婚恋行业宏观动态为头条的每日资讯聚合，面向公众号发布。**
**草稿标题含「威海红娘新闻」**（main_title 固定"威海红娘新闻"，秒哒函数生成 `{date_chinese||date_display} 威海红娘新闻`；HTML大标题固定 `{date_display} 威海红娘新闻`）。

## 触发条件
- 每日定时触发（**08:00**，cloud模式）或用户手动要求"运行"
- 前置条件：前一日产出目录存在（用于去重）
- **运行规则：无需用户审批任何权限，直接执行，可无人值守**
- **积分红线（V2 核心约束）：单次运行积分必须 ≤240 积分**；超预算视为运行失败，须复盘调用次数并收敛后重跑，不得长期超支

## 选题结构（固定5条，强制顺序）

| 位置 | 要求 |
|------|------|
| 第1条（头条） | **宏观类资讯，尽量有数据支撑**（tag：宏观动态/行业观察）：如民政部婚姻登记数据、全国结婚率/初婚年龄/婚介市场规模、婚介行业监管政策、婚俗改革新规、彩礼治理等 |
| 第2-4条 | **尽量贴近威海相亲相关资讯**（tag：威海相亲/相亲故事/婚介所动态/婚姻趣闻）：威海本地相亲活动、青年联谊、婚介机构运营动态、婚姻家庭趣事；**若威海本地资讯不足，可选用其他省份相亲新闻或趣味资讯兜底** |
| 第5条（最后一条） | **威海婚介所相关新闻优先**（如威海本地婚介机构动态、红娘服务、婚介所活动）；**如无婚介所资讯，则选威海相亲相关新闻**（tag：威海婚介所/威海相亲） |

**严禁改变顺序**：宏观头条必须在第1条，威海本地（婚介所优先）新闻必须在最后一条。中间3条可调顺序但不越位。

## 积分预算红线（V2 新增）

积分主要由「模型推理 + 工具调用返回内容」构成（历史实测约 8-12 积分/条工具流水；2026-10-08 HOT_NEWS 单次 154 条流水 ≈1295 积分）。V2 通过**压缩调用次数和返回体量**把单次控制在 240 积分内。

| 环节 | V1 调用量 | V2 调用量 | 预算参考（积分） |
|------|-----------|-----------|------------------|
| 版本取回 | API列版本+3次raw下载+head | 1 次 bash（合并探测/下载/MD5复用） | 5~15 |
| 去重 | memory_search + 读前一日json | memory_search 1 + bash 提取标题 1 | 10~25 |
| 新闻搜索 | **5 次并行 websearch** + 独立配图搜索 | **3 次并行 websearch**（+按需补搜1次，条件触发） | 30~70 |
| 生成 news_data.json | 1 次 write | 1 次 write | 5~10 |
| 配图下载与处理 | 独立图片搜索 + 多次 curl + 逐张处理 | **1 次 bash 批量**（原文og:image + 精确词Bing + PIL一键） | 10~25 |
| 配图视觉验证 | **5 次 read 逐张** | **1 次 read 拼接图**（异常才补读单张） | 15~40 |
| 运行 runner | 1 次 bash | 1 次 bash | 10~25 |
| 最终验证 | 多处 read/检查 | 1 次 bash 汇总（配图结果复用） | 5~15 |
| **合计（参考）** | — | **约 11-13 次调用** | **约 90~225，预留余量 ≤240** |

**控费红线（执行时逐条遵守）**：
1. 全程不得 `webfetch` 逐条打开新闻原文（只用搜索摘要，V1 同款约束）。
2. 不得读取 runner.py 或 hot_news_runner.py 全文（版本确认用 `head -c`/MD5 即可；凭据载体只在 runner 内部被静态提取）。
3. websearch 一律收紧返回条数（web_count 推荐 6-8，若接口支持），输出只取标题/来源/摘要关键句，不转述整段。
4. 配图视觉验证默认只 read 1 次拼接图；只有拼接图不够清晰或疑似不匹配时才补读单张。
5. 每步 bash 输出收敛为「关键状态 + 一行结论」，不打印整文件、不多次 ls 大目录。

## 版本获取规则（V2 精简）

### 自动获取最新版（合并为 1 次 bash）
1. **禁止使用 `git clone`**（易超时），改用 `curl -sL` 从 GitHub raw 下载
2. 动态获取最新SKILL文件名：
   ```bash
   LATEST_SKILL=$(curl -sL --max-time 15 "https://api.github.com/repos/wowobai/dumate-skills/contents/matchmaking-brief" | \
     python3 -c "import json,sys; files=[f['name'] for f in json.load(sys.stdin) if f['name'].startswith('matchmaking_skill_SKILL_V')]; files.sort(); print(files[-1])")
   ```
3. Runner脚本固定文件名：`matchmaking_runner.py`
4. **MD5 复用（控费关键）**：下载前先取上一日产出目录或本地已复制副本的 MD5；下载后用 MD5 比对，相同则输出 `VERSION SAME` 并复用本地副本，**不重复下载**；不同才替换为新版。若 raw 下载超时，直接使用本地 skills/user 或已复制的最新版。
5. 一并下载 `hot_news_runner.py`（公众号凭据载体）到产出目录：运行 runner 时从其中提取 WX/SUPABASE 凭据；**hot_news_runner.py 仅作凭据载体，不会被运行**。
6. 用 `head -c 300 matchmaking_runner.py` 确认版本号后即可，**禁止 read 全文**。

### 权限规则
- **全程无权限确认**：不向用户请求任何权限审批
- 直接执行所有步骤：GitHub拉取、新闻搜索、配图下载、脚本运行、公众号草稿创建
- 不展示授权提示，不等待用户确认

## 环境判断

| 环境 | 判定方式 | 产出目录 | 公众号草稿 |
|------|---------|---------|----------|
| 沙箱 | `os.name == 'posix'` 且工作目录含 `ses_` | `{workdir}/{yyyyMMdd}威海红娘新闻/` | **走秒哒代理** |
| 其他环境 | 未适配 | - | 跳过草稿 |

## 工作流程（V2 精简，全程约 11-13 次调用）

### 步骤0：日期与产出目录
按「积分精简版」单次 bash 完成：
```bash
YYYYMMDD=$(date '+%Y%m%d'); DATE_DISPLAY=$(date '+%Y.%m.%d')
# date_chinese 由 python 生成（如 二零二六年十月十一日）
mkdir -p {workdir}/${YYYYMMDD}威海红娘新闻/images
```
产出目录固定：`{workdir}/{yyyyMMdd}威海红娘新闻/`。

### 步骤1：取最新版（1 次 bash，含 MD5 复用）
```bash
cd {workdir}/${YYYYMMDD}威海红娘新闻
LATEST_SKILL=$(curl -sL --max-time 15 "https://api.github.com/repos/wowobai/dumate-skills/contents/matchmaking-brief" | \
  python3 -c "import json,sys; files=[f['name'] for f in json.load(sys.stdin) if f['name'].startswith('matchmaking_skill_SKILL_V')]; files.sort(); print(files[-1])")
echo "LATEST_SKILL=$LATEST_SKILL"
# 下载 runner / SKILL / hot_news_runner（raw 超时则用本地最新副本）
curl -sL --connect-timeout 10 --max-time 20 -o matchmaking_runner.py "https://raw.githubusercontent.com/wowobai/dumate-skills/main/matchmaking-brief/matchmaking_runner.py" || cp {上日目录}/matchmaking_runner.py .
curl -sL --connect-timeout 10 --max-time 20 -o "${LATEST_SKILL}" "https://raw.githubusercontent.com/wowobai/dumate-skills/main/matchmaking-brief/${LATEST_SKILL}" || cp {上日目录}/${LATEST_SKILL} .
curl -sL --connect-timeout 10 --max-time 20 -o hot_news_runner.py "https://raw.githubusercontent.com/wowobai/dumate-skills/main/hot-news-brief/hot_news_runner.py" || cp {上日目录}/hot_news_runner.py .
# MD5 复用判定 + 版本确认（只输出结论行）
PREV=$(ls {上日目录}/matchmaking_runner.py 2>/dev/null && md5sum {上日目录}/matchmaking_runner.py | cut -d' ' -f1)
CUR=$(md5sum matchmaking_runner.py | cut -d' ' -f1)
[ "$PREV" = "$CUR" ] && echo "VERSION SAME: runner 复用上日副本（省一次下载）" || echo "VERSION UPDATED"
head -c 300 matchmaking_runner.py  # 确认版本号，禁止 read 全文
```
流程已固化于本 V2 文档：**常规运行不再 read SKILL 全文（0 次 read）**。仅当步骤1下载的最新 SKILL 版本名大于 V2 且流程有实质变化时，才 read 该新版 SKILL 全文并按其执行；版本相同或仅提示语变化，则直接按 V2 流程继续，不额外 read。

### 步骤2：去重（2 次调用）
1. 用 `memory_search`（1 次）搜索前 1-2 日威海红娘/婚介新闻选题记录，记录已用标题关键词。
2. 读取前一日产出目录 `{前一日}威海红娘新闻/news_data.json` 的标题列表（1 次 bash，用 python 只输出标题与关键词，不打印全文）：
   ```bash
   python3 -c "import json; d=json.load(open('{前一日}威海红娘新闻/news_data.json',encoding='utf-8')); print('\n'.join(n['title'] for n in d['news']))"
   ```
3. 比对新选新闻标题/事件主体，与前 1-2 日重复的**一律排除**。

### 步骤3：并行搜索新闻（3 次 websearch + 按需补搜1次）
**并行 3 次 websearch**（一轮发出，不等单次完成；web_count 收紧，推荐 6-8）：
1. 宏观头条：`婚姻登记 结婚率 数据 政策 婚介市场 监管 {yyyy年M月}`（须有数据支撑）
2. 威海相亲/婚介动态（覆盖 2-4 条与第 5 条候选）：`威海 相亲 青年联谊 婚恋 活动 红娘 {yyyy年M月}`
3. 威海婚介机构（第 5 条优先）：`威海 婚介所 婚介机构 红娘 服务 动态 {yyyy年M月}`

**按需补搜（仅当 3 次并行结果不足以凑齐 5 条不重复新闻时发起，上限 1 次）**：
- 威海素材不足 → `威海 相亲 联谊 {yyyy年M月}`（换词或细分区域）
- 仍需外省兜底 → `相亲 婚恋 趣事 新闻 {yyyy年M月}` 或 `婚介 行业 整治 婚托 规范 {yyyy年M月}`（二选一，不同时发起）

**红线**：
- **仅从搜索摘要提取信息**，禁止 webfetch 逐条打开原文（省积分）
- **信息源红线（L1优先）**：L1=民政部官网、全国婚恋婚介官方机构、威海本地官方媒体（威海新闻网、威海日报、Hi威海客户端等）；L2=省市民政/妇联/共青团官方账号；L3=央视新闻/新华社/人民日报等全国权威；L4=新浪/网易/澎湃等主流媒体；**黑名单：百家号（baijiahao.baidu.com）一律禁止**
- 每条新闻须 **2 个以上消息来源**；无法双源验证的标"待确认"
- 选 5 条不与前 1-2 日重复的新闻，按「选题结构」固定顺序排列

### 步骤4：生成 news_data.json（1 次 write）
在产出目录下创建 `news_data.json`：
```json
{
  "date": "20261011",
  "date_display": "2026.10.11",
  "date_chinese": "二零二六年十月十一日",
  "news": [
    {
      "id": "1",
      "tag": "宏观动态",
      "title": "新闻标题（第1条须为宏观类资讯，尽量含数据支撑）",
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
**注意**：summary 与 impact 中严禁英文双引号 `"`，用中文引号 `“ ”` 替代。

### 步骤5：配图下载与处理（1 次 bash，V2 精简）
**控费要点：不发起独立图片搜索**。配图来源优先级（**V2.1 实测修正**）：
1. **首选：新闻原文 URL 提取 og:image**——从步骤3搜索结果中已经出现的新闻原文链接，用 curl 抓取页面 `<meta property="og:image">` 取图（过滤 logo/icon/avatar/business/transform/kandian/w180h180 等 URL 特征；无 og:image 时再回退解析正文首图）
2. **次选：精确词 Bing 图片搜索**——用 `https://www.bing.com/images/search?q=精确事件/机构名` 抓 HTML 中 `murl` 字段取图；**关键词务必带原文明确的事件/机构/地点名**（如"重庆梁平 月老红娘 相亲"），不要用泛词（泛词会返回不相关图）；优先可访问且无水印的图
3. **禁用通道（实测不可用，勿再尝试）**：百度图片 API `https://image.baidu.com/search/acjson` 已反爬（返回 Forbid spider access）；websearch 的 image_count 不返回图片条目，不作为配图通道

**下载与处理一次脚本完成（1 次 bash）**：
```bash
cd {workdir}/${YYYYMMDD}威海红娘新闻
# 按上述优先级为 news_1~news_5 取图，下载至 images/news_{id}.jpg
# PIL 程序化：格式检查（webp/png 转 jpg）→ 压缩（max 1200px宽、quality=85）→ 预筛（min_dim>=200、size>=10KB，不合格换源）
# 输出每张图的结果行（OK/WARN/换源），不打印图片内容
python3 <<'EOF'
# 对已下载的 images/news_{id} 原图执行 PIL 批处理（逻辑固定，实现细节由执行方补齐）：
# 1) 格式检查：webp/png 统一转 jpg；
# 2) 压缩：max 宽 1200px、quality=85；
# 3) 预筛：min_dim>=200 且 size>=10KB，不合格换源重下；
# 4) 输出每张图最终状态行 OK/WARN/换源，不打印图片内容。
# runner 内置配图压缩与一致性校验作为第二道防线。
EOF
```
配图文件名强制：`news_1.jpg` ~ `news_5.jpg`（**带下划线**）。

**视觉验证（V2 精简为 1 次 read）**：
- 先用 PIL 将 5 张图拼成一张预览图 `images/preview_verify.jpg`（2 行 3 列，每格缩放至约 200px 宽，白底留边）。
- 用 `read` 工具读取拼接图 1 次，逐格确认 5 张图与对应新闻标题匹配；**严禁带台词/字幕/文字图片**。
- 仅当拼接图上某格不清晰或疑似不匹配时，才单独 read 该张原图（异常补读，正常流程只有 1 次 read）。

### 步骤6：运行统一脚本（1 次 bash）
```bash
cd {workdir}/${YYYYMMDD}威海红娘新闻
python -X utf8 matchmaking_runner.py news_data.json
```
脚本自动执行（2合1，**无PPT**）：
1. **自动依赖安装**：requests/Pillow
2. **公众号HTML**：蓝色系主题，文件名 `wechat_article.html`
3. **公众号草稿**（仅沙箱环境）：POST 到秒哒 Supabase Edge Function，payload 带 `main_title:"威海红娘新闻"`
4. **验证**：内置 verify_all()（HTML 存在、draft_id 非空）、check_text_quality()（文案防错）、check_selection_structure()（选题结构）、check_image_consistency()（配图尺寸一致性）

如 runner 报告结构/文案 FAIL，修正 news_data.json 后**重跑一次**修复；不得带病交付。

### 步骤7：统一验证（1 次 bash 汇总，配图结果复用步骤5）
```bash
cd {workdir}/${YYYYMMDD}威海红娘新闻
echo "--- HTML ---"; ls -la wechat_article.html 2>/dev/null || echo "HTML MISSING"
echo "--- 草稿 ---"; python3 -c "import json; d=json.load(open('draft_verify.json',encoding='utf-8')); print('draft_id:', d.get('draft_media_id')); print('title:', d.get('draft_title')); print('标题含威海红娘新闻:', '威海红娘新闻' in (d.get('draft_title') or ''))"
echo "--- 选题结构 ---"; python3 -c "import json; n=json.load(open('news_data.json',encoding='utf-8'))['news']; print('第1条宏观:', any(k in (n[0]['title']+n[0]['summary']) for k in ['政策','数据','登记','结婚率','规模','增长','同比'])); print('最后1条威海:', any(k in n[-1]['title'] for k in ['威海','荣成','文登','乳山','经区','高区','临港','环翠']))"
```
**验收标准（全部通过才交付）**：
- [ ] `wechat_article.html` 存在
- [ ] `draft_id` 非空且草稿标题含「威海红娘新闻」
- [ ] 选题结构：第 1 条宏观（有数据支撑）、最后 1 条威海（婚介所优先/相亲兜底）
- [ ] 5 张配图 `images/news_{1-5}.jpg` 存在，且步骤5拼接图已确认视觉匹配
- [ ] 文案质量：无英文双引号、无残留虚字/句尾孤字/重复字、引号成对
- [ ] **积分：单次运行 ≤240 积分**（若不满足，复盘调用次数与搜索返回体量后收敛）

## 公众号草稿 - 秒哒代理方案（沿用 V1）

### 架构
```
沙箱(DuMate) ──POST news_data.json + 5张图──> 秒哒应用(固定IP) ──> 微信API
                                                          <──draft_id──
```
### 秒哒应用信息
- 后端：Supabase Edge Function，URL: `https://backend.appmiaoda.com/projects/supabase340340166944145408/functions/v1/create-draft`
- 秒哒服务器IP：`106.13.244.120`（已加入公众号白名单）
- **草稿标题固定规则**：payload 中 `main_title:"威海红娘新闻"`，秒哒函数生成 `{date_chinese||date_display} 威海红娘新闻`
- **严禁**出现"威海旅游新闻"/"热点社会新闻"/"婚介资讯"等字样——标题恒含「威海红娘新闻」，不同主题任务标题不得混用

### 沙箱调用方式
脚本内置 `gen_wechat_draft()` 自动 POST multipart/form-data 到秒哒 Supabase Edge Function，Bearer+apikey 双认证头；凭据优先环境变量，缺失时从同目录 hot_news_runner.py 源码提取（**读取凭据常量值仅在脚本内部完成，运行方不得打印凭据**）。

## 信息源红线（婚介领域）
- 婚介政策类：民政部官网、全国人大/国务院官网、地方民政部门官微（L1/L2 优先）
- 婚介行业类：婚介行业协会、主流媒体深度报道
- 威海本地类：威海新闻网、威海日报、Hi威海客户端、威海广播电视台
- **黑名单：百家号（baijiahao.baidu.com）一律禁止**
- 每条新闻须 2 个以上消息来源

## 写作规范
- summary 完整陈述核心事实（谁做了什么+关键数字+关键动作），150-200字
- impact 基于单条新闻自身逻辑，100-150字影响分析，不跨事件嫁接因果关系
- title/summary/impact 中严禁英文双引号，用中文引号 `“ ”`
- 第 1 条宏观头条的 summary 应突出数据（登记对数、结婚率、市场规模、同比增长）与政策/事件要点
- 2-4 条威海相亲资讯应突出本地信息（时间/地点/主办方）；外省资讯兜底时保持相亲/婚恋主题相关
- 第 5 条威海婚介所新闻应突出机构名称/活动/服务内容；无婚介所资讯时选威海相亲新闻兜底

### 文案防错红线（沿用 V1.1，形成过病句教训）
1. **数字-单位完整性**：凡出现 "升至/降至/同比增长/占比" 等表述，数字必须带完整单位并紧接正常标点（如 `升至28%，女性为13%`）。**禁止**出现 `28%至，`、`升至8%的`、`增至13%，` 这类"数字+%+单字虚词+标点"的拼接残留。
2. **句尾孤字检查**：summary/impact 任何分句不得以"至/的/了/为/在/与/及/等/和/并"等单字虚词结尾。
3. **重复字检查**：同句不得出现连续重复虚字（如"至至"、"的的"）或本不存在的叠词。
4. **引号配对**：中文弯引号 `“ ”` 必须成对，严禁 ASCII 双引号 `"` 混入 summary/impact/title。
5. **口径一致性**：同一新闻内同一指标不得混用两种表述（如"未婚比例"与"未婚率"指同一数据时口径必须统一）。
6. **机械校验**：runner 内置 `check_text_quality()` 会报出上述问题，检出即失败，发布前必须修正 news_data.json 后重跑。

## 积分复盘（V2 新增，每次运行后执行）
运行完成后，如实际积分 >240 或调用次数 >12：
1. 列出本运行每一步实际调用次数与估算积分
2. 定位超支环节（搜索返回体量？read 次数？补搜？重跑？）
3. 收敛下一版流程（收紧 web_count、合并调用、减少异常补读）并更新 SKILL
4. 把经验记入 memory（历史已确认：每日定时任务是积分消耗大头，单任务曾达 1200-2800 积分/次，需持续压缩）

## 文件分发规则
每次更新SKILL版本时，**必须**同步上传：
1. **GitHub**：`wowobai/dumate-skills` 仓库 `matchmaking-brief/` 目录（SKILL + runner）
2. **本地**：通过 file_export 保存到用户指定路径

## 关键文件

| 文件 | 用途 |
|------|------|
| `matchmaking_runner.py` | **统一脚本**（HTML+公众号草稿，2合1，无PPT，含自动依赖安装与校验） |
| `hot_news_runner.py` | 公众号凭据载体（不被运行，仅被 runner 静态提取凭据） |
| `news_data.json` | 每日新闻数据文件（JSON格式） |
| `images/news_{1-5}.jpg` | 5张配图（压缩后，文件名带下划线） |
| `images/preview_verify.jpg` | 5张配图拼接预览（V2 视觉验证用，1次read完成） |
| `wechat_article.html` | 公众号图文HTML |
| `draft_verify.json` | 草稿创建结果（draft_id/title） |

## 版本历史

| 版本 | 日期 | 核心变更 |
|------|------|---------|
| V1 | 2026-09-30 | 初始版本：仿照 weihai_travel_skill_V2 云端架构；无PPT，仅公众号HTML+草稿；选题结构固定；草稿标题恒含「威海红娘新闻」；每日08:00定时触发 |
| V1.1 | 2026-09-30 | 修复 HTML 大标题误接「每日热点」后缀；新增文案防错校验 check_text_quality() |
| **V2** | **2026-10-11** | **积分精简版：单次运行积分红线≤240。并行搜索 5→3（+条件补搜1次）；取消独立图片搜索（改原文/百度图API+1次bash批量）；配图视觉验证 5 次 read→1 次拼接图 read；取版合并 1 次 bash 且 MD5 复用；最终验证收敛 1 次 bash；总调用 11-13 次、积分约 90~225；新增积分预算表与运行后积分复盘** |
| **V2.1** | **2026-10-11** | **实测修正配图链路：百度图片 API 已反爬（Forbid spider access）不可用、websearch 不返回图片条目，弃用两者；配图改为「原文og:image 提取优先 → 精确词 Bing（murl）兜底」；同步修复 runner V1.2 引号配对判断（左==右，原奇偶判断会误报合法单对引号）** |

## 依据
本SKILL V2 对齐 weihai_travel_skill_V2 / HOT_NEWS 云端架构（自动版本拉取、秒哒草稿链路、依赖自安装、PIL配图预筛），按婚介领域定制选题结构与信息源红线；V2 在保持全部功能与约束的前提下，通过压缩搜索次数、配图链路与验证次数将单次积分控制在 240 以内。公众号凭据来源见 hot-news-brief/hot_news_runner.py。
