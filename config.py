import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Telegram API Credentials
API_ID = int(os.getenv("API_ID", 0))
API_HASH = os.getenv("API_HASH", "")
SESSION_STRING = os.getenv("SESSION_STRING", "")
BOT_TOKEN = os.getenv("BOT_TOKEN", "")

# Destination Settings
CHANNEL_LINK = os.getenv("CHANNEL_LINK", "")

# Scraper Settings
DEFAULT_HEADLESS = True  # Set to False for local debugging
DOWNLOAD_DIR = "videos"
DATA_DIR = "data"

# Anti-Bot Settings (Cloudflare WARP or proxies)
USE_PROXY = False  # Set to True on VPS after installing WARP
PROXY_SERVER = "socks5://127.0.0.1:40000"  # Default Cloudflare WARP proxy port

# Validation
if not API_ID or not API_HASH:
    print("[!] Warning: API_ID or API_HASH not found in environment. Telegram features will be disabled.")
