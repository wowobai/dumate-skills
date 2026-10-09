# weihai_travel_skill_V5（积分精简版）

## 功能
威海旅游新闻每日全流程自动化：搜索威海本地旅游新闻 → 去重 → 配图 → PPT/docx/公众号草稿（runner 三合一）。

**V5 核心目标：单日积分最低（与 HOT_NEWS 合计 ≤500/日）。相比 V4 变更：删除多模态 read 锚点语义验证（曾单次 173 分 ×2）、websearch 10→3 次、JSON 输出减半、SKILL 瘦身约 60%、成本复盘程序化。保留 L1 官方来源优先、锚点规则（程序化校验）、至少 3 条威海本地、草稿标题固定。**

## 触发条件
- 每日定时触发（18:00，cloud）或用户手动要求"运行"。
- **权限直通：全程不等待用户审批，直接执行。**

## 版本获取规则（含降级）
1. 动态获取最新 SKILL 文件名：
   ```bash
   curl -sL "https://api.github.com/repos/wowobai/dumate-skills/contents/weihai-travel-brief" | \
     python3 -c "import json,sys; files=[f['name'] for f in json.load(sys.stdin) if f['name'].startswith('weihai_travel_skill_SKILL_V')]; files.sort(); print(files[-1])"
   ```
2. 用 GitHub API base64 下载最新 SKILL 与 `weihai_travel_runner.py` 到产出目录。
3. **下载失败降级**：curl 失败仅重试 1 次；仍失败立即使用工作区/项目已有版本执行。
4. 每次运行都拉最新版。

## 工作流程

### 步骤1：搜索新闻（3 次并行）+ 去重 + 双源验证
1. `memory_search` 1 次查前 1-2 日威海选题；读前一日 `{前一日}旅游新闻/news_data.json` 去重。
2. **并行 3 次 websearch（一轮发出）：**
   - `"威海 旅游 新闻 {yyyy年M月d日}"`
   - `"威海 文旅 景区 活动 {yyyy年M月}"`
   - `"威海 网红打卡 美食 景区 新政策 {yyyy年M月}"`
3. 筛选规则（必须全部满足）：
   - 共 5 条：**至少 3 条威海本地**，其余可省内/旅游行业；前一日已用新闻排除；
   - **L1 官方来源优先**（威海文旅局/大众网威海/威海新闻网/Hi威海/官方公众号）；权威媒体次之；
   - 每条须 2 个以上来源（双源验证），单源不采用；
   - 只选近 2 天内新闻；**禁止百家号**；
   - 同一事件合并单条，禁止重复拆分。

### 步骤2：生成 news_data.json（精简输出）
字段 date/date_display/date_chinese/news[]，每条含 id/title/location/body/source/analysis/data_source/image_query：
- body：100-120 字（人物/地点+事件+关键数据），严禁英文双引号
- analysis：60-80 字（单条新闻自身分析）
- location：地点（威海本地条目必须含具体区/镇/景区锚点）
- source：据XXX报道（2 个以上来源顿号分隔）
- image_query：含 **地点锚点词 + 主体锚点词**（供配图程序化校验）

### 步骤3：配图（程序化，无多模态 read）
1. **优选**：从上一步 websearch 结果直接取图；不足 5 条补 1 次 `websearch(query="威海 对应地点/事件", image_count=5)`。
2. URL 域名/模式过滤：跳过 logo/icon/avatar/biz 等非新闻图。
3. 下载 `images/travel_1.jpg` ~ `travel_5.jpg`（**带下划线**）。
4. **程序化锚点校验（runner 内置 PIL，与 runner 阈值一致）**：min_dim≥200、文件≥10KB + image_query 需含 location 锚点词 + 来源域名白名单；不合格自动换源 1 次。
5. 优先威海实景/现场照；严禁带字幕/台词/远景空镜。

### 步骤4：运行三合一脚本
```bash
python -X utf8 weihai_travel_runner.py news_data.json
```
runner 自动：装依赖 → 生成 PPT（浅色/蓝色系，8页5图）→ 新闻稿 docx → 公众号 HTML → 秒哒草稿（草稿标题固定为"威海旅游新闻"）→ verify_all 验证。

### 步骤5：验证产出（无 read 轮）
- verify_all() 输出：PPT>100KB/8页/5图、docx>100KB/5新闻/5图/中文日期、HTML 存在、draft_id 非空。
- 只读 runner 输出判断，不额外调工具复核；failed 项如实汇总（不自行多轮修复）。

## 成本控制（程序化）
- 运行开始：1 次积分接口查余额写入产出目录 cost_report.md 首行；运行中禁止反复查询。
- 运行结束：runner 自动 append 完成时间与 verify 结果；模型只输出 1-2 行摘要。**不写复盘长文**。
- 纠错闭环：错误记 cost_report.md 3 行（现象/受影响条目/处置）；SKILL 升级由维护会话处理。

## 红线（强制保留）
- 至少 3 条威海本地新闻；L1 官方来源优先；新闻去重；浅色主题 PPT；双源验证；禁止百家号；近 2 天新鲜度；草稿标题固定"威海旅游新闻"；权限直通。

## 版本历史（极简）
- V5（2026-10-09）：积分精简版——删多模态 read 锚点验证、websearch 10→3 次、JSON 输出减半、SKILL 瘦身、复盘程序化；保留选题红线与偏好。
- V2–V4：历史演进（锚点语义验证引入后被本版程序化替代、自我改进闭环、成本复盘），核心规则已并入本版。