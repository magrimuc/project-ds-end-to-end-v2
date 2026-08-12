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
from src.matcher import load_products, find_best_match
from src.text_optimizer import TextOptimizer

# Initialize cart and scan state
if "cart" not in st.session_state:
    st.session_state.cart = {}
if "scan_results" not in st.session_state:
    st.session_state.scan_results = []
if "raw_text" not in st.session_state:
    st.session_state.raw_text = ""
if "data_url" not in st.session_state:
    st.session_state.data_url = None
if "active_tab" not in st.session_state:
    st.session_state.active_tab = "📸 Foto scannen"

def reset_scan_state():
    st.session_state.scan_results = []
    st.session_state.raw_text = ""
    st.session_state.data_url = None
    if "last_analyzed_foto" in st.session_state:
        del st.session_state["last_analyzed_foto"]

# App Header
st.markdown('<div class="main-header">🎒 Schulbedarf Foto-Scanner</div>', unsafe_allow_html=True)
st.markdown('<div class="sub-header">Optimiert für Mobilgeräte. Fotografieren Sie eine Materialliste ab, um sie direkt zu digitalisieren.</div>', unsafe_allow_html=True)

# 1. Document view button placed at the top (above tabs) if a document is loaded
if st.session_state.get("data_url"):
    st.link_button("📄 Dokument anzeigen", st.session_state.data_url, use_container_width=True)

# 2. Navigation / Tabs using st.radio programmatically controlled
tab_options = ["📸 Foto scannen", "🛒 Warenkorb", "📦 Produktkatalog"]
st.session_state.active_tab = st.radio(
    "Navigation",
    options=tab_options,
    index=tab_options.index(st.session_state.active_tab),
    horizontal=True,
    label_visibility="collapsed"
)

# Render active tab content
if st.session_state.active_tab == "📸 Foto scannen":
    st.markdown("### 1. Zettel abfotografieren oder Bild hochladen")
    
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
                        raw_text = run_local_ocr(doc_bytes)
                        
                        optimizer = TextOptimizer()
                        raw_text = optimizer.optimize(raw_text)
                        
                        st.session_state.raw_text = raw_text
                        parsed_items = parse_ocr_text(raw_text)

                        scan_results = []
                        for item in parsed_items:
                            match = find_best_match(item['raw_text'], products_list)
                            best_match_id = match['product_id'] if match else 0
                            scan_results.append({
                                "raw_text": item['raw_text'],
                                "quantity": item['quantity'],
                                "best_match_id": best_match_id
                            })
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
        # Note: The "Bildname" widget (copy-box) is hidden as requested
        st.markdown("### 2. Erkannte Produkte verifizieren")
        
        products_df = pd.read_csv("data/products.csv")
        options = {row['id']: f"{row['name']} ({row['brand']}) - {row['price']:.2f} €" for _, row in products_df.iterrows()}
        options[0] = "-- Kein passendes Produkt --"
        
        form_data = []
        col1, col2, col3, col_add_header = st.columns([3, 4, 2, 1])
        col1.markdown("**Erkannter Text**")
        col2.markdown("**Katalog-Produkt**")
        col3.markdown("**Menge**")
        col_add_header.markdown("**Neu**")
        
        for i, res in enumerate(st.session_state.scan_results):
            c_text, c_match, c_qty, c_insert = st.columns([3, 4, 2, 1])
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
            form_data.append((sel_id, qty))
            
            if c_insert.button("➕", key=f"insert_after_mobile_{i}", help="Neue Zeile darunter einfügen"):
                new_results = []
                for idx in range(len(st.session_state.scan_results)):
                    p_val = st.session_state.get(f"mobile_prod_{idx}", st.session_state.scan_results[idx]['best_match_id'])
                    q_val = st.session_state.get(f"mobile_qty_{idx}", st.session_state.scan_results[idx]['quantity'])
                    new_results.append({
                        "raw_text": st.session_state.scan_results[idx]['raw_text'],
                        "quantity": q_val,
                        "best_match_id": p_val
                    })
                new_results.insert(i + 1, {"raw_text": "-----------------------------------", "quantity": 1, "best_match_id": 0})
                st.session_state.scan_results = new_results
                st.rerun()
            
        if st.button("Ausgewählte Artikel in den Warenkorb übernehmen", type="primary", use_container_width=True):
            added = 0
            for prod_id, qty in form_data:
                if prod_id != 0:
                    st.session_state.cart[prod_id] = st.session_state.cart.get(prod_id, 0) + qty
                    added += 1
                    
            st.success(f"{added} Artikel wurden erfolgreich hinzugefügt!")
            st.session_state.scan_results = []
            st.session_state.active_tab = "🛒 Warenkorb"  # Switch to cart tab programmatically
            st.rerun()

elif st.session_state.active_tab == "🛒 Warenkorb":
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
        
        st.markdown("---")
        if st.button("🗑️ Warenkorb leeren"):
            st.session_state.cart = {}
            st.rerun()
            
    # "+ Neuer Artikel" Popover placed under the cart (visible whether empty or not)
    st.markdown("---")
    products_df = pd.read_csv("data/products.csv")
    options = {row['id']: f"{row['name']} ({row['brand']}) - {row['price']:.2f} €" for _, row in products_df.iterrows()}
    options[0] = "-- Kein passendes Produkt --"
    
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

elif st.session_state.active_tab == "📦 Produktkatalog":
    st.markdown("### Verfügbare Artikel im System")
    st.dataframe(pd.read_csv("data/products.csv"))
