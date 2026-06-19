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

# ---------------------------------------------------------
# APP CONFIG
# ---------------------------------------------------------

APP_NAME = "EstateLaunch Agent Desk"
st.set_page_config(page_title=APP_NAME, layout="wide")

st.markdown("""
<style>
.block-container{max-width:1240px;padding-top:5.25rem;font-family:system-ui,-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif}
.title{font-size:2rem;font-weight:800;color:#17202a}
.sub{color:#5d6673;margin:.2rem 0 1rem}
.navbar{display:flex;gap:.5rem;margin:1rem 0 1.5rem}
.navbtn{flex:1;padding:.6rem .8rem;border-radius:8px;border:1px solid #dfe5ec;background:#f8fafc;color:#17202a;font-weight:600;text-align:center;cursor:pointer}
.navbtn-active{background:#10252b;color:#ffffff;border-color:#10252b}
.preview{border:1px solid #d7dee7;border-radius:8px;overflow:hidden;background:#fff}
.hero{min-height:310px;background:#10252b;color:white;display:flex;align-items:flex-end;padding:24px;background-size:cover;background-position:center}
.hero h2{font-size:2.1rem;margin:0 0 4px}
.price{display:inline-block;background:#d94f30;color:white;border-radius:4px;padding:6px 10px;font-weight:800}
.grid2{display:grid;grid-template-columns:1fr 1fr;gap:14px;padding:18px}
.small{color:#66717e;font-size:.9rem}
.toolbar button{margin-right:6px;padding:4px 8px;border-radius:4px;border:1px solid #ccc;background:#f0f0f0;cursor:pointer}
</style>
""", unsafe_allow_html=True)

st.markdown(
    f'<div class="title">{APP_NAME}</div>'
    '<div class="sub">Real estate listing, brochure, social creative, appointment, and revenue workflow.</div>',
    unsafe_allow_html=True
)

# ---------------------------------------------------------
# SESSION STATE
# ---------------------------------------------------------

if "listing" not in st.session_state:
    st.session_state.listing = {}
if "appointments" not in st.session_state:
    st.session_state.appointments = []
if "template_notes" not in st.session_state:
    st.session_state.template_notes = []
if "images" not in st.session_state:
    st.session_state.images = []
if "section" not in st.session_state:
    st.session_state.section = "Listing"

# ---------------------------------------------------------
# CONSTANTS
# ---------------------------------------------------------

SOCIAL_SIZES = {
    "TikTok Portrait 1080x1920": (1080, 1920),
    "Instagram Portrait 1080x1350": (1080, 1350),
    "Instagram Square 1080x1080": (1080, 1080),
    "Facebook Landscape 1200x630": (1200, 630),
    "LinkedIn Landscape 1200x627": (1200, 627),
    "Story/Reel Portrait 1080x1920": (1080, 1920),
}

# ---------------------------------------------------------
# BASIC HTML TOOLBAR (CLOUD SAFE)
# ---------------------------------------------------------

def basic_toolbar(label, key):
    st.markdown(f"### {label}")

    col1, col2, col3 = st.columns(3)
    with col1:
        if st.button("Bold", key=f"bold_{key}"):
            st.session_state[key] = st.session_state.get(key, "") + "<b></b>"
    with col2:
        if st.button("Italic", key=f"italic_{key}"):
            st.session_state[key] = st.session_state.get(key, "") + "<i></i>"
    with col3:
        if st.button("Underline", key=f"underline_{key}"):
            st.session_state[key] = st.session_state.get(key, "") + "<u></u>"

    return st.text_area("", value=st.session_state.get(key, ""), key=key, height=150)

# ---------------------------------------------------------
# HELPERS
# ---------------------------------------------------------

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

def html_to_plain(html):
    soup = BeautifulSoup(html, "html.parser")
    return " ".join(soup.get_text(" ").split())

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

def circular_image(img, diameter):
    img = img.resize((diameter, diameter))
    mask = Image.new("L", (diameter, diameter), 0)
    draw = ImageDraw.Draw(mask)
    draw.ellipse((0, 0, diameter, diameter), fill=255)
    output = Image.new("RGBA", (diameter, diameter))
    output.paste(img, (0, 0), mask)
    return output

# ---------------------------------------------------------
# SOCIAL IMAGE GENERATOR
# ---------------------------------------------------------

def social_image(size, listing, images, platform, headline_html, font_size, selected_photo):
    headline = html_to_plain(headline_html)
    w, h = size
    base = Image.new("RGB", size, "#10252b")

    if images:
        chosen = next((img for name, img in images if name == selected_photo), images[0][1])
        base = fit_image(chosen, size)
        overlay = Image.new("RGBA", size, (0, 0, 0, 95))
        base = Image.alpha_composite(base.convert("RGBA"), overlay).convert("RGB")

    draw = ImageDraw.Draw(base)
    margin = max(42, int(w * 0.055))

    price = listing.get("price", "$749,000")
    location = listing.get("location", "Austin, TX")
    agent = listing.get("agent", "Agent contact")
    deadline = listing.get("deadline", str(date.today() + timedelta(days=21)))

    # Price badge
    badge_h = max(58, int(h * 0.045))
    draw.rounded_rectangle((margin, margin, margin + int(w * 0.34), margin + badge_h),
                           radius=10, fill="#d94f30")
    draw.text((margin + 22, margin + 14), price, fill="white",
              font=font(max(26, int(w * 0.034)), True))

    # Headline
    headline_font = font(font_size, True)
    y = int(h * 0.55) if h > w else int(h * 0.34)

    for line in wrap_text(draw, headline, headline_font, w - margin * 2)[:3]:
        draw.text((margin, y), line, fill="white", font=headline_font)
        y += int(headline_font.size * 1.12)

    # Subline
    sub = f"{location} | Contact by {deadline}"
    draw.text((margin, y + 12), sub, fill="#f3f7f8",
              font=font(max(24, int(w * 0.028)), False))

    # Footer bar
    draw.rectangle((0, h - int(h * .12), w, h), fill="#10252b")
    draw.text((margin, h - int(h * .08)),
              f"{agent}  |  Schedule a showing",
              fill="white", font=font(max(24, int(w * 0.027)), True))

    return base

# ---------------------------------------------------------
# BROCHURE PDF GENERATOR
# ---------------------------------------------------------

def make_brochure_pdf(listing, images, edits_html, hero_name, bottom_names, agent_photo_name,
                      accent_hex="#d94f30", footer_hex="#10252b"):

    edits = {
        "headline": html_to_plain(edits_html["headline"]),
        "promo": html_to_plain(edits_html["promo"]),
        "highlights": html_to_plain(edits_html["highlights"]),
        "footer": html_to_plain(edits_html["footer"]),
    }

    mem = io.BytesIO()
    c = canvas.Canvas(mem, pagesize=letter)
    w, h = letter
    margin = 42
    hero_h = 270

    accent_color = colors.HexColor(accent_hex)
    footer_color = colors.HexColor(footer_hex)

    # Hero image
    if images and hero_name:
        hero_img = next((img for name, img in images if name == hero_name), images[0][1])
        hero = fit_image(hero_img, (1100, 520))
        b = io.BytesIO()
        hero.save(b, format="JPEG", quality=90)
        b.seek(0)
        c.drawImage(ImageReader(b), 0, h - hero_h, width=w, height=hero_h,
                    preserveAspectRatio=False, mask="auto")
        c.setFillColor(colors.Color(0, 0, 0, alpha=.35))
        c.rect(0, h - hero_h, w, hero_h, stroke=0, fill=1)

    # Headline
    c.setFillColor(colors.white)
    c.setFont("Helvetica-Bold", 23)
    c.drawString(margin, h - 82, edits["headline"][:58])

    c.setFont("Helvetica", 12)
    c.drawString(margin, h - 105, listing.get("location", ""))

    # Price badge
    c.setFillColor(accent_color)
    c.roundRect(w - margin - 150, h - 92, 150, 36, 5, stroke=0, fill=1)
    c.setFillColor(colors.white)
    c.setFont("Helvetica-Bold", 15)
    c.drawCentredString(w - margin - 75, h - 78, listing.get("price", ""))

    # Highlights
    y = h - hero_h - 34
    c.setFillColor(colors.HexColor("#17202a"))
    c.setFont("Helvetica-Bold", 16)
    c.drawString(margin, y, "Property Highlights")
    y -= 22

    c.setFont("Helvetica", 10)
    c.setFillColor(colors.HexColor("#33404d"))
    for line in wrap_text(c, edits["highlights"], font(10), 90):
        c.drawString(margin, y, line)
        y -= 14

    # Promo
    y -= 8
    c.setFont("Helvetica-Bold", 14)
    c.setFillColor(colors.HexColor("#17202a"))
    c.drawString(margin, y, "Why buyers click")
    y -= 20

    c.setFont("Helvetica", 10)
    c.setFillColor(colors.HexColor("#33404d"))
    for line in wrap_text(c, edits["promo"], font(10), 90):
        c.drawString(margin, y, line)
        y -= 14

    # Bottom gallery
    bottom_imgs = [img for name, img in images if name in bottom_names][:3]
    if bottom_imgs:
        x = margin
        y_img = 110
        for img in bottom_imgs:
            thumb = fit_image(img, (170, 105))
            b = io.BytesIO()
            thumb.save(b, format="JPEG", quality=88)
            b.seek(0)
            c.drawImage(ImageReader(b), x, y_img, width=155, height=95,
                        preserveAspectRatio=False, mask="auto")
            x += 165

    # Footer bar
    footer_h = 70
    c.setFillColor(footer_color)
    c.rect(0, 0, w, footer_h, stroke=0, fill=1)

    # Agent photo
    agent_img = None
    if agent_photo_name:
        try:
            agent_img = next(img for name, img in images if name == agent_photo_name)
        except StopIteration:
            agent_img = None

    if agent_img:
        circ = circular_image(agent_img, 60)
        b = io.BytesIO()
        circ.save(b, format="PNG")
        b.seek(0)
        c.drawImage(ImageReader(b), margin, 5, width=60, height=60, mask="auto")
        text_x = margin + 75
    else:
        text_x = margin

    # Footer text
    c.setFillColor(colors.white)
    c.setFont("Helvetica-Bold", 12)
    c.drawString(text_x, 40, edits["footer"][:95])

    c.setFont("Helvetica", 10)
    c.drawString(text_x, 22, f"Contact by {listing.get('deadline','')}")

    c.showPage()
    c.save()
    mem.seek(0)
    return mem.getvalue()

# ---------------------------------------------------------
# TEMPLATE SCRAPER
# ---------------------------------------------------------

def scrape_templates(query, urls):
    notes = []
    headers = {"User-Agent": "EstateLaunchTemplateResearch/1.0"}

    targets = [u.strip() for u in urls.splitlines() if u.strip()]
    if query.strip():
        google_url = "https://www.google.com/search?tbm=isch&q=" + quote_plus(query)
        targets.insert(0, google_url)

    for url in targets[:8]:
        try:
            html = requests.get(url, headers=headers, timeout=10).text
            soup = BeautifulSoup(html, "html.parser")
            title = soup.title.get_text(" ", strip=True) if soup.title else url
            text = " ".join(soup.get_text(" ").split())[:1500]

            keywords = [
                "luxury", "minimal", "modern", "bold", "photo", "editorial",
                "clean", "real estate", "brochure", "template", "agent",
                "open house", "premium", "elegant", "gradient", "geometric"
            ]
            cues = [k for k in keywords if k in text.lower()]

            notes.append({
                "source": url,
                "title": title[:140],
                "style_cues": ", ".join(cues) or "general clean layout",
                "excerpt": text[:260]
            })

        except Exception as e:
            notes.append({
                "source": url,
                "title": "Could not scrape",
                "style_cues": "manual review needed",
                "excerpt": str(e)[:180]
            })

    return notes

# ---------------------------------------------------------
# SAVE LISTING
# ---------------------------------------------------------

def save_listing(headline, price, location, deadline, agent, details_html, canva_url):
    details_plain = html_to_plain(details_html)
    st.session_state.listing = {
        "headline": headline,
        "price": price,
        "location": location,
        "deadline": str(deadline),
        "agent": agent,
        "details": details_plain,
        "promo": f"Discover {headline} in {location}. {details_plain} Contact {agent} by {deadline}.",
        "canva_url": canva_url,
    }

# ---------------------------------------------------------
# TOP NAVIGATION
# ---------------------------------------------------------

sections = ["Listing", "Brochure PDF", "Social Media Assets", "Captions", "Template Research", "Appointments & Revenue"]
icons = ["🏠", "📄", "📱", "✍️", "🎨", "📊"]

st.markdown("<div class='navbar'>", unsafe_allow_html=True)
nav_cols = st.columns(len(sections))

for i, (sec, icon) in enumerate(zip(sections, icons)):
    with nav_cols[i]:
        active = st.session_state.section == sec
        if st.button(f"{icon} {sec}", key=f"nav_{sec}"):
            st.session_state.section = sec
        cls = "navbtn-active" if active else "navbtn"
        st.markdown(f"<div class='{cls}'></div>", unsafe_allow_html=True)

st.markdown("</div>", unsafe_allow_html=True)

# ---------------------------------------------------------
# SECTION: LISTING
# ---------------------------------------------------------

listing = st.session_state.listing or {
    "headline": "Modern Family Home With Designer Finishes",
    "price": "$749,000",
    "location": "Austin, TX",
    "deadline": str(date.today() + timedelta(days=21)),
    "agent": "Angela Lee
