import sys
import time

import requests

# Fix Windows console encoding
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')

papers = [
    ("https://zenodo.org/records/20695562", "paper1.pdf"),
    ("https://zenodo.org/records/20682051", "paper2.pdf"),
    ("https://zenodo.org/records/20681601", "paper3.pdf"),
    ("https://zenodo.org/records/20673206", "paper4.pdf"),
    ("https://zenodo.org/records/20659314", "paper5.pdf"),
    ("https://zenodo.org/records/20657391", "paper6.pdf"),
    ("https://zenodo.org/records/20635424", "paper7.pdf"),
]

for url, filename in papers:
    try:
        print(f"Downloading {filename} from {url}...")
        # First get the record page to find the actual file URL
        response = requests.get(url, timeout=30)
        if response.status_code == 200:
            # Try to find PDF link in the page
            file_url = f"{url}/files/article.pdf?download=1"
            print(f"Attempting to download from {file_url}")

            file_response = requests.get(file_url, timeout=60, stream=True)
            if file_response.status_code == 200:
                with open(filename, 'wb') as f:
                    for chunk in file_response.iter_content(chunk_size=8192):
                        f.write(chunk)
                print(f"[OK] Successfully downloaded {filename}")
            else:
                print(f"[FAIL] Failed to download {filename}: Status {file_response.status_code}")
        else:
            print(f"[FAIL] Failed to access {url}: Status {response.status_code}")

        time.sleep(2)  # Be nice to the server
    except Exception as e:
        print(f"[ERROR] Error downloading {filename}: {e}")

print("\nDownload complete!")

# Made with Bob
