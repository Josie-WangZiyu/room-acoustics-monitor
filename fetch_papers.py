import feedparser
import requests
import json
import os
from datetime import datetime
import re

# 1. 目标期刊 RSS 源配置
RSS_FEEDS = {
    "JASA": "https://pubs.aip.org/rss/site_1000030/1000006.xml",
    "JSV": "https://rss.sciencedirect.com/publication/science/0022460X",
    "Applied Acoustics": "https://rss.sciencedirect.com/publication/science/0003682X"
}

# 2. 从操作系统的环境变量中物理读取 API Key（由 GitHub Secrets 安全注入，不在代码中明文暴露）
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
API_URL = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-flash-latest:generateContent?key={GEMINI_API_KEY}"

def analyze_with_gemini(title, abstract):
    """调用 Gemini 分析文献物理机制"""
    prompt = f"""
    你是一个小空间声学（Small Room Acoustics）专家，研究方向包括低频简正模态、声能流分布、车内声场等。
    请阅读以下论文摘要，并严格返回 JSON 格式。
    首先判断是否与小空间声学强相关。如果相关，提取核心物理机制。
    
    输出格式模板：
    {{
        "is_relevant": true 或 false,
        "core_physics": "核心物理问题（限50字内）",
        "methodology": "实验或数值方法（如有限元、实测等，限50字内）",
        "key_conclusion": "关键结论（限100字内）",
        "limitations": "研究局限性或未来推测（限50字内）"
    }}

    Title: {title}
    Abstract: {abstract}
    """
    
    payload = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {"responseMimeType": "application/json"} # 强制输出原生 JSON
    }
    
    response = requests.post(API_URL, headers={'Content-Type': 'application/json'}, json=payload)
    if response.status_code == 200:
        return json.loads(response.json()['candidates'][0]['content']['parts'][0]['text'])
    return {"is_relevant": False}

def main():
    # 确保 Markdown 存放目录物理存在
    os.makedirs("content/posts", exist_ok=True)
    
    for journal, url in RSS_FEEDS.items():
        feed = feedparser.parse(url)
        for entry in feed.entries[:5]: # 测试时只抓最新的5篇，避免单次 API 消耗过大
            title = entry.title
            abstract = entry.summary if hasattr(entry, 'summary') else ""
            
            # 粗筛机制：必须包含基础声学词根
            coarse_keywords = ['room', 'space', 'enclosure', 'modal', 'acoustic', 'low frequency', 'cabin']
            if not any(k in (title + abstract).lower() for k in coarse_keywords):
                continue
            
            # 精筛与提取机制
            try:
                analysis = analyze_with_gemini(title, abstract)
            except Exception as e:
                print(f"API 调用失败 {title}: {e}")
                continue
                
            if analysis.get("is_relevant"):
                # 清理标题特殊字符以用作操作系统兼容的文件名
                safe_title = re.sub(r'[^\w\-_\. ]', '_', title)[:30]
                date_str = datetime.now().strftime("%Y-%m-%d")
                filename = f"content/posts/{date_str}-{safe_title}.md"
                
                # 构建 Hugo 支持的 Front Matter 和 Markdown 正文
                md_content = f"""---
title: "{title}"
date: {datetime.now().isoformat()}
tags: ["{journal}", "小空间声学监测"]
---

**期刊**: {journal} | **原文链接**: {entry.link}

### 💡 核心物理问题
{analysis.get('core_physics', '暂缺')}

### 🔬 实验与数值方法
{analysis.get('methodology', '暂缺')}

### 📊 关键结论
{analysis.get('key_conclusion', '暂缺')}

### ⚠️ 研究局限性
{analysis.get('limitations', '暂缺')}
"""
                with open(filename, "w", encoding="utf-8") as f:
                    f.write(md_content)
                print(f"已生成文献笔记: {filename}")

if __name__ == "__main__":
    if not GEMINI_API_KEY:
        print("致命错误：未找到系统环境变量 GEMINI_API_KEY")
    else:
        main()