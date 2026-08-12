import re

import streamlit as st
import os
import sys
import pandas as pd
from PIL import Image

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

def reset_scan_state():
    st.session_state.scan_results = []
    st.session_state.raw_text = ""
    if "last_analyzed_foto" in st.session_state:
        del st.session_state["last_analyzed_foto"]

# App Header
st.markdown('<div class="main-header">🎒 Schulbedarf Foto-Scanner</div>', unsafe_allow_html=True)
st.markdown('<div class="sub-header">Optimiert für Mobilgeräte. Fotografieren Sie eine Materialliste ab, um sie direkt zu digitalisieren.</div>', unsafe_allow_html=True)

# Tabs
tab_scan, tab_cart, tab_catalog = st.tabs(["📸 Foto scannen", "🛒 Warenkorb", "📦 Produktkatalog"])

# --- TAB 1: EINGABE & SCANNEN ---
with tab_scan:
    st.markdown("### 1. Zettel abfotografieren oder Bild hochladen")
    
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

                    # Korrigiere Farben in den geparsten Artikeln
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
                    st.toast("Analyse erfolgreich abgeschlossen!")
                    st.rerun()
                except Exception as e:
                    st.error(f"Fehler bei der automatischen Analyse: {e}")

        # Display side-by-side copy-box and Document Show button
        import base64
        b64 = base64.b64encode(uploaded_file.getvalue()).decode()
        mime = uploaded_file.type if hasattr(uploaded_file, "type") else "image/png"
        data_url = f"data:{mime};base64,{b64}"
        
        col_copy, col_show = st.columns([7, 3])
        
        with col_copy:
            import urllib.parse
            encoded_text = urllib.parse.quote(st.session_state.get("raw_text", ""))
            filename_lbl = uploaded_file.name if hasattr(uploaded_file, "name") else "Foto"
            js_code = f"""
            <div id="copy-box" style="cursor: pointer; padding: 0.5rem 1rem; border-radius: 0.5rem; background-color: rgba(28, 187, 180, 0.15); border: 1px solid rgba(28, 187, 180, 0.3); color: #36d1dc; font-family: sans-serif; font-size: 14px; display: flex; align-items: center; justify-content: space-between; user-select: none;">
                <span>📸 Dokument geladen: <strong>{filename_lbl}</strong></span>
                <span style="font-size: 0.8rem; border: 1px solid rgba(54, 209, 220, 0.4); padding: 2px 6px; border-radius: 4px;">Klicken zum Kopieren des erfassten Rohtexts</span>
            </div>
            <script>
            document.getElementById('copy-box').addEventListener('click', () => {{
                const text = decodeURIComponent("{encoded_text}");
                if (navigator.clipboard && navigator.clipboard.writeText) {{
                    navigator.clipboard.writeText(text).then(() => {{
                        alert('Rohtext wurde in die Zwischenablage kopiert!');
                    }}).catch(err => {{
                        fallbackCopy(text);
                    }});
                }} else {{
                    fallbackCopy(text);
                }}
            }});
            function fallbackCopy(text) {{
                const textArea = document.createElement("textarea");
                textArea.value = text;
                document.body.appendChild(textArea);
                textArea.select();
                try {{
                    document.execCommand('copy');
                    alert('Rohtext wurde in die Zwischenablage kopiert!');
                }} catch (err) {{
                    alert('Kopieren fehlgeschlagen.');
                }}
                document.body.removeChild(textArea);
            }}
            </script>
            """
            import streamlit.components.v1 as components
            components.html(js_code, height=50)
            
        with col_show:
            st.link_button("📄 Dokument anzeigen", data_url, use_container_width=True)

        # Verification UI
        if st.session_state.scan_results:
            st.markdown("---")
            st.markdown("### 3. Artikel verifizieren & Warenkorb bestücken")
            
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
                
                if c_insert.button("➕", key=f"insert_after_mobile_{i}", help="Neue Zeile darunter einfügen"):
                    # Persist current modified inputs before inserting
                    new_results = []
                    for idx in range(len(st.session_state.scan_results)):
                        p_val = st.session_state.get(f"mobile_prod_{idx}", st.session_state.scan_results[idx]['best_match_id'])
                        q_val = st.session_state.get(f"mobile_qty_{idx}", st.session_state.scan_results[idx]['quantity'])
                        new_results.append({
                            "raw_text": st.session_state.scan_results[idx]['raw_text'],
                            "quantity": q_val,
                            "best_match_id": p_val
                        })
                    # Insert new empty row
                    new_results.insert(i + 1, {"raw_text": "-----------------------------------", "quantity": 1, "best_match_id": 0})
                    st.session_state.scan_results = new_results
                    st.rerun()
                
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
        
        st.markdown("---")
        if st.button("🗑️ Warenkorb leeren"):
            st.session_state.cart = {}
            st.rerun()

# --- TAB 3: PRODUKTKATALOG ---
with tab_catalog:
    st.markdown("### Verfügbare Artikel im System")
    st.dataframe(pd.read_csv("data/products.csv"))
