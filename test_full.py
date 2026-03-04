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
os.environ["LITELLM_DROP_PARAMS"] = "true"

from src.config import get_config
from src.api_client import AlphaSignalClient
from src.converter import HtmlToMarkdownConverter
from src.llm import LLMService
from src.email_sender import EmailSender

print("=== Step 1: Fetch AlphaSignal API ===")
client = AlphaSignalClient()
campaign = client.get_last_campaign()
subject = campaign.get("subject", "AI News")[:50]
print(f"Subject: {subject}...")

print("\n=== Step 2: Convert HTML to Markdown ===")
converter = HtmlToMarkdownConverter()
md = converter.convert(campaign.get("html", ""))
with open("test.md", "w", encoding="utf-8") as f:
    f.write(md)
print(f"Markdown length: {len(md)} chars")

print("\n=== Step 3: Summarize with LLM ===")
llm = LLMService()
# Use first 4000 chars for summarization
md_sample = md[:4000]
html_summary = llm.summarize_news(
    markdown_content=md_sample,
    original_url="https://alphasignal.ai",
    subject=subject,
)
print(f"Summary length: {len(html_summary)} chars")

print("\n=== Step 4: Send Email via Resend ===")
email_sender = EmailSender()
try:
    result = email_sender.send_campaign(
        subject=subject,
        html=html_summary,
    )
    print(f"Email sent successfully!")
    print(f"Result: {result}")
except Exception as e:
    print(f"Email send failed: {e}")
    import traceback

    traceback.print_exc()

print("\n=== Complete! ===")
