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
from src.parser import parse_ocr_text
from src.matcher import load_products, find_best_match

st.set_page_config(
    page_title="PDF Order List Upload",
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

st.markdown('<div class="main-header">📄 Analyze PDF Order List</div>', unsafe_allow_html=True)
st.write("Upload the school's digital PDF supply list to extract items automatically.")

# Load env key for Gemini API
gemini_key = os.environ.get("GEMINI_API_KEY", "")

def reset_pdf_state():
    if "raw_text" in st.session_state:
        del st.session_state["raw_text"]
    if "last_analyzed_pdf" in st.session_state:
        del st.session_state["last_analyzed_pdf"]
    st.session_state.scan_results = []

uploaded_pdf = st.file_uploader("Upload PDF file...", type=["pdf"], on_change=reset_pdf_state)

if uploaded_pdf is not None:
    file_id = f"{uploaded_pdf.name}_{uploaded_pdf.size}"
    
    if st.session_state.get("last_analyzed_pdf") != file_id:
        with st.spinner("Analyzing PDF automatically..."):
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
                st.toast("Analysis completed successfully!")
                st.rerun()
            except Exception as e:
                st.error(f"Error during automatic analysis: {e}")

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
            <span>📄 Document loaded: <strong>{uploaded_pdf.name}</strong></span>
            <span style="font-size: 0.8rem; border: 1px solid rgba(54, 209, 220, 0.4); padding: 2px 6px; border-radius: 4px;">Click to copy extracted raw text</span>
        </div>
        <script>
        document.getElementById('copy-box').addEventListener('click', () => {{
            const text = decodeURIComponent("{encoded_text}");
            if (navigator.clipboard && navigator.clipboard.writeText) {{
                navigator.clipboard.writeText(text).then(() => {{
                    alert('Raw text copied to clipboard!');
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
                alert('Raw text copied to clipboard!');
            }} catch (err) {{
                alert('Copy failed.');
            }}
            document.body.removeChild(textArea);
        }}
        </script>
        """
        import streamlit.components.v1 as components
        components.html(js_code, height=50)
        
    with col_show:
        st.link_button("📄 View Document", data_url, use_container_width=True)

# If we have scan results, show verification UI
if "scan_results" in st.session_state and st.session_state.scan_results:
    st.markdown("### 🛒 Verify Detected Products")
    
    # Load products table
    import pandas as pd
    products_df = pd.read_csv("data/products.csv")
    options = {row['id']: f"{row['name']} ({row['brand']}) - {row['price']:.2f} €" for _, row in products_df.iterrows()}
    options[0] = "-- No matching product --"
    
    form_data = []
    col1, col2, col3 = st.columns([4, 6, 2])
    col1.markdown("**Detected Text**")
    col2.markdown("**Catalog Product**")
    col3.markdown("**Quantity**")
    
    for i, res in enumerate(st.session_state.scan_results):
        c_text, c_match, c_qty = st.columns([4, 6, 2])
        c_text.markdown(f"<div class='erkannter-text'>{res['raw_text']}</div>", unsafe_allow_html=True)
        
        default_id = res['best_match_id'] if res['best_match_id'] in options else 0
        
        sel_id = c_match.selectbox(
            f"Product {i}",
            options=list(options.keys()),
            format_func=lambda x: options[x],
            index=list(options.keys()).index(default_id),
            key=f"pdf_prod_{i}",
            label_visibility="collapsed"
        )
        
        qty = c_qty.number_input(
            f"Quantity {i}",
            min_value=1,
            value=int(res['quantity']),
            step=1,
            key=f"pdf_qty_{i}",
            label_visibility="collapsed"
        )
        form_data.append((sel_id, qty))
        
    if st.button("Add items to cart", type="primary", use_container_width=True):
        if "cart" not in st.session_state:
            st.session_state.cart = {}
            
        added = 0
        for prod_id, qty in form_data:
            if prod_id != 0:
                st.session_state.cart[prod_id] = st.session_state.cart.get(prod_id, 0) + qty
                added += 1
                
        st.success(f"{added} items added to cart!")
        st.session_state.scan_results = []
        st.session_state.analyzed = False
        st.session_state.cart_source = "pdf"
        st.switch_page("pages/cart.py")

# --- WARENKORB (unter PDF Upload) ---
st.markdown("---")
st.markdown("### 🛒 Your Current Cart")

if "cart" not in st.session_state or not st.session_state.cart:
    st.write("The cart is empty.")
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
                "Brand": row['brand'],
                "Quantity": qty,
                "Unit Price": f"{row['price']:.2f} €",
                "Total Price": f"{total:.2f} €"
            })
            
    st.table(pd.DataFrame(cart_rows))
    st.markdown(f"### **Grand Total: {grand_total:.2f} €**")
    
    st.markdown("---")
    if st.button("🗑️ Clear Cart", key="clear_cart_pdf"):
        st.session_state.cart = {}
        st.rerun()
