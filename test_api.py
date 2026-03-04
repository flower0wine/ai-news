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

print("=== Step 1: Fetch AlphaSignal API ===")
client = AlphaSignalClient()
campaign = client.get_last_campaign()
subject = campaign.get("subject", "N/A")
print(f"Subject: {subject[:50]}...")  # Truncate to avoid encoding issues
print(f"HTML length: {len(campaign.get('html', ''))} chars")

print("\n=== Step 2: Convert HTML to Markdown ===")
converter = HtmlToMarkdownConverter()
md = converter.convert(campaign.get("html", ""))
print(f"Markdown length: {len(md)} chars")
print(f"Preview:\n{md[:500]}...")
