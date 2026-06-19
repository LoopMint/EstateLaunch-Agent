import re
import zipfile
import io
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
.block-container{max-width:1240px;padding-top:5.25rem;font-family:system-ui}
.title{font-size:2rem;font-weight:800;color:#17202a}
.sub{color:#5d6673;margin:.2rem 0 1rem}
.preview{border:1px solid #d7dee7;border-radius:8px;overflow:hidden;background:#fff}
.hero{min-height:300px;background:#10252b;color:white;display:flex;align-items:flex-end;padding:24px}
.price{display:inline-block;background:#d94f30;color:white;border-radius:4px;padding:6px 10px;font-weight:800}
.grid2{display:grid;grid-template-columns:1fr 1fr;gap:14px;padding:18px}
.small{color:#66717e;font-size:.9rem}
</style>
""", unsafe_allow_html=True)

st.markdown(f"<div class='title'>{APP_NAME}</div>", unsafe_allow_html=True)
st.markdown("<div class='sub'>Real estate marketing + brochure + CRM engine</div>", unsafe_allow_html=True)


# ---------------- SESSION STATE ----------------
if "properties" not in st.session_state:
    st.session_state.properties = [{
        "id": 1,
        "headline": "ParkTown Residences",
        "price": "$1,750,000",
        "location": "Tampines North, Singapore",
        "deadline": str(date.today() + timedelta(days=21)),
        "agent": "Angela Lee",
        "details": "Nature-inspired residential development.",
        "status": "Available",
        "commission_rate": 2.5
    }]

if "selected_property_id" not in st.session_state:
    st.session_state.selected_property_id = 1

if "images" not in st.session_state:
    st.session_state.images = []

if "appointments" not in st.session_state:
    st.session_state.appointments = []

if "closed_deals" not in st.session_state:
    st.session_state.closed_deals = []


# ---------------- HELPERS ----------------
def load_images(uploaded):
    imgs = []
    for f in uploaded or []:
        try:
            img = Image.open(io.BytesIO(f.getvalue())).convert("RGB")
            imgs.append((f.name, img))
        except:
            pass
    return imgs


def fit(img, size):
    return ImageOps.fit(img, size, method=Image.LANCZOS)


def parse_price(x):
    try:
        return float(re.sub(r"[^\d.]", "", str(x)))
    except:
        return 0.0


def wrap(draw, text, font, max_w):
    words = str(text).split()
    lines, line = [], ""
    for w in words:
        t = (line + " " + w).strip()
        if draw.textlength(t, font=font) <= max_w:
            line = t
        else:
            if line:
                lines.append(line)
            line = w
    if line:
        lines.append(line)
    return lines


# ---------------- SOCIAL IMAGE ----------------
def social_image(size, listing, images):
    w, h = size
    base = Image.new("RGB", size, "#10252b")

    if images:
        base = fit(images[0][1], size)

    draw = ImageDraw.Draw(base)

    font_big = ImageFont.load_default()
    margin = 40

    draw.text((margin, margin), listing["headline"], fill="white", font=font_big)
    draw.text((margin, margin + 30), listing["location"], fill="white", font=font_big)
    draw.text((margin, margin + 60), listing["price"], fill="white", font=font_big)

    return base


# ---------------- PDF ----------------
def make_pdf(listing, images):
    mem = io.BytesIO()
    c = canvas.Canvas(mem, pagesize=letter)

    w, h = letter

    c.setFont("Helvetica-Bold", 20)
    c.drawString(50, 750, listing["headline"])

    c.setFont("Helvetica", 12)
    c.drawString(50, 730, listing["location"])
    c.drawString(50, 710, listing["price"])

    if images:
        img = images[0][1]
        buf = io.BytesIO()
        img.save(buf, format="JPEG")
        buf.seek(0)
        c.drawImage(ImageReader(buf), 50, 400, width=500, height=250)

    c.showPage()
    c.save()
    mem.seek(0)
    return mem.getvalue()


# ---------------- TABS ----------------
tabs = st.tabs([
    "Property Info",
    "Creative Design",
    "Social Media",
    "Appointments",
    "Commission"
])

listing = next((p for p in st.session_state.properties
                if p["id"] == st.session_state.selected_property_id),
               st.session_state.properties[0])

images = st.session_state.images


# ---------------- TAB 1 ----------------
with tabs[0]:
    st.subheader("Property Entry")

    uploads = st.file_uploader("Upload images", type=["png", "jpg", "jpeg"], accept_multiple_files=True)
    if uploads:
        st.session_state.images = load_images(uploads)

    listing["headline"] = st.text_input("Headline", listing["headline"])
    listing["price"] = st.text_input("Price", listing["price"])
    listing["location"] = st.text_input("Location", listing["location"])

    if st.button("Save"):
        st.success("Saved")


# ---------------- TAB 2 ----------------
with tabs[1]:
    st.subheader("Brochure")

    pdf = make_pdf(listing, images)

    st.download_button(
        "Download PDF",
        pdf,
        file_name="brochure.pdf",
        mime="application/pdf"
    )


# ---------------- TAB 3 ----------------
with tabs[2]:
    st.subheader("Social Media")

    for k in ["TikTok", "Instagram", "LinkedIn"]:
        st.markdown(f"### {k}")
        st.text(caption_for := f"{listing['headline']} in {listing['location']} - {listing['price']}")

    st.image(social_image((1080, 1080), listing, images))


# ---------------- TAB 4 ----------------
with tabs[3]:
    st.subheader("Appointments")

    with st.form("appt"):
        name = st.text_input("Client")
        dt = st.date_input("Date", date.today())
        if st.form_submit_button("Add"):
            st.session_state.appointments.append({
                "client": name,
                "date": str(dt),
                "property": listing["headline"]
            })
            st.success("Added")

    st.dataframe(pd.DataFrame(st.session_state.appointments))


# ---------------- TAB 5 ----------------
with tabs[4]:
    st.subheader("Commission")

    if st.session_state.closed_deals:
        df = pd.DataFrame(st.session_state.closed_deals)
        st.dataframe(df)
        st.bar_chart(df.groupby("Property")["Commission"].sum())
        st.metric("Total", f"${df['Commission'].sum():,.2f}")
    else:
        st.info("No deals yet.")
