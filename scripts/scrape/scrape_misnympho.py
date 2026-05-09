import os
import json
import time
import sys

# Ensure core is in path
sys.path.append(os.path.join(os.path.dirname(__file__), "..", ".."))

from core.scraper import get_profile_data
from core.downloader import process_video_queue # Using the robust version

def main():
    target_url = "https://wet3.click/user/misnympho"
    profile_name = "misnympho"
    
    print(f"[*] Starting FULL scrape and download for: {target_url}")
    
    # Ensure data directory exists
    data_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "data")
    if not os.path.exists(data_dir):
        os.makedirs(data_dir)
        
    # 1. Scrape video metadata (Skip if already exists in data folder)
    data_file = os.path.join(data_dir, f"{profile_name}_data.json")
    
    if os.path.exists(data_file) and os.path.getsize(data_file) > 0:
        print(f"[*] Found existing data at {data_file}. Skipping scrape step.", flush=True)
        with open(data_file, "r") as f:
            videos = json.load(f)
    else:
        # We set max_pages to None to get everything (estimated 32 pages)
        videos = get_profile_data(target_url, max_pages=None)
        if not videos:
            print("[!] No videos found. Check the URL or connection.", flush=True)
            return
        print(f"[SUCCESS] Scraped {len(videos)} items.", flush=True)
        # Save the data for safety
        with open(data_file, "w") as f:
            json.dump(videos, f, indent=4)
        print(f"[*] Scraped data saved to: {data_file}", flush=True)
        
    # 2. Process download queue
    # We'll save them to 'videos/misnympho/' and name them 'misnympho_XX'
    output_folder = f"videos/{profile_name}"
    process_video_queue(videos, output_dir=output_folder, prefix=profile_name)

if __name__ == "__main__":
    main()
