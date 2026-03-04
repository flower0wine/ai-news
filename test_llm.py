import sys
import os
import io

# Fix Windows encoding issues
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

sys.path.insert(0, "package")

# Load env
from pathlib import Path

with open(".env.local", encoding="utf-8") as f:
    for line in f:
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            k, v = line.split("=", 1)
            os.environ[k] = v
os.environ["IS_LOCAL"] = "true"

from src.config import get_config
from src.api_client import AlphaSignalClient
from src.converter import HtmlToMarkdownConverter
from src.llm import LLMService

print("=== Step 1: Fetch AlphaSignal API ===")
client = AlphaSignalClient()
campaign = client.get_last_campaign()
subject = campaign.get("subject", "N/A")[:50]
print(f"Subject: {subject}...")
print(f"HTML length: {len(campaign.get('html', ''))} chars")

print("\n=== Step 2: Convert HTML to Markdown ===")
converter = HtmlToMarkdownConverter()
md = converter.convert(campaign.get("html", ""))
print(f"Markdown length: {len(md)} chars")

print("\n=== Step 3: Summarize with LLM (Volcengine) ===")
llm = LLMService()
print(f"Using model: {llm.model}")

# Use first 3000 chars to avoid too many tokens
md_sample = md[:3000]
original_url = "https://alphasignal.ai"

html_summary = llm.summarize_news(
    markdown_content=md_sample,
    original_url=original_url,
    subject=subject,
)

print(f"Summary length: {len(html_summary)} chars")
print(f"Summary preview:\n{html_summary[:500]}...")
