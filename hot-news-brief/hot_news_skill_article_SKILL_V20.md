# hot_news_skill_article_V20

> 云端每日自动化 Skill —— HOT_NEWS 热点新闻：搜索头条热点 → 判定明星/文娱头条 → 生成 PPT/公众号图文/草稿

## 功能

- 每日自动搜索头条热点，匹配用户画像
- 生成 PPT + 公众号 HTML + 公众号草稿发布
- 三次硬性选题规则（V19新增，本版保留）：
- **同事件合并为单条报道**（禁止拆分多条）
- 头条必须为 40 岁以下明星热点新闻
- 末条必须为文娱行业新闻（不含票房信息）
- 每次运行前动态获取最新版 SKILL 与 runner
- **V20新增：运行成本记录与效率复盘强制闭环（运行前积分快照 → 运行后 cost_report.md 成本复盘），版本自检，下载统一 GitHub API，错误复盘与 Skill 自我改进闭环**

## 变更摘要

### V19 → V20 变更摘要

| 维度 | V19 | V20 |
|------|-----|-----|
| 成本可见性 | 无成本记录，消耗不可查 | **运行前记录积分快照（余额）+ 运行后记录 token 统计/耗时；产出目录写 cost_report.md（运行成本复盘文档）** |
| 效率复盘 | 无 | **每次运行结束强制复盘：①发现更高效率的方法 → 写入 SKILL 经验库；②复盘浪费 token 的错误做法 → 定改进方案；③成本与教训沉淀入 cost_report.md** |
| 下载路径 | SKILL 用 GitHub API，runner 仍用 raw 易超时 | **runner 也改用 GitHub API base64 下载，raw 仅注释保留** |
| 版本同步 | SKILL 与 runner 版本漂移无自检 | **新增版本自检：下载后核对 SKILL 文件名版本与 runner 头注释版本，不一致必须记录并注明执行基线** |
| 错误闭环 | 仅有“一次成功运行设计”，无纠错回流 | **补齐“错误复盘与 Skill 自我改进”强制闭环（四层根因分析+防复发），对齐威海旅游 V3** |

### V18 → V19 变更摘要

| 维度 | V18 | V19 |
|------|-----|-----|
| 选题规则 | 软性建议 | **三条硬性规则并可校验**：同事件合并为单条报道；头条必须为 40 岁以下明星热点新闻；末条必须为文娱行业新闻且不含票房信息 |
| 校验流程 | 靠人工目测 | 筛选后逐条规则校验 |
| 版本策略 | 执行时可能用旧版 | 运行前动态获取 GitHub 上最新版 |

## 版本策略

### 每次运行前必须执行（V19 强化）

1. **动态获取最新版 SKILL**：通过 GitHub API 获取 `hot-news-brief` 目录下最新的 `SKILL_V*` 文件（禁 raw、禁 git clone、禁硬编码版本号）
2. **动态获取最新版 runner**：GitHub API 获取 `hot_news_runner.py`
3. 运行产物目录记录版本信息（版本号 + runner 版本 + 拉取时间）
4. 最新版 SKILL 文件名形如 `hot_news_skill_article_SKILL_V20.md`，以目录内 API 返回实际最新为准

## 权限规则

- **全程无权限确认**：不向用户请求任何权限审批
- 直接执行所有步骤：GitHub 拉取、新闻搜索、配图下载、脚本运行、公众号草稿创建
- 不展示授权提示，不等待用户确认

## 当前用户偏好（强制保留）

- 轻色主题 PPT
- 双源交叉验证（两个以上网站或官方来源）
- 单源新闻不采用
- 推荐职位真实性验证（如适用）

## 环境判断

| 环境 | 判定方式 | 产出目录 | 公众号草稿 |
|------|---------|---------|----------|
| 沙箱 | `os.name == 'posix'` 且工作目录含 `ses_` | `{workdir}/{yyyyMMdd}热点新闻/` | **走秒哒代理** |
| 其他环境 | 未适配 | - | 跳过草稿 |

## 工作流程

### 步骤0：获取最新版本

1. 获取最新 SKILL 文件名（GitHub API）：
```bash
# 禁止 git clone（易超时）；禁止硬编码版本号；raw.githubusercontent.com 可能超时，优先用 API 的 base64 content
LATEST_SKILL=$(curl -sL "https://api.github.com/repos/wowobai/dumate-skills/contents/hot-news-brief" | \
  python3 -c "import json,sys; files=[f['name'] for f in json.load(sys.stdin) if f['name'].startswith('hot_news_skill_article_SKILL_V')]; files.sort(); print(files[-1])")
```
2. 下载 SKILL（GitHub API base64）：
```bash
curl -sL "https://api.github.com/repos/wowobai/dumate-skills/contents/hot-news-brief/${LATEST_SKILL}?ref=main" | \
  python3 -c "import json,sys,base64; d=json.load(sys.stdin); open('/tmp/${LATEST_SKILL}','w').write(base64.b64decode(d['content']).decode('utf-8'))"
```
3. 下载 runner（V20：统一 GitHub API base64，raw 易超时已废弃）：
```bash
curl -sL --connect-timeout 15 --max-time 30 "https://api.github.com/repos/wowobai/dumate-skills/contents/hot-news-brief/hot_news_runner.py?ref=main" | \
  python3 -c "import json,sys,base64; d=json.load(sys.stdin); open('/tmp/hot_news_runner.py','w').write(base64.b64decode(d['content']).decode('utf-8'))"
```
4. 版本自检（V20 新增）：
```bash
head -5 /tmp/hot_news_runner.py  # 确认版本号，如与 SKILL 版本不一致须记录并注明执行基线
```
5. 创建产出目录并复制：
```bash
mkdir -p {workdir}/{yyyyMMdd}热点新闻/images
cp /tmp/hot_news_runner.py {workdir}/{yyyyMMdd}热点新闻/
cp /tmp/${LATEST_SKILL} {workdir}/{yyyyMMdd}热点新闻/
```

### 步骤0.5：运行成本记录（V20 新增，强制）

**每次运行前必须执行，禁止跳过：**
1. 记录运行前积分快照：积分总览接口的当前余额（或运行前最近一次已知余额）；**仅此一次调用积分接口，运行中不得反复查询**
2. 记录启动时间与 SKILL 版本号（${LATEST_SKILL}）
3. 将以上信息写入产出目录 `cost_report.md`（若产出目录尚未创建则先创建）

### 步骤1：搜索新闻 + 去重 + 三条硬性选题规则（V19 强化）

1. 用 websearch 并行搜索（5 路并行，V19 已验证有效）：头条热点、社会新闻、娱乐、明星、文娱
2. 同一事件合并为单条报道（如头条被多个来源报道，合并成一条，配图/来源取最优）
3. 筛选头条（必须 40 岁以下明星热点）→ 头条占位符
4. 筛选末条（必须文娱行业新闻，不含票房）→ 末条占位符
5. 新闻来源双源交叉验证：两个以上网站或官方来源
6. 填入标题、摘要、图片URL

### 步骤2：检测并安装依赖

```bash
cd {workdir}/{yyyyMMdd}热点新闻 && python3 hot_news_runner.py --check-deps
```

### 步骤3：填充占位符并运行 runner 生成内容

```bash
cd {workdir}/{yyyyMMdd}热点新闻 && python3 hot_news_runner.py -o news_content.json
```

### 步骤4：配图下载与校验

```bash
python3 -c "import requests; [requests.get(u, timeout=30).content ...]"
```

**V19 验证通过：PIL 预筛图片有效避免无效图；下载失败自动换候选图**

### 步骤5：验证产出

1. 检查 PPT：浅色主题、内容完整、无占位符残留
2. 检查公众号 HTML：双源验证、标题正确
3. 检查草稿：标题、摘要、封面

### 步骤6：运行成本复盘与效率改进（V20 新增，强制）

**运行结束后（验证产出时一并执行），在产出目录 `cost_report.md` 追加以下内容并随交付提交：**

1. **成本快照**：运行前余额 → 运行后余额（或本次消耗的估算积分），差值即本次运行成本
2. **token 统计**：本次运行的主要步骤耗时与大致 token 消耗（搜索/配图/生成/验证各环节），能取到准确值用准确值，取不到写估算值并标注
3. **效率经验**：本次运行中发现的更高效率做法（如某类搜索词更快命中、某来源配图质量更高），**必须**写入 SKILL「经验沉淀」区或本文件的改进建议，供下次运行参考
4. **浪费复盘**：本次运行中浪费 token 的错误做法（重复搜索、无效验证、超时重试、上下文重复注入等），逐条记录现象与根因，制定改进方案
5. **改进落地**：改进方案直接写入 SKILL（版本+1 按「错误复盘与 Skill 自我改进」流程执行）或登记为待下版落实项

**成本核算不阻塞产出交付，但必须记录；连续两次运行不写 cost_report.md 视为流程违规。**

### 步骤7：公众号草稿

按秒哒代理方案创建公众号草稿。

## 错误复盘与 Skill 自我改进（V20 新增，强制闭环）

**任何一次运行发现错误（新闻数据错误、来源违规、配图不符、草稿标题错误、验证失败、成本异常等），必须执行以下闭环，禁止只修本次产物了事（对齐威海旅游 V3）：**

1. **记录错误事实**：日期、受影响的条目/字段、错误现象（截图或描述）
2. **四层根因分析**（逐层排查）：
   - 流程层：SKILL 规则是否有可操作的判定标准？哪里缺失或含糊？
   - 脚本层：runner 校验是否覆盖该错误维度？
   - 来源层：配图/数据来源是否有约束漏洞（泛图替代、单源信息）？
   - 闭环层：此错误是否源自以往错误未沉淀？
3. **更新 Skill**：将防错规则写入 SKILL.md 对应步骤 + 更新 runner.py 校验逻辑（含反例入库）
4. **升级版本**：SKILL 版本号 +1（如 V19→V20），在版本历史表登记变更，执行后必须填写成本复盘段落
5. **推回 GitHub**：SKILL.md 与 runner.py 同步上传 `wowobai/dumate-skills` 仓库 `hot-news-brief/` 目录
6. **归档复盘**：在产出目录写复盘文档（根因分析+改进说明+预防机制），并随交付提交

**防复发要求**：
- 同一类型错误不得第二次出现（反例库机制）
- 类似/衍生错误在写规则时一并覆盖
- 每次 Skill 更新必须同步更新 runner 版本号与 SKILL 版本历史，保证远端自洽

## 经验沉淀（历次运行验证有效的做法，保留）

- 5 路并行搜索（头条热点/社会/娱乐/明星/文娱）命中率高
- 禁止 webfetch 大正文，改 websearch 摘要 + 定向补充
- PIL 预筛配图，避免下载无效图（V19 验证）
- 动态获取 SKILL/runner 版本（V19 强化，禁 raw/clone/硬编码）
- ensure_dependencies 一次成功运行（runner 内置）

## 版本历史

| 版本 | 日期 | 变更说明 |
|------|------|---------|
| V14 | 2026-09-21 | 公众号草稿从 appmiaoda.com/api 改为直调 Supabase Edge Function，添加 Bearer+apikey 双认证头，修复 entrypoint 部署问题 |
| V15 | 2026-09-21 | 新增机制 |
| V16 | 2026 | 完善 |
| V17 | 2026-09-21 | 补丁式更新（版本漂移修复） |
| V18 | 2026-09-21 | 版本问题修复：版本号从 V17 升级 V18，补齐版本历史 |
| V19 | 2026-09-22 | **三条硬性选题规则固化**：同事件合并为单条报道（禁止拆分）+ 头条必须为 40 岁以下明星热点新闻 + 末条必须为文娱行业新闻且不含票房信息；三条规则在筛选后逐条校验 |
| V20 | 2026-10-07 | **运行成本记录与效率复盘强制闭环**：运行前积分快照 + 运行后 cost_report 成本复盘（效率经验/浪费 token 复盘/改进落地）；runner 下载统一 GitHub API；新增版本自检；补齐错误复盘与 Skill 自我改进闭环（对齐威海旅游 V3） |
