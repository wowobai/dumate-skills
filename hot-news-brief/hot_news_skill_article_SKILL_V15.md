# hot_news_skill_article_V15

## 概述
每日热点文娱新闻自动生成技能。搜索当天热点文娱新闻，生成PPT、新闻稿docx、公众号HTML、公众号草稿（4合1）。
运行脚本：`hot_news_runner.py`（从GitHub拉取最新版）。

## 选题规则（必须遵守）
1. **第一条新闻不得是票房总结类**。票房总结配图容易与文不符（如图片显示55亿但文中写60亿），且作为头条吸引力不足。应选择具体影片、演出、赛事等有明确视觉素材的新闻作为第一条。
2. 只选发布当天或前一日发生的新闻，超过2天的旧闻一律排除。
3. 固定5条新闻，不多不少。
4. 搜索后筛选时不能只看"多来源"和"非百家号"，事件时效性是第一过滤条件。

## 配图规则
1. 每条新闻必须配1张图，共5张，保存为 `images/news_1.jpg` ~ `images/news_5.jpg`。
2. 配图必须与新闻内容匹配，搜索时用具体关键词（影片名+海报、人名+事件场景等）。
3. 下载后用 `compress_image()` 压缩（宽度>1200缩放，JPEG quality=85）。
4. 下载后检查图片格式，webp需转为JPEG。
5. runner内置 `check_image_consistency()` 校验每张图尺寸、文件大小、与标题对应关系。

## 公众号草稿模式（V15核心变更）
**5条新闻合并为1篇图文（单article模式），不是5篇独立图文。**
- Edge Function `createDraft` 已修改为将5条新闻拼接到一个article的content中。
- 文章标题：`{date_chinese} 热点文娱新闻`（如"二零二六年七月二十九日 热点文娱新闻"）。
- 封面图（thumb_media_id）：用 `images[0]`（即 `news_1.jpg`，第一条最热新闻的配图）上传为永久素材。
- 内容图片：所有5张图都通过 `uploadimg` 上传为正文内嵌图，`contentImageUrls[i]` 对应 `news[i]` 的配图。
- `show_cover_pic` 设为 `1`。

## Supabase Edge Function 直调捷径（V14建立，V15沿用）
**不再通过 appmiaoda.com/api 调用，直接调 Supabase Edge Function。**

### 配置
- Supabase URL: `https://backend.appmiaoda.com/projects/supabase340340166944145408`
- Edge Function 端点: `{SUPABASE_URL}/functions/v1/create-draft`
- Anon Key: 从秒哒前端JS的 `VITE_SUPABASE_ANON_KEY` 提取（已硬编码在runner.py中）
- 请求头: `Authorization: Bearer {key}` + `apikey: {key}`（双认证头，缺一不可）
- 请求格式: `multipart/form-data`，包含 `news_data`（JSON字符串）+ `images`（图片文件数组）

### 秒哒服务器固定IP
- IP: `106.13.244.120`（连续3次测试一致，确认固定不变）
- 已加入微信公众号IP白名单，永久生效。

### 草稿失败标准化3步诊断
1. `GET {SUPABASE_URL}/functions/v1/server-ip` → 查白名单（返回token=白名单OK，返回40164=IP不在白名单）
2. `POST {SUPABASE_URL}/functions/v1/create-draft` → 查部署（报"could not find an appropriate entrypoint"=未部署成功）
3. 通过 `miaoda_api.py chat` 远程修复Edge Function部署问题

## 产出交付规则
1. 固定5条新闻，只发1个草稿（单article模式）。
2. 只导出4个文件：PPT、docx、HTML、news_data.json。
3. 多余散落文件用 `cleanup_workspace()` 自动清理。
4. `cleanup_workspace()` 使用 `os.path.abspath(__file__)` 排除自身脚本不被删除。

## 执行流程（Token优化版）

### 步骤1: 拉取最新SKILL和runner
```
GitHub仓库: wowobai/dumate-skills → hot-news-brief/
  - hot_news_skill_article_SKILL_V15.md（本文件）
  - hot_news_runner.py（V15）
```
**注意**: GitHub上的文件可能因base64双重编码而损坏。如果下载后内容以 `IyEvdXNyL2Jpbi9lbnY` 开头，说明是base64编码的，需要用GitHub API下载原始字节：
```python
import requests, base64
url = "https://api.github.com/repos/wowobai/dumate-skills/contents/hot-news-brief/hot_news_runner.py"
resp = requests.get(url, headers={"Accept": "application/vnd.github.v3+json"})
content = base64.b64decode(resp.json()["content"]).decode("utf-8")
```

### 步骤2: 搜索新闻
- 用 `websearch` 搜索当天热点文娱新闻，`freshness=pw`（一周内）。
- 搜索关键词：`7月29日 热点文娱新闻 2026`、具体领域关键词等。
- 筛选5条，遵守选题规则（第一条不得是票房总结类）。

### 步骤3: 搜索配图
- 为每条新闻用 `websearch` 搜索匹配图片，`image_count=3`。
- 下载图片到 `images/news_1.jpg` ~ `images/news_5.jpg`。
- 压缩、格式检查、一致性校验。

### 步骤4: 构建news_data.json
```json
{
  "date": "20260729",
  "date_display": "2026.07.29",
  "date_chinese": "二零二六年七月二十九日",
  "news": [
    {"id": "1", "title": "...", "body": "...", "source": "...", "analysis": "...", "image_query": "..."},
    ...共5条
  ]
}
```

### 步骤5: 运行runner
```bash
python -X utf8 hot_news_runner.py "20260729热点新闻/news_data.json"
```
runner自动完成：压缩配图 → 生成PPT → 生成docx → 生成HTML → 创建公众号草稿 → 验证 → 配图一致性校验 → 清理散落文件。

### 步骤6: 导出文件
用 `file_export` 导出4个文件：PPT、docx、HTML、news_data.json。

## Token优化捷径（重要）
1. **不要重复搜索已知的配置信息**：Supabase URL、Anon Key、秒哒IP、微信凭据等已硬编码在runner.py中，不需要每次搜索。
2. **runner一次性完成所有产出**：PPT+docx+HTML+草稿+验证+清理，一次调用完成，不需要分步执行。
3. **配图搜索用image_count=3**：一次搜索获取3张候选图，选最匹配的下载。
4. **miaoda chat修改Edge Function时用简短指令**：如"把createDraft改为单篇：articles只放1个元素，content拼接5条新闻，标题用date_chinese"。
5. **GitHub文件损坏检测**：下载后检查首行是否为 `#!/usr/bin/env python3`，如果不是则是base64编码损坏，用GitHub API重新下载。
6. **cleanup_workspace自动清理**：不需要手动find+rm散落文件，runner自动完成。
7. **docx依赖**：运行前确保 `pip install python-docx` 已安装，cleanup会删除__pycache__导致下次运行需要重装。

## 文件分发规则
每次更新SKILL版本时，必须同步上传到三个平台：
1. GitHub仓库 `wowobai/dumate-skills` 的 `hot-news-brief/` 目录
2. 秒哒应用 `app-dbhlf1n9e3up`（通过miaoda_api.py chat更新后publish发布）
3. 本地通过file_export保存到 `D:\dumate\plan\hot_news_plan\`

## 版本历史
- V15: 单篇草稿模式（5合1）、配图一致性校验、文件清理、选题规则强化、Token优化捷径
- V14: Supabase Edge Function直调、Bearer+apikey双认证、标准化3步诊断
- V13: 初始版本，通过appmiaoda.com/api调用
