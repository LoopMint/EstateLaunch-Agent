import io
import pandas as pd
import streamlit as st
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.utils import ImageReader
from reportlab.pdfgen import canvas

# --- App Config ---
st.set_page_config(page_title="Agent Desk", layout="wide")

if "properties" not in st.session_state:
    st.session_state.properties = []

# --- Helper: PDF Engine ---
def generate_brochure(listing):
    mem = io.BytesIO()
    c = canvas.Canvas(mem, pagesize=letter)
    c.setFont("Helvetica-Bold", 16)
    c.drawString(50, 750, "The Property") # Updated Header
    c.setFont("Helvetica", 12)
    c.drawString(50, 730, f"Headline: {listing.get('headline')}")
    c.drawString(50, 710, f"Price: {listing.get('price')}")
    c.save()
    mem.seek(0)
    return mem.getvalue()

# --- Tab Layout ---
tabs = st.tabs(["Database Listing & Finance", "CRM Intake", "Brochure PDF", "Social Media Plan", "Appointment"])

# --- TAB 1: DATABASE & FINANCE ---
with tabs[0]:
    st.subheader("Property Portfolio Ledger")
    
    if st.session_state.properties:
        df = pd.DataFrame(st.session_state.properties)
        edited_df = st.data_editor(
            df,
            column_config={"status": st.column_config.SelectboxColumn(options=["Available", "Sold"])},
            use_container_width=True
        )
        # Update session state from editor
        st.session_state.properties = edited_df.to_dict('records')
        
        # Finance Reporting Integration
        st.subheader("End-of-Day Revenue Report")
        sold_props = [p for p in st.session_state.properties if p['status'] == 'Sold']
        if sold_props:
            total_comm = sum([float(str(p['actual_sold_price']).replace('$','').replace(',','')) * 0.02 for p in sold_props])
            st.metric("Total Commission Received", f"${total_comm:,.2f}")
        else:
            st.info("No sold properties yet.")
    else:
        st.write("No properties added yet.")

# --- TAB 2: CRM ---
with tabs[1]:
    st.subheader("Add New Property")
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

# --- TAB 3: BROCHURE PDF ---
with tabs[2]:
    st.subheader("Generate Brochure")
    selection = st.selectbox("Select Property", [p['headline'] for p in st.session_state.properties])
    target = next((p for p in st.session_state.properties if p['headline'] == selection), None)
    if target:
        st.download_button("Download PDF", generate_brochure(target), "brochure.pdf")

# --- TAB 4: SOCIAL MEDIA PLAN ---
with tabs[3]:
    st.subheader("Social Media Plan")
    st.write("Plan your content here.")
    # (Captions and Planner logic)

# --- TAB 5: APPOINTMENT ---
with tabs[4]:
    st.subheader("Appointments")
    # (Appointment booking logic)
