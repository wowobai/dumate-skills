# hot_news_skill_article_V16

## 概述
每日热点文娱新闻自动生成技能。搜索当天热点文娱新闻，生成PPT、新闻稿docx、公众号HTML、公众号草稿（4合1）。
运行脚本：`hot_news_runner.py`（从GitHub拉取最新版）。

## 选题规则（必须遵守）
1. **第一条新闻不得是票房总结类**。票房总结配图容易与文不符，且作为头条吸引力不足。应选择具体影片、演出、赛事等有明确视觉素材的新闻作为第一条。
2. 只选发布当天或前一日发生的新闻，超过2天的旧闻一律排除。
3. 固定5条新闻，不多不少。
4. 搜索后筛选时不能只看"多来源"和"非百家号"，事件时效性是第一过滤条件。
5. 选题必须区分"突发新闻事件"与"持续性话题/数据更新"——票房累积数字更新、开播剧后续话题均不算真正的新闻。
6. 选题不仅满足时效性，还必须有足够的话题热度和大众关注度，应优先选择当晚上微博热搜、有明确视觉素材、大众讨论度高的新闻。冷门突发事件不适合作为热点新闻。

## 去重规则（V16新增，必须遵守）
1. **运行前必须搜索前一日新闻选题**：在搜索今日新闻之前，先用 `memory_search` 搜索前一日（及前两日）的热点新闻选题，获取已选新闻标题列表。
2. **标题去重**：如果今日候选新闻与前一日已选新闻属于同一事件（即使标题措辞不同），必须替换为其他新闻。判断标准：
   - 同一影片/同一明星的同一事件（如"沈腾新片定档"昨天已选，今天不能再选）
   - 同一事件的后续进展不算新新闻（如"定档"之后"点映"不算新选题，除非有重大新信息）
   - 不同角度的独立事件可以选（如同日某明星的A事件和B事件是不同事件）
3. **去重范围**：检查前2个自然日的选题记录。如果记忆搜索无结果，用 `websearch` 搜索"前一日日期+热点新闻"确认。
4. **去重失败兜底**：如果去重检查遗漏，导致重复新闻被选中，用户指出后必须立即替换，并更新SKILL。

## 配图规则
1. 每条新闻必须配1张图，共5张，保存为 `images/news_1.jpg` ~ `images/news_5.jpg`。
2. 配图必须与新闻内容匹配，搜索时用具体关键词。
3. 下载后用 `compress_image()` 压缩。
4. 下载后检查图片格式，webp需转为JPEG。
5. runner内置 `check_image_consistency()` 校验每张图尺寸、文件大小、与标题对应关系。
6. **配图来源优先级（V16新增）**：
   - 第一优先：用 `webfetch` 抓取新闻原文HTML，从中提取 `<img>` 标签的实际内嵌图片URL
   - 第二优先：`websearch` 搜索结果中的图片URL（image_count=3）
   - 禁止：仅凭搜索结果icon或封面图URL，不验证直接下载
7. **配图URL日期检查（V16新增）**：下载前检查URL路径中是否包含日期信息，如果URL中的日期与新闻事件日期明显不符（相差超过7天），必须更换URL。
8. **配图视觉验证（V16新增）**：下载后用 `read` 工具查看图片，确认图片内容与新闻标题描述一致。如果图片内容与新闻不匹配，必须重新搜索下载。

## 公众号草稿模式（V15沿用）
**5条新闻合并为1篇图文（单article模式），不是5篇独立图文。**
- 文章标题：`{date_chinese} 热点文娱新闻`。
- 封面图（thumb_media_id）：用 `images[0]`（即 `news_1.jpg`）上传为永久素材。
- 内容图片：所有5张图都通过 `uploadimg` 上传为正文内嵌图。
- `show_cover_pic` 设为 `1`。

## Supabase Edge Function 直调捷径（V14建立，V16沿用）
**不再通过 appmiaoda.com/api 调用，直接调 Supabase Edge Function。**

### 配置
- Supabase URL: `https://backend.appmiaoda.com/projects/supabase340340166944145408`
- Edge Function 端点: `{SUPABASE_URL}/functions/v1/create-draft`
- Anon Key: 已硬编码在runner.py中
- 请求头: `Authorization: Bearer {key}` + `apikey: {key}`（双认证头，缺一不可）
- 请求格式: `multipart/form-data`，包含 `news_data`（JSON字符串）+ `images`（图片文件数组）

### 秒哒服务器固定IP
- IP: `106.13.244.120`（确认固定不变）
- 已加入微信公众号IP白名单，永久生效。

### 草稿失败标准化3步诊断
1. `GET {SUPABASE_URL}/functions/v1/server-ip` → 查白名单
2. `POST {SUPABASE_URL}/functions/v1/create-draft` → 查部署
3. 通过 `miaoda_api.py chat` 远程修复Edge Function部署问题

## 产出交付规则
1. 固定5条新闻，只发1个草稿（单article模式）。
2. 只导出4个文件：PPT、docx、HTML、news_data.json。
3. 多余散落文件用 `cleanup_workspace()` 自动清理。

## 执行流程（Token优化版）

### 步骤1: 拉取最新SKILL和runner
```
GitHub仓库: wowobai/dumate-skills → hot-news-brief/
  - hot_news_skill_article_SKILL_V16.md（本文件）
  - hot_news_runner.py（V16）
```

### 步骤2: 去重检查（V16新增，必须在搜索新闻之前执行）
1. 用 `memory_search` 搜索关键词"热点新闻 选题"，获取前1-2日的选题记录
2. 整理已选新闻标题列表
3. 如果记忆搜索无结果，用 `websearch` 搜索"前一日日期 热点文娱新闻"确认
4. 在后续搜索今日新闻时，排除与已选新闻重复的选题

### 步骤3: 搜索新闻
- 用 `websearch` 搜索当天热点文娱新闻，`freshness=pw`（一周内）。
- 筛选5条，遵守选题规则。
- 筛选时对照步骤2的去重列表，排除重复选题。

### 步骤4: 搜索并下载配图
- 为每条新闻用 `websearch` 搜索匹配图片，`image_count=3`。
- **优先用 `webfetch` 抓取新闻原文HTML，提取 `<img>` 标签中的实际图片URL**。
- 下载前检查URL中是否含旧日期，如有则更换。
- 下载后用 `read` 工具查看每张图片，确认视觉内容与新闻匹配。
- 压缩、格式检查、一致性校验。

### 步骤5: 构建news_data.json并运行runner
```bash
python -X utf8 hot_news_runner.py "20260807热点新闻/news_data.json"
```

### 步骤6: 导出文件
用 `file_export` 导出4个文件：PPT、docx、HTML、news_data.json。

## Token优化捷径（重要）
1. **不要重复搜索已知的配置信息**：配置已硬编码在runner.py中。
2. **runner一次性完成所有产出**。
3. **配图搜索用image_count=3**。
4. **GitHub文件损坏检测**：下载后检查首行是否为 `#!/usr/bin/env python3`。
5. **docx依赖**：运行前确保 `pip install python-docx` 已安装。

## 文件分发规则
每次更新SKILL版本时，必须同步上传到三个平台：
1. GitHub仓库 `wowobai/dumate-skills` 的 `hot-news-brief/` 目录
2. 秒哒应用 `app-dbhlf1n9e3up`（通过miaoda_api.py chat更新后publish发布）
3. 本地通过file_export保存

## 版本历史
- V16: 新增去重规则、配图来源优先级、配图URL日期检查、配图视觉验证
- V15: 单篇草稿模式（5合1）、配图一致性校验、文件清理、选题规则强化、Token优化捷径
- V14: Supabase Edge Function直调、Bearer+apikey双认证、标准化3步诊断
- V13: 初始版本，通过appmiaoda.com/api调用
