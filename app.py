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
    '<div class="sub">Real estate listing, brochure, social creative, appointment, and revenue workflow.</div>',
    unsafe_allow_html=True
)

if "listing" not in st.session_state:
    st.session_state.listing = {}
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
    location = listing.get("location", "Austin, TX")
    agent = listing.get("agent", "Angela Lee | 555-0100")
    deadline = listing.get("deadline", str(date.today() + timedelta(days=21)))
    
    # Context-aware font adjustment based on aspect ratio rules
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
    
    # 2px Padding Box Badge Structure
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
    
    # Render Footer Track
    draw.rectangle((0, h - footer_height, w, h), fill=footer_hex)
    footer_text_font = font(max(18, int(w * 0.026)), True)
    footer_y = h - int(footer_height / 2) - 10
    
    draw.text((margin, footer_y), f"{agent}", fill="white", font=footer_text_font)
    draw.text((w - margin - 160, footer_y), platform.split()[0], fill="#9edfd4", font=footer_text_font)
    
    return base


def make_social_zip(listing, images, selected_sizes, social_headline, social_font_size, social_photo, accent_color, footer_color):
    mem = io.BytesIO()
    with zipfile.ZipFile(mem, "w", zipfile.ZIP_DEFLATED) as zf:
        captions = []
        for label in selected_sizes:
            img = social_image(
                SOCIAL_SIZES[label], listing, images, label, 
                social_headline, social_font_size, social_photo,
                accent_hex=accent_color, footer_hex=footer_color
            )
            b = io.BytesIO()
            img.save(b, format="PNG")
            zf.writestr(re.sub(r"[^a-zA-Z0-9]+", "_", label).strip("_") + ".png", b.getvalue())
            captions.append({"asset": label, "caption": caption_for(label, listing), "cta": "Book a private showing"})
        zf.writestr("captions.csv", pd.DataFrame(captions).to_csv(index=False))
        zf.writestr("canva_prompt.txt", canva_prompt(listing))
    mem.seek(0)
    return mem.getvalue()


def canva_prompt(listing):
    return (
        "Create a premium real estate marketing artwork using the uploaded property photos. "
        "Use a clean luxury editorial layout with a large hero image, price badge in the upper right, "
        "location under the headline, and agent contact footer. "
        f"Headline: {listing.get('headline','Modern Home Just Listed')}. "
        f"Price: {listing.get('price','$749,000')}. Location: {listing.get('location','Austin, TX')}. "
        f"Contact deadline: {listing.get('deadline','soon')}. Agent: {listing.get('agent','Agent contact')}."
    )


def caption_for(platform, listing):
    location = listing.get("location", "this neighborhood")
    price = listing.get("price", "a compelling price")
    deadline = listing.get("deadline", "soon")
    details = listing.get("details", "a move-in-ready home with standout features")
    if "TikTok" in platform or "Story" in platform:
        return f"POV: you found the listing everyone will ask about in {location}. {price}. Contact by {deadline} for a private showing. #realestate #hometour"
    if "LinkedIn" in platform:
        return f"New listing in {location}: {details} Offered at {price}. Buyer agents and relocation clients can contact us by {deadline} for showing support."
    if "Facebook" in platform:
        return f"Just listed in {location}. {details} Offered at {price}. Message us before {deadline} to schedule a tour."
    return f"Just listed: {location} at {price}. {details} Save this one and book a showing before {deadline}."


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


def make_brochure_pdf(listing, images, edits, hero_name, bottom_names,
                      accent_hex="#d94f30", footer_hex="#10252b"):

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
        c.drawImage(ImageReader(b), safe, hero_y, width=usable_w, height=hero_h,
                    preserveAspectRatio=False, mask="auto")
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
    c.drawString(left_x, y_left, "About This Property")
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
            c.drawImage(ImageReader(b), x, y_img, width=img_w, height=img_h,
                        preserveAspectRatio=False, mask="auto")
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


def scrape_templates(query, urls):
    results = []
    # Basic structural mock fallback for pipeline preservation 
    for url in [u.strip() for u in urls.split("\n") if u.strip()][:3]:
        results.append({"source": url, "style_cues": "Clean margins, white backgrounds, heavy font weights for key metrics"})
    if not results and query:
        results.append({"source": f"Search: {query}", "style_cues": "Asymmetrical photo blocks, distinct callouts, dark footers"})
    return results


def save_listing(headline, price, location, deadline, agent, details, canva_url):
    st.session_state.listing = {
        "headline": headline,
        "price": price,
        "location": location,
        "deadline": str(deadline),
        "agent": agent,
        "details": details,
        "canva_url": canva_url,
    }


# Unified Layout Tab Management
tabs = st.tabs(["Listing", "Brochure PDF", "Social Media", "Template Research", "Appointments & Revenue"])

with tabs[0]:
    col1, col2 = st.columns([.45, .55])
    with col1:
        uploads = st.file_uploader("Upload multiple property photos", type=["png", "jpg", "jpeg"], accept_multiple_files=True)
        images = load_images(uploads)
        if images:
            st.session_state.images = [(name, img.copy()) for name, img in images]
            st.image([img for _, img in images[:4]], caption=[name for name, _ in images[:4]], width=180)
    with col2:
        headline = st.text_input("Listing headline", st.session_state.listing.get("headline", "Modern Family Home With Designer Finishes"))
        price = st.text_input("Price", st.session_state.listing.get("price", "$749,000"))
        location = st.text_input("Location", st.session_state.listing.get("location", "Austin, TX"))
        deadline = st.date_input("Contact by deadline", date.today() + timedelta(days=21))
        agent = st.text_input("Agent contact", st.session_state.listing.get("agent", "Angela Lee | 555-0100"))
        details = st.text_area(
            "Property details (intro, up to 2 paragraphs)",
            st.session_state.listing.get("details", "4 bed, 3 bath, renovated kitchen, walkable neighborhood, solar panels, large backyard."),
            height=140,
        )
        canva_url = st.text_input("Optional Canva artwork link", st.session_state.listing.get("canva_url", ""))

        if st.button("Save listing package"):
            save_listing(headline, price, location, deadline, agent, details, canva_url)
            st.success("Listing package saved.")

listing = st.session_state.listing or {
    "headline": "ParkTown Residences",
    "price": "$1,750,000",
    "location": "Austin, TX",
    "deadline": str(date.today() + timedelta(days=21)),
    "agent": "Angela Tan | 9555 0100",
    "details": "Thoughtfully designed as a nature-inspired extension of the neighborhood, with easy access to parks and amenities.",
    "canva_url": "",
}
images = st.session_state.get("images", [])

# Shared design variables
accent_color = "#d94f30"
footer_color = "#10252b"

with tabs[1]:
    st.subheader("Editable brochure layout")
    c1, c2 = st.columns([.48, .52])
    with c1:
        edit_headline = listing.get("headline", "")
        about_text = st.text_area("About This Property (intro, up to 2 paragraphs)", listing.get("details", ""), height=140)

        default_highlights = "\n".join([
            "Direct access to retail mall, MRT and bus interchange",
            "Near renowned schools and education clusters",
            "Green boulevard linking to nearby parks and eco corridors",
            "Close to key business hubs and job centers",
            "Family-friendly facilities and modern amenities",
        ])
        highlights_text = st.text_area("Why We Recommend (one highlight per line, up to 5)", default_highlights, height=140)
        edit_footer = st.text_input("Footer/contact line", listing.get("agent", ""))

        st.markdown("### Brochure font sizes (2px steps)")
        title_size = st.slider("Title font size", 18, 60, 26, step=2)
        body_size = st.slider("Body font size", 10, 24, 12, step=2)
        footer_size = st.slider("Footer font size", 10, 20, 12, step=2)

        st.markdown("### Brochure style options")
        accent_color = st.color_picker("Accent color (price badge)", "#d94f30")
        footer_color = st.color_picker("Footer bar color", "#10252b")

        hero_choice = None
        bottom_choices = []
        if images:
            hero_choice = st.selectbox("Select hero image", options=[name for name, _ in images], index=0)
            bottom_choices = st.multiselect(
                "Select bottom gallery images (up to 3)",
                options=[name for name, _ in images],
                default=[name for name, _ in images[1:4]] if len(images) > 1 else [],
            )

        pdf_data = make_brochure_pdf(
            listing, images,
            {
                "headline": edit_headline, "about": about_text, "highlights": highlights_text,
                "footer": edit_footer, "title_size": title_size, "body_size": body_size, "footer_size": footer_size,
            },
            hero_choice, bottom_choices, accent_hex=accent_color, footer_hex=footer_color,
        )
        st.download_button("Download brochure PDF", pdf_data, file_name="estate_brochure.pdf", mime="application/pdf")

    with c2:
        if images and hero_choice:
            hero_preview = next((img for name, img in images if name == hero_choice), images[0][1])
            st.image(hero_preview, caption="Hero image preview", use_container_width=True)
        elif images:
            st.image(images[0][1], caption="Hero image preview", use_container_width=True)

        about_html = "<br>".join(about_text.split("\n"))
        highlights_html = "<br>".join("• " + l for l in [l.strip() for l in highlights_text.split("\n") if l.strip()][:5])

        st.markdown(f"""
        <div class='preview'>
          <div class='hero'>
            <div>
              <h2>{listing.get('headline','')}</h2>
              <div>{listing.get('location','')}</div>
              <div class='price'>{listing.get('price','')}</div>
            </div>
          </div>
          <div class='grid2'>
            <div><b>About This Property</b><br><span class='small'>{about_html}</span></div>
            <div><b>Why We Recommend</b><br><span class='small'>{highlights_html}</span></div>
          </div>
          <div style='padding:14px 18px;background:{footer_color};color:white'>{edit_footer} | Contact by {listing.get('deadline','')}</div>
        </div>
        """, unsafe_allow_html=True)

with tabs[2]:
    st.subheader("Unified Social Media Campaign Studio")
    
    sc1, sc2 = st.columns([0.45, 0.55])
    with sc1:
        st.markdown("### 1. Amend Content Rules")
        social_headline_input = st.text_input("Social Headline Overwrite", listing.get("headline", ""))
        social_price_input = st.text_input("Social Price Overwrite", listing.get("price", ""))
        social_location_input = st.text_input("Social Location Overwrite", listing.get("location", ""))
        
        st.markdown("### 2. Layout Fine-Tuning")
        social_font_size = st.slider("Base Canvas Font Size", 24, 110, 56)
        
        social_photo = None
        if images:
            social_photo = st.selectbox("Social Image Focus Asset", [name for name, _ in images], index=0)
            
        custom_social_listing = {
            "headline": social_headline_input,
            "price": social_price_input,
            "location": social_location_input,
            "agent": listing.get("agent", ""),
            "deadline": listing.get("deadline", ""),
            "details": listing.get("details", "")
        }

        st.markdown("### 3. Package Export Distribution")
        selected_platforms = st.multiselect("Select Assets to Package", list(SOCIAL_SIZES), default=list(SOCIAL_SIZES))
        
        if selected_platforms:
            zip_data = make_social_zip(
                custom_social_listing, images, selected_platforms, social_headline_input, 
                social_font_size, social_photo, accent_color, footer_color
            )
            st.download_button(
                "Download Unified Social Campaign (.ZIP)",
                zip_data,
                file_name="estate_social_campaign.zip",
                mime="application/zip",
                use_container_width=True
            )
        else:
            st.info("Check-mark at least one distribution target platform option above.")

    with sc2:
        st.markdown("### 4. Interactive Cross-Platform Previews")
        preview_size = st.selectbox("Toggle Aspect Ratio Adaptation View", list(SOCIAL_SIZES), index=1)
        
        preview = social_image(
            SOCIAL_SIZES[preview_size],
            custom_social_listing,
            images,
            preview_size,
            social_headline_input,
            social_font_size,
            social_photo,
            accent_hex=accent_color,
            footer_hex=footer_color
        )
        st.image(preview, caption=f"Dynamic Adaptation Render Framework ({preview_size})", use_container_width=True)
        
        # Display platform-specific interactive caption block
        st.markdown("#### Generated Platform Caption Track")
        current_caption = caption_for(preview_size, custom_social_listing)
        st.text_area("Live Clipboard-Ready Caption", current_caption, height=90, key="live_caption_box")

    # Lower Full Campaign Copy Grid Segment
    st.markdown("---")
    st.markdown("### Master Copy & Asset Summary Registry")
    rows = [{"platform_size": label, "caption": caption_for(label, custom_social_listing), "hook_type": "curiosity + deadline", "cta": "Book a private showing"} for label in SOCIAL_SIZES]
    df = pd.DataFrame(rows)
    st.data_editor(df, use_container_width=True, hide_index=True)

with tabs[3]:
    st.subheader("Scrape and adapt template inspiration")
    query = st.text_input("Search query", "luxury real estate brochure template Instagram property listing")
    urls = st.text_area("Or paste template/sample URLs, one per line", "")
    if st.button("Search/scrape template cues"):
        st.session_state.template_notes = scrape_templates(query, urls)
    if st.session_state.template_notes:
        notes_df = pd.DataFrame(st.session_state.template_notes)
        st.dataframe(notes_df, use_container_width=True)
        cues = "; ".join(notes_df["style_cues"].dropna().astype(str).tolist())
        adapted = canva_prompt(listing) + " Adapt visual style cues from research: " + cues
        st.text_area("Adapted AI/Canva design prompt", adapted, height=150)

with tabs[4]:
    with st.form("appointment"):
        client = st.text_input("Buyer / client", "Jordan Smith")
        appt_date = st.date_input("Appointment date", date.today() + timedelta(days=2))
        status = st.selectbox("Status", ["Scheduled", "Shown", "Offer", "Under Contract", "Closed", "Lost"])
        revenue = st.number_input("Expected or closed revenue", min_value=0.0, value=12000.0, step=500.0)
        notes = st.text_area("Sales support notes", "Needs financing pre-approval and school district comparison.")
        if st.form_submit_button("Save appointment/status"):
            st.session_state.appointments.append({"client": client, "date": str(appt_date), "status": status, "revenue": revenue, "notes": notes})
    appts = pd.DataFrame(st.session_state.appointments)
    if not appts.empty:
        st.dataframe(appts, use_container_width=True)
        st.bar_chart(appts.groupby("status")["revenue"].sum())
