import asyncio
import os
import json
from playwright.async_api import async_playwright
from dotenv import load_dotenv

from downloader import async_decode_token, async_download_via_requests, get_cookies_and_ua
from telegram_utils import TelegramService

load_dotenv()

async def test_single_upload_async():
    print("--- Starting Async Single Upload Test ---", flush=True)
    
    # 1. Load sample data
    with open('scraped_data.json', 'r') as f:
        data = json.load(f)
    
    video = data[0] # Pick the first one
    caption = "Maliyaofficial - Test Upload (Async/Threaded) #00"
    file_path = "temp_test_video_async.mp4"
    
    # 2. Resolve Link
    session_data = get_cookies_and_ua()
    ua = session_data['user_agent']
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(user_agent=ua)
        await context.add_cookies(session_data['cookies'])
        page = await context.new_page()
        
        print("[*] Resolving link (Async, flush=True)...")
        sd_link = await async_decode_token(page, video['link'])
        await browser.close()
        
    if not sd_link:
        print("[!] Link resolution failed.", flush=True)
        return
        
    # 3. Download
    print("[*] Downloading (Async/Threaded, flush=True)...")
    success = await async_download_via_requests(sd_link, session_data['cookies'], ua, file_path)
    
    if not success:
        print("[!] Download failed.", flush=True)
        return
        
    # 4. Telegram Upload
    tg = TelegramService()
    await tg.start()
    await tg.resolve_channel(os.getenv("CHANNEL_LINK"))
    
    print("[*] Uploading...", flush=True)
    upload_success = await tg.upload_video(file_path, caption)
    
    if upload_success:
        print("[SUCCESS] Full Async flow verified!", flush=True)
    else:
        print("[FAIL] Telegram upload failed.", flush=True)
        
    # 5. Cleanup
    if os.path.exists(file_path):
        os.remove(file_path)
        print("[*] Cleaned up temp file.", flush=True)
        
    await tg.client.disconnect()

if __name__ == "__main__":
    asyncio.run(test_single_upload_async())
