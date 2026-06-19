import io
import re
import zipfile
from datetime import date, timedelta
from urllib.parse import quote_plus

import pandas as pd
import requests
import streamlit as st
from bs4 import BeautifulSoup
from PIL import Image, ImageDraw, ImageFont, ImageOps
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.utils import ImageReader
from reportlab.pdfgen import canvas

APP_NAME = "EstateLaunch Agent Desk"
st.set_page_config(page_title=APP_NAME, layout="wide")
st.markdown("""
<style>
.block-container{max-width:1240px;padding-top:5.25rem;font-family:system-ui,-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif}
.title{font-size:2rem;font-weight:800;color:#17202a}
.sub{color:#5d6673;margin:.2rem 0 1rem}
.panel{border:1px solid #dfe5ec;border-radius:8px;padding:1rem;background:white;box-shadow:0 1px 3px rgba(0,0,0,.04);margin-bottom:.75rem}
.kpi{border-left:4px solid #1b6f6a;background:#f5f8fa;border-radius:6px;padding:.7rem 1rem}
.tag{background:#e7f2f0;color:#164e4a;border-radius:99px;padding:.15rem .45rem;font-size:.78rem;font-weight:700}
.preview{border:1px solid #d7dee7;border-radius:8px;overflow:hidden;background:#fff}
.hero{min-height:310px;background:#10252b;color:white;display:flex;align-items:flex-end;padding:24px;background-size:cover;background-position:center}
.hero h2{font-size:2.1rem;margin:0 0 4px}
.price{display:inline-block;background:#d94f30;color:white;border-radius:4px;padding:6px 10px;font-weight:800}
.grid2{display:grid;grid-template-columns:1fr 1fr;gap:14px;padding:18px}
.small{color:#66717e;font-size:.9rem}
</style>
""", unsafe_allow_html=True)
st.markdown(
    f'<div class="title">{APP_NAME}</div>'
    '<div class="sub">Singapore real estate multi-property tracker, marketing engine, and ABSD revenue desk.</div>',
    unsafe_allow_html=True
)

# Global Session Infrastructure
if "properties" not in st.session_state:
    st.session_state.properties = [
        {
            "id": 1,
            "headline": "ParkTown Residences",
            "price": "$1,750,000",
            "location": "Tampines North, Singapore",
            "deadline": str(date.today() + timedelta(days=21)),
            "agent": "Angela Lee | 65-9123-4567",
            "details": "Thoughtfully designed as a nature-inspired extension of the neighborhood, with integrated retail mall access.",
            "canva_url": "",
            "status": "Available",
            "commission_rate": 2.5
        }
    ]
if "selected_property_id" not in st.session_state: st.session_state.selected_property_id = 1
if "appointments" not in st.session_state: st.session_state.appointments = []
if "template_notes" not in st.session_state: st.session_state.template_notes = []
if "images" not in st.session_state: st.session_state.images = []
if "closed_deals" not in st.session_state: st.session_state.closed_deals = []

SOCIAL_SIZES = {
    "TikTok Portrait 1080x1920": (1080, 1920),
    "Instagram Portrait 1080x1350": (1080, 1350),
    "Instagram Square 1080x1080": (1080, 1080),
    "Facebook Landscape 1200x630": (1200, 630),
    "LinkedIn Landscape 1200x627": (1200, 627),
    "Story/Reel Portrait 1080x1920": (1080, 1920),
}

# --- Utility Core Functions ---
def load_images(uploaded):
    images = []
    for file in uploaded or []:
        try:
            img = Image.open(io.BytesIO(file.getvalue())).convert("RGB")
            images.append((file.name, img))
        except Exception:
            st.warning(f"Could not read image: {file.name}")
    return images

def fit_image(img, size):
    return ImageOps.fit(img, size, method=Image.LANCZOS, centering=(0.5, 0.5))

def font(size, bold=False):
    font_names = ["arialbd.ttf" if bold else "arial.ttf", "DejaVuSans-Bold.ttf" if bold else "DejaVuSans.ttf", "LiberationSans-Bold.ttf" if bold else "LiberationSans.ttf", "Helvetica-Bold" if bold else "Helvetica"]
    for name in font_names:
        try: return ImageFont.truetype(name, size)
        except: continue
    return ImageFont.load_default()

def parse_price_to_float(price_str):
    try:
        cleaned = re.sub(r'[^\d.]', '', str(price_str))
        return float(cleaned) if cleaned else 0.0
    except: return 0.0

def wrap_text(draw, text, fnt, max_width):
    words = str(text).split()
    lines, line = [], ""
    for word in words:
        trial = (line + " " + word).strip()
        width = draw.textbbox((0, 0), trial, font=fnt)[2]
        if width <= max_width: line = trial
        else:
            if line: lines.append(line)
            line = word
    if line: lines.append(line)
    return lines

# --- Asset Render Engines (Condensed) ---
def social_image(size, listing, images, platform, headline, base_font_size, selected_photo, accent_hex="#d94f30", footer_hex="#10252b"):
    w, h = size
    base = Image.new("RGB", size, footer_hex)
    if images:
        chosen = next((img for name, img in images if name == selected_photo), images[0][1]) if selected_photo else images[0][1]
        base = fit_image(chosen, size)
        overlay = Image.new("RGBA", size, (0, 0, 0, 105))
        base = Image.alpha_composite(base.convert("RGBA"), overlay).convert("RGB")
    draw = ImageDraw.Draw(base)
    margin = max(42, int(w * 0.06))
    headline_font = font(base_font_size, True)
    draw.text((margin, h/2), headline, fill="white", font=headline_font)
    return base

def caption_for(platform, listing):
    return f"Just listed in {listing.get('location', 'Singapore')}: {listing.get('details', '')} Guide Price: {listing.get('price', 'POA')}."

def make_brochure_pdf(listing, images, edits, hero_name, bottom_names, accent_hex="#d94f30", footer_hex="#10252b"):
    mem = io.BytesIO()
    c = canvas.Canvas(mem, pagesize=letter)
    c.drawString(100, 750, f"Brochure: {listing.get('headline', '')}")
    c.save()
    mem.seek(0)
    return mem.getvalue()

# --- App Tabs ---
tabs = st.tabs(["Property Info", "Creative Design", "Social Media Plan", "Set Appointment", "Commission Dashboard"])

active_id = st.session_state.selected_property_id
listing = next((p for p in st.session_state.properties if p['id'] == active_id), st.session_state.properties[0])

with tabs[0]:
    col1, col2 = st.columns([.45, .55])
    with col1:
        uploads = st.file_uploader("Upload images", type=["png", "jpg", "jpeg"], accept_multiple_files=True)
        if uploads: st.session_state.images = load_images(uploads)
    with col2:
        in_headline = st.text_input("Property Name", listing.get("headline", ""))
        if st.button("Submit"):
            listing.update({"headline": in_headline})
            st.rerun()

with tabs[4]:
    st.subheader("Potential Earnings & Commission Dashboard")
    with st.expander("Log a New Sale"):
        with st.form("log_sale_form", clear_on_submit=True):
            selected_listing = st.selectbox("Select Listing", [p['headline'] for p in st.session_state.properties])
            sale_price = st.number_input("Final Sale Price (SGD)", value=1000000.0, step=1000.0)
            comm_rate = st.number_input("Commission Rate (%)", value=2.5, step=0.1)
            if st.form_submit_button("Log Sale"):
                earned = sale_price * (comm_rate / 100)
                st.session_state.closed_deals.append({"Property": selected_listing, "Price": sale_price, "Commission": earned})
                st.rerun()

    if st.session_state.closed_deals:
        df_deals = pd.DataFrame(st.session_state.closed_deals)
        edited_df = st.data_editor(df_deals, use_container_width=True)
        if st.button("Delete Selected Records"):
            st.session_state.closed_deals = edited_df.to_dict('records')
            st.rerun()
        st.bar_chart(df_deals.groupby("Property")["Commission"].sum())
        st.metric("Total Realized Commission", f"SGD ${df_deals['Commission'].sum():,.2f}")
