import streamlit as st
import os
import sys

# Load local .env file
if os.path.exists(".env"):
    with open(".env") as f:
        for line in f:
            if line.strip() and not line.startswith("#"):
                parts = line.strip().split("=", 1)
                if len(parts) == 2:
                    k, v = parts
                    os.environ[k.strip()] = v.strip().strip('"').strip("'")

# Ensure root directory is in sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.ocr_engine import extract_text_from_pdf
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
        color: #ffffff;
    }
    .main-header {
        font-size: 2.2rem;
        font-weight: 800;
        background: linear-gradient(90deg, #36d1dc, #5b86e5);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        margin-bottom: 0.5rem;
    }
    /* Ensure text in tables/warenkorb is white */
    div[data-testid="stTable"] td, div[data-testid="stTable"] th, table td, table th {
        color: #ffffff !important;
    }
    /* Ensure text in Erkannter Text columns is white */
    .erkannter-text {
        color: #ffffff !important;
        font-size: 14px;
        padding-top: 5px;
    }
</style>
""", unsafe_allow_html=True)

st.markdown('<div class="main-header">📄 PDF-Bestellzettel Analysieren</div>', unsafe_allow_html=True)
st.write("Laden Sie die digitale PDF-Materialliste der Schule hoch, um Artikel automatisch zu extrahieren.")

# Load env key for Gemini API
gemini_key = os.environ.get("GEMINI_API_KEY", "")

def reset_pdf_state():
    if "raw_text" in st.session_state:
        del st.session_state["raw_text"]
    if "last_analyzed_pdf" in st.session_state:
        del st.session_state["last_analyzed_pdf"]
    st.session_state.scan_results = []

uploaded_pdf = st.file_uploader("PDF-Datei hochladen...", type=["pdf"], on_change=reset_pdf_state)

if uploaded_pdf is not None:
    file_id = f"{uploaded_pdf.name}_{uploaded_pdf.size}"
    
    if st.session_state.get("last_analyzed_pdf") != file_id:
        with st.spinner("PDF wird automatisch analysiert..."):
            try:
                raw_text = extract_text_from_pdf(uploaded_pdf.getvalue())
                st.session_state.raw_text = raw_text
                
                products_list = load_products("data/products.csv")
                parsed_items = []
                if raw_text.strip():
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
                scan_results.sort(key=lambda x: 1 if x['best_match_id'] == 0 else 0)
                st.session_state.scan_results = scan_results
                st.session_state.last_analyzed_pdf = file_id
                st.toast("Analyse erfolgreich abgeschlossen!")
                st.rerun()
            except Exception as e:
                st.error(f"Fehler bei der automatischen Analyse: {e}")

    # Display side-by-side copy-box and Document Show button
    import base64
    b64 = base64.b64encode(uploaded_pdf.getvalue()).decode()
    data_url = f"data:application/pdf;base64,{b64}"
    
    col_copy, col_show = st.columns([7, 3])
    
    with col_copy:
        import urllib.parse
        encoded_text = urllib.parse.quote(st.session_state.get("raw_text", ""))
        js_code = f"""
        <div id="copy-box" style="cursor: pointer; padding: 0.5rem 1rem; border-radius: 0.5rem; background-color: rgba(28, 187, 180, 0.15); border: 1px solid rgba(28, 187, 180, 0.3); color: #36d1dc; font-family: sans-serif; font-size: 14px; display: flex; align-items: center; justify-content: space-between; user-select: none;">
            <span>📄 Dokument geladen: <strong>{uploaded_pdf.name}</strong></span>
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

# If we have scan results, show verification UI
if "scan_results" in st.session_state and st.session_state.scan_results:
    st.markdown("### 🛒 Erkannte Produkte verifizieren")
    
    # Load products table
    import pandas as pd
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
        
        if c_insert.button("➕", key=f"insert_after_pdf_{i}", help="Neue Zeile darunter einfügen"):
            # Persist current modified inputs before inserting
            new_results = []
            for idx in range(len(st.session_state.scan_results)):
                p_val = st.session_state.get(f"pdf_prod_{idx}", st.session_state.scan_results[idx]['best_match_id'])
                q_val = st.session_state.get(f"pdf_qty_{idx}", st.session_state.scan_results[idx]['quantity'])
                new_results.append({
                    "raw_text": st.session_state.scan_results[idx]['raw_text'],
                    "quantity": q_val,
                    "best_match_id": p_val
                })
            # Insert new empty row
            new_results.insert(i + 1, {"raw_text": "-----------------------------------", "quantity": 1, "best_match_id": 0})
            st.session_state.scan_results = new_results
            st.rerun()
        
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
        st.session_state.analyzed = False
        st.switch_page("pages/cart.py")
