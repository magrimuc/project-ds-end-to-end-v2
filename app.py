import streamlit as st
import os
import sys

# Ensure root directory is in sys.path
sys.path.append(os.path.abspath(os.path.dirname(__file__)))

from src.device_detector import is_mobile_device

# Initialize session state for device override
if "override_device_detect" not in st.session_state:
    st.session_state.override_device_detect = False

# Page definitions (Custom titles and icons)
foto_page = st.Page("foto.py", title="Foto", icon="📸")
pdf_page = st.Page("pages/pdf_upload.py", title="PDF", icon="📄")
cart_page = st.Page("pages/cart.py", title="Warenkorb", icon="🛒")
pull_page = st.Page("pages/pull.py", title="Pull", icon="🔄")

# Device Routing
is_mobile = is_mobile_device()
if not is_mobile and not st.session_state.override_device_detect:
    st.session_state.override_device_detect = True
    st.switch_page(pdf_page)

# Render Navigation
pg = st.navigation([foto_page, pdf_page, cart_page, pull_page])
pg.run()
