#!/usr/bin/env python3
"""
Download papers from Zenodo using their API
"""
import requests
import time
import json

zenodo_records = [
    "20695562",
    "20682051", 
    "20681601",
    "20673206",
    "20659314",
    "20657391",
    "20635424"
]

for i, record_id in enumerate(zenodo_records, 1):
    try:
        print(f"\n[{i}/7] Fetching record {record_id}...")
        
        # Get record metadata from Zenodo API
        api_url = f"https://zenodo.org/api/records/{record_id}"
        response = requests.get(api_url, timeout=30)
        
        if response.status_code == 200:
            data = response.json()
            
            # Find PDF files
            files = data.get('files', [])
            if not files:
                print(f"  [WARN] No files found in record {record_id}")
                continue
            
            # Download first PDF file
            for file_info in files:
                filename = file_info.get('key', '')
                if filename.lower().endswith('.pdf'):
                    download_url = file_info.get('links', {}).get('self')
                    file_size = file_info.get('size', 0)
                    
                    if download_url:
                        print(f"  Found: {filename} ({file_size} bytes)")
                        print(f"  Downloading from: {download_url}")
                        
                        file_response = requests.get(download_url, timeout=60, stream=True)
                        if file_response.status_code == 200:
                            output_filename = f"paper{i}.pdf"
                            with open(output_filename, 'wb') as f:
                                for chunk in file_response.iter_content(chunk_size=8192):
                                    f.write(chunk)
                            print(f"  [OK] Saved as {output_filename}")
                            break
                        else:
                            print(f"  [FAIL] Download failed: Status {file_response.status_code}")
                    else:
                        print(f"  [WARN] No download link found")
            else:
                print(f"  [WARN] No PDF files found in record")
        else:
            print(f"  [FAIL] API request failed: Status {response.status_code}")
        
        time.sleep(2)  # Be nice to the server
        
    except Exception as e:
        print(f"  [ERROR] {e}")

print("\n[DONE] Download complete!")

# Made with Bob
