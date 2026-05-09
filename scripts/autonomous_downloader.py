import json
import os
import time
import sys
from downloader import process_video_queue

# Fix for Windows console unicode issues
try:
    if sys.stdout.encoding.lower() != 'utf-8':
        import codecs
        sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer, 'strict')
        sys.stderr = codecs.getwriter('utf-8')(sys.stderr.buffer, 'strict')
except (AttributeError, TypeError):
    # Fallback for environments where encoding is not a string or missing
    pass

def main():
    print("====================================", flush=True)
    print("   AUTONOMOUS DOWNLOADER (RETRY ENGINE, flush=True)")
    print("====================================", flush=True)
    
    scraped_file = "scraped_data.json"
    if not os.path.exists(scraped_file):
        print(f"[ERROR] {scraped_file} not found. Please run the scraper first.", flush=True)
        return
        
    with open(scraped_file, "r", encoding='utf-8') as f:
        videos = json.load(f)
        
    print(f"[*] Found {len(videos, flush=True)} videos in {scraped_file}")
    
    if not os.path.exists("videos"):
        os.makedirs("videos")
        
    iteration = 1
    while True:
        print(f"\n--- ITERATION {iteration} ---", flush=True)
        
        # Filter for videos that don't exist or are too small
        to_download = []
        for i, v in enumerate(videos):
            count = i + 1
            clean_title = "".join([c for c in v['title'] if c.isalnum() or c in (' ', '_')]).strip()
            if not clean_title or clean_title == "▶":
                clean_title = f"Video_{count}"
            filename = f"{clean_title}_{count}.mp4"
            output_path = os.path.join("videos", filename)
            
            if not os.path.exists(output_path) or os.path.getsize(output_path) < 1024 * 1024:
                to_download.append(v)
                
        if not to_download:
            print("\n[SUCCESS] All videos downloaded!", flush=True)
            break
            
        print(f"[*] {len(to_download, flush=True)} videos remaining. Starting batch...")
        try:
            process_video_queue(to_download)
        except Exception as e:
            print(f"[!] Batch interrupted: {e}", flush=True)
            
        print("\n[*] Iteration finished. Resting for 30s before next pass...", flush=True)
        time.sleep(30)
        iteration += 1

if __name__ == "__main__":
    main()
