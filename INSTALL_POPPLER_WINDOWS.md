# Installing Poppler on Windows for PDF OCR

## Option 1: Using Pre-built Binaries (Recommended)

1. **Download Poppler for Windows:**
   - Visit: https://github.com/oschwartz10612/poppler-windows/releases/
   - Download the latest release (e.g., `Release-23.11.0-0.zip`)

2. **Extract the Archive:**
   - Extract the zip file to a location like `C:\poppler`
   - You should see a `bin` folder inside

3. **Add to PATH:**
   - Open System Properties → Environment Variables
   - Edit the `Path` variable
   - Add: `C:\poppler\Library\bin` (or wherever you extracted it)
   - Click OK to save

4. **Verify Installation:**
   ```powershell
   pdftoppm -h
   ```
   If you see help text, poppler is installed correctly.

5. **Install Python packages:**
   ```powershell
   python -m pip install pdf2image pytesseract
   ```

## Option 2: Using Conda (If you have Anaconda/Miniconda)

```powershell
conda install -c conda-forge poppler
python -m pip install pdf2image pytesseract
```

## Option 3: Using Chocolatey (If you have Chocolatey installed)

```powershell
choco install poppler
python -m pip install pdf2image pytesseract
```

## Verify Installation

After installation, test with:
```python
from pdf2image import convert_from_path
images = convert_from_path("test.pdf")
print(f"Converted {len(images)} pages")
```

## Note

If you don't want to install poppler, the system will still work for text-based PDFs. OCR (for scanned PDFs) will be disabled, but regular PDF extraction will continue to work.


