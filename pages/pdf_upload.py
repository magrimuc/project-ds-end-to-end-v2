import streamlit as st
import os
import sys

# Ensure root directory is in sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.ocr_engine import run_gemini_ocr, extract_text_from_pdf
from src.parser import parse_ocr_text
from src.matcher import load_products, find_best_match

st.set_page_config(
    page_title="PDF Bestellzettel Upload",
    page_icon="📄",
    layout="wide"
)

# Custom Styling
st.markdown("""
<style>
    .stApp {
        background-color: #0e1117;
        color: #e0e0e0;
    }
    .main-header {
        font-size: 2.2rem;
        font-weight: 800;
        background: linear-gradient(90deg, #36d1dc, #5b86e5);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        margin-bottom: 0.5rem;
    }
</style>
""", unsafe_allow_html=True)

# Navigation link back to mobile app if needed
if st.button("⬅ Zurück zur Hauptseite (Foto-Upload)"):
    st.switch_page("app.py")

st.markdown('<div class="main-header">📄 PDF-Bestellzettel Analysieren</div>', unsafe_allow_html=True)
st.write("Laden Sie die digitale PDF-Materialliste der Schule hoch, um Artikel automatisch zu extrahieren.")

# Load env key for Gemini API
gemini_key = os.environ.get("GEMINI_API_KEY", "")

# Sidebar OCR mode configuration
with st.sidebar:
    st.markdown("### ⚙️ OCR-Konfiguration")
    ocr_mode = st.radio(
        "Erkennungs-Modus:",
        ["Lokales PDF-Text-Parsing", "AI-gestützt (Gemini API)"],
        help="Lokales Text-Parsing liest Text direkt aus editierbaren PDFs. Gemini OCR verarbeitet auch eingescannte Bild-PDFs perfekt."
    )
    if ocr_mode == "AI-gestützt (Gemini API)":
        gemini_key_input = st.text_input("Gemini API-Schlüssel:", value=gemini_key, type="password")
        if gemini_key_input:
            gemini_key = gemini_key_input

uploaded_pdf = st.file_uploader("PDF-Datei hochladen...", type=["pdf"])

if uploaded_pdf is not None:
    st.info(f"📄 **Datei geladen:** {uploaded_pdf.name}")
    
    if st.button("PDF analysieren", type="primary"):
        pdf_bytes = uploaded_pdf.getvalue()
        
        with st.spinner("PDF wird ausgelesen..."):
            try:
                products_list = load_products("data/products.csv")
                parsed_items = []
                
                if ocr_mode == "AI-gestützt (Gemini API)":
                    if not gemini_key:
                        st.error("Bitte einen Gemini API-Schlüssel in der Seitenleiste eingeben!")
                    else:
                        # Call Gemini to process the PDF
                        raw_json = run_gemini_ocr(pdf_bytes, "application/pdf", gemini_key)
                        import json
                        parsed_items = json.loads(raw_json)
                else:
                    # Parse local editable PDF text
                    raw_text = extract_text_from_pdf(pdf_bytes)
                    if not raw_text.strip():
                        st.warning("⚠️ Kein Text gefunden. Handelt es sich um ein gescanntes PDF? Bitte nutze den AI-gestützten Modus.")
                    else:
                        st.text_area("Extrahierter Rohtext:", raw_text, height=150)
                        parsed_items = parse_ocr_text(raw_text)
                
                # Match catalog products
                scan_results = []
                for item in parsed_items:
                    match = find_best_match(item['raw_text'], products_list)
                    if match and match['product_id']:
                        scan_results.append({
                            "raw_text": item['raw_text'],
                            "quantity": item['quantity'],
                            "best_match_id": match['product_id']
                        })
                    
                st.session_state.scan_results = scan_results
                st.success("Analyse erfolgreich abgeschlossen!")
                
            except Exception as e:
                st.error(f"Fehler bei der Analyse: {e}")

# If we have scan results, show verification UI
if "scan_results" in st.session_state and st.session_state.scan_results:
    st.markdown("### 🛒 Erkannte Produkte verifizieren")
    
    # Load products table
    import pandas as pd
    products_df = pd.read_csv("data/products.csv")
    options = {row['id']: f"{row['name']} ({row['brand']}) - {row['price']:.2f} €" for _, row in products_df.iterrows()}
    options[0] = "-- Kein passendes Produkt --"
    
    form_data = []
    col1, col2, col3 = st.columns([3, 4, 2])
    col1.markdown("**Erkannter Text**")
    col2.markdown("**Katalog-Produkt**")
    col3.markdown("**Menge**")
    
    for i, res in enumerate(st.session_state.scan_results):
        c_text, c_match, c_qty = st.columns([3, 4, 2])
        c_text.text(res['raw_text'])
        
        default_id = res['best_match_id'] if res['best_match_id'] in options else 0
        
        sel_id = c_match.selectbox(
            f"Produkt {i}",
            options=list(options.keys()),
            format_func=lambda x: options[x],
            index=list(options.keys()).index(default_id),
            key=f"pdf_prod_{i}",
            label_visibility="collapsed"
        )
        
        qty = c_qty.number_input(
            f"Menge {i}",
            min_value=1,
            value=int(res['quantity']),
            step=1,
            key=f"pdf_qty_{i}",
            label_visibility="collapsed"
        )
        form_data.append((sel_id, qty))
        
    if st.button("Artikel in den Warenkorb übernehmen", type="primary", use_container_width=True):
        if "cart" not in st.session_state:
            st.session_state.cart = {}
            
        added = 0
        for prod_id, qty in form_data:
            if prod_id != 0:
                st.session_state.cart[prod_id] = st.session_state.cart.get(prod_id, 0) + qty
                added += 1
                
        st.success(f"{added} Artikel wurden in den Warenkorb gelegt!")
        st.session_state.scan_results = []
        st.rerun()
