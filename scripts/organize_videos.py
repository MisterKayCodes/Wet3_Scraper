import os
import shutil
import re
import sys

# Script moved to scripts/ folder
def organize_videos(creator_name, source_dir="../videos"):
    """
    Moves MP4 files from source_dir to a subfolder named after creator_name.
    """
    # Relative path from scripts/ to root
    source_path = os.path.abspath(os.path.join(os.path.dirname(__file__), source_dir))
    if not os.path.exists(source_path):
        print(f"[!] Source directory not found: {source_path}", flush=True)
        return

    target_dir = os.path.join(source_path, creator_name)
    if not os.path.exists(target_dir):
        os.makedirs(target_dir)
        print(f"[*] Created directory: {target_dir}", flush=True)
    
    all_items = os.listdir(source_path)
    files = [f for f in all_items if os.path.isfile(os.path.join(source_path, f))]
    
    print(f"[*] Scanning {len(files)} files in {source_dir}...")
    
    count = 0
    skipped = 0
    
    def sort_key(f):
        nums = re.findall(r'\d+', f)
        return int(nums[0]) if nums else 0
    
    files.sort(key=sort_key)

    for filename in files:
        if not filename.lower().endswith('.mp4'):
            continue
            
        match = re.search(r'(\d+)', filename)
        if match:
            num = match.group(1)
            new_filename = f"{creator_name}_{num}.mp4"
            
            old_path = os.path.join(source_path, filename)
            new_path = os.path.join(target_dir, new_filename)
            
            if os.path.exists(new_path):
                skipped += 1
                continue
            
            try:
                shutil.move(old_path, new_path)
                count += 1
            except Exception as e:
                print(f"[!] Error moving {filename}: {e}", flush=True)
    
    print(f"\n[+] Total Moved: {count}")
    print(f"[*] Total Skipped: {skipped}")

if __name__ == "__main__":
    if len(sys.argv) > 1:
        creator = sys.argv[1]
    else:
        creator = input("Enter Creator Name: ").strip()
    if creator:
        organize_videos(creator)
