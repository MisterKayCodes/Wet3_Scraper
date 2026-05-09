import os
import json
from core.scraper import get_profile_data
from core.downloader import process_video_queue

class ScrapeOrchestrator:
    """
    Orchestrates the workflow between scraping and downloading.
    Matches the 'Services' pattern from Mr_Assistant.
    """
    
    def __init__(self, data_dir="data", output_dir="videos"):
        self.data_dir = data_dir
        self.output_dir = output_dir
        if not os.path.exists(self.data_dir):
            os.makedirs(self.data_dir)

    def run_full_pipeline(self, profile_url, profile_name, mode="all", headless=True, progress_callback=None, tg_service=None):
        """
        1. Scrapes profile (if JSON not found)
        2. Downloads based on mode (1, 10, all)
        """
        data_file = os.path.join(self.data_dir, f"{profile_name}_data.json")
        
        # --- PHASE 1: SCRAPE ---
        if os.path.exists(data_file) and os.path.getsize(data_file) > 0:
            print(f"[*] Service: Found existing data for {profile_name}. Loading...")
            with open(data_file, "r") as f:
                videos = json.load(f)
        else:
            print(f"[*] Service: Starting fresh scrape for {profile_name}...")
            videos = get_profile_data(profile_url, max_pages=None, headless=headless)
            if not videos:
                return {"status": "error", "message": "Scraping failed or no items found."}
            
            with open(data_file, "w") as f:
                json.dump(videos, f, indent=4)

        # --- PHASE 2: FILTER BY MODE ---
        if mode == "1":
            queue = [videos[0]] if videos else []
        elif mode == "10":
            queue = videos[:10]
        else:
            queue = videos

        if not queue:
            return {"status": "error", "message": "No items to download."}

        # --- PHASE 3: DOWNLOAD ---
        print(f"[*] Service: Starting download of {len(queue)} items (Mode: {mode})...")
        process_video_queue(
            queue, 
            output_dir=os.path.join(self.output_dir, profile_name), 
            prefix=profile_name,
            headless=headless,
            progress_callback=progress_callback,
            tg_service=tg_service
        )
        
        return {"status": "success", "count": len(queue), "file": data_file}
