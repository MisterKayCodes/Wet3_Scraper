import os
import time
import base64
import urllib.parse
import requests
import json
import asyncio
import aiohttp
from playwright.sync_api import sync_playwright
from playwright.async_api import async_playwright
try:
    from playwright_stealth import stealth
except ImportError:
    stealth = None
from tqdm import tqdm
from utils.browser_utils import bypass_modal
from .hls_downloader import download_hls_stream
from .telegram_utils import TelegramService, upload_file_sync
import config

# Fix for Windows console unicode issues
import sys
import io
try:
    if sys.stdout.encoding.lower() != 'utf-8':
        import codecs
        sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer, 'strict')
        sys.stderr = codecs.getwriter('utf-8')(sys.stderr.buffer, 'strict')
except (AttributeError, TypeError):
    # Fallback for environments where encoding is not a string or missing
    pass

# Calculate project root (one level up from core/)
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SESSION_FILE = os.path.join(PROJECT_ROOT, "data", "session.json")

def get_cookies_and_ua():
    """Loads captured session data."""
    if os.path.exists(SESSION_FILE):
        try:
            with open(SESSION_FILE, "r") as f:
                return json.load(f)
        except Exception as e:
            print(f"[!] Error loading session.json: {e}", flush=True)
    return None

def resolve_monetized_link(monetized_url):
    """Fast extraction without browser for verification."""
    try:
        parsed_input = urllib.parse.urlparse(monetized_url)
        input_qs = urllib.parse.parse_qs(parsed_input.query)
        if 'token' in input_qs:
            token_b64 = urllib.parse.unquote(input_qs['token'][0])
            decoded_str = base64.b64decode(token_b64).decode('utf-8')
            data = json.loads(decoded_str)
            return data.get('u')
    except:
        pass
    return None

def decode_token(page, monetized_url, status_callback=None):
    """
    Extracts the 'sd' link from the monetized URL.
    FAST EXTRACTION: Checks for a direct token in the URL first to bypass broken redirects.
    """
    print(f"[*] Resolving: {monetized_url[:60]}...", flush=True)
    
    # --- PHASE 1: FAST EXTRACTION (No Browser Needed) ---
    parsed_input = urllib.parse.urlparse(monetized_url)
    input_qs = urllib.parse.parse_qs(parsed_input.query)
    
    if 'token' in input_qs:
        token_b64 = urllib.parse.unquote(input_qs['token'][0])
        try:
            decoded_str = base64.b64decode(token_b64).decode('utf-8')
            data = json.loads(decoded_str)
            if isinstance(data, dict) and 'u' in data:
                # If it's a Wasabi link, we skip Fast Extraction to use the Browser Capture flow
                if "wasabisys.com" in data['u']:
                    print(f"[*] Wasabi link detected, using Browser flow to ensure authorization...", flush=True)
                else:
                    print(f"[+] Fast Extraction SUCCESS: {data['u']}", flush=True)
                    return data['u']
        except Exception as e:
            print(f"[*] Fast Extraction skipped/failed: {e}", flush=True)

    # --- PHASE 1.5: RAW HTTP EXTRACTION (The Ghost Bypass) ---
    print(f"[*] Attempting Raw HTTP Bypass...", flush=True)
    try:
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8"
        }
        req_kwargs = {"headers": headers, "timeout": 15}
        if config.USE_PROXY:
            req_kwargs["proxies"] = {"http": config.PROXY_SERVER, "https": config.PROXY_SERVER}
        
        res = requests.get(monetized_url, **req_kwargs)
        if res.status_code == 200:
            import re
            # Force the regex to ONLY match tokens starting with 'eyJ' (which is Base64 for '{"')
            token_match = re.search(r'token=(eyJ[a-zA-Z0-9%+/=]+)', res.text)
            if not token_match:
                token_match = re.search(r'"token":"(eyJ[a-zA-Z0-9%+/=]+)"', res.text)
                
            if token_match:
                token_b64 = urllib.parse.unquote(token_match.group(1))
                try:
                    decoded_str = base64.b64decode(token_b64).decode('utf-8')
                    if '"u":' in decoded_str:
                        data = json.loads(decoded_str)
                        print(f"[+] Ghost Bypass SUCCESS: {data['u'][:60]}...", flush=True)
                        return data['u']
                except Exception as e:
                    print(f"[-] Ghost Bypass decode failed: {e}", flush=True)
            else:
                print("[-] Ghost Bypass: Token not found in HTML (Could be a Cloudflare challenge page)", flush=True)
        else:
            print(f"[-] Ghost Bypass: Blocked by server (HTTP {res.status_code})", flush=True)
    except Exception as e:
        print(f"[-] Ghost Bypass failed: {e}", flush=True)

    # --- PHASE 2: BROWSER RESOLUTION (Fallback) ---
    for attempt in range(3):
        if attempt > 0 and status_callback:
            status_callback(f"⚠️ <b>Timeout detected.</b> Retrying resolution (Attempt {attempt+1}/3)...")
            
        try:
            # Use domcontentloaded for speed on redirect-heavy pages
            # Use a realistic referer to look human
            referer = "https://wet3.click/user/chika1"
            # Increased timeout to 90s to give Cloudflare challenge pages time to load
            page.goto(monetized_url, wait_until="domcontentloaded", timeout=90000, referer=referer)
            time.sleep(5) # Wait for redirects to settle
            bypass_modal(page)
            
            current_url = page.url

            # Check if we are on a host like send.now
            if "send.now" in current_url:
                print(f"[+] Gateway reached: {current_url}", flush=True)
                return current_url
                
            # Check for direct 'sd' in query params first (Gateway flow)
            parsed = urllib.parse.urlparse(current_url)
            qs = urllib.parse.parse_qs(parsed.query)
            if 'sd' in qs:
                return qs['sd'][0]
                
            # Check for 'token' (Legacy flow)
            def find_token(s):
                if "token=" in s:
                    return s.split("token=")[1].split("&")[0]
                return None

            token_b64 = find_token(current_url)
            if not token_b64 and 'next' in qs:
                token_b64 = find_token(urllib.parse.unquote(qs['next'][0]))

            if token_b64:
                token_b64 = urllib.parse.unquote(token_b64)
                try:
                    # Attempt JSON parsing (New Pattern)
                    decoded_str = base64.b64decode(token_b64).decode('utf-8')
                    try:
                        data = json.loads(decoded_str)
                        if isinstance(data, dict) and 'u' in data:
                            print(f"[+] Direct CDN link found: {data['u']}", flush=True)
                            return data['u']
                    except:
                        # Fallback to URL parsing (Old Pattern)
                        parsed_dest = urllib.parse.urlparse(decoded_str)
                        dest_qs = urllib.parse.parse_qs(parsed_dest.query)
                        if 'sd' in dest_qs:
                            return dest_qs['sd'][0]
                except Exception as e:
                    print(f"[!] Error decoding token: {e}", flush=True)
            
            # --- PHASE 3: SOURCE EXTRACTION (Search for tokens in JS/HTML) ---
            content = page.content()
            import re
            # Look for strictly valid Base64 JSON tokens
            token_match = re.search(r'token=(eyJ[a-zA-Z0-9%+/=]+)', content)
            if not token_match:
                token_match = re.search(r'"token":"(eyJ[a-zA-Z0-9%+/=]+)"', content)
            
            if token_match:
                token_b64 = urllib.parse.unquote(token_match.group(1))
                print(f"[*] Found token in page source: {token_b64[:20]}...", flush=True)
                try:
                    decoded_str = base64.b64decode(token_b64).decode('utf-8')
                    if '"u":' in decoded_str:
                        data = json.loads(decoded_str)
                        return data['u']
                    elif "sd=" in decoded_str:
                        # Handle double encoded or nested links
                        sd_match = re.search(r'sd=([a-zA-Z0-9%+/=:?&_-]+)', decoded_str)
                        if sd_match:
                            return urllib.parse.unquote(sd_match.group(1))
                except:
                    pass
            
            # If we reach here and it's a 429, retry
            if "too many requests" in page.content().lower():
                print(f"[!] Rate limited (429, flush=True). Backing off {10 * (attempt + 1)}s...")
                time.sleep(10 * (attempt + 1))
                continue
                
            break # Success or non-retryable failure
        except Exception as e:
            print(f"[!] Resolution attempt {attempt+1} failed: {e}", flush=True)
            # Take a debug screenshot to see what's wrong
            try:
                os.makedirs("debug", exist_ok=True)
                page.screenshot(path=f"debug/debug_fail_res_{attempt+1}.png")
                print(f"[*] Debug screenshot saved: debug/debug_fail_res_{attempt+1}.png", flush=True)
            except: pass
            
            # Smart Auto-Refresh: Clear Cloudflare by visiting the root homepage
            if attempt < 2:
                print("[*] 🔄 Performing Anti-Bot Session Refresh (Clearing Cloudflare)...", flush=True)
                try:
                    page.goto("https://wet3.click/", timeout=30000, wait_until="domcontentloaded")
                    time.sleep(3)
                    bypass_modal(page)
                except Exception as refresh_err:
                    print(f"    [!] Refresh minor error (ignored): {refresh_err}", flush=True)
            
            time.sleep(5)
            
    return None

async def async_decode_token(page, monetized_url):
    """
    ASYNC version of decode_token.
    """
    print(f"[*] Resolving (Async, flush=True): {monetized_url[:60]}...")
    
    # --- PHASE 1: FAST EXTRACTION ---
    parsed_input = urllib.parse.urlparse(monetized_url)
    input_qs = urllib.parse.parse_qs(parsed_input.query)
    
    if 'token' in input_qs:
        token_b64 = urllib.parse.unquote(input_qs['token'][0])
        try:
            decoded_str = base64.b64decode(token_b64).decode('utf-8')
            data = json.loads(decoded_str)
            if isinstance(data, dict) and 'u' in data:
                if "wasabisys.com" in data['u']:
                    print(f"[*] Wasabi link detected in token (Async, flush=True), using Browser flow...")
                else:
                    print(f"[+] Fast Extraction SUCCESS (Async, flush=True): {data['u']}")
                    return data['u']
        except Exception as e:
            print(f"[*] Fast Extraction skipped/failed (Async, flush=True): {e}")

    # --- PHASE 2: BROWSER RESOLUTION ---
    for attempt in range(3):
        try:
            await page.goto(monetized_url, wait_until="domcontentloaded", timeout=90000)
            await asyncio.sleep(5)
            # bypass_modal is sync, but we can call it here if we convert it or just call the evaluate parts
            # For now, let's just use the sync version if possible or skip for async
            # (I'll keep it sync for now as downloader mostly uses sync playwright)
            bypass_modal(page)
            
            current_url = page.url

            # Check if we are on a host like send.now
            if "send.now" in current_url:
                print(f"[+] Gateway reached (Async, flush=True): {current_url}")
                return current_url
            parsed = urllib.parse.urlparse(current_url)
            qs = urllib.parse.parse_qs(parsed.query)
            if 'sd' in qs:
                return qs['sd'][0]
                
            def find_token(s):
                if "token=" in s:
                    return s.split("token=")[1].split("&")[0]
                return None

            token_b64 = find_token(current_url)
            if not token_b64 and 'next' in qs:
                token_b64 = find_token(urllib.parse.unquote(qs['next'][0]))

            if token_b64:
                token_b64 = urllib.parse.unquote(token_b64)
                try:
                    decoded_str = base64.b64decode(token_b64).decode('utf-8')
                    try:
                        data = json.loads(decoded_str)
                        if isinstance(data, dict) and 'u' in data:
                            return data['u']
                    except:
                        parsed_dest = urllib.parse.urlparse(decoded_str)
                        dest_qs = urllib.parse.parse_qs(parsed_dest.query)
                        if 'sd' in dest_qs:
                            return dest_qs['sd'][0]
                except Exception as e:
                    print(f"[!] Error decoding token (Async, flush=True): {e}")
            
            content = await page.content()
            if "too many requests" in content.lower():
                print(f"[!] Rate limited (Async, flush=True). Backing off {10 * (attempt + 1)}s...")
                await asyncio.sleep(10 * (attempt + 1))
                continue
                
            break
        except Exception as e:
            print(f"[!] Resolution attempt {attempt+1} failed (Async, flush=True): {e}")
            await asyncio.sleep(5)
            
    return None

def download_video_with_capture(context, sd_url, output_path, progress_callback=None, status_callback=None):
    """
    Uses the shared context to trigger and capture the video download.
    """
    print(f"[*] Opening host page: {sd_url}", flush=True)
    captured_url = None
    user_agent = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36"
    
    page = context.new_page()
    if stealth:
        try: stealth(page)
        except: pass
        
    def handle_request(request):
        nonlocal captured_url
        url = request.url
        # Capture Videos, Images, and BunnyCDN streams
        video_exts = [".mp4", ".m3u8", ".ts", ".m4s"]
        image_exts = [".jpg", ".jpeg", ".png", ".webp", ".gif"]
        cdn_domains = ["b-cdn.net", "allaccessfans.co", "ucarecdn.com"]
        
        is_video = any(ext in url.lower() for ext in video_exts) or "video" in request.headers.get("content-type", "").lower()
        is_image = any(ext in url.lower() for ext in image_exts) or "image" in request.headers.get("content-type", "").lower()
        is_cdn_media = any(domain in url.lower() for domain in cdn_domains) and (is_video or is_image)
        
        if is_video or is_image or is_cdn_media:
            # IGNORE KNOWN PREVIEW PATTERNS
            if "preview" in url.lower() or "/thumb" in url.lower():
                return

            if not captured_url:
                media_type = "video" if is_video else "image"
                print(f"[*] Captured potential {media_type}: {url[:60]}...", flush=True)
                captured_url = url

    context.on("request", handle_request)
    
    success = False
    try:
        print(f"[*] Navigating to {sd_url}...", flush=True)
        
        # --- ENHANCED STEALTH & SMART RETRY LOOP ---
        for attempt in range(3):
            if attempt > 0 and status_callback:
                status_callback(f"⚠️ <b>Page unresponsive.</b> Reloading capture tool (Attempt {attempt+1}/3)...")
                
            try:
                # Reduced timeout from 90s to 45s
                page.goto(sd_url, wait_until="commit", timeout=45000)
            except Exception as e:
                if "ERR_ABORTED" in str(e):
                    print("[*] Page aborted load (likely triggered a download, flush=True). Proceeding...")
                elif "Timeout" in str(e):
                    print(f"[!] Timeout on attempt {attempt+1}. Clearing state and retrying...", flush=True)
                    # Smart retry: clear cookies specific to this page to reset connection
                    context.clear_cookies()
                    time.sleep(2)
                    continue # Skip the rest of this attempt and try again
                else:
                    raise e
            
            bypass_modal(page)
            
            # Wait for either the button OR the challenge OR the player
            for _ in range(30):
                content = page.content().lower()
                if "security verification" in content or "verify you are human" in content:
                    if _ == 0: print("[!] Cloudflare Challenge detected. Waiting for it to clear...", flush=True)
                    time.sleep(2)
                elif page.query_selector("#downloadbtn") or page.query_selector("video") or page.query_selector("iframe") or captured_url:
                    # If we found a video or iframe or captured a URL, wait a bit for it to settle
                    # If the captured URL looks like a segment or small playlist, we might want to wait for the master
                    if captured_url and (".ts" in captured_url or "seg-" in captured_url):
                         captured_url = None # Reset and wait for the .m3u8 master
                         continue
                    
                    if not captured_url:
                        time.sleep(10) # Wait longer for HD switch
                    break
                else:
                    time.sleep(1)
            
            if captured_url:
                break
                
            btn = page.query_selector("#downloadbtn")
            if btn:
                print("[*] Download button found!", flush=True)
                btn.click()
                # Look for stream for up to 30s
                for i in range(30):
                    if captured_url: break
                    time.sleep(1)
                if captured_url:
                    break
            else:
                print(f"[!] Attempt {attempt+1}: Download button not visible. Page might be stuck or challenging us.", flush=True)
                # Force click the Turnstile if we can find it
                try:
                    checkbox = page.query_selector("iframe[src*='turnstile'] >> #checkbox")
                    if checkbox:
                        print("[*] Found Turnstile checkbox, attempting click...", flush=True)
                        checkbox.click()
                except: pass
                time.sleep(5)
                if attempt < 4: print("[*] Retrying page load...", flush=True)

        if captured_url:
            cookies = context.cookies()
            if ".m3u8" in captured_url.lower():
                 # Use the new stitcher for HLS streams
                 success = download_hls_stream(captured_url, output_path, headers={'User-Agent': user_agent}, cookies={c['name']: c['value'] for c in cookies}, progress_callback=progress_callback)
            else:
                 success = download_via_requests(captured_url, cookies, user_agent, output_path)
        else:
            print("[!] Stream not found in network traffic after all attempts.", flush=True)
            os.makedirs("debug", exist_ok=True)
            page.screenshot(path=f"debug/debug_no_stream_{os.path.basename(output_path)}.png")
            # Debug log the page text
            text = page.inner_text("body")[:500]
            print(f"[*] Page text snippet: {text}...", flush=True)
            
    except Exception as e:
        print(f"[!] Download error: {e}", flush=True)
    finally:
        page.close()
        context.remove_listener("request", handle_request)
        
    return success

def download_via_requests(url, browser_cookies, user_agent, output_path, referrer=None, origin=None):
    """Actual file download logic with progress bar."""
    # List of possible referrers to try if one fails
    referrers_to_try = [referrer] if referrer else []
    if "wasabisys.com" in url:
        if "https://send.now/" not in referrers_to_try:
            referrers_to_try.append("https://send.now/")
        if "https://nelb6o.wet3.click/" not in referrers_to_try:
            referrers_to_try.append("https://nelb6o.wet3.click/")

    cookie_dict = {c['name']: c['value'] for c in browser_cookies}
    
    for ref in referrers_to_try:
        print(f"[*] Attempting download with Referer: {ref}", flush=True)
        headers = {
            'User-Agent': user_agent,
            'Accept': '*/*',
            'Accept-Language': 'en-US,en;q=0.9',
            'Connection': 'keep-alive',
            'Sec-Fetch-Dest': 'video',
            'Sec-Fetch-Mode': 'cors',
            'Sec-Fetch-Site': 'cross-site',
            'Referer': ref,
            'Origin': ref.rstrip('/') if ref else None
        }
        
        req_kwargs = {"headers": headers, "cookies": cookie_dict, "stream": True, "timeout": 60}
        import config
        if config.USE_PROXY:
            req_kwargs["proxies"] = {"http": config.PROXY_SERVER, "https": config.PROXY_SERVER}

        try:
            with requests.get(url, **req_kwargs) as r:
                if r.status_code == 403:
                    print(f"[!] 403 Forbidden with Referer: {ref}. Trying next...", flush=True)
                    continue
                r.raise_for_status()
                content_type = r.headers.get("content-type", "").lower()
                
                # Auto-correct extension based on content-type
                final_path = output_path
                if "image" in content_type:
                    if not final_path.lower().endswith((".jpg", ".png", ".webp", ".jpeg")):
                        final_path = os.path.splitext(final_path)[0] + ".jpg"
                elif "video" in content_type:
                    if not final_path.lower().endswith((".mp4", ".ts", ".m4s")):
                        final_path = os.path.splitext(final_path)[0] + ".mp4"
                
                total_size = int(r.headers.get('content-length', 0))
                with open(final_path, 'wb') as f, tqdm(
                    desc=os.path.basename(final_path)[:30],
                    total=total_size,
                    unit='B', unit_scale=True, unit_divisor=1024
                ) as bar:
                    for chunk in r.iter_content(chunk_size=8192):
                        bar.update(f.write(chunk))
                
                if final_path != output_path:
                    print(f"[*] Saved as {os.path.basename(final_path)} (detected {content_type})", flush=True)
                return True
        except Exception as e:
            print(f"[!] Request attempt failed: {e}", flush=True)
            continue
            
    return False

async def async_download_via_requests(url, browser_cookies, user_agent, output_path, referrer=None, origin=None):
    """
    Async wrapper around the synchronous requests-based downloader.
    Uses asyncio.to_thread to avoid blocking the event loop.
    """
    return await asyncio.to_thread(
        download_via_requests, url, browser_cookies, user_agent, output_path, referrer, origin
    )

def process_video_queue(videos_list, start_index=1, output_dir="videos", prefix=None, headless=False, progress_callback=None, status_callback=None, tg_service=None):
    """
    OPTIMIZED: Uses a single browser context for the entire queue.
    """
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
        
    # Initialize Telegram Service if configured
    tg = tg_service
    if not tg and os.getenv("SESSION_STRING"):
        try:
            tg = TelegramService()
            # Use the client's own loop to avoid 'loop change' errors
            tg.client.loop.run_until_complete(tg.start())
            tg.client.loop.run_until_complete(tg.resolve_channel(os.getenv("CHANNEL_LINK")))
            tg.client.loop.run_until_complete(tg.send_log(f"🚀 Starting download queue for {len(videos_list)} items in <b>{output_dir}</b>"))
        except Exception as e:
            print(f"[!] Telegram init failed: {e}", flush=True)
            tg = None

    print(f"[*] Starting optimized download queue ({'HEADLESS' if headless else 'VISIBLE'}) for {len(videos_list)} items...", flush=True)
    
    import random
    user_agents = [
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36"
    ]
    
    session_data = get_cookies_and_ua()
    base_ua = session_data.get('user_agent') if session_data else user_agents[0]
    
    # PRIORITIZATION: Sort so videos (priority) come before images
    videos_list = sorted(videos_list, key=lambda x: x.get('type', 'video') != 'video')
    
    with sync_playwright() as p, tqdm(total=len(videos_list), desc="Overall Progress", unit="item") as pbar:
        # Using Chromium (Visible Mode for Debugging)
        # --- ANTI-BOT PROXY INTEGRATION ---
        launch_kwargs = {"headless": headless, "args": ["--disable-blink-features=AutomationControlled", "--no-sandbox"]}
        if config.USE_PROXY:
            launch_kwargs["proxy"] = {"server": config.PROXY_SERVER}
            print(f"[*] 🛡️ Launching Downloader via WARP Proxy: {config.PROXY_SERVER}", flush=True)

        browser = p.chromium.launch(**launch_kwargs)
        context = browser.new_context(user_agent=base_ua)
        
        # Inject cookies if we have them
        if session_data:
            print("[*] Injecting hijacked session cookies...", flush=True)
            cookies = session_data.get('cookies', [])
            unique_cookies = {}
            for cookie in cookies:
                key = (cookie['name'], cookie.get('domain'))
                unique_cookies[key] = cookie
            try:
                context.add_cookies(list(unique_cookies.values()))
            except Exception as e:
                print(f"[!] Warning: Some cookies failed to inject: {e}", flush=True)
            
        page = context.new_page()
        if stealth:
            try: stealth(page)
            except: pass
        page.add_init_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
        
        # --- MEMORY OPTIMIZATION: Block heavy assets ---
        page.route("**/*", lambda route: route.abort() if route.request.resource_type in ["image", "font", "stylesheet"] else route.continue_())
        
        
        for i, video in enumerate(videos_list):
            # ROTATION: Every 5 items, swap identity and refresh page
            if i > 0 and i % 5 == 0:
                print(f"[*] Camouflage rotation: Refreshing identity...", flush=True)
                page.close()
                context.set_extra_http_headers({"User-Agent": random.choice(user_agents)})
                page = context.new_page()
                if stealth:
                    try: stealth(page)
                    except: pass
                page.add_init_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
                page.route("**/*", lambda route: route.abort() if route.request.resource_type in ["image", "font", "stylesheet"] else route.continue_())
                time.sleep(random.randint(5, 10))

            count = start_index + i
            
            # 1. Determine Identity & Extension
            is_video = video.get('type', 'video') == 'video'
            ext = ".mp4" if is_video else ".jpg"
            
            if prefix:
                filename = f"{prefix}_{count:02d}{ext}"
            else:
                clean_title = "".join([c for c in video['title'] if c.isalnum() or c in (' ', '_')]).strip()
                if not clean_title or clean_title == "▶":
                    clean_title = f"{'Video' if is_video else 'Image'}_{count}"
                filename = f"{clean_title}_{count}{ext}"
            
            output_path = os.path.join(output_dir, filename)
            uploaded_flag = f"{output_path}.uploaded"
            
            # --- SMART RESUME LOGIC ---
            if os.path.exists(uploaded_flag):
                print(f"[*] Skipping already fully processed/uploaded: {filename}", flush=True)
                continue
                
            needs_download = True
            if os.path.exists(output_path) and os.path.getsize(output_path) > 2048:
                print(f"[*] File already downloaded but not uploaded. Resuming upload for: {filename}", flush=True)
                needs_download = False

            print(f"\n[{count}/{len(videos_list) + start_index - 1}] Task: {video['title']} ({video['type'].upper()})", flush=True)
            if status_callback: 
                status_callback(f"⬇️ <b>Processing:</b> {count}/{len(videos_list)}\n📂 <code>{filename}</code>")
            
            # --- PHASE 1: DOWNLOAD (If needed) ---
            success = False
            if needs_download:
                # 1. Resolve Link (using shared page)
                sd_link = decode_token(page, video['link'], status_callback=status_callback)
                
                if sd_link:
                    # --- SMART ROUTING ---
                    is_hls = ".m3u8" in sd_link.lower()
                    is_direct = False
                    if not is_hls:
                        if "ucarecdn.com" in sd_link or any(ext in sd_link.lower() for ext in ['.mp4', '.m4v', '.mov']):
                            if "wasabisys.com" not in sd_link: # Wasabi is NEVER direct
                                is_direct = True
                    
                    if is_hls:
                        # Route directly to HLS stitcher — never use browser for a stream URL
                        print(f"[*] Direct HLS stream detected. Stitching...", flush=True)
                        cookies = {c['name']: c['value'] for c in context.cookies()}
                        success = download_hls_stream(sd_link, output_path, headers={'User-Agent': base_ua}, cookies=cookies, progress_callback=progress_callback)
                    elif is_direct:
                        print(f"[+] Downloading DIRECT link...", flush=True)
                        success = download_via_requests(sd_link, context.cookies(), base_ua, output_path, referrer="https://nelb6o.wet3.click/")
                    else:
                        print(f"[*] Using Browser Capture for: {sd_link}", flush=True)
                        success = download_video_with_capture(context, sd_link, output_path, progress_callback=progress_callback, status_callback=status_callback)
                else:
                    print(f"[!] Critical failure: Failed to resolve link for: {video['title']}. Skipping to next video.", flush=True)
                    continue # Skip this video instead of crashing the whole bot
            else:
                success = True # We skipped download, so pretend it was successful so we can upload
            
            # --- PHASE 2: UPLOAD ---
            if success:
                if needs_download:
                    print(f"[SUCCESS] Saved to {output_path}", flush=True)
                    
                # --- TELEGRAM UPLOAD (Deadlock-Free) ---
                if tg:
                    # Resolve channel: prefer in-memory config, fall back to persisted settings
                    channel_link = config.CHANNEL_LINK
                    if not channel_link:
                        try:
                            from utils.settings_manager import load_settings
                            channel_link = load_settings().get("target_channel", "")
                        except: pass
                    
                    if not channel_link:
                        print("[!] CHANNEL_LINK not set — skipping upload. Use /set_channel in the bot.", flush=True)
                    else:
                        caption = f"👤 Creator: {prefix or 'Unknown'}\n📁 File: {filename}"
                        print(f"[*] ⏳ Starting deadlock-free upload for: {filename}", flush=True)
                        upload_success = upload_file_sync(output_path, caption, channel_link)
                        if upload_success:
                            print(f"[+] ✅ Upload to Telegram successful!", flush=True)
                            open(uploaded_flag, 'w').close()
                            try:
                                os.remove(output_path)
                                print(f"[*] 🗑️ Deleted local file: {filename}", flush=True)
                            except: pass
                        else:
                            print(f"[!] Upload failed for {filename}. Will retry on next run.", flush=True)
            else:
                print(f"[!] Failed to download: {video['title']}", flush=True)
                if tg:
                    try:
                        def safe_run_fail(coro):
                            if tg.client.loop.is_running():
                                return asyncio.run_coroutine_threadsafe(coro, tg.client.loop).result()
                            else:
                                return tg.client.loop.run_until_complete(coro)
                        safe_run_fail(tg.send_log(f"❌ Failed to download <code>{video['title']}</code>"))
                    except Exception as e:
                        print(f"[!] Telegram Log Crashed: {e}", flush=True)
            
            pbar.update(1)
            # Random jitter cooldown (20 to 45 seconds) to avoid rate limits
            jitter = random.randint(20, 45)
            time.sleep(jitter)
            
        browser.close()
    print("\n[*] Queue processing finished.", flush=True)

if __name__ == "__main__":
    pass
