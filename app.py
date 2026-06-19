import io
import pandas as pd
import streamlit as st
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas

# --- App Config ---
st.set_page_config(page_title="Agent Desk", layout="wide")

if "properties" not in st.session_state:
    st.session_state.properties = []
if "appointments" not in st.session_state:
    st.session_state.appointments = []

# --- Helper: PDF Engine ---
def generate_brochure(listing):
    mem = io.BytesIO()
    c = canvas.Canvas(mem, pagesize=letter)
    c.setFont("Helvetica-Bold", 16)
    c.drawString(50, 750, "The Property") 
    c.setFont("Helvetica", 12)
    c.drawString(50, 730, f"Headline: {listing.get('headline')}")
    c.drawString(50, 710, f"Location: {listing.get('location')}")
    c.drawString(50, 690, f"Listing Price: {listing.get('price')}")
    c.save()
    mem.seek(0)
    return mem.getvalue()

# --- Tab Layout ---
tabs = st.tabs(["Database Listing & Finance", "CRM Intake", "Brochure PDF", "Social Media Plan", "Appointments & Financial Reporting"])

# --- TAB 1: DATABASE LISTING ---
with tabs[0]:
    st.subheader("Property Portfolio Ledger")
    if st.session_state.properties:
        df = pd.DataFrame(st.session_state.properties)
        edited_df = st.data_editor(
            df,
            column_config={"status": st.column_config.SelectboxColumn(options=["Available", "Sold"])},
            use_container_width=True, num_rows="dynamic"
        )
        st.session_state.properties = edited_df.to_dict('records')
    else:
        st.write("No properties in database.")

# --- TAB 2: CRM ---
with tabs[1]:
    st.subheader("Property CRM Intake")
    with st.form("crm_intake"):
        head = st.text_input("Headline")
        price = st.text_input("Listing Price")
        sold = st.text_input("Actual Sold Price")
        loc = st.text_input("Location")
        if st.form_submit_button("Add to Database"):
            st.session_state.properties.append({
                "headline": head, "price": price, "actual_sold_price": sold, 
                "location": loc, "status": "Available"
            })
            st.success("Property added.")
            st.rerun()

# --- TAB 3: BROCHURE PDF ---
with tabs[2]:
    st.subheader("Generate Brochure")
    if st.session_state.properties:
        selection = st.selectbox("Select Property", [p['headline'] for p in st.session_state.properties])
        target = next((p for p in st.session_state.properties if p['headline'] == selection), None)
        if target:
            st.download_button("Download PDF", generate_brochure(target), "brochure.pdf")
    else:
        st.warning("Add a property first.")

# --- TAB 4: SOCIAL MEDIA PLAN ---
with tabs[3]:
    st.subheader("Social Media Plan")
    st.text_area("Caption Repository:")
    st.info("Virality Planner: Track your content calendar here.")

# --- TAB 5: APPOINTMENTS & FINANCIAL REPORTING ---
with tabs[4]:
    st.subheader("Appointments & Financial Reporting")
    
    # Appointment Section
    st.markdown("### Client Appointment Registry")
    with st.form("appt_form"):
        p_name = st.selectbox("Select Property", [p['headline'] for p in st.session_state.properties] if st.session_state.properties else ["No properties"])
        c_name = st.text_input("Client Name")
        c_date = st.date_input("Appointment Date")
        if st.form_submit_button("Add Appointment"):
            st.session_state.appointments.append({"Property": p_name, "Client": c_name, "Date": str(c_date)})
            st.rerun()

    if st.session_state.appointments:
        st.table(pd.DataFrame(st.session_state.appointments))

    st.divider()

    # Financial Reporting Section
    st.markdown("### Commission Reconciliation")
    if st.session_state.properties:
        df_props = pd.DataFrame(st.session_state.properties)
        
        def clean_price(val):
            return float(str(val).replace('$', '').replace(',', '').strip()) if val else 0.0

        df_props['cleaned_price'] = df_props['actual_sold_price'].apply(clean_price)
        df_props['Commission (2%)'] = df_props['cleaned_price'] * 0.02

        sold_df = df_props[df_props['status'] == 'Sold']
        pending_df = df_props[df_props['status'] != 'Sold']

        c1, c2 = st.columns(2)
        with c1:
            st.metric("Total Commission Received (Sold)", f"${sold_df['Commission (2%)'].sum():,.2f}")
        with c2:
            st.metric("Pending Commission (Pipeline)", f"${pending_df['Commission (2%)'].sum():,.2f}")

        st.markdown("#### Transaction Ledger")
        st.table(df_props[['headline', 'status', 'actual_sold_price', 'Commission (2%)']])
    else:
        st.info("No property data available.")
