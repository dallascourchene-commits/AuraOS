import sys

try:
    import PyPDF2
    has_pypdf2 = True
except ImportError:
    has_pypdf2 = False

try:
    import pdfplumber
    has_pdfplumber = True
except ImportError:
    has_pdfplumber = False

def extract_with_pypdf2(pdf_path):
    """Extract text using PyPDF2"""
    with open(pdf_path, 'rb') as file:
        reader = PyPDF2.PdfReader(file)
        text = []
        for i, page in enumerate(reader.pages[:10]):  # First 10 pages
            text.append(f"\n--- Page {i+1} ---\n")
            text.append(page.extract_text())
        return ''.join(text)

def extract_with_pdfplumber(pdf_path):
    """Extract text using pdfplumber"""
    with pdfplumber.open(pdf_path) as pdf:
        text = []
        for i, page in enumerate(pdf.pages[:10]):  # First 10 pages
            text.append(f"\n--- Page {i+1} ---\n")
            text.append(page.extract_text())
        return ''.join(text)

if __name__ == "__main__":
    pdfs = [
        "Second_Paper.pdf",
        "Third_Paper.pdf",
        "AuraOS__A_Polysynthetic_Cognitive_Substrate_for_High-Dimensional_Edge_Orchestration_and_Visual_Code_Topology.pdf"
    ]
    
    if not has_pypdf2 and not has_pdfplumber:
        print("ERROR: Neither PyPDF2 nor pdfplumber is installed.")
        print("Install with: pip install PyPDF2 pdfplumber")
        sys.exit(1)
    
    for pdf_path in pdfs:
        try:
            print(f"\n{'='*80}")
            print(f"EXTRACTING: {pdf_path}")
            print('='*80)
            
            if has_pdfplumber:
                text = extract_with_pdfplumber(pdf_path)
            else:
                text = extract_with_pypdf2(pdf_path)
            
            # Save to text file
            output_path = pdf_path.replace('.pdf', '_extracted.txt')
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(text)
            
            print(f"SUCCESS: Extracted to {output_path}")
            print(f"Preview (first 500 chars):\n{text[:500]}")
            
        except Exception as e:
            print(f"ERROR extracting {pdf_path}: {e}")
    
    print(f"\n{'='*80}")
    print("Extraction complete!")

# Made with Bob
