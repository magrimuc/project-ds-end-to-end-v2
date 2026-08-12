import streamlit as st
import pandas as pd
import os

# Initialize cart in session state if not present
if "cart" not in st.session_state:
    st.session_state.cart = {}

st.markdown('<div class="main-header">🛒 Ihr Warenkorb</div>', unsafe_allow_html=True)
st.markdown('<div class="sub-header">Hier finden Sie alle gesammelten Artikel aus Ihren Materiallisten.</div>', unsafe_allow_html=True)

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
    if st.button("🗑️ Warenkorb leeren", key="clear_cart_global"):
        st.session_state.cart = {}
        st.rerun()

# "+ Neuer Artikel" Popover under the cart
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
        key="manual_add_global_sel"
    )
    qty_manual = st.number_input("Menge:", min_value=1, value=1, step=1, key="manual_add_global_qty")
    if st.button("Hinzufügen", key="manual_add_global_btn", type="primary", use_container_width=True):
        if selected_prod != 0:
            st.session_state.cart[selected_prod] = st.session_state.cart.get(selected_prod, 0) + qty_manual
            st.toast("Artikel hinzugefügt!")
            st.rerun()
