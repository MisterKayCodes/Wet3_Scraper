import os
import json
import sys

# Add project root to path so we can import from core
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from core.scraper import get_profile_videos
from core.downloader import process_video_queue

def main():
    # 1. SETUP - Change these for each new creator
    creator_name = "zelda"
    target_url = f"https://wet3.click/user/{creator_name}"
    
    # Paths (Absolute based on project root)
    project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    data_file = os.path.join(project_root, "data", f"{creator_name}_data.json")
    output_dir = os.path.join(project_root, "videos", creator_name)
    
    print(f"[*] Starting scrape and download for: {target_url}", flush=True)
    
    # 2. Scrape video metadata (Skip if already exists)
    if os.path.exists(data_file) and os.path.getsize(data_file) > 0:
        print(f"[*] Found existing {data_file}. Skipping scrape step.", flush=True)
        with open(data_file, "r") as f:
            videos = json.load(f)
    else:
        print("[*] No existing data found. Starting fresh scrape...", flush=True)
        videos = get_profile_videos(target_url)
        if not videos:
            print("[!] No videos found or scrape failed.", flush=True)
            return
            
        # Ensure data dir exists
        os.makedirs(os.path.dirname(data_file), exist_ok=True)
        with open(data_file, "w") as f:
            json.dump(videos, f, indent=4)
        print(f"[SUCCESS] Scraped {len(videos)} videos.", flush=True)
    
    # 3. Process download queue
    process_video_queue(videos, output_dir=output_dir, prefix=creator_name)

if __name__ == "__main__":
    main()
