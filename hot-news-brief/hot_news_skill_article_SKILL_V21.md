# hot_news_skill_article_V21（积分精简版）

## 功能
每日热点文娱新闻全流程自动化：搜索新闻 → 去重 → 配图 → PPT/docx/公众号草稿（runner 4合1）。

**V21 核心目标：把单日积分消耗压到最低（与威海旅游合计 ≤500/日）。相比 V20 的变更：删除多模态 read 视觉验证（10次/日）、websearch 由 10 次减至 3 次、news_data.json 输出减半、SKILL 瘦身约 60%、运行成本复盘改程序化（模型不再写长文）。**

## 触发条件
- 每日定时触发（11:00，cloud）或用户手动要求"运行"。
- **运行规则：无需用户审批任何权限，直接执行，不等待确认。**

## 版本获取规则（含降级）
1. 动态获取最新 SKILL 文件名：
   ```bash
   curl -sL "https://api.github.com/repos/wowobai/dumate-skills/contents/hot-news-brief" | \
     python3 -c "import json,sys; files=[f['name'] for f in json.load(sys.stdin) if f['name'].startswith('hot_news_skill_article_SKILL_V')]; files.sort(); print(files[-1])"
   ```
2. 用 GitHub API base64 下载该 SKILL 与 `hot_news_runner.py` 到产出目录。
3. **下载失败降级（禁止反复重试）**：任一步 curl 失败，立即改用工作区/project 已有同名文件继续；重试次数上限 1 次。
4. 每次运行都拉最新版；不缓存旧版。

## 工作流程

### 步骤1：搜索新闻（3 次并行 → 5 条）+ 去重 + 双源验证
1. 用 `memory_search` 1 次搜索前 1-2 日选题记录用于去重；同时读前一日 `{前一日}热点新闻/news_data.json` 比对。
2. **并行 3 次 websearch（一轮发出）：**
   - `"今日热点文娱新闻 明星 综艺 {yyyy年M月d日}"`
   - `"娱乐圈 文娱行业动态 公司 平台 {yyyy年M月}"`
   - `"微博热搜 娱乐 影视 {yyyy年M月d日}"`
3. **仅从搜索摘要提取信息**，禁止 webfetch 逐条打开原文。
4. 筛选规则（必须全部满足）：
   - 5 条不重复（与前一日去重）；
   - 每条须有 2 个以上消息来源（双源验证），单源不采用；
   - 头条必须是 40 岁以下明星热点新闻；
   - 末条必须是文娱行业相关新闻（公司/平台/产业），不含票房信息；
   - 同一事件合并单条报道，禁止按人物/视角拆分；
   - 只选当天或前一日新闻，超过 2 天旧闻排除；
   - **禁止百家号**（baijiahao.baidu.com）。

### 步骤2：生成 news_data.json（精简输出）
在产出目录创建 `news_data.json`，字段固定为 date/date_display/date_chinese/news[]，每条含 id/title/body/source/analysis/data_source/image_query：
- body：100-120 字（涵盖人物+事件+关键数据），严禁英文双引号
- analysis：60-80 字（单条新闻自身逻辑，不跨事件嫁接）
- source：据XXX报道（2 个以上来源用顿号分隔）
- data_source：数据来源：XXX、XXX
- image_query：2-3 词，含事件/人物锚点
- title：完整陈述核心事实

### 步骤3：配图（程序化，无多模态 read）
1. **优选**：从上一步 websearch 返回结果中已有图片 URL 选取（同批获取，不再单独搜索）；不足 5 条时最多补 1 次 `websearch(query="新闻关键词", image_count=5)`。
2. **URL 域名/模式过滤**：跳过 logo/icon/avatar/favicon/business/transform/w180h180/kandian/default.png 等非新闻图。
3. 下载为 `images/news_1.jpg` ~ `news_5.jpg`（**带下划线**，禁止 news1.jpg）。
4. **程序化校验（runner 内置 PIL，与 runner 阈值一致）**：min_dim≥200、文件≥10KB、宽高比合理；不合格自动换源 1 次（URL 更换），不再人工 read。
5. 严禁带台词/字幕/文字图片；优先人物照/新闻现场照/颁奖照。

### 步骤4：运行统一脚本
```bash
python -X utf8 hot_news_runner.py news_data.json
```
runner 自动：装依赖 → 生成 PPT（浅色/蓝色系，8页5图）→ 新闻稿 docx → 公众号 HTML → 秒哒草稿（5图必须）→ verify_all 验证 → 通过后清理散落文件。

### 步骤5：验证产出（无 read 轮）
- verify_all() 输出一次通过结果：PPT>100KB/8页/5图、docx>100KB/5新闻/5图/中文日期、HTML 存在、draft_id 非空。
- 只读 runner 输出做判断，不额外调用工具复核；有任何 failed 项则如实汇总失败项与原因（不自行多轮修复）。

## 成本控制（程序化）
- 运行开始：模型仅 1 次调用积分接口（console.bce.baidu.com/api/dumate/points/overview 或已知余额）写入产出目录 cost_report.md 首行；**运行中禁止反复查积分**。
- 运行结束：runner 自动 append 完成时间与 verify 结果；模型只输出 1-2 行摘要（余额差值、成功/失败、产出路径）。**不写效率经验/浪费复盘长文**。
- 发现错误：在 cost_report.md 记 3 行（现象/受影响的条目/处置），交付时带出；SKILL 升级由维护会话处理，不在运行内自析。

## 红线（强制保留）
- 新闻去重（排除前一日已用新闻）；浅色主题 PPT；双源交叉验证（两个以上来源，单源不采用）；禁止百家号；全程权限直通；日期新鲜度（当天/前一日）。

## 版本历史（极简）
- V21（2026-10-09）：积分精简版——删除多模态 read 验证、websearch 10→3 次、JSON 输出减半、SKILL 瘦身、复盘程序化；保留全部选题红线与用户偏好。
- V13–V20：历史演进（三合一脚本、秒哒草稿、一次成功设计、三条硬性选题规则、成本记录闭环），核心规则已并入本版。