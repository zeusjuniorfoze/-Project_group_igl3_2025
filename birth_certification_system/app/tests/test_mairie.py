# test_pdfkit.py
import sys
print("🔧 Python utilisé :", sys.executable)

import pdfkit
print("✅ pdfkit est bien importé")

# Crée un PDF simple
pdfkit.from_string("Hello 👋, ceci est un test PDF", "test_output.pdf")
print("📄 Fichier PDF généré : test_output.pdf")
