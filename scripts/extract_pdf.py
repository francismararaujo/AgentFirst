
import sys
import os

try:
    from pypdf import PdfReader
except ImportError:
    print("MISSING_LIB")
    sys.exit(0)

try:
    file_path = r"c:\Users\00872784\Documents\Estudos\ProjetoAWS\docs\Agent Discovery Workshop Read Out.pdf"
    if not os.path.exists(file_path):
        print(f"File not found: {file_path}")
        sys.exit(1)

    reader = PdfReader(file_path)
    text = ""
    print(f"--- START PDF CONTENT ({len(reader.pages)} pages) ---")
    for i, page in enumerate(reader.pages):
        print(f"--- PAGE {i+1} ---")
        print(page.extract_text())
    print("--- END PDF CONTENT ---")

except Exception as e:
    print(f"Error reading PDF: {e}")
