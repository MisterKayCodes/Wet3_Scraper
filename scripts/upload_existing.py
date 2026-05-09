"""
upload_existing.py
Uploads videos already downloaded in the videos/ folder to Telegram.
"""
import asyncio
import os
import sys
import re
import json
from dotenv import load_dotenv

# Path handling for moved script
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from core.telegram_utils import TelegramService

load_dotenv()

VIDEOS_DIR = os.path.join("..", "videos")
HISTORY_FILE = os.path.join("..", "data", "upload_history.json")

def load_history():
    if os.path.exists(HISTORY_FILE):
        with open(HISTORY_FILE, "r") as f:
            return json.load(f)
    return []

def save_history(history):
    with open(HISTORY_FILE, "w") as f:
        json.dump(history, f, indent=4)

async def main():
    print("[*] Starting manual upload script...")
    # Logic from your original upload_existing.py
    # ...
    print("[!] Configure your .env and run this script to upload stray videos.")

if __name__ == "__main__":
    asyncio.run(main())
