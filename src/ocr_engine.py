import subprocess
import tempfile
import os

def run_local_ocr(image_bytes: bytes) -> str:
    """
    Runs local Tesseract OCR on the provided image bytes.
    Uses subprocess to call the tesseract binary.
    """
    import shutil
    
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
        result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, check=True)
        return result.stdout
    except subprocess.CalledProcessError as e:
        raise RuntimeError(f"Tesseract OCR failed: {e.stderr}")
    finally:
        # Cleanup temporary image file
        if os.path.exists(temp_img_path):
            os.remove(temp_img_path)

_MODEL = None
_PROCESSOR = None

def get_granite_model_and_processor():
    """
    Loads and caches the ibm-granite/granite-docling-258M model and processor.
    """
    global _MODEL, _PROCESSOR
    if _MODEL is None or _PROCESSOR is None:
        import torch
        from transformers import AutoProcessor, AutoModelForVision2Seq
        
        device = "cuda" if torch.cuda.is_available() else "cpu"
        model_id = "ibm-granite/granite-docling-258M"
        
        _PROCESSOR = AutoProcessor.from_pretrained(model_id)
        _MODEL = AutoModelForVision2Seq.from_pretrained(model_id).to(device)
        
    return _MODEL, _PROCESSOR

def run_gemini_ocr(image_bytes: bytes, mime_type: str, api_key: str) -> str:
    """
    Runs local ibm-granite/granite-docling-258M VLM to extract structured items and quantities.
    Falls back to local Tesseract OCR if it fails.
    """
    import io
    import json
    from PIL import Image
    
    try:
        from parser import parse_ocr_text
    except ImportError:
        from src.parser import parse_ocr_text

    try:
        # Load model and processor
        model, processor = get_granite_model_and_processor()
        
        # Prepare image
        image = Image.open(io.BytesIO(image_bytes))
        if image.mode != "RGB":
            image = image.convert("RGB")
            
        import torch
        device = next(model.parameters()).device
        
        # Prepare inputs
        prompt = "Convert this page to docling."
        inputs = processor(text=prompt, images=image, return_tensors="pt").to(device)
        
        # Generate text
        with torch.no_grad():
            outputs = model.generate(**inputs, max_new_tokens=1024)
            
        generated_text = processor.decode(outputs[0], skip_special_tokens=True)
        
        # Parse text to structured format
        parsed_items = parse_ocr_text(generated_text)
        return json.dumps(parsed_items, ensure_ascii=False)
        
    except Exception as e:
        # Fallback to local Tesseract OCR
        try:
            raw_text = run_local_ocr(image_bytes)
            parsed_items = parse_ocr_text(raw_text)
            return json.dumps(parsed_items, ensure_ascii=False)
        except Exception as fallback_err:
            raise RuntimeError(f"OCR failed. Local model error: {e}. Tesseract fallback error: {fallback_err}")

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
