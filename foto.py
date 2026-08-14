import re
import streamlit as st
import os
import sys
import pandas as pd
from PIL import Image
import base64
import urllib.parse

# Ensure root directory is in sys.path
sys.path.append(os.path.abspath(os.path.dirname(__file__)))

from src.ocr_engine import run_local_ocr
from src.parser import parse_ocr_text
from src.matcher import load_products, find_best_match, predict_subject, predict_document_level, split_by_colors
from src.text_optimizer import TextOptimizer

# Initialize cart and scan state
if "cart" not in st.session_state:
    st.session_state.cart = {}
if "scan_results" not in st.session_state:
    st.session_state.scan_results = []
if "raw_text" not in st.session_state:
    st.session_state.raw_text = ""
if "raw_ocr_text" not in st.session_state:
    st.session_state.raw_ocr_text = ""
if "optimized_with_cl_info" not in st.session_state:
    st.session_state.optimized_with_cl_info = ""
if "data_url" not in st.session_state:
    st.session_state.data_url = None

def reset_scan_state():
    st.session_state.scan_results = []
    st.session_state.raw_text = ""
    st.session_state.raw_ocr_text = ""
    st.session_state.optimized_with_cl_info = ""
    st.session_state.data_url = None
    if "last_analyzed_foto" in st.session_state:
        del st.session_state["last_analyzed_foto"]

# App Header
st.markdown('<div class="main-header">🎒 School Supplies Photo Scanner</div>', unsafe_allow_html=True)
st.markdown('<div class="sub-header">Optimized for mobile devices. Take a photo of a school list to digitize it instantly.</div>', unsafe_allow_html=True)

# Document actions placed at the top if a document is loaded
if st.session_state.get("data_url"):
    col_doc, col_copier = st.columns([3, 7])
    with col_doc:
        st.link_button("📄 View Document", st.session_state.data_url, use_container_width=True)
    with col_copier:
        import urllib.parse
        encoded_ocr = urllib.parse.quote(st.session_state.get("raw_ocr_text", ""))
        encoded_opt = urllib.parse.quote(st.session_state.get("raw_text", ""))
        encoded_cl = urllib.parse.quote(st.session_state.get("optimized_with_cl_info", ""))
        
        js_code = f"""
        <div style="display: flex; gap: 8px; font-family: sans-serif; height: 38px; align-items: center;">
            <button id="btn-ocr" style="flex: 1; height: 100%; border-radius: 4px; background-color: #262730; color: #fff; border: 1px solid #464855; cursor: pointer; font-size: 13px; font-weight: 500;">📋 Raw Text (OCR)</button>
            <button id="btn-opt" style="flex: 1; height: 100%; border-radius: 4px; background-color: #262730; color: #fff; border: 1px solid #464855; cursor: pointer; font-size: 13px; font-weight: 500;">📋 Optimized Text</button>
            <button id="btn-cl" style="flex: 1; height: 100%; border-radius: 4px; background-color: #262730; color: #fff; border: 1px solid #464855; cursor: pointer; font-size: 13px; font-weight: 500;">📋 Optimized + Cl Info</button>
        </div>
        <script>
        function copyText(encodedText, successMsg) {{
            const text = decodeURIComponent(encodedText);
            if (navigator.clipboard && navigator.clipboard.writeText) {{
                navigator.clipboard.writeText(text).then(() => {{
                    alert(successMsg);
                }}).catch(err => {{
                    fallbackCopy(text, successMsg);
                }});
            }} else {{
                fallbackCopy(text, successMsg);
            }}
        }}
        function fallbackCopy(text, successMsg) {{
            const textArea = document.createElement("textarea");
            textArea.value = text;
            document.body.appendChild(textArea);
            textArea.select();
            try {{
                document.execCommand('copy');
                alert(successMsg);
            }} catch (err) {{
                alert('Copy failed.');
            }}
            document.body.removeChild(textArea);
        }}
        document.getElementById('btn-ocr').addEventListener('click', () => copyText("{encoded_ocr}", "Raw OCR text copied to clipboard!"));
        document.getElementById('btn-opt').addEventListener('click', () => copyText("{encoded_opt}", "Optimized raw text copied to clipboard!"));
        document.getElementById('btn-cl').addEventListener('click', () => copyText("{encoded_cl}", "Optimized text with cluster info copied to clipboard!"));
        </script>
        """
        import streamlit.components.v1 as components
        components.html(js_code, height=45)

st.markdown("### 1. Take a photo or upload an image")

# Hide input controls if we already have scan results (until committed)
if not st.session_state.scan_results:
    source_type = st.radio("Eingabequelle wählen:", ["Kamera benutzen", "Bild hochladen"], horizontal=True, on_change=reset_scan_state)
    
    uploaded_file = None
    if source_type == "Bild hochladen":
        uploaded_file = st.file_uploader("Bild (PNG, JPG, JPEG, WEBP) auswählen...", type=["png", "jpg", "jpeg", "webp"], on_change=reset_scan_state)
    else:
        uploaded_file = st.camera_input("Foto der Materialliste aufnehmen", on_change=reset_scan_state)
        
    if uploaded_file is not None:
        file_id = f"{uploaded_file.name}_{uploaded_file.size}" if hasattr(uploaded_file, "name") else "camera_photo"
        
        if st.session_state.get("last_analyzed_foto") != file_id:
            with st.spinner("Foto wird automatisch analysiert..."):
                try:
                    doc_bytes = uploaded_file.getvalue()
                    products_list = load_products("data/products.csv")
                    raw_ocr = run_local_ocr(doc_bytes)
                    st.session_state.raw_ocr_text = raw_ocr
                    
                    # Export raw text (before optimization) to a text file
                    txt_path = os.path.join(os.path.dirname(__file__), "data", "ocr_raw_text.txt")
                    with open(txt_path, "w", encoding="utf-8") as text_file:
                        text_file.write(raw_ocr)
                    
                    optimizer = TextOptimizer()
                    raw_text = optimizer.optimize(raw_ocr)
                    
                    st.session_state.raw_text = raw_text
                    parsed_items = parse_ocr_text(raw_text)

                    # Predict document level
                    lines_for_level = [item['raw_text'] for item in parsed_items]
                    doc_level = predict_document_level(lines_for_level)

                    scan_results = []
                    cl_info_lines = []
                    current_subj = "Allgemein"
                    for item in parsed_items:
                        current_subj = predict_subject(item['raw_text'], prev_subject=current_subj)
                        cl_info_lines.append(f"Line: {item['raw_text']} | Level: {doc_level or 'Allgemein'} | Subject: {current_subj or 'Allgemein'}")
                        match = find_best_match(item['raw_text'], products_list, level=doc_level, subject=current_subj)
                        
                        splits = split_by_colors(item['raw_text'], item['quantity'], match, products_list)
                        for split in splits:
                            scan_results.append({
                                "raw_text": item['raw_text'],
                                "quantity": split['quantity'],
                                "best_match_id": split['product_id']
                            })
                    st.session_state.optimized_with_cl_info = "\n".join(cl_info_lines)
                    scan_results.sort(key=lambda x: 1 if x['best_match_id'] == 0 else 0)
                    st.session_state.scan_results = scan_results
                    st.session_state.last_analyzed_foto = file_id
                    
                    # Generate data URL for document display
                    b64 = base64.b64encode(doc_bytes).decode()
                    mime = uploaded_file.type if hasattr(uploaded_file, "type") else "image/png"
                    st.session_state.data_url = f"data:{mime};base64,{b64}"
                    
                    st.toast("Analyse erfolgreich abgeschlossen!")
                    st.rerun()
                except Exception as e:
                    st.error(f"Fehler bei der automatischen Analyse: {e}")

# If we have scan results, show verification UI
if st.session_state.scan_results:
    st.markdown("### 2. Erkannte Produkte verifizieren")
    
    products_df = pd.read_csv("data/products.csv")
    options = {row['id']: f"{row['name']} ({row['brand']}) - {row['price']:.2f} €" for _, row in products_df.iterrows()}
    options[0] = "-- Kein passendes Produkt --"
    
    form_data = []
    col1, col2, col3, col4 = st.columns([4, 5, 2, 1])
    col1.markdown("**Erkannter Text**")
    col2.markdown("**Katalog-Produkt**")
    col3.markdown("**Menge**")
    col4.markdown("**Aktion**")
    
    to_delete = None
    for i, res in enumerate(st.session_state.scan_results):
        c_text, c_match, c_qty, c_del = st.columns([4, 5, 2, 1])
        c_text.markdown(f"<div class='erkannter-text'>{res['raw_text']}</div>", unsafe_allow_html=True)
        
        default_id = res['best_match_id'] if res['best_match_id'] in options else 0
        
        sel_id = c_match.selectbox(
            f"Produkt {i}",
            options=list(options.keys()),
            format_func=lambda x: options[x],
            index=list(options.keys()).index(default_id),
            key=f"mobile_prod_{i}",
            label_visibility="collapsed"
        )
        
        qty = c_qty.number_input(
            f"Menge {i}",
            min_value=1,
            value=int(res['quantity']),
            step=1,
            key=f"mobile_qty_{i}",
            label_visibility="collapsed"
        )
        
        if c_del.button("-", key=f"mobile_del_{i}", help="Zeile löschen", use_container_width=True):
            to_delete = i
            
        form_data.append((sel_id, qty))
        
    if to_delete is not None:
        st.session_state.scan_results.pop(to_delete)
        st.rerun()
        
    if st.button("Ausgewählte Artikel in den Warenkorb übernehmen", type="primary", use_container_width=True):
        added = 0
        for prod_id, qty in form_data:
            if prod_id != 0:
                st.session_state.cart[prod_id] = st.session_state.cart.get(prod_id, 0) + qty
                added += 1
                
        st.success(f"{added} Artikel wurden erfolgreich hinzugefügt!")
        st.session_state.scan_results = []
        st.session_state.cart_source = "foto"
        st.switch_page("pages/cart.py")  # Switch to global cart page programmatically
