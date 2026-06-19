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

if "selected_property_id" not in st.session_state:
    st.session_state.selected_property_id = 1

if "appointments" not in st.session_state:
    st.session_state.appointments = []

if "template_notes" not in st.session_state:
    st.session_state.template_notes = []

if "images" not in st.session_state:
    st.session_state.images = []

if "closed_deals" not in st.session_state:
    st.session_state.closed_deals = []

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
    font_names = [
        "arialbd.ttf" if bold else "arial.ttf",
        "DejaVuSans-Bold.ttf" if bold else "DejaVuSans.ttf",
        "LiberationSans-Bold.ttf" if bold else "LiberationSans.ttf",
        "Helvetica-Bold" if bold else "Helvetica"
    ]
    for name in font_names:
        try:
            return ImageFont.truetype(name, size)
        except Exception:
            continue
    return ImageFont.load_default()


def parse_price_to_float(price_str):
    try:
        cleaned = re.sub(r'[^\d.]', '', str(price_str))
        return float(cleaned) if cleaned else 0.0
    except Exception:
        return 0.0


def wrap_text(draw, text, fnt, max_width):
    words = str(text).split()
    lines, line = [], ""
    for word in words:
        trial = (line + " " + word).strip()
        width = draw.textbbox((0, 0), trial, font=fnt)[2]
        if width <= max_width:
            line = trial
        else:
            if line:
                lines.append(line)
            line = word
    if line:
        lines.append(line)
    return lines


# --- Core Asset Render Engines ---
def social_image(size, listing, images, platform, headline, base_font_size, selected_photo, accent_hex="#d94f30", footer_hex="#10252b"):
    w, h = size
    base = Image.new("RGB", size, footer_hex)

    if images:
        if selected_photo:
            chosen = next((img for name, img in images if name == selected_photo), images[0][1])
        else:
            chosen = images[0][1]
        base = fit_image(chosen, size)
        overlay = Image.new("RGBA", size, (0, 0, 0, 105))
        base = Image.alpha_composite(base.convert("RGBA"), overlay).convert("RGB")

    draw = ImageDraw.Draw(base)
    margin = max(42, int(w * 0.06))

    price = listing.get("price", "$749,000")
    location = listing.get("location", "Singapore")
    agent = listing.get("agent", "Angela Lee")
    deadline = listing.get("deadline", str(date.today() + timedelta(days=21)))

    is_landscape = w > h
    optimized_font_size = int(base_font_size * 0.75) if is_landscape else base_font_size

    headline_font = font(optimized_font_size, True)
    loc_font = font(max(18, int(optimized_font_size * 0.45)), False)
    price_font = font(max(20, int(optimized_font_size * 0.50)), True)

    footer_height = int(h * 0.12) if h > w else int(h * 0.15)
    content_y_max = h - footer_height - margin

    wrapped_lines = wrap_text(draw, headline, headline_font, w - margin * 2)[:3]
    line_height = draw.textbbox((0, 0), "A", font=headline_font)[3] * 1.2
    total_text_h = len(wrapped_lines) * line_height

    current_y = content_y_max - total_text_h - 110
    if current_y < margin:
        current_y = margin

    for line in wrapped_lines:
        draw.text((margin, current_y), line, fill="white", font=headline_font)
        current_y += line_height

    current_y += 10
    draw.text((margin, current_y), f"{location}  |  Contact by {deadline}", fill="#e2e8f0", font=loc_font)

    current_y += 24
    p_box = draw.textbbox((0, 0), price, font=price_font)
    p_w = p_box[2] - p_box[0]
    p_h = p_box[3] - p_box[1]

    pad = 6
    draw.rounded_rectangle(
        (margin, current_y, margin + p_w + (pad * 2), current_y + p_h + (pad * 2) + 4),
        radius=4,
        fill=accent_hex
    )
    draw.text((margin + pad, current_y + pad), price, fill="white", font=price_font)

    draw.rectangle((0, h - footer_height, w, h), fill=footer_hex)
    footer_text_font = font(max(18, int(w * 0.026)), True)
    footer_y = h - int(footer_height / 2) - 10

    draw.text((margin, footer_y), f"{agent}", fill="white", font=footer_text_font)
    draw.text((w - margin - 160, footer_y), platform.split()[0], fill="#9edfd4", font=footer_text_font)

    return base


def make_brochure_pdf(listing, images, edits, hero_name, bottom_names, accent_hex="#d94f30", footer_hex="#10252b"):
    mem = io.BytesIO()
    c = canvas.Canvas(mem, pagesize=letter)
    w, h = letter

    safe = 0
    usable_w = w
    hero_h = 300

    accent_color = colors.HexColor(accent_hex)
    footer_color = colors.HexColor(footer_hex)

    hero_y = h - hero_h

    if images and hero_name:
        hero_img = next((img for name, img in images if name == hero_name), images[0][1])
        hero = fit_image(hero_img, (int(usable_w * 2), int(hero_h * 2)))
        b = io.BytesIO()
        hero.save(b, format="JPEG", quality=90)
        b.seek(0)
        c.drawImage(ImageReader(b), 0, hero_y, width=usable_w, height=hero_h)

    c.showPage()
    c.save()
    mem.seek(0)
    return mem.getvalue()


def caption_for(platform, listing):
    location = listing.get("location", "Singapore")
    price = listing.get("price", "POA")
    deadline = listing.get("deadline", "soon")
    details = listing.get("details", "Premium residential project.")

    if "TikTok" in platform or "Story" in platform:
        return f"POV: Walking through your future luxury layout in {location}. Listed at {price}. Contact before {deadline}."
    if "LinkedIn" in platform:
        return f"New Residential Opportunity in {location}: {details} Positioned at {price}."
    return f"Just listed in {location}: {details} Guide Price: {price}."


# --- Tabs ---
tabs = st.tabs([
    "Property Info",
    "Creative Design",
    "Social Media Plan",
    "Set Appointment",
    "Commission Dashboard"
])

active_id = st.session_state.selected_property_id
listing = next((p for p in st.session_state.properties if p['id'] == active_id), st.session_state.properties[0])

images = st.session_state.get("images", [])

# TAB 1 (unchanged logic)
with tabs[0]:
    col1, col2 = st.columns([.45, .55])

    with col1:
        uploads = st.file_uploader("Upload images", type=["png", "jpg", "jpeg"], accept_multiple_files=True)
        new_images = load_images(uploads)

        if new_images:
            st.session_state.images = [(name, img.copy()) for name, img in new_images]

    with col2:
        in_headline = st.text_input("Property Name", listing.get("headline", ""))

        if st.button("Submit"):
            st.rerun()

# TAB 5 FIX SAFE
with tabs[4]:
    st.subheader("Commission Dashboard")

    if st.session_state.closed_deals:
        df_deals = pd.DataFrame(st.session_state.closed_deals)
        st.dataframe(df_deals)

        st.bar_chart(df_deals.groupby("Property")["Commission"].sum())
        st.metric("Total Commission", f"${df_deals['Commission'].sum():,.2f}")
    else:
        st.info("No closed deals yet.")
