"""
[AURA_MASTER_KEY]
ST3GG_BASE: 0xa8fa-[Q-SYS:6C2848D106FBD645]
DIKWP_TIER: WISDOM
PWFST_ALIGNMENT: GIZAAGI'IN (Mutual Benefit)
DEPENDENCIES: PyPDF2
FUNCTIONS: None
SYNOPSIS: [CODE]
def optimized_fallback():
    pass
[/CODE]
[/AURA_MASTER_KEY]
"""
#!/usr/bin/env python3
"""
Extract text from newly downloaded papers 1-4
"""
import PyPDF2

papers = [
    ("paper1.pdf", "paper1_extracted.txt"),  # 7th Paper
    ("paper2.pdf", "paper2_extracted.txt"),  # 6th Paper
    ("paper3.pdf", "paper3_extracted.txt"),  # 5th Paper
    ("paper4.pdf", "paper4_extracted.txt"),  # 4th Paper
]

for pdf_file, output_file in papers:
    try:
        print(f"\n{'='*80}")
        print(f"EXTRACTING: {pdf_file}")
        print('='*80)

        with open(pdf_file, 'rb') as f:
            reader = PyPDF2.PdfReader(f)
            num_pages = len(reader.pages)

            with open(output_file, 'w', encoding='utf-8') as out:
                # Extract first 15 pages or all pages if less
                pages_to_extract = min(15, num_pages)

                for page_num in range(pages_to_extract):
                    page = reader.pages[page_num]
                    text = page.extract_text()
                    out.write(f"\n--- Page {page_num + 1} ---\n")
                    out.write(text)

            print(f"SUCCESS: Extracted {pages_to_extract} pages to {output_file}")

            # Show preview
            with open(output_file, encoding='utf-8') as f:
                preview = f.read(500)
                print(f"Preview (first 500 chars):\n{preview}")

    except Exception as e:
        print(f"ERROR: {e}")

print("\n" + "="*80)
print("Extraction complete!")

# Made with Bob
