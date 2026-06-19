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
    '<div class="sub">Real estate management, creative and finances dashboard.</div>',
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
            "agent": "Angela Tan: 9123 4567",
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

def make_social_jpeg_zip(listing, images, selected_photo, accent_color, footer_color):
    mem = io.BytesIO()
    with zipfile.ZipFile(mem, "w", zipfile.ZIP_DEFLATED) as zf:
        for label, dimensions in SOCIAL_SIZES.items():
            img = social_image(
                dimensions, listing, images, label, 
                listing.get("headline", "Property Feature"), 56, selected_photo,
                accent_hex=accent_color, footer_hex=footer_color
            )
            b = io.BytesIO()
            img.convert("RGB").save(b, format="JPEG", quality=90)
            file_clean_name = re.sub(r"[^a-zA-Z0-9]+", "_", label).strip("_") + ".jpg"
            zf.writestr(file_clean_name, b.getvalue())
    mem.seek(0)
    return mem.getvalue()

def caption_for(platform, listing):
    location = listing.get("location", "Singapore")
    price = listing.get("price", "POA")
    deadline = listing.get("deadline", "soon")
    details = listing.get("details", "Premium residential project.")
    if "TikTok" in platform or "Story" in platform:
        return f"POV: Walking through your future luxury layout in {location}. Listed at {price}. Contact before {deadline}. #sgrealestate #propertytour"
    if "LinkedIn" in platform:
        return f"New Residential Opportunity in {location}: {details} Positioned at {price}. Connect directly for a structural prospectus review ahead of the closing date: {deadline}."
    return f"Just listed in {location}: {details} Guide Price: {price}. PM to schedule a private viewing."

def wrap_pdf(c, text, font_name, font_size, max_width):
    words = str(text).split()
    lines = []
    line = ""
    for word in words:
        trial = (line + " " + word).strip()
        if c.stringWidth(trial, font_name, font_size) <= max_width:
            line = trial
        else:
            if line:
                lines.append(line)
            line = word
    if line:
        lines.append(line)
    return lines

def make_brochure_pdf(listing, images, edits, hero_name, bottom_names, accent_hex="#d94f30", footer_hex="#10252b"):
    mem = io.BytesIO()
    c = canvas.Canvas(mem, pagesize=letter)
    w, h = letter
    safe = 0
    usable_w = w - (safe * 2)
    hero_h = 300
    line_gap = 18

    accent_color = colors.HexColor(accent_hex)
    footer_color = colors.HexColor(footer_hex)
    hero_y = h - safe - hero_h

    if images and hero_name:
        hero_img = next((img for name, img in images if name == hero_name), images[0][1])
        hero = fit_image(hero_img, (int(usable_w * 2), int(hero_h * 2)))
        b = io.BytesIO()
        hero.save(b, format="JPEG", quality=90)
        b.seek(0)
        c.drawImage(ImageReader(b), safe, hero_y, width=usable_w, height=hero_h, preserveAspectRatio=False, mask="auto")
        c.setFillColor(colors.Color(0, 0, 0, alpha=.35))
        c.rect(safe, hero_y, usable_w, hero_h, stroke=0, fill=1)
    else:
        c.setFillColor(footer_color)
        c.rect(safe, hero_y, usable_w, hero_h, stroke=0, fill=1)

    col_pad = 40
    title_size = edits.get("title_size", 26)
    body_size = edits.get("body_size", 12)
    
    price_text = listing.get("price", "")
    price_font_size = body_size + 2
    c.setFont("Helvetica-Bold", price_font_size)
    price_width = c.stringWidth(price_text, "Helvetica-Bold", price_font_size)
    
    pad = 2  
    box_w = price_width + (pad * 2)
    box_h = price_font_size + (pad * 2) + 2 
    
    price_box_y = hero_y + 20
    loc_y = price_box_y + box_h + 10
    title_y = loc_y + body_size + 14

    c.setFillColor(colors.white)
    c.setFont("Helvetica-Bold", title_size)
    c.drawString(safe + col_pad, title_y, edits["headline"][:70])

    c.setFont("Helvetica", body_size)
    c.drawString(safe + col_pad, loc_y, listing.get("location", ""))

    c.setFillColor(accent_color)
    c.roundRect(safe + col_pad, price_box_y, box_w, box_h, 4, stroke=0, fill=1)
    
    c.setFillColor(colors.white)
    c.setFont("Helvetica-Bold", price_font_size)
    c.drawString(safe + col_pad + pad, price_box_y + pad + 1, price_text)

    col_w = (usable_w / 2) - col_pad - 10
    left_x = safe + col_pad
    right_x = safe + (usable_w / 2) + 10
    y_left = hero_y - 50
    y_right = hero_y - 50

    c.setFillColor(colors.HexColor("#17202a"))
    c.setFont("Helvetica-Bold", body_size + 5)
    c.drawString(left_x, y_left, "About The Property")
    y_left -= 28

    c.setFont("Helvetica", body_size)
    c.setFillColor(colors.HexColor("#33404d"))
    about_paras = [p.strip() for p in edits["about"].split("\n") if p.strip()][:2]

    for para in about_paras:
        wrapped = wrap_pdf(c, para, "Helvetica", body_size, col_w)
        for line in wrapped:
            c.drawString(left_x, y_left, line)
            y_left -= line_gap
        y_left -= line_gap // 2

    c.setFillColor(colors.HexColor("#17202a"))
    c.setFont("Helvetica-Bold", body_size + 5)
    c.drawString(right_x, y_right, "Why We Recommend")
    y_right -= 28

    c.setFont("Helvetica", body_size)
    c.setFillColor(colors.HexColor("#33404d"))
    highlight_lines = [l.strip() for l in edits["highlights"].split("\n") if l.strip()][:5]
    
    bullet_symbol = "• "
    bullet_w = c.stringWidth(bullet_symbol, "Helvetica", body_size)

    for item in highlight_lines:
        wrapped = wrap_pdf(c, item, "Helvetica", body_size, col_w - bullet_w)
        for i, line in enumerate(wrapped):
            if i == 0:
                c.drawString(right_x, y_right, bullet_symbol)
                c.drawString(right_x + bullet_w, y_right, line)
            else:
                c.drawString(right_x + bullet_w, y_right, line)
            y_right -= line_gap
        y_right -= line_gap // 2

    bottom_imgs = [img for name, img in images if name in bottom_names][:3]
    if bottom_imgs:
        img_w = (usable_w - (col_pad * 2) - 20) / 3
        img_h = img_w * 0.65
        x = safe + col_pad
        y_img = safe + 70 + 20
        for img in bottom_imgs:
            thumb = fit_image(img, (int(img_w*2), int(img_h*2)))
            b = io.BytesIO()
            thumb.save(b, format="JPEG", quality=88)
            b.seek(0)
            c.drawImage(ImageReader(b), x, y_img, width=img_w, height=img_h, preserveAspectRatio=False, mask="auto")
            x += img_w + 10

    footer_h = 70
    c.setFillColor(footer_color)
    c.rect(safe, safe, usable_w, footer_h, stroke=0, fill=1)

    c.setFillColor(colors.white)
    c.setFont("Helvetica-Bold", edits.get("footer_size", 12))
    c.drawString(safe + col_pad, safe + 30, edits["footer"][:95])
    c.drawRightString(safe + usable_w - col_pad, safe + 30, f"Contact by {listing.get('deadline','')}")

    c.showPage()
    c.save()
    mem.seek(0)
    return mem.getvalue()

# --- Singapore Stamp Duty (ABSD Framework) Calculation ---
def calculate_singapore_absd(property_value, profile, property_count):
    rates = {
        "Singapore Citizen": [0.0, 0.20, 0.30],
        "Singapore Permanent Resident": [0.05, 0.30, 0.35],
        "Foreigner": [0.60, 0.60, 0.60]
    }
    idx = 0 if property_count == "1st Property" else (1 if property_count == "2nd Property" else 2)
    rate = rates.get(profile, [0.60, 0.60, 0.60])[idx]
    return property_value * rate, rate

# --- Tab Layout Grid System ---
tabs = st.tabs([
    "Property Info",
    "Creative Design",
    "Social Media Plan",
    "Set Appointment",
    "Commission Dashboard"
])

# Find active record payload context matching tracking focus selection
active_id = st.session_state.selected_property_id
listing = next((p for p in st.session_state.properties if p['id'] == active_id), None)
if not listing and st.session_state.properties:
    listing = st.session_state.properties[0]
    st.session_state.selected_property_id = listing['id']
elif not listing:
    listing = {
        "id": 0,
        "headline": "",
        "price": "$0",
        "location": "",
        "deadline": str(date.today()),
        "agent": "",
        "details": "",
        "canva_url": "",
        "status": "Available",
        "commission_rate": 2.5
    }

images = st.session_state.get("images", [])
accent_color = "#d94f30"
footer_color = "#10252b"

# --- TAB 1: LISTING ENTRY ---
with tabs[0]:
    col1, col2 = st.columns([.45, .55])
    with col1:
        uploads = st.file_uploader("Upload images", type=["png", "jpg", "jpeg"], accept_multiple_files=True)
        new_images = load_images(uploads)
        if new_images:
            st.session_state.images = [(name, img.copy()) for name, img in new_images]
            st.image(
                [img for _, img in st.session_state.images[:4]],
                caption=[name for name, _ in st.session_state.images[:4]],
                width=180
            )
    with col2:
        in_headline = st.text_input("Property Name", listing.get("headline", ""))
        in_price = st.text_input("Price", listing.get("price", ""))
        in_location = st.text_input("Location / Sector", listing.get("location", ""))
        in_deadline = st.date_input("Offer Closing Date", date.today() + timedelta(days=21))
        in_agent = st.text_input("Agent", listing.get("agent", ""))
        in_details = st.text_area("Description", listing.get("details", ""), height=120)
        in_comm = st.slider(
            "Agent Fee Share Commission %",
            1.0,
            3.0,
            float(listing.get("commission_rate", 2.0)),
            step=0.1
        )
        in_status = st.selectbox(
            "Status",
            ["Available", "In Progress", "Sold"]
            )
        )
        
        if st.button("Submit"):
            if listing['id'] != 0:
                for idx, p in enumerate(st.session_state.properties):
                    if p['id'] == active_id:
                        st.session_state.properties[idx] = {
                            "id": active_id,
                            "headline": in_headline,
                            "price": in_price,
                            "location": in_location,
                            "deadline": str(in_deadline),
                            "agent": in_agent,
                            "details": in_details,
                            "canva_url": listing.get("canva_url", ""),
                            "status": in_status,
                            "commission_rate": in_comm
                        }
                st.success("Updated existing tracking profile target entries.")
            else:
                new_id = max([p['id'] for p in st.session_state.properties]) + 1 if st.session_state.properties else 1
                st.session_state.properties.append({
                    "id": new_id,
                    "headline": in_headline,
                    "price": in_price,
                    "location": in_location,
                    "deadline": str(in_deadline),
                    "agent": in_agent,
                    "details": in_details,
                    "canva_url": "",
                    "status": in_status,
                    "commission_rate": in_comm
                })
                st.session_state.selected_property_id = new_id
                st.success("Appended new structural property tracker profile row node.")
            st.rerun()

# --- TAB 2: BROCHURE PDF ---
with tabs[1]:
    st.subheader(f"Design: {listing.get('headline','')}")
    c1, c2 = st.columns([.48, .52])
    with c1:
        edit_headline = listing.get("headline", "")
        about_text = st.text_area("Body Copy", listing.get("details", ""), height=140)
        default_highlights = (
            "Premium mass transit access grid linkages\n"
            "Elite scholastic infrastructure zones\n"
            "High capital performance history"
        )
        highlights_text = st.text_area(
            "Why We Recommend (One line per item)",
            default_highlights,
            height=100
        )
        edit_footer = st.text_input("Footer Text", listing.get("agent", ""))

        title_size = st.slider("Title Size", 18, 60, 26, step=2)
        body_size = st.slider("Body Text Size", 10, 24, 12, step=2)
        accent_color = st.color_picker("Price Color", "#d94f30")
        footer_color = st.color_picker("Footer Color", "#10252b")

        hero_choice = None
        bottom_choices = []
        if images:
            hero_choice = st.selectbox(
                "Header Image",
                options=[name for name, _ in images],
                index=0
            )
            bottom_choices = st.multiselect(
                "Assign Footer Thumbnails (Max 3)",
                options=[name for name, _ in images],
                default=[name for name, _ in images[1:4]] if len(images) > 1 else []
            )

        pdf_data = make_brochure_pdf(
            listing,
            images,
            {
                "headline": edit_headline,
                "about": about_text,
                "highlights": highlights_text,
                "footer": edit_footer,
                "title_size": title_size,
                "body_size": body_size
            },
            hero_choice,
            bottom_choices,
            accent_hex=accent_color,
            footer_hex=footer_color
        )
        
        st.markdown("### Generate Creative")
        st.download_button(
            "Download Flyer PDF",
            pdf_data,
            file_name="estate_brochure.pdf",
            mime="application/pdf",
            use_container_width=True
        )

        # NOTE: Social media ZIP button removed as requested

    with c2:
        about_html = "<br>".join(about_text.split("\n"))
        highlights_html = "<br>".join(
            "• " + l
            for l in [l.strip() for l in highlights_text.split("\n") if l.strip()][:5]
        )
        st.markdown(f"""
        <div class='preview'>
          <div class='hero' style='background-color:{footer_color}'>
            <div>
              <h2>{listing.get('headline','')}</h2>
              <div>{listing.get('location','')}</div>
              <div class='price'>{listing.get('price','')}</div>
            </div>
          </div>
          <div class='grid2'>
            <div><b>About The Property</b><br><span class='small'>{about_html}</span></div>
            <div><b>Why We Recommend</b><br><span class='small'>{highlights_html}</span></div>
          </div>
          <div style='padding:14px 18px;background:{footer_color};color:white'>
            {edit_footer} | Closing Date: {listing.get('deadline','')}
          </div>
        </div>
        """, unsafe_allow_html=True)

# --- TAB 3: SOCIAL MEDIA ---
with tabs[2]:
    st.subheader("Social Media Plan")
    st.markdown("### Proposed Captions")
    rows = [
        {
            "platform_size": label,
            "caption": caption_for(label, listing),
            "hook_type": "Curiosity Capture Framework",
            "cta": "Schedule private showing profile"
        }
        for label in SOCIAL_SIZES
    ]
    df = pd.DataFrame(rows)
    edited_df = st.data_editor(df, use_container_width=True, hide_index=True)
    
    st.markdown("---")
    st.markdown("### Schedule")
    calendar_plan = [
        {
            "Day": "Day 1",
            "Platform": "TikTok / Vertical Shorts Reel",
            "Organic Strategy Scheme": "POV Financial Discovery Hook",
            "Algorithmic Virality Engine Instruction Rules": "Anchor on immediate price comparison text anchors. Target local pricing sentiment indices to generate immediate community comment engagement loops."
        },
        {
            "Day": "Day 3",
            "Platform": "Instagram Multi-Image Slide",
            "Organic Strategy Scheme": "Architectural Asset Breakdown Gallery",
            "Algorithmic Virality Engine Instruction Rules": "Isolate high-impact highlight bullets. Force carousel retention tracking metrics by framing secondary images as hidden layout advantages."
        },
        {
            "Day": "Day 5",
            "Platform": "LinkedIn Professional Brief",
            "Organic Strategy Scheme": "District Infrastructure Yield Analysis",
            "Algorithmic Virality Engine Instruction Rules": "Focus on geographical expansion, commercial integration, and investment durability factors. Explicitly define clear steps leading up to the final closing date."
        }
    ]
    st.table(pd.DataFrame(calendar_plan))

# --- TAB 4: APPOINTMENT ---
with tabs[3]:
    st.subheader(f"Leads CRM: {listing.get('headline','')}")
    with st.form("appointment_form"):
        client = st.text_input("Prospect Name", "Michael Tan")
        appt_date = st.date_input("Scheduled Showing Date", date.today() + timedelta(days=2))
        status = st.selectbox(
            "Status",
            ["Scheduled", "Shown", "Offer Table", "Under Contract", "Closed / Settled", "Lost / Cancelled"]
        )
        notes = st.text_area("Remarks", "Reviewing ABSD liability brackets for multiple properties.")
        
        if st.form_submit_button("Submit"):
            derived_revenue = parse_price_to_float(listing.get("price", "0"))
            st.session_state.appointments.append({
                "property_id": listing['id'],
                "property_name": listing['headline'],
                "client": client,
                "date": str(appt_date),
                "status": status,
                "price_offer": derived_revenue,
                "remarks": notes
            })
            st.success("Scheduled")
            
    appts = pd.DataFrame(st.session_state.appointments)
    if not appts.empty:
        st.markdown("### Master Lead Interactivity Ledger")
        st.dataframe(appts, use_container_width=True)

# --- TAB 5: ABSD & REVENUE REPORTING (SINGAPORE COMPLIANCE) ---
with tabs[4]:
    st.subheader("Commission Dashboard")
    
    val_base = parse_price_to_float(listing.get("price", "0"))
    st.metric(
        label="Asset Basis Valuation",
        value=f"SGD ${val_base:,.2f}"
    )
    
    st.markdown("---")
    st.markdown("### 1. ABSD Exposure Estimator Matrix")
    
    rc1, rc2 = st.columns(2)
    with rc1:
        buyer_profile = st.selectbox(
            "Buyer Demographic Profile Tier",
            ["Singapore Citizen", "Singapore Permanent Resident", "Foreigner"]
        )
        property_holding = st.selectbox(
            "Buyer Household Holding Status",
            ["1st Property", "2nd Property", "3rd Property+"]
        )
    with rc2:
        absd_fee, active_rate = calculate_singapore_absd(val_base, buyer_profile, property_holding)
        st.metric(
            label="Estimated ABSD Percentage Rate Apply",
            value=f"{active_rate * 100:.1f}%"
        )
        st.metric(
            label="Calculated ABSD Liability Charge Due",
            value=f"SGD ${absd_fee:,.2f}"
        )
        
    st.markdown("---")
    st.markdown("### 2. End-of-Day Agent Payout & Revenue Tracking Summary")
    st.markdown(
        "Track realized financial metrics based on entries marked as **Sold** "
        "within your active tracking matrix ledger database."
    )
    
    total_pipeline_volume = 0.0
    total_realized_fees = 0.0
    closed_properties_list = []
    
    for p in st.session_state.properties:
        if p.get("status") == "Sold":
            p_val = parse_price_to_float(p.get("price", "0"))
            rate = float(p.get("commission_rate", 2.5)) / 100.0
            earned = p_val * rate
            total_pipeline_volume += p_val
            total_realized_fees += earned
            closed_properties_list.append({
                "Property ID": p['id'],
                "Headline": p['headline'],
                "Closing Value": p_val,
                "Fee Share %": f"{p['commission_rate']}%",
                "Your Net Payout Revenue": earned
            })
            
    kc1, kc2 = st.columns(2)
    with kc1:
        st.metric(
            label="Total Closed Transaction Portfolio Volume",
            value=f"SGD ${total_pipeline_volume:,.2f}"
        )
    with kc2:
        st.metric(
            label="Net Agent Payout Commission Capital (End-of-Day Received)",
            value=f"SGD ${total_realized_fees:,.2f}",
            delta="Realized Revenue Flow"
        )
        
    if closed_properties_list:
        st.markdown("#### Itemized Closed Deal Registry Rows")
        st.dataframe(pd.DataFrame(closed_properties_list), use_container_width=True, hide_index=True)
    else:
        st.info(
            "No transaction properties are marked as 'Sold' within your master track registry folder yet. "
            "Move an asset status element to 'Sold' under the 'Property Ledger' or 'Listing Entry' workspace "
            "to compute real-time commission payout structures."
        )
