import subprocess
import tempfile
import os

def run_local_ocr(image_bytes: bytes) -> str:
    """
    Runs local Tesseract OCR on the provided image bytes.
    Uses subprocess to call the tesseract binary.
    """
    # Write image to a temporary file
    with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as temp_img:
        temp_img.write(image_bytes)
        temp_img_path = temp_img.name

    try:
        # Run tesseract redirecting output to stdout
        # -l deu+eng specifies both German and English
        cmd = ["tesseract", temp_img_path, "stdout", "-l", "deu+eng"]
        result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, check=True)
        return result.stdout
    except subprocess.CalledProcessError as e:
        raise RuntimeError(f"Tesseract OCR failed: {e.stderr}")
    finally:
        # Cleanup temporary image file
        if os.path.exists(temp_img_path):
            os.remove(temp_img_path)

def run_gemini_ocr(image_bytes: bytes, mime_type: str, api_key: str) -> str:
    """
    Runs Gemini multimodal OCR to extract structured items and quantities from the image.
    """
    from google import genai
    from google.genai import types
    import json

    client = genai.Client(api_key=api_key)
    
    prompt = """
    Erkenne alle bestellten Artikel auf dem Foto der Schulbedarfsliste.
    Gib das Ergebnis als valides JSON-Array zurück. Jedes Objekt im Array muss folgende Schlüssel haben:
    - "raw_text": der gelesene Text des Artikels (ohne die Mengenangabe)
    - "quantity": die erkannte Anzahl / Menge als Ganzzahl (Standard ist 1, falls keine Zahl erkennbar ist)
    
    Beispiel-Ausgabe:
    [
      {"raw_text": "Bleistift HB Faber Castell", "quantity": 2},
      {"raw_text": "Rechenheft DIN A4 kariert", "quantity": 5}
    ]
    
    Gib ausschließlich das reine JSON-Array zurück, ohne Markdown-Formatierung wie ```json ... ```.
    """

    try:
        response = client.models.generate_content(
            model='gemini-2.5-flash',
            contents=[
                types.Part.from_bytes(
                    data=image_bytes,
                    mime_type=mime_type
                ),
                prompt
            ]
        )
        
        # Clean response text in case model still wraps it in markdown code blocks
        clean_text = response.text.strip()
        if clean_text.startswith("```"):
            lines = clean_text.splitlines()
            if lines[0].startswith("```"):
                lines = lines[1:]
            if lines[-1].startswith("```"):
                lines = lines[:-1]
            clean_text = "\n".join(lines).strip()
            
        return clean_text
    except Exception as e:
        raise RuntimeError(f"Gemini API request failed: {e}")

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
