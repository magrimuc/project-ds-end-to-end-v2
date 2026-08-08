import streamlit as st
import os
import sys
import pandas as pd
from PIL import Image

# Ensure root directory is in sys.path
sys.path.append(os.path.abspath(os.path.dirname(__file__)))

from src.device_detector import is_mobile_device
from src.ocr_engine import run_gemini_ocr, run_local_ocr
from src.parser import parse_ocr_text
from src.matcher import load_products, find_best_match

# Page Configuration
st.set_page_config(
    page_title="Schulbedarf OCR & Bestell-Manager",
    page_icon="🎒",
    layout="wide"
)

# Custom Premium Styling
st.markdown("""
<style>
    .stApp {
        background-color: #0e1117;
        color: #e0e0e0;
    }
    .main-header {
        font-size: 2.2rem;
        font-weight: 800;
        background: linear-gradient(90deg, #ff7e5f, #feb47b);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        margin-bottom: 0.5rem;
    }
    .sub-header {
        font-size: 1.1rem;
        color: #a0aec0;
        margin-bottom: 2rem;
    }
</style>
""", unsafe_allow_html=True)

# Initialize cart and scan state
if "cart" not in st.session_state:
    st.session_state.cart = {}
if "scan_results" not in st.session_state:
    st.session_state.scan_results = []
if "override_device_detect" not in st.session_state:
    st.session_state.override_device_detect = False

# Device Routing
is_mobile = is_mobile_device()

# If desktop and not overridden, automatically redirect to PDF page
if not is_mobile and not st.session_state.override_device_detect:
    st.session_state.override_device_detect = True # prevent redirect loops on manual navigation
    st.switch_page("pages/pdf_upload.py")

# App Header
st.markdown('<div class="main-header">🎒 Schulbedarf Foto-Scanner</div>', unsafe_allow_html=True)
st.markdown('<div class="sub-header">Optimiert für Mobilgeräte. Fotografieren Sie eine Materialliste ab, um sie direkt zu digitalisieren.</div>', unsafe_allow_html=True)

if not is_mobile:
    st.info("💻 **Desktop-Gerät erkannt:** Sie wurden automatisch zur PDF-Upload-Seite weitergeleitet. Sie können diese Ansicht manuell nutzen.")
    if st.button("📄 Zur PDF-Upload Seite wechseln"):
        st.switch_page("pages/pdf_upload.py")

# Load env key for Gemini API
gemini_key = os.environ.get("GEMINI_API_KEY", "")

# Sidebar OCR mode configuration
with st.sidebar:
    st.markdown("### ⚙️ OCR-Konfiguration")
    ocr_mode = st.radio(
        "Erkennungs-Modus:",
        ["Kamera-OCR (Lokal)", "AI-gestützt (Gemini API)"],
        help="Lokal nutzt Tesseract OCR auf Ihrem System. Gemini OCR erkennt auch handgeschriebene Zettel perfekt."
    )
    if ocr_mode == "AI-gestützt (Gemini API)":
        gemini_key_input = st.text_input("Gemini API-Schlüssel:", value=gemini_key, type="password")
        if gemini_key_input:
            gemini_key = gemini_key_input

# Tabs
tab_scan, tab_cart, tab_catalog = st.tabs(["📸 Foto scannen", "🛒 Warenkorb", "📦 Produktkatalog"])

# --- TAB 1: EINGABE & SCANNEN ---
with tab_scan:
    st.markdown("### 1. Zettel abfotografieren oder Bild hochladen")
    
    source_type = st.radio("Eingabequelle wählen:", ["Kamera benutzen", "Bild hochladen"], horizontal=True)
    
    uploaded_file = None
    if source_type == "Bild hochladen":
        uploaded_file = st.file_uploader("Bild (PNG, JPG, JPEG, WEBP) auswählen...", type=["png", "jpg", "jpeg", "webp"])
    else:
        uploaded_file = st.camera_input("Foto der Materialliste aufnehmen")
        
    if uploaded_file is not None:
        col_img, col_act = st.columns([1, 1])
        
        with col_img:
            image = Image.open(uploaded_file)
            st.image(image, caption="Erfasstes Foto", use_column_width=True)
            
        with col_act:
            st.markdown("### 2. Analyse starten")
            if st.button("Foto analysieren", type="primary"):
                doc_bytes = uploaded_file.getvalue()
                
                with st.spinner("Text wird extrahiert..."):
                    try:
                        products_list = load_products("data/products.csv")
                        parsed_items = []
                        
                        if ocr_mode == "AI-gestützt (Gemini API)":
                            if not gemini_key:
                                st.error("Bitte einen Gemini API-Schlüssel in der Seitenleiste eingeben!")
                            else:
                                raw_json = run_gemini_ocr(doc_bytes, uploaded_file.type if hasattr(uploaded_file, 'type') else "image/png", gemini_key)
                                import json
                                parsed_items = json.loads(raw_json)
                        else:
                            # Local Tesseract OCR
                            raw_text = run_local_ocr(doc_bytes)
                            st.text_area("Erkannter Rohtext:", raw_text, height=150)
                            parsed_items = parse_ocr_text(raw_text)
                            
                        # Catalog Matching
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

        # Verification UI
        if st.session_state.scan_results:
            st.markdown("---")
            st.markdown("### 3. Artikel verifizieren & Warenkorb bestücken")
            
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
                    f"Mobile Produkt {i}",
                    options=list(options.keys()),
                    format_func=lambda x: options[x],
                    index=list(options.keys()).index(default_id),
                    key=f"mobile_prod_{i}",
                    label_visibility="collapsed"
                )
                
                qty = c_qty.number_input(
                    f"Mobile Menge {i}",
                    min_value=1,
                    value=int(res['quantity']),
                    step=1,
                    key=f"mobile_qty_{i}",
                    label_visibility="collapsed"
                )
                form_data.append((sel_id, qty))
                
            col_submit, col_add = st.columns([2, 1])
            with col_submit:
                if st.button("Ausgewählte Artikel in den Warenkorb übernehmen", type="primary", use_container_width=True):
                    added = 0
                    for prod_id, qty in form_data:
                        if prod_id != 0:
                            st.session_state.cart[prod_id] = st.session_state.cart.get(prod_id, 0) + qty
                            added += 1
                            
                    st.success(f"{added} Artikel wurden erfolgreich hinzugefügt!")
                    st.session_state.scan_results = []
                    st.rerun()
            with col_add:
                with st.popover("➕ Neuer Artikel", use_container_width=True):
                    st.markdown("### Artikel suchen & hinzufügen")
                    selected_prod = st.selectbox(
                        "Produkt auswählen:",
                        options=list(options.keys()),
                        format_func=lambda x: options[x],
                        key="manual_add_mobile_sel"
                    )
                    qty_manual = st.number_input("Menge:", min_value=1, value=1, step=1, key="manual_add_mobile_qty")
                    if st.button("Hinzufügen", key="manual_add_mobile_btn", type="primary", use_container_width=True):
                        if selected_prod != 0:
                            st.session_state.cart[selected_prod] = st.session_state.cart.get(selected_prod, 0) + qty_manual
                            st.toast("Artikel hinzugefügt!")
                            st.rerun()

# --- TAB 2: WARENKORB ---
with tab_cart:
    st.markdown("### Ihr aktueller Warenkorb")
    if not st.session_state.cart:
        st.write("Der Warenkorb ist leer.")
    else:
        products_df = pd.read_csv("data/products.csv")
        cart_rows = []
        grand_total = 0.0
        
        for prod_id, qty in list(st.session_state.cart.items()):
            prod_row = products_df[products_df['id'] == prod_id]
            if not prod_row.empty:
                row = prod_row.iloc[0]
                total = row['price'] * qty
                grand_total += total
                cart_rows.append({
                    "ID": prod_id,
                    "Name": row['name'],
                    "Marke": row['brand'],
                    "Menge": qty,
                    "Einzelpreis": f"{row['price']:.2f} €",
                    "Gesamtpreis": f"{total:.2f} €"
                })
                
        st.table(pd.DataFrame(cart_rows))
        st.markdown(f"### **Gesamtsumme: {grand_total:.2f} €**")
        
        # Recommendations integration
        from src.recommender import Recommender
        recommender = Recommender()
        cart_ids = list(st.session_state.cart.keys())
        
        predicted_grade, recs = recommender.get_recommendations(cart_ids, top_n=5)
        
        st.markdown("---")
        st.markdown(f"### 🎯 Prognostizierte Klassenstufe: **{predicted_grade}**")
        
        if recs:
            st.markdown("#### 💡 Empfohlene Ergänzungen für dieses Schuljahr:")
            for rec in recs:
                col_name, col_price, col_add = st.columns([5, 2, 2])
                col_name.write(f"**{rec['name']}** ({rec['brand']})")
                col_price.write(f"{rec['price']:.2f} €")
                if col_add.button("➕ Hinzufügen", key=f"add_rec_mobile_{rec['product_id']}"):
                    st.session_state.cart[rec['product_id']] = st.session_state.cart.get(rec['product_id'], 0) + 1
                    st.toast(f"{rec['name']} wurde hinzugefügt!")
                    st.rerun()
                    
        st.markdown("---")
        if st.button("🗑️ Warenkorb leeren"):
            st.session_state.cart = {}
            st.rerun()

# --- TAB 3: PRODUKTKATALOG ---
with tab_catalog:
    st.markdown("### Verfügbare Artikel im System")
    st.dataframe(pd.read_csv("data/products.csv"))
