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
    y = int(h * 0.55) if h > w else int(h * 0.34)
    for line in wrap_text(draw, headline, headline_font, w - margin * 2)[:3]:
        draw.text((margin, y), line, fill="white", font=headline_font)
        y += int(headline_font.size * 1.12)
    sub = f"{location} | Contact by {deadline}"
    draw.text((margin, y + 12), sub, fill="#f3f7f8", font=font(max(24, int(w * 0.028)), False))
    draw.rectangle((0, h - int(h * .12), w, h), fill="#10252b")
    draw.text((margin, h - int(h * .08)), f"{agent}  |  Schedule a showing", fill="white", font=font(max(24, int(w * 0.027)), True))
    draw.text((w - margin - 220, h - int(h * .08)), platform.split()[0], fill="#9edfd4", font=font(max(22, int(w * 0.024)), True))
    return base


def make_social_zip(listing, images, selected_sizes):
    mem = io.BytesIO()
    with zipfile.ZipFile(mem, "w", zipfile.ZIP_DEFLATED) as zf:
        captions = []
        for label in selected_sizes:
            img = social_image(SOCIAL_SIZES[label], listing, images, label)
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


def make_brochure_pdf(listing, images, edits):
    mem = io.BytesIO()
    c = canvas.Canvas(mem, pagesize=letter)
    w, h = letter
    margin = 42
    hero_h = 270
    if images:
        hero = fit_image(images[0][1], (1100, 520))
        b = io.BytesIO(); hero.save(b, format="JPEG", quality=90); b.seek(0)
        c.drawImage(ImageReader(b), 0, h - hero_h, width=w, height=hero_h, preserveAspectRatio=False, mask="auto")
        c.setFillColor(colors.Color(0, 0, 0, alpha=.35)); c.rect(0, h - hero_h, w, hero_h, stroke=0, fill=1)
    else:
        c.setFillColor(colors.HexColor("#10252b")); c.rect(0, h - hero_h, w, hero_h, stroke=0, fill=1)
    c.setFillColor(colors.white); c.setFont("Helvetica-Bold", 23); c.drawString(margin, h - 82, edits["headline"][:58])
    c.setFont("Helvetica", 12); c.drawString(margin, h - 105, listing.get("location", ""))
    c.setFillColor(colors.HexColor("#d94f30")); c.roundRect(w - margin - 150, h - 92, 150, 36, 5, stroke=0, fill=1)
    c.setFillColor(colors.white); c.setFont("Helvetica-Bold", 15); c.drawCentredString(w - margin - 75, h - 78, listing.get("price", ""))
    y = h - hero_h - 34
    c.setFillColor(colors.HexColor("#17202a")); c.setFont("Helvetica-Bold", 16); c.drawString(margin, y, "Property Highlights"); y -= 22
    c.setFont("Helvetica", 10); c.setFillColor(colors.HexColor("#33404d"))
    for line in wrap_pdf(edits["highlights"], 90):
        c.drawString(margin, y, line); y -= 14
    y -= 8
    c.setFont("Helvetica-Bold", 14); c.setFillColor(colors.HexColor("#17202a")); c.drawString(margin, y, "Why buyers click"); y -= 20
    c.setFont("Helvetica", 10); c.setFillColor(colors.HexColor("#33404d"))
    for line in wrap_pdf(edits["promo"], 90):
        c.drawString(margin, y, line); y -= 14
    if len(images) > 1:
        x = margin
        y_img = 110
        for _, img in images[1:4]:
            thumb = fit_image(img, (170, 105)); b = io.BytesIO(); thumb.save(b, format="JPEG", quality=88); b.seek(0)
            c.drawImage(ImageReader(b), x, y_img, width=155, height=95, preserveAspectRatio=False, mask="auto")
            x += 165
    c.setFillColor(colors.HexColor("#10252b")); c.rect(0, 0, w, 54, stroke=0, fill=1)
    c.setFillColor(colors.white); c.setFont("Helvetica-Bold", 11)
    c.drawString(margin, 32, edits["footer"][:95])
    c.drawRightString(w - margin, 32, f"Contact by {listing.get('deadline','')}")
    c.showPage(); c.save(); mem.seek(0)
    return mem.getvalue()


def wrap_pdf(text, width):
    words = str(text).split(); lines = []; line = ""
    for word in words:
        trial = (line + " " + word).strip()
        if len(trial) <= width:
            line = trial
        else:
            if line: lines.append(line)
            line = word
    if line: lines.append(line)
    return lines


def scrape_templates(query, urls):
    notes = []
    headers = {"User-Agent": "EstateLaunchTemplateResearch/1.0"}
    targets = [u.strip() for u in urls.splitlines() if u.strip()]
    if query.strip():
        targets.insert(0, "https://duckduckgo.com/html/?q=" + quote_plus(query + " real estate brochure social media template"))
    for url in targets[:5]:
        try:
            html = requests.get(url, headers=headers, timeout=8).text
            soup = BeautifulSoup(html, "html.parser")
            title = (soup.find("title").get_text(" ", strip=True) if soup.find("title") else url)[:140]
            text = " ".join(soup.get_text(" ").split())[:1200]
            cues = []
            for word in ["luxury", "minimal", "modern", "bold", "photo", "price", "agent", "sold", "open house", "template", "brochure"]:
                if word in text.lower(): cues.append(word)
            notes.append({"source": url, "title": title, "style_cues": ", ".join(cues) or "clean real estate layout", "excerpt": text[:260]})
        except Exception as e:
            notes.append({"source": url, "title": "Could not scrape", "style_cues": "manual review needed", "excerpt": str(e)[:180]})
    return notes


def save_listing(headline, price, location, deadline, agent, details, canva_url):
    st.session_state.listing = {
        "headline": headline, "price": price, "location": location, "deadline": str(deadline),
        "agent": agent, "details": details, "promo": f"Discover {headline} in {location}. {details} Contact {agent} by {deadline}.",
        "canva_url": canva_url,
    }


tabs = st.tabs(["Listing", "Brochure PDF", "Social Media Assets", "Captions", "Template Research", "Appointments & Revenue"])

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
        details = st.text_area("Property details", st.session_state.listing.get("details", "4 bed, 3 bath, renovated kitchen, walkable neighborhood, solar panels, large backyard."), height=120)
        canva_url = st.text_input("Optional Canva artwork link", st.session_state.listing.get("canva_url", ""))
        if st.button("Save listing package"):
            save_listing(headline, price, location, deadline, agent, details, canva_url)
            st.success("Listing package saved.")

listing = st.session_state.listing or {
    "headline": "Modern Family Home With Designer Finishes", "price": "$749,000", "location": "Austin, TX",
    "deadline": str(date.today() + timedelta(days=21)), "agent": "Angela Lee | 555-0100",
    "details": "4 bed, 3 bath, renovated kitchen, walkable neighborhood, solar panels, large backyard.", "canva_url": "",
}
images = st.session_state.get("images", [])

with tabs[1]:
    st.subheader("Editable brochure layout")
    c1, c2 = st.columns([.48, .52])
    with c1:
        edit_headline = st.text_input("Brochure headline", listing.get("headline", ""))
        edit_promo = st.text_area("Promotional copy", listing.get("promo", ""), height=120)
        edit_highlights = st.text_area("Highlights", listing.get("details", ""), height=120)
        edit_footer = st.text_input("Footer/contact line", listing.get("agent", ""))
        st.text_area("Canva prompt", canva_prompt(listing), height=130)
        if listing.get("canva_url"):
            st.link_button("Open Canva artwork", listing["canva_url"])
        pdf_data = make_brochure_pdf(listing, images, {"headline": edit_headline, "promo": edit_promo, "highlights": edit_highlights, "footer": edit_footer})
        st.download_button("Download brochure PDF", pdf_data, file_name="estate_brochure.pdf", mime="application/pdf")
    with c2:
        hero_style = ""
        if images:
            st.image(images[0][1], caption="Hero image preview", use_container_width=True)
        st.markdown(f"""
        <div class='preview'>
          <div class='hero' style='{hero_style}'>
            <div><span class='price'>{listing.get('price','')}</span><h2>{edit_headline}</h2><div>{listing.get('location','')}</div></div>
          </div>
          <div class='grid2'><div><b>Highlights</b><br><span class='small'>{edit_highlights}</span></div><div><b>Buyer hook</b><br><span class='small'>{edit_promo}</span></div></div>
          <div style='padding:14px 18px;background:#10252b;color:white'>{edit_footer} | Contact by {listing.get('deadline','')}</div>
        </div>
        """, unsafe_allow_html=True)

with tabs[2]:
    st.subheader("Generate platform-ready social images")
    selected = st.multiselect("Social sizes", list(SOCIAL_SIZES), default=list(SOCIAL_SIZES))
    preview_size = st.selectbox("Preview size", list(SOCIAL_SIZES), index=1)
    if images:
        preview = social_image(SOCIAL_SIZES[preview_size], listing, images, preview_size)
        st.image(preview, caption=preview_size, use_container_width=False)
    else:
        st.info("Upload property photos on the Listing tab for photo-based previews.")
    if selected:
        zip_data = make_social_zip(listing, images, selected)
        st.download_button("Download zipped social media package", zip_data, file_name="estate_social_media_assets.zip", mime="application/zip")

with tabs[3]:
    st.subheader("Click-focused social captions")
    rows = []
    for label in SOCIAL_SIZES:
        rows.append({"platform_size": label, "caption": caption_for(label, listing), "hook_type": "curiosity + deadline", "cta": "Book a private showing"})
    df = pd.DataFrame(rows)
    st.data_editor(df, use_container_width=True, hide_index=True)
    st.download_button("Download caption bank CSV", df.to_csv(index=False), file_name="estate_caption_bank.csv")

with tabs[4]:
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
        st.download_button("Download template research CSV", notes_df.to_csv(index=False), file_name="template_research.csv")

with tabs[5]:
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
        st.download_button("Download CRM CSV", appts.to_csv(index=False), file_name="real_estate_pipeline.csv")
