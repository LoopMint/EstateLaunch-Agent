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
.block-container{max-width:1240px;padding-top:1.25rem}.title{font-size:2rem;font-weight:800;color:#17202a}.sub{color:#5d6673;margin:.2rem 0 1rem}.panel{border:1px solid #dfe5ec;border-radius:8px;padding:1rem;background:white;box-shadow:0 1px 3px rgba(0,0,0,.04);margin-bottom:.75rem}.kpi{border-left:4px solid #1b6f6a;background:#f5f8fa;border-radius:6px;padding:.7rem 1rem}.tag{background:#e7f2f0;color:#164e4a;border-radius:99px;padding:.15rem .45rem;font-size:.78rem;font-weight:700}.preview{border:1px solid #d7dee7;border-radius:8px;overflow:hidden;background:#fff}.hero{min-height:310px;background:#10252b;color:white;display:flex;align-items:flex-end;padding:24px;background-size:cover;background-position:center}.hero h2{font-size:2.1rem;margin:0 0 4px}.price{display:inline-block;background:#d94f30;color:white;border-radius:4px;padding:6px 10px;font-weight:800}.grid2{display:grid;grid-template-columns:1fr 1fr;gap:14px;padding:18px}.small{color:#66717e;font-size:.9rem}
</style>
""", unsafe_allow_html=True)
st.markdown(f'<div class="title">{APP_NAME}</div><div class="sub">Real estate listing, brochure, Canva, social creative, appointment, and revenue workflow.</div>', unsafe_allow_html=True)

if "listing" not in st.session_state:
    st.session_state.listing = {}
if "appointments" not in st.session_state:
    st.session_state.appointments = []
if "template_notes" not in st.session_state:
    st.session_state.template_notes = []

SOCIAL_SIZES = {
    "TikTok Portrait 1080x1920": (1080, 1920),
    "Instagram Portrait 1080x1350": (1080, 1350),
    "Instagram Square 1080x1080": (1080, 1080),
    "Facebook Landscape 1200x630": (1200, 630),
    "LinkedIn Landscape 1200x627": (1200, 627),
    "Story/Reel Portrait 1080x1920": (1080, 1920),
}


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
    try:
        name = "arialbd.ttf" if bold else "arial.ttf"
        return ImageFont.truetype(name, size)
    except Exception:
        return ImageFont.load_default()


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


def social_image(size, listing, images, platform):
    w, h = size
    base = Image.new("RGB", size, "#10252b")
    if images:
        base = fit_image(images[0][1], size)
        overlay = Image.new("RGBA", size, (0, 0, 0, 95))
        base = Image.alpha_composite(base.convert("RGBA"), overlay).convert("RGB")
    draw = ImageDraw.Draw(base)
    margin = max(42, int(w * 0.055))
    price = listing.get("price", "$749,000")
    location = listing.get("location", "Austin, TX")
    headline = listing.get("headline", "Modern Home Just Listed")
    agent = listing.get("agent", "Angela Lee | 555-0100")
    deadline = listing.get("deadline", str(date.today() + timedelta(days=21)))
    badge_h = max(58, int(h * 0.045))
    draw.rounded_rectangle((margin, margin, margin + int(w * 0.34), margin + badge_h), radius=10, fill="#d94f30")
    draw.text((margin + 22, margin + 14), price, fill="white", font=font(max(26, int(w * 0.034)), True))
    headline_font = font(max(42, int(w * 0.065)), True)
