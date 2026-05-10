import time

def bypass_modal(page):
    """Bypasses modals (ad-walls, donation popups) that block interaction."""
    print("[*] Checking for modals/overlays...", flush=True)
    for i in range(3): # Try up to 3 times
        try:
            # 1. Try clicking common close button selectors (and Cloudflare Checkbox)
            selectors = [
                "[aria-label='Close']",
                ".close",
                "button:has-text('X')",
                "button:has-text('Understand')",
                "button:has-text('Close')",
                "button:has-text('Understood')",
                ".modal-close",
                ".close-modal",
                "button:has-text('UNLOCK FEED')"
            ]
            for selector in selectors:
                if page.is_visible(selector):
                    print(f"[+] Clicking modal closer: {selector}", flush=True)
                    page.click(selector)
                    time.sleep(1)
            
            # --- CLOUDFLARE TURNSTILE SOLVER ---
            try:
                # Cloudflare check boxes are inside iframes
                for frame in page.frames:
                    if frame.locator(".cf-turnstile-wrapper").is_visible() or frame.locator("input[type='checkbox']").is_visible():
                        print("[+] Found Cloudflare Checkbox. Attempting click...", flush=True)
                        frame.locator("input[type='checkbox'], .cf-turnstile-wrapper").first.click()
                        time.sleep(3)
            except: pass
            
            # 2. Specific for wet3 'Unlock Feed' buttons that are ad-walls
            if page.is_visible("button:has-text('UNLOCK FEED')"):
                 print("[+] Ad-wall detected. Clicking UNLOCK FEED...", flush=True)
                 page.click("button:has-text('UNLOCK FEED')")
                 time.sleep(1)

            # 3. Check for overlays that prevent clicking (JS removal)
            page.evaluate('''() => {
                const overlays = document.querySelectorAll('.modal, .overlay, .popup, [class*="modal"], [class*="overlay"]');
                overlays.forEach(el => el.remove());
                document.body.style.overflow = 'auto'; // Re-enable scrolling if blocked
            }''')
        except:
            pass
