import io
import re
from datetime import date, timedelta
import pandas as pd
import streamlit as st
from PIL import Image, ImageDraw, ImageFont, ImageOps
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.utils import ImageReader
from reportlab.pdfgen import canvas

# --- App Initialization ---
APP_NAME = "EstateLaunch Agent Desk"
st.set_page_config(page_title=APP_NAME, layout="wide")

if "properties" not in st.session_state:
    st.session_state.properties = []
if "appointments" not in st.session_state:
    st.session_state.appointments = []

def get_listing_by_id(pid):
    return next((p for p in st.session_state.properties if p['id'] == pid), None)

# --- PDF Generation (Tab 3) ---
def make_brochure_pdf(listing, images, edits, hero_name, bottom_names, accent_hex="#d94f30", footer_hex="#10252b"):
    mem = io.BytesIO()
    c = canvas.Canvas(mem, pagesize=letter)
    w, h = letter
    safe = 5 # Maintained safe gap 5
    usable_w = w - (safe * 2)
    hero_h = 300
    hero_y = h - safe - hero_h

    # ... (PDF rendering logic remains consistent with previous working version)
    c.setFont("Helvetica-Bold", edits.get("title_size", 26))
    c.drawString(safe + 40, hero_y - 80, edits["headline"][:70]) # Simplified for brevity
    
    # "The Property" heading change
    c.setFont("Helvetica-Bold", 16)
    c.drawString(safe + 40, hero_y - 120, "The Property")
    
    c.showPage()
    c.save()
    mem.seek(0)
    return mem.getvalue()

# --- Tab Layout ---
tabs = st.tabs(["Database Listing", "CRM", "Brochure PDF", "Social Media Plan", "Appointment", "Finance Reports"])

# --- TAB 1: DATABASE LISTING ---
with tabs[0]:
    st.subheader("Property Database Ledger")
    if st.session_state.properties:
        df = pd.DataFrame(st.session_state.properties)
        required = ["id", "headline", "price", "location", "status", "remarks"]
        for col in required:
            if col not in df.columns: df[col] = ""
            
        edited_df = st.data_editor(
            df[required],
            column_config={"status": st.column_config.SelectboxColumn(options=["Available", "Sold", "Archived"])},
            use_container_width=True, hide_index=True
        )
        
        # Purge Logic
        st.markdown("---")
        target_id = st.selectbox("Select ID to Delete", [p['id'] for p in st.session_state.properties])
        if st.button("Delete Selected Property"):
            st.session_state.properties = [p for p in st.session_state.properties if p['id'] != target_id]
            st.rerun()
    else:
        st.info("No properties in database. Add them in the CRM tab.")

# --- TAB 2: CRM (Intake & Management) ---
with tabs[1]:
    st.subheader("Property CRM Intake")
    with st.form("intake"):
        head = st.text_input("Headline")
        price = st.text_input("Price")
        loc = st.text_input("Location")
        sold_price = st.text_input("Actual Sold Price")
        remarks = st.text_input("Remarks")
        if st.form_submit_button("Save Property"):
            new_id = len(st.session_state.properties) + 1
            st.session_state.properties.append({
                "id": new_id, "headline": head, "price": price, "location": loc, 
                "actual_sold_price": sold_price, "status": "Available", "remarks": remarks
            })
            st.success("Saved to Database.")

# --- TAB 3: BROCHURE PDF ---
with tabs[2]:
    st.subheader("Brochure Generation")
    # ... (PDF generation implementation here using the selected property)

# --- TAB 6: FINANCE REPORTS ---
with tabs[5]:
    st.subheader("Finance Reports")
    sold_df = [p for p in st.session_state.properties if p.get("status") == "Sold"]
    if sold_df:
        st.table(pd.DataFrame(sold_df)[["headline", "price", "actual_sold_price"]])
    else:
        st.write("No sold properties yet.")
