import streamlit as st
import pandas as pd
import os

# Initialize cart in session state if not present
if "cart" not in st.session_state:
    st.session_state.cart = {}

st.markdown('<div class="main-header">🛒 Your Cart</div>', unsafe_allow_html=True)
st.markdown('<div class="sub-header">Here you will find all the collected items from your school supply lists.</div>', unsafe_allow_html=True)

if not st.session_state.cart:
    st.session_state.cart_source = None
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
    if st.button("🗑️ Clear Cart", key="clear_cart_global"):
        st.session_state.cart = {}
        st.session_state.cart_source = None
        st.rerun()

# "+ New Item" Popover under the cart
st.markdown("---")
products_df = pd.read_csv("data/products.csv")
options = {row['id']: f"{row['name']} ({row['brand']}) - {row['price']:.2f} €" for _, row in products_df.iterrows()}
options[0] = "-- No matching product --"

with st.popover("➕ New Item", use_container_width=True):
    st.markdown("### Search & Add Item")
    selected_prod = st.selectbox(
        "Select product:",
        options=list(options.keys()),
        format_func=lambda x: options[x],
        key="manual_add_global_sel"
    )
    qty_manual = st.number_input("Quantity:", min_value=1, value=1, step=1, key="manual_add_global_qty")
    if st.button("Add", key="manual_add_global_btn", type="primary", use_container_width=True):
        if selected_prod != 0:
            st.session_state.cart[selected_prod] = st.session_state.cart.get(selected_prod, 0) + qty_manual
            st.toast("Item added!")
            st.rerun()
