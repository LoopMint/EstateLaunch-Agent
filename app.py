import io
import pandas as pd
import streamlit as st
from reportlab.lib.pagesizes import letter
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
    c.drawString(50, 710, f"Location: {listing.get('location')}")
    c.drawString(50, 690, f"Listing Price: {listing.get('price')}")
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
            use_container_width=True, num_rows="dynamic"
        )
        st.session_state.properties = edited_df.to_dict('records')
        
        st.divider()
        st.subheader("Finance Reports & End-of-Day Revenue")
        
        sold_props = [p for p in st.session_state.properties if p.get('status') == 'Sold']
        if sold_props:
            # Calculation: Assuming 2% commission on actual sold price
            total_comm = sum([float(str(p.get('actual_sold_price', 0)).replace('$','').replace(',','')) * 0.02 for p in sold_props])
            st.metric("Total Commission Received (End-of-Day)", f"${total_comm:,.2f}")
            st.table(pd.DataFrame(sold_props)[["headline", "price", "actual_sold_price"]])
        else:
            st.info("No properties marked as 'Sold' for revenue calculation.")
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
    st.write("### Caption Repository")
    st.text_area("Create and save your post captions here:")
    st.write("### Virality Planner")
    st.info("Track your content calendar based on AI-driven posting times.")

# --- TAB 5: APPOINTMENT ---
with tabs[4]:
    st.subheader("Appointments")
    st.write("Manage your showings and client meetings.")
