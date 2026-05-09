import os
import sys
import time
import base64
import urllib.parse
from playwright.sync_api import sync_playwright

def decode_token(token_str):
    try:
        decoded = base64.b64decode(token_str).decode('utf-8')
        print(f"[*] Decoded Token: {decoded}", flush=True)
        parsed_url = urllib.parse.urlparse(decoded)
        query_params = urllib.parse.parse_qs(parsed_url.query)
        if 'sd' in query_params:
            return query_params['sd'][0]
    except Exception as e:
        print(f"[!] Error decoding token: {e}", flush=True)
    return None

def deep_inspect_sd_link(sd_url):
    print(f"[*] Deep Inspecting: {sd_url}", flush=True)
    
    with sync_playwright() as p:
        # Launch with a persistent context or at least a visible UA
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
            viewport={"width": 1280, "height": 720}
        )
        page = context.new_page()
        
        # Monitor all requests
        def handle_request(request):
            if request.method == "POST":
                print(f"[POST] {request.url}", flush=True)
                print(f"      Payload: {request.post_data}", flush=True)

        page.on("request", handle_request)
        page.on("response", lambda r: print(f"[RESP] {r.status} {r.url}", flush=True) if r.status >= 400 else None)

        try:
            print("[*] Navigating...", flush=True)
            page.goto(sd_url, wait_until="load")
            time.sleep(5)
            
            # Check for timers
            timers = page.query_selector_all("[id*='timer'], [class*='timer']")
            for t in timers:
                print(f"[!] Found potential timer element: {t.inner_text(, flush=True)}")
            
            # Look for the download button
            btn = page.query_selector("#downloadbtn")
            if btn:
                print(f"[+] Download button found: {btn.inner_text(, flush=True)}")
                # Hover first
                btn.hover()
                time.sleep(1)
                # Click it
                print("[*] Clicking...", flush=True)
                btn.click()
                
                # Wait for something to happen
                print("[*] Waiting for result...", flush=True)
                for _ in range(15):
                    time.sleep(2)
                    if "challenge" in page.url.lower():
                        print("[!!!] Hit a CAPTCHA/Challenge wall.", flush=True)
                        break
                    # Check for new text on page
                    # Maybe it says "Click here to download" now?
                    content = page.content().lower()
                    if "click here to download" in content or ".mp4" in content:
                        print("[?] Detected change in content. Might be ready.", flush=True)
                        break
            else:
                print("[!] Download button NOT found.", flush=True)
            
            # Success snapshot
            page.screenshot(path="final_inspect.png")
            print("[*] Saved final_inspect.png", flush=True)
            
        except Exception as e:
            print(f"[ERROR] {e}", flush=True)
            
        browser.close()

if __name__ == "__main__":
    token = "aHR0cHM6Ly9uZWxiNm8ud2V0My5jbGljay9wbGF5ZXIvODg0NDA/c2Q9aHR0cHMlM0ElMkYlMkZzZW5kLm5vdyUyRjJoMmY0d3MxeHVmbyZjdD0xJnNraXBfYWQ9MQ=="
    sd_link = decode_token(token)
    if sd_link:
        deep_inspect_sd_link(sd_link)
