import os
import shutil
import glob

def organize():
    # 1. Create directories
    folders = ['core', 'scripts', 'data', 'debug', 'logs', 'research_logs']
    for folder in folders:
        if not os.path.exists(folder):
            os.makedirs(folder)
            print(f"[*] Created folder: {folder}")

    # 2. Define move mappings
    moves = [
        # Core logic
        (['scraper.py', 'downloader.py', 'hls_downloader.py', 'utils.py', 'telegram_utils.py', 'authorize.py'], 'core'),
        # Scripts
        (['scrape_chika1.py', 'scrape_altegurrl.py', 'autonomous_downloader.py', 'batch_uploader.py', 'verify_optimized.py'], 'scripts'),
        # Data
        (['*_data.json', 'scraped_data.json', 'session.json', 'upload_history.json'], 'data'),
        # Debug / Logs
        (['*.png', '*.html', 'error_state.png', 'player_debug.png'], 'debug'),
        # Research Logs
        (['research_*.png'], 'research_logs'),
        (['*.txt', '*.log'], 'logs')
    ]

    for patterns, dest in moves:
        for pattern in patterns:
            for file in glob.glob(pattern):
                if os.path.exists(file):
                    try:
                        shutil.move(file, os.path.join(dest, os.path.basename(file)))
                        print(f"[OK] Moved {file} -> {dest}/")
                    except Exception as e:
                        print(f"[!] Could not move {file}: {e}")

    print("\n[SUCCESS] Workspace organized!")
    print("Next step: Use 'python scripts/scrape_altegurrl.py' to start your new scrape.")

if __name__ == "__main__":
    organize()
