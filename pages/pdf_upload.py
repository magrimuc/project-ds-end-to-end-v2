import streamlit as st
import os
import sys
import pandas as pd

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
from src.parser import parse_ocr_text, detect_grade_from_text
from src.text_optimizer import TextOptimizer
from src.matcher import load_products, find_best_match, predict_subject, predict_document_level, split_by_colors

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
    if "raw_ocr_text" in st.session_state:
        del st.session_state["raw_ocr_text"]
    if "optimized_with_cl_info" in st.session_state:
        del st.session_state["optimized_with_cl_info"]
    if "last_analyzed_pdf" in st.session_state:
        del st.session_state["last_analyzed_pdf"]
    if "detected_grade" in st.session_state:
        del st.session_state["detected_grade"]
    st.session_state.scan_results = []

uploaded_pdf = st.file_uploader("PDF-Datei hochladen...", type=["pdf"], on_change=reset_pdf_state)

if uploaded_pdf is not None:
    file_id = f"{uploaded_pdf.name}_{uploaded_pdf.size}"
    
    if st.session_state.get("last_analyzed_pdf") != file_id:
        with st.spinner("PDF wird automatisch analysiert..."):
            try:
                raw_ocr = extract_text_from_pdf(uploaded_pdf.getvalue())
                st.session_state.raw_ocr_text = raw_ocr
                
                optimizer = TextOptimizer()
                raw_text = optimizer.optimize(raw_ocr)
                st.session_state.raw_text = raw_text
                
                # Detect grade from the first 8 lines
                st.session_state.detected_grade = detect_grade_from_text(raw_ocr)
                
                products_list = load_products("data/products.csv")
                parsed_items = []
                if raw_text.strip():
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
        encoded_ocr = urllib.parse.quote(st.session_state.get("raw_ocr_text", ""))
        encoded_opt = urllib.parse.quote(st.session_state.get("raw_text", ""))
        encoded_cl = urllib.parse.quote(st.session_state.get("optimized_with_cl_info", ""))
        
        js_code = f"""
        <div style="display: flex; gap: 8px; font-family: sans-serif; height: 38px; align-items: center; width: 100%;">
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
        
    with col_show:
        st.link_button("📄 View Document", data_url, use_container_width=True)

# If we have scan results, show verification UI
if "scan_results" in st.session_state and st.session_state.scan_results:
    if "detected_grade" in st.session_state:
        st.write(f"ermittelte Klassenstufe {st.session_state.detected_grade}")
    st.markdown("### 🛒 Erkannte Produkte verifizieren")
    
    # Load products table
    import pandas as pd
    products_df = pd.read_csv("data/products.csv")
    options = {row['id']: f"{row['name']} ({row['brand']}) - {row['price']:.2f} €" for _, row in products_df.iterrows()}
    options[0] = "-- Kein passendes Produkt --"
    
    form_data = []
    col1, col2, col3 = st.columns([4, 6, 2])
    col1.markdown("**Erkannter Text**")
    col2.markdown("**Katalog-Produkt**")
    col3.markdown("**Menge**")
    
    for i, res in enumerate(st.session_state.scan_results):
        c_text, c_match, c_qty = st.columns([4, 6, 2])
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
        st.session_state.cart_source = "pdf"
        st.switch_page("pages/cart.py")

# --- WARENKORB (unter PDF Upload) ---
st.markdown("---")
st.markdown("### 🛒 Ihr aktueller Warenkorb")

if "cart" not in st.session_state or not st.session_state.cart:
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
    if st.button("🗑️ Warenkorb leeren", key="clear_cart_pdf"):
        st.session_state.cart = {}
        st.rerun()
