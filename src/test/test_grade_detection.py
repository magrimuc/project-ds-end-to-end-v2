import os
import pytest
from pypdf import PdfReader
from src.ocr_engine import extract_text_from_pdf
from src.text_optimizer import TextOptimizer
from src.parser import detect_grade_from_text

def test_grade_detection_on_downloads():
    downloads_dir = "/home/martin/Dokumente/python/DSML/week8/week8a/data/downloads"
    assert os.path.exists(downloads_dir), f"Downloads directory {downloads_dir} does not exist"
    
    pdf_files = sorted([f for f in os.listdir(downloads_dir) if f.endswith(".pdf")], key=lambda x: int(x.split('_')[-1].split('.')[0]))
    assert len(pdf_files) > 0, "No PDF files found in downloads directory"
    
    detected_grades = {}
    
    for pdf_file in pdf_files:
        pdf_path = os.path.join(downloads_dir, pdf_file)
        with open(pdf_path, "rb") as f:
            pdf_bytes = f.read()
            
        # 1. Extract text (using extract_text_from_pdf like app does)
        raw_ocr = extract_text_from_pdf(pdf_bytes)
        
        # 2. Optimize text (using TextOptimizer like app does)
        optimizer = TextOptimizer()
        optimized_text = optimizer.optimize(raw_ocr)
        
        # 3. Detect grade (cluster assignment)
        grade = detect_grade_from_text(raw_ocr)
        
        if grade != "keine":
            detected_grades[pdf_file] = grade
            
    print(f"\nDetected grades: {detected_grades}")
    print(f"Total detected: {len(detected_grades)}")
    
    # Assert we can detect at least some grades (specifically 28 based on our run)
    assert len(detected_grades) == 28
    
    # Verify specific known cases
    assert detected_grades["school_list_1.pdf"] == "1"
    assert detected_grades["school_list_2.pdf"] == "2"
    assert detected_grades["school_list_7.pdf"] == "2"
    assert detected_grades["school_list_14.pdf"] == "5"
    assert detected_grades["school_list_16.pdf"] == "7"
    assert detected_grades["school_list_18.pdf"] == "10"
    assert detected_grades["school_list_23.pdf"] == "5"
    assert detected_grades["school_list_24.pdf"] == "11"

