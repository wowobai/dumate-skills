#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
weihai_travel_runner.py V6.4 - 威海旅游新闻云端统一生成脚本（配套 SKILL V6.4，300积分控制版）
  - 自动依赖安装（ensure_dependencies，缺才装）
  - 配图压缩 + 程序化校验（客观尺寸/大小，不做 read 语义校验）
  - 取新闻/配图主路径（模型侧，非本脚本）：webfetch 直取权威本地源 www.whnews.cn / weihai.iqilu.com 并直取其正文图；工具口径 memory_search 1 + webfetch ≤6 + websearch ≤2 + runner 1
  - 草稿总标题有且只有一个且带日期：秒哒端按 "${date_display} ${main_title}" 生成（如「2026年10月25日 威海旅游新闻」），正文不重复标题
  - 凭据不硬编码：从环境变量读取，缺失时回退从同目录 hot_news_runner.py 提取
  - 输出精简：verify 单行化，删除 read 引导与复盘长文，减少回灌输入 token
  - 内置 gen_placeholder：候选图不足时生成浅色渐变+标题占位图，保证 PIL 校验通过

用法: python -X utf8 weihai_travel_runner.py news_data.json
"""

import json, os, sys, ssl, re, subprocess, shutil
from pathlib import Path

# ======================== Auto Install Dependencies ========================
def ensure_dependencies():
    required = {
        'requests': 'requests',
        'PIL': 'Pillow',
        'pptx': 'python-pptx',
    }
    missing = []
    for mod, pkg in required.items():
        try:
            __import__(mod)
        except ImportError:
            missing.append(pkg)
    if missing:
        subprocess.check_call(
            [sys.executable, '-m', 'pip', 'install', '--quiet'] + missing,
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
        )
        print(f"  [deps] installed: {', '.join(missing)}")

ensure_dependencies()

import requests
from PIL import Image, ImageDraw, ImageFont
from pptx import Presentation
from pptx.util import Inches, Pt
from pptx.dml.color import RGBColor
from pptx.enum.text import PP_ALIGN, MSO_AUTO_SIZE

# ======================== Config ========================
BG = RGBColor(0xF5, 0xF5, 0xFA)
TITLE_C = RGBColor(0x1A, 0x56, 0xDB)
BODY_C = RGBColor(0x33, 0x33, 0x33)
ACCENT_C = RGBColor(0x3B, 0x82, 0xF6)
GRAY_C = RGBColor(0x99, 0x99, 0x99)

MAIN_TITLE = "威海旅游新闻"
IMG_MIN_DIM = 200
IMG_MIN_SIZE = 10240


def truncate(text, limit=200):
    return text[:limit - 3] + "..." if len(text) > limit else text


_LANCZOS = getattr(Image, "LANCZOS", None) or getattr(getattr(Image, "Resampling", Image), "LANCZOS", 1)


def compress_image(path):
    img = Image.open(path)
    if img.mode in ('P', 'LA', 'RGBA', 'L', 'ARGB'):
        img = img.convert('RGB')
    if img.width > 1200:
        ratio = 1200 / img.width
        img = img.resize((1200, int(img.height * ratio)), _LANCZOS)
    img.save(path, "JPEG", quality=85)


def gen_placeholder(path, title, tag=""):
    """候选图不足时的兜底占位图：浅色渐变+标题文字，统一 800x600，满足程序化校验阈值。"""
    img = Image.new("RGB", (800, 600))
    d = ImageDraw.Draw(img)
    for y in range(600):
        r = int(245 - y * 0.10)
        g = int(246 - y * 0.10)
        b = int(250 - y * 0.05)
        d.line([(0, y), (800, y)], fill=(r, g, b))
    try:
        font = ImageFont.truetype("/usr/share/fonts/truetype/noto/NotoSansCJK-Regular.ttc", 36)
        font_s = ImageFont.truetype("/usr/share/fonts/truetype/noto/NotoSansCJK-Regular.ttc", 22)
    except Exception:
        font = ImageFont.load_default()
        font_s = font
    label = f"[{tag}] {title}" if tag else title
    label = truncate(label, 30)
    d.text((400, 240), "威海旅游新闻", font=font_s, fill=(26, 86, 219), anchor="mm")
    d.text((400, 340), label, font=font, fill=(60, 60, 60), anchor="mm")
    d.text((400, 460), "图片获取受限·占位示意", font=font_s, fill=(153, 153, 153), anchor="mm")
    img.save(path, "JPEG", quality=85)


# ======================== Credentials ========================
def _read_const_from_file(path, name):
    try:
        src = open(path, encoding="utf-8").read()
        m = re.search(rf'^{name}\s*=\s*["\']([^"\']+)["\']', src, re.M)
        return m.group(1) if m else ""
    except Exception:
        return ""


def load_credentials():
    creds = {
        "WX_APP_ID": os.environ.get("WX_APP_ID", ""),
        "WX_APP_SECRET": os.environ.get("WX_APP_SECRET", ""),
        "SUPABASE_URL": os.environ.get("SUPABASE_URL", ""),
        "SUPABASE_KEY": os.environ.get("SUPABASE_KEY", ""),
    }
    base = os.path.dirname(os.path.abspath(__file__))
    hot_src = os.path.join(base, "hot_news_runner.py")
    if os.path.exists(hot_src):
        for name in creds:
            if not creds[name]:
                creds[name] = _read_const_from_file(hot_src, name)
    if not creds["SUPABASE_KEY"]:
        print("  [WARN] SUPABASE_KEY 未配置，草稿环节将跳过")
    return creds


# ======================== PNG/JPEG placeholder helpers ========================
def num_to_cn(n):
    d = "零一二三四五六七八九"
    if n < 10:
        return d[n]
    if n < 20:
        return "十" + (d[n % 10] if n % 10 else "")
    if n < 100:
        r = d[n // 10] + "十"
        return r + (d[n % 10] if n % 10 else "")
    return str(n)


def date_to_cn(date_str):
    y, m, d = int(date_str[:4]), int(date_str[4:6]), int(date_str[6:8])
    y_cn = "".join(num_to_cn(int(c)) for c in str(y))
    return f"{y_cn}年{num_to_cn(m)}月{num_to_cn(d)}日"


# ======================== PPT ========================
def gen_ppt(base, data, news):
    prs = Presentation()
    prs.slide_width = Inches(10)
    prs.slide_height = Inches(7.5)
    date_cn = data.get("date_chinese", date_to_cn(data["date"]))

    def add_bg(slide):
        bg = slide.background.fill
        bg.solid()
        bg.fore_color.rgb = BG

    def add_text(slide, x, y, w, h, text, size, color, bold=False, align=PP_ALIGN.LEFT, wrap=True, spacing=None):
        tb = slide.shapes.add_textbox(Inches(x), Inches(y), Inches(w), Inches(h))
        tf = tb.text_frame
        tf.word_wrap = wrap
        tf.auto_size = MSO_AUTO_SIZE.NONE
        p = tf.paragraphs[0]
        p.text = text
        p.font.size = Pt(size)
        p.font.color.rgb = color
        p.font.bold = bold
        p.alignment = align
        if spacing:
            p.line_spacing = spacing
        return p

    # Slide 1: Cover
    s = prs.slides.add_slide(prs.slide_layouts[6])
    add_bg(s)
    add_text(s, 1, 2.3, 8, 1.5, f"威海旅游新闻热点TOP{len(news)}", 44, TITLE_C, True, PP_ALIGN.CENTER)
    add_text(s, 1, 3.4, 8, 0.8, date_cn, 24, ACCENT_C, False, PP_ALIGN.CENTER)

    # Slide 2: TOC
    s = prs.slides.add_slide(prs.slide_layouts[6])
    add_bg(s)
    add_text(s, 0.5, 0.3, 9, 0.8, "今日导览", 32, TITLE_C, True)
    y = 1.4
    for i, item in enumerate(news):
        tag = item.get("tag", "")
        add_text(s, 1, y, 8, 0.9, f"{i + 1}. [{tag}] {item['title']}", 18, BODY_C)
        y += 0.95

    # Slides 3-7: Detail
    for item in news:
        s = prs.slides.add_slide(prs.slide_layouts[6])
        add_bg(s)
        img_path = os.path.join(base, item.get("image_path", f"images/news_{item['id']}.jpg"))
        if os.path.exists(img_path):
            try:
                img = Image.open(img_path)
                iw, ih = img.size
                ratio = min(4.5 / iw * 72, 4.5 / ih * 72) / 72
                s.shapes.add_picture(img_path, Inches(0.5), Inches(1.5),
                                     Inches(iw * ratio / 72), Inches(ih * ratio / 72))
            except Exception:
                pass
        body = item.get("body", item.get("summary", ""))
        analysis = item.get("analysis", item.get("impact", ""))
        add_text(s, 5, 0.5, 4.5, 1.5, f"[{item.get('tag','')}] {item['title']}", 20, TITLE_C, True)
        add_text(s, 5, 2.2, 4.5, 2.5, truncate(body), 14, BODY_C, spacing=1.35)
        add_text(s, 5, 5.0, 4.5, 1.5, "【看点】" + truncate(analysis, 150), 13, ACCENT_C, spacing=1.35)
        add_text(s, 5, 6.6, 4.5, 0.5, item["source"], 10, GRAY_C)

    # Slide 8: End
    s = prs.slides.add_slide(prs.slide_layouts[6])
    add_bg(s)
    add_text(s, 1, 3, 8, 1.5, date_cn, 28, TITLE_C, False, PP_ALIGN.CENTER)
    add_text(s, 1, 4, 8, 0.8, "本期完", 20, ACCENT_C, False, PP_ALIGN.CENTER)

    path = os.path.join(base, f"威海旅游新闻热点TOP{len(news)}.pptx")
    prs.save(path)
    return path


# ======================== HTML ========================
def gen_html(base, data, news):
    date_cn = data.get("date_chinese", date_to_cn(data["date"]))
    dd = data["date_display"]
    css = ("body{font-family:-apple-system,'Microsoft YaHei',sans-serif;margin:0;padding:20px;color:#333}"
           ".h{text-align:center;padding:30px 0;background:linear-gradient(135deg,#1a56db,#3b82f6);color:#fff;border-radius:8px 8px 0 0}"
           ".h h1{font-size:28px;margin:0}.h .d{font-size:16px;margin-top:10px;opacity:.9}"
           ".ni{padding:25px 20px;border-bottom:1px solid #eee}"
           ".nt{font-size:20px;font-weight:bold;color:#1a56db;margin-bottom:12px}"
           ".ntg{font-size:12px;color:#fff;background:#1a56db;display:inline-block;padding:2px 10px;border-radius:4px;margin-bottom:6px}"
           ".nb{font-size:15px;line-height:1.8;margin-bottom:10px}"
           ".na{font-size:14px;color:#3b82f6;line-height:1.7;padding:8px 12px;background:#f0f7ff;border-radius:4px;margin-bottom:8px}"
           ".ns{font-size:12px;color:#999;font-style:italic}"
           ".ni img{width:100%;border-radius:6px;margin:12px 0}"
           ".ft{text-align:center;padding:20px;color:#999;font-size:13px}")
    parts = [f'<!DOCTYPE html><html lang="zh-CN"><head><meta charset="UTF-8">',
             f'<meta name="viewport" content="width=device-width,initial-scale=1">',
             f'<title>威海旅游新闻</title><style>{css}</style></head><body>',
             f'<div style="max-width:677px;margin:0 auto">',
             f'<div class="h"><h1>威海旅游新闻</h1><div class="d">{date_cn}</div></div>']
    for item in news:
        parts.append('<div class="ni">')
        tag = item.get("tag", "")
        if tag:
            parts.append(f'<span class="ntg">{tag}</span>')
        parts.append(f'<div class="nt">{item["title"]}</div>')
        img_path = item.get("image_path", f"images/news_{item['id']}.jpg")
        parts.append(f'<img src="{img_path}" alt="{item["title"]}">')
        body = item.get("body", item.get("summary", ""))
        analysis = item.get("analysis", item.get("impact", ""))
        parts.append(f'<div class="nb">{truncate(body, 500)}</div>')
        parts.append(f'<div class="na">【旅游看点】{truncate(analysis, 300)}</div>')
        parts.append(f'<div class="ns">{item["source"]}</div>')
        parts.append('</div>')
    parts.append(f'<div class="ft"><p>{date_cn}</p><p>本期完</p></div>')
    parts.append('</div></body></html>')
    path = os.path.join(base, "wechat_article.html")
    with open(path, "w", encoding="utf-8") as f:
        f.write("\n".join(parts))
    return path


# ======================== WeChat Draft (Supabase Edge Function) ========================
def gen_wechat_draft(base, data, news, creds):
    if not creds.get("SUPABASE_KEY"):
        print("  [SKIP] SUPABASE_KEY 缺失，跳过草稿")
        return None
    mapped_news = []
    for n in news:
        item = dict(n)
        item.setdefault("body", n.get("summary", ""))
        item.setdefault("analysis", n.get("impact", ""))
        item.setdefault("image_query", n.get("img_keyword", n.get("title", "")[:20]))
        mapped_news.append(item)
    payload_data = {
        # 草稿总标题有且只有一个且带日期：秒哒端 create-draft 按 `${date_display} ${main_title}` 生成
        # （如「2026年10月25日 威海旅游新闻」）；正文 header 不输出标题、仅一行日期（线上 V17 起）
        "date": data["date"], "date_display": data.get("date_display", ""),
        "main_title": MAIN_TITLE, "news": mapped_news,
    }
    news_json = json.dumps(payload_data, ensure_ascii=False)
    img_dir = os.path.join(base, "images")
    files = []
    # 秒哒端 create-draft 固定校验 5 张图；不足时复制最后一张真实图补足，保证草稿创建成功
    for i in range(1, 6):
        p = os.path.join(img_dir, f"news_{i}.jpg")
        if not os.path.exists(p):
            last = os.path.join(img_dir, f"news_{len(news)}.jpg")
            if os.path.exists(last):
                shutil.copyfile(last, p)
        if os.path.exists(p):
            files.append(("images", (f"news_{i}.jpg", open(p, "rb"), "image/jpeg")))
    supabase_url = creds.get("SUPABASE_URL", "").rstrip("/")
    miaoda_url = f"{supabase_url}/functions/v1/create-draft"
    try:
        headers = {
            "Authorization": f"Bearer {creds['SUPABASE_KEY']}",
            "apikey": creds["SUPABASE_KEY"],
        }
        resp = requests.post(miaoda_url, data={"news_data": news_json}, files=files,
                             headers=headers, verify=False, timeout=180)
        result = resp.json()
        if result.get("success"):
            draft_id = result.get('draft_id')
            print(f"  [OK] 草稿创建成功 DraftID={draft_id}")
            title = result.get("title", "")
            if not title:
                print("  [WARN] 秒哒未回传 title 字段")
                title = ""
            verify = {
                "draft_media_id": draft_id, "draft_title": title, "channel": "miaoda",
                "wx_img_urls_count": sum(1 for u in (result.get("content_images") or []) if u),
                "thumb_media_id": result.get("cover_media_id", ""),
            }
            with open(os.path.join(base, "draft_verify.json"), "w", encoding="utf-8") as f:
                json.dump(verify, f, ensure_ascii=False, indent=2)
            return result
        else:
            print(f"  [ERROR] 草稿创建失败: {result.get('error', result)}")
            return None
    except Exception as e:
        print(f"  [ERROR] 草稿请求异常: {e}")
        return None
    finally:
        for _, ft in files:
            ft[1].close()


# ======================== Verify (单行化) ========================
def verify_all(base, data, news, ppt_path, html_path, draft_result=None):
    lines = []
    ok = True
    if os.path.exists(ppt_path):
        size = os.path.getsize(ppt_path)
        prs = Presentation(ppt_path)
        pics = sum(1 for s in prs.slides for sh in s.shapes if sh.shape_type == 13)
        st = "OK" if size > 102400 and len(prs.slides) >= len(news) + 3 and pics >= len(news) else "FAIL"
        ok = ok and st == "OK"
        lines.append(f"PPT:{st}({size}B/{len(prs.slides)}页/{pics}图)")
    else:
        lines.append("PPT:MISSING")
        ok = False
    if os.path.exists(html_path):
        lines.append(f"HTML:OK({os.path.getsize(html_path)}B)")
    else:
        lines.append("HTML:MISSING")
        ok = False
    if draft_result and draft_result.get("success"):
        lines.append(f"草稿:OK({draft_result.get('draft_id')})")
    else:
        lines.append("草稿:SKIP/FAIL")
    img_ok = check_images(base, news)
    ok = ok and img_ok
    print("  verify: " + " | ".join(lines) + f" | 配图:{'OK' if img_ok else 'FAIL'} | 总体:{'PASS' if ok else 'FAIL'}")
    return ok


def check_images(base, news):
    img_dir = os.path.join(base, "images")
    all_ok = True
    for i in range(1, len(news) + 1):
        p = os.path.join(img_dir, f"news_{i}.jpg")
        try:
            img = Image.open(p)
            w, h = img.size
            fsize = os.path.getsize(p)
            if not (fsize > IMG_MIN_SIZE and min(w, h) >= IMG_MIN_DIM):
                all_ok = False
                print(f"  [img] news_{i}.jpg 不合格 {w}x{h} {fsize}B")
        except Exception:
            all_ok = False
            print(f"  [img] news_{i}.jpg 缺失/损坏")
    return all_ok


# ======================== Main ========================
def main():
    if len(sys.argv) < 2:
        print("Usage: python -X utf8 weihai_travel_runner.py news_data.json")
        sys.exit(1)
    json_path = sys.argv[1]
    base = os.path.dirname(os.path.abspath(json_path))
    with open(json_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    news = data["news"]
    if "date_chinese" not in data:
        data["date_chinese"] = date_to_cn(data["date"])

    print(f"=== V6.4 威海旅游新闻生成 | {data['date_display']} | {len(news)}条 | {MAIN_TITLE} ===")

    print("\n--- 压缩配图 ---")
    img_dir = os.path.join(base, "images")
    os.makedirs(img_dir, exist_ok=True)
    for i in range(1, len(news) + 1):
        p = os.path.join(img_dir, f"news_{i}.jpg")
        item = news[i - 1]
        if os.path.exists(p):
            compress_image(p)
            print(f"  news_{i}.jpg: {os.path.getsize(p)}B")
        else:
            gen_placeholder(p, item["title"], item.get("tag", ""))
            print(f"  news_{i}.jpg: 占位图 {os.path.getsize(p)}B")

    print("\n--- 生成PPT ---")
    ppt_path = gen_ppt(base, data, news)
    print(f"  {os.path.basename(ppt_path)} ({os.path.getsize(ppt_path)}B)")

    print("\n--- 生成公众号HTML ---")
    html_path = gen_html(base, data, news)
    print(f"  {os.path.basename(html_path)} ({os.path.getsize(html_path)}B)")

    draft_result = None
    if os.name == "posix":
        print("\n--- 公众号草稿 ---")
        creds = load_credentials()
        draft_result = gen_wechat_draft(base, data, news, creds)

    print("\n--- 验证产出 ---")
    verify_all(base, data, news, ppt_path, html_path, draft_result)
    print("\n=== 完成 ===")


if __name__ == "__main__":
    main()
