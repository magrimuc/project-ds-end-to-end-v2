import subprocess
import tempfile
import os

def run_local_ocr(image_bytes: bytes) -> str:
    """
    Runs local Tesseract OCR on the provided image bytes.
    Uses subprocess to call the tesseract binary.
    """
    import shutil
    
    # 1. Locate the dictionary/words file
    base_dir = os.path.dirname(os.path.abspath(__file__))
    words_path = os.path.join(base_dir, "data", "tesseract_words.txt")
    if not os.path.exists(words_path):
        words_path = os.path.join(base_dir, "..", "data", "tesseract_words.txt")
        
    # 2. Write a temporary config file pointing to this words file if it exists
    config_temp_path = None
    if os.path.exists(words_path):
        try:
            with tempfile.NamedTemporaryFile(suffix=".config", mode="w", delete=False, encoding="utf-8") as temp_cfg:
                temp_cfg.write(f"user_words_file {words_path}\n")
                config_temp_path = temp_cfg.name
        except Exception as e:
            print(f"Warning: Could not create temporary Tesseract config: {e}")
            
    # Write image to a temporary file
    with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as temp_img:
        temp_img.write(image_bytes)
        temp_img_path = temp_img.name

    try:
        # Determine tesseract command/executable path
        tesseract_cmd = os.environ.get("TESSERACT_PATH", "tesseract")
        
        if tesseract_cmd == "tesseract" and not shutil.which(tesseract_cmd):
            # Check common default paths on Windows
            user_profile = os.environ.get("USERPROFILE", "")
            local_app_data = os.environ.get("LOCALAPPDATA", "")
            
            common_windows_paths = [
                r"C:\Program Files\Tesseract-OCR\tesseract.exe",
                r"C:\Program Files (x86)\Tesseract-OCR\tesseract.exe"
            ]
            if user_profile:
                common_windows_paths.append(os.path.join(user_profile, r"AppData\Local\Tesseract-OCR\tesseract.exe"))
                common_windows_paths.append(os.path.join(user_profile, r"AppData\Local\Programs\Tesseract-OCR\tesseract.exe"))
            if local_app_data:
                common_windows_paths.append(os.path.join(local_app_data, r"Tesseract-OCR\tesseract.exe"))
                common_windows_paths.append(os.path.join(local_app_data, r"Programs\Tesseract-OCR\tesseract.exe"))
                
            found = False
            for path in common_windows_paths:
                if os.path.exists(path):
                    tesseract_cmd = path
                    found = True
                    break
            
            if not found:
                raise FileNotFoundError(
                    f"Tesseract executable not found in PATH or standard directories: {common_windows_paths}. "
                    "Please install Tesseract or define the 'TESSERACT_PATH' environment variable (e.g. in your .env file) "
                    "pointing to your tesseract.exe."
                )
                    
        # Run tesseract redirecting output to stdout
        # -l deu+eng specifies both German and English
        cmd = [tesseract_cmd, temp_img_path, "stdout", "-l", "deu+eng"]
        if config_temp_path:
            cmd.append(config_temp_path)
            
        result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, check=True)
        return result.stdout
    except subprocess.CalledProcessError as e:
        raise RuntimeError(f"Tesseract OCR failed: {e.stderr}")
    finally:
        # Cleanup temporary files
        if os.path.exists(temp_img_path):
            os.remove(temp_img_path)
        if config_temp_path and os.path.exists(config_temp_path):
            os.remove(config_temp_path)

def extract_text_from_pdf(pdf_bytes: bytes) -> str:
    """
    Extracts text page-by-page from a PDF file using pypdf.
    """
    import io
    from pypdf import PdfReader

    try:
        reader = PdfReader(io.BytesIO(pdf_bytes))
        extracted_text = []
        for page in reader.pages:
            text = page.extract_text()
            if text:
                extracted_text.append(text)
        return "\n".join(extracted_text)
    except Exception as e:
        raise RuntimeError(f"Error reading PDF: {e}")
