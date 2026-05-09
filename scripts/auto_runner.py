import subprocess
import time
import sys
import os

def run_with_recovery():
    print("====================================", flush=True)
    print("   SMART AUTO-RECOVERY ENGINE v2", flush=True)
    print("====================================", flush=True)
    
    creator = input("\nEnter Creator Name (e.g., zelda): ").strip()
    if not creator: return

    # Calculate the absolute path to the scrape folder
    script_dir = os.path.dirname(os.path.abspath(__file__))
    script_path = os.path.join(script_dir, "scrape", f"scrape_{creator}.py")
    
    consecutive_failures = 0
    attempt = 1

    while True:
        print(f"\n[ATTEMPT #{attempt}] Starting scraper...", flush=True)
        
        start_time = time.time()
        result = subprocess.run(["py", script_path], check=False)
        duration = time.time() - start_time

        if result.returncode == 0:
            print(f"\n[SUCCESS] Script finished normally.", flush=True)
            break 
        else:
            print(f"\n[!] Script crashed (Code: {result.returncode}).", flush=True)

        # DECISION LOGIC:
        print("\n[!] Failure detected. Entering 5-minute cooldown...", flush=True)
        for i in range(300, 0, -1):
            if i % 60 == 0: print(f"[*] Cooling down... {i//60}m left", flush=True)
            time.sleep(1)
            
        attempt += 1

if __name__ == "__main__":
    try:
        run_with_recovery()
    except KeyboardInterrupt:
        print("\n[!] Stopped by user.")
