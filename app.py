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

APP_NAME = "EstateLaunch Agent Desk"
st.set_page_config(page_title=APP_NAME, layout="wide")
st.markdown("""
<style>
.block-container{max-width:1240px;padding-top:5.25rem;font-family:system-ui,-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif}
.title{font-size:2rem;font-weight:800;color:#17202a}
.sub{color:#5d6673;margin:.2rem 0 1rem}
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

# Global Session Management
if "properties" not in st.session_state:
    st.session_state.properties = [
        {
            "id": 1,
            "headline": "ParkTown Residences",
            "price": "$1,750,000",
            "actual_sold_price": "$1,720,000",
            "location": "Tampines North, Singapore",
            "deadline": str(date.today() + timedelta(days=21)),
            "agent": "Angela Tan: 9123 4567",
            "details": "Integrated retail mall access with direct transit connections.",
            "status": "Sold",
            "commission_rate": 2.5,
            "remarks": "Negotiation finalized below listing price target."
        },
        {
            "id": 2,
            "headline": "Marina East Penthouse",
            "price": "$4,200,000",
            "actual_sold_price": "$0",
            "location": "District 15, Singapore",
            "deadline": str(date.today() + timedelta(days=30)),
            "agent": "Angela Tan: 9123 4567",
            "details": "Full waterfront views with private lift access framework.",
            "status": "Available",
            "commission_rate": 3.0,
            "remarks": "High interest during first weekend viewings."
        }
    ]
if "selected_property_id" not in st.session_state:
    st.session_state.selected_property_id = 1
if "appointments" not in st.session_state:
    st.session_state.appointments = []
if "images" not in st.session_state:
    st.session_state.images = []

SOCIAL_SIZES = {
    "TikTok Portrait 1080x1920": (1080, 1920),
    "Instagram Portrait 1080x1350": (1080, 1350),
    "Instagram Square 1080x1080": (1080, 1080),
    "Facebook Landscape 1200x630": (1200, 630),
    "LinkedIn Landscape 1200x627": (1200, 627),
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

def parse_price_to_float(price_str):
    try:
        cleaned = re.sub(r'[^\d.]', '', str(price_str))
        return float(cleaned) if cleaned else 0.0
    except Exception:
        return 0.0

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
    lines, line = [], ""
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

    c.setFillColor(colors.white)
    c.setFont("Helvetica-Bold", edits.get("footer_size", 12))
    c.drawString(safe + col_pad, safe + 30, edits["footer"][:95])
    c.drawRightString(safe + usable_w - col_pad, safe + 30, f"Contact by {listing.get('deadline','')}")

    c.showPage()
    c.save()
    mem.seek(0)
    return mem.getvalue()

def calculate_singapore_absd(property_value, profile, property_count):
    rates = {
        "Singapore Citizen": [0.0, 0.20, 0.30],
        "Singapore Permanent Resident": [0.05, 0.30, 0.35],
        "Foreigner": [0.60, 0.60, 0.60]
    }
    idx = 0 if property_count == "1st Property" else (1 if property_count == "2nd Property" else 2)
    rate = rates.get(profile, [0.60, 0.60, 0.60])[idx]
    return property_value * rate, rate

# --- Master Tabbed Matrix Layout Grid ---
tabs = st.tabs(["Property Portfolio Ledger", "Listing Entry", "Brochure PDF", "Social Media Plan", "Appointment", "Finance Reports"])

# --- TAB 1: PROPERTY PORTFOLIO LEDGER ---
with tabs[0]:
    st.subheader("Accumulated Property Portfolio Hub")
    st.markdown("Review and manage your complete property pipeline dataset below. Modifications to **Status** and **Remarks** save directly to memory.")
    
    if st.session_state.properties:
        ledger_df = pd.DataFrame(st.session_state.properties)
        
        # Interactive Editing Grid for Status and Remarks
        edited_ledger = st.data_editor(
            ledger_df[["id", "headline", "price", "location", "status", "remarks"]],
            column_config={
                "status": st.column_config.SelectboxColumn("Status", options=["Available", "Offer Received", "Sold", "Archived"], width="medium"),
                "remarks": st.column_config.TextColumn("Agent Remarks", width="large"),
                "id": st.column_config.NumberColumn("ID", disabled=True, width="small"),
                "headline": st.column_config.TextColumn("Property Headline", disabled=True),
                "price": st.column_config.TextColumn("Listing Price", disabled=True),
                "location": st.column_config.TextColumn("District Location", disabled=True)
            },
            use_container_width=True,
            hide_index=True,
            key="ledger_editor"
        )
        
        # Sync changes back to main session state
        for idx, row in edited_ledger.iterrows():
            for prop in st.session_state.properties:
                if prop["id"] == row["id"]:
                    prop["status"] = row["status"]
                    prop["remarks"] = row["remarks"]

        # Selection Engine for Global Focus Setup
        prop_options = {f"{p['headline']} ({p['price']})": p['id'] for p in st.session_state.properties}
        selected_option = st.selectbox("Set Workspace Focus Target Property:", list(prop_options.keys()))
        st.session_state.selected_property_id = prop_options[selected_option]
        
        # Inline Table Purge Controls
        st.markdown("### Purge Selected Property")
        purge_options = {f"ID {p['id']} - {p['headline']}": p['id'] for p in st.session_state.properties}
        target_purge_name = st.selectbox("Select Target Row Node to Permanently Delete:", ["Select Item"] + list(purge_options.keys()))
        
        if target_purge_name != "Select Item" and st.button("Execute Permanent Table Delete"):
            purge_id = purge_options[target_purge_name]
            st.session_state.properties = [p for p in st.session_state.properties if p['id'] != purge_id]
            st.success(f"Successfully purged property node entry from tracking records.")
            st.rerun()
    else:
        st.warning("No active property records accumulated yet. Proceed to the 'Listing Entry' tab to build your workspace.")

# Resolve operational contextual pointers based on user focus selection
active_id = st.session_state.selected_property_id
listing = next((p for p in st.session_state.properties if p['id'] == active_id), None)
if not listing and st.session_state.properties:
    listing = st.session_state.properties[0]
    st.session_state.selected_property_id = listing['id']
elif not listing:
    listing = {"id":0, "headline":"", "price":"$0", "actual_sold_price":"$0", "location":"", "deadline":str(date.today()), "agent":"", "details":"", "status":"Available", "commission_rate":2.5, "remarks":""}

images = st.session_state.get("images", [])

# --- TAB 2: LISTING ENTRY ---
with tabs[1]:
    st.subheader("Property Intake Registration Center")
    col1, col2 = st.columns([.45, .55])
    with col1:
        uploads = st.file_uploader("Upload staging imagery collateral", type=["png", "jpg", "jpeg"], accept_multiple_files=True)
        new_images = load_images(uploads)
        if new_images:
            st.session_state.images = [(name, img.copy()) for name, img in new_images]
            st.image([img for _, img in st.session_state.images[:4]], caption=[name for name, _ in st.session_state.images[:4]], width=180)
    with col2:
        in_headline = st.text_input("Property Headline Title", listing.get("headline", ""))
        in_price = st.text_input("Listing Base Price (Target Guide)", listing.get("price", ""))
        in_sold_price = st.text_input("Actual Final Sold Price (Set if transaction closed)", listing.get("actual_sold_price", "$0"))
        in_location = st.text_input("District Location Parameters", listing.get("location", ""))
        in_deadline = st.date_input("Closing Offer Turnaround Cutoff", date.today() + timedelta(days=21))
        in_agent = st.text_input("Lead Booking Agent Field", listing.get("agent", ""))
        in_details = st.text_area("Narrative Structural Specs", listing.get("details", ""), height=100)
        in_comm = st.slider("Agreed Net Commission Percentage Rate %", 0.0, 10.0, float(listing.get("commission_rate", 2.5)), step=0.1)
        in_status = st.selectbox("Set Pipeline Phase Status", ["Available", "Offer Received", "Sold", "Archived"], index=["Available", "Offer Received", "Sold", "Archived"].index(listing.get("status", "Available")))
        in_remarks = st.text_input("Initial Intake Remarks", listing.get("remarks", ""))
        
        if st.button("Commit Property Node Configuration"):
            if listing['id'] != 0:
                for idx, p in enumerate(st.session_state.properties):
                    if p['id'] == active_id:
                        st.session_state.properties[idx] = {
                            "id": active_id, "headline": in_headline, "price": in_price, "actual_sold_price": in_sold_price,
                            "location": in_location, "deadline": str(in_deadline), "agent": in_agent, "details": in_details,
                            "status": in_status, "commission_rate": in_comm, "remarks": in_remarks
                        }
                st.success("Updated existing property profile configuration.")
            else:
                new_id = max([p['id'] for p in st.session_state.properties]) + 1 if st.session_state.properties else 1
                st.session_state.properties.append({
                    "id": new_id, "headline": in_headline, "price": in_price, "actual_sold_price": in_sold_price,
                    "location": in_location, "deadline": str(in_deadline), "agent": in_agent, "details": in_details,
                    "status": in_status, "commission_rate": in_comm, "remarks": in_remarks
                })
                st.session_state.selected_property_id = new_id
                st.success("Appended new portfolio listing card track entry point node.")
            st.rerun()

# --- TAB 3: BROCHURE PDF ---
with tabs[2]:
    st.subheader(f"Collateral Engine Studio: {listing.get('headline','')}")
    c1, c2 = st.columns([.48, .52])
    with c1:
        edit_headline = listing.get("headline", "")
        about_text = st.text_area("Core Summary Callout Copy", listing.get("details", ""), height=120)
        highlights_text = st.text_area("Advantage Metrics (One line per item)", "Direct Mass Transit Infrastructure Grid Links\nElite Local Scholastic Districts", height=80)
        edit_footer = st.text_input("Footer Signoff Track", listing.get("agent", ""))

        title_size = st.slider("Title Typography Scale", 18, 60, 26, step=2)
        body_size = st.slider("Body Detail Formatting Size", 10, 24, 12, step=2)
        accent_color = st.color_picker("Brand Pop Highlight Color Selection", "#d94f30")
        footer_color = st.color_picker("Structural Base Framing Color Panel", "#10252b")

        hero_choice = None
        bottom_choices = []
        if images:
            hero_choice = st.selectbox("Assign Primetime Imagery Asset", options=[name for name, _ in images], index=0)
            bottom_choices = st.multiselect("Assign Multi-Gallery Thumbnails (Max 3)", options=[name for name, _ in images], default=[name for name, _ in images[1:4]] if len(images) > 1 else [])

        pdf_data = make_brochure_pdf(listing, images, {"headline": edit_headline, "about": about_text, "highlights": highlights_text, "footer": edit_footer, "title_size": title_size, "body_size": body_size}, hero_choice, bottom_choices, accent_hex=accent_color, footer_hex=footer_color)
        st.download_button("Download Print Brochure Sheet (PDF)", pdf_data, file_name="estate_brochure.pdf", mime="application/pdf", use_container_width=True)

    with c2:
        about_html = "<br>".join(about_text.split("\n"))
        highlights_html = "<br>".join("• " + l for l in [l.strip() for l in highlights_text.split("\n") if l.strip()][:5])
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
            <div><b>About Layout Focus</b><br><span class='small'>{about_html}</span></div>
            <div><b>Why We Recommend</b><br><span class='small'>{highlights_html}</span></div>
          </div>
          <div style='padding:14px 18px;background:{footer_color};color:white'>{edit_footer} | Closing Date Track: {listing.get('deadline','')}</div>
        </div>
        """, unsafe_allow_html=True)

# --- TAB 4: SOCIAL MEDIA PLAN ---
with tabs[3]:
    st.subheader("Social Copywriting Studio & Organic Distribution Blueprint")
    st.markdown("### Master Clipboard-Ready Platforms Caption Matrix")
    rows = [{"platform_size": label, "caption": caption_for(label, listing), "hook_type": "Direct Structural Hook Frame", "cta": "Schedule VIP booking tour details"} for label in SOCIAL_SIZES]
    df = pd.DataFrame(rows)
    st.data_editor(df, use_container_width=True, hide_index=True)
    
    st.markdown("---")
    st.markdown("### AI Organic Algorithmic Virality Timeline Strategy")
    calendar_plan = [
        {"Day": "Day 1", "Platform": "TikTok / Shorts Track", "Strategy Angle": "POV Financial Contrast Hook", "Algorithmic Delivery Directives": "Structure video layers to lock visual retention benchmarks early. Highlight value gaps explicitly inside the description window."},
        {"Day": "Day 3", "Platform": "Instagram Multi-Slide", "Strategy Angle": "Interior Asset Deep Dive Gallery", "Algorithmic Delivery Directives": "Drive carousel layout optimization actions by prompting saves to maximize backend performance calculations."},
        {"Day": "Day 5", "Platform": "LinkedIn Executive Grid", "Strategy Angle": "District Growth Vector Analysis", "Algorithmic Delivery Directives": "Target corporate professional demographics. Detail infrastructure updates and connection value profiles cleanly."}
    ]
    st.table(pd.DataFrame(calendar_plan))

# --- TAB 5: APPOINTMENT ---
with tabs[4]:
    st.subheader(f"Lead Funnel Tracking Board: {listing.get('headline','')}")
    with st.form("appointment_form"):
        client = st.text_input("Prospect Client Identity Name", "Michael Tan")
        appt_date = st.date_input("Scheduled Tour Event Timeline Date", date.today() + timedelta(days=2))
        status = st.selectbox("Deal Status Lifecycle Phase", ["Scheduled", "Shown", "Offer Table", "Under Contract", "Closed / Settled", "Lost / Cancelled"])
        notes = st.text_area("Consultation Brief Notes", "Analyzing multi-unit ABSD exposure options.", height=80)
        
        if st.form_submit_button("Commit Client Lead Entry"):
            derived_revenue = parse_price_to_float(listing.get("price", "0"))
            st.session_state.appointments.append({
                "property_id": listing['id'], "property_name": listing['headline'], "client": client, 
                "date": str(appt_date), "status": status, "revenue_basis": derived_revenue, "notes": notes
            })
            st.success(f"Interaction committed to master data table pipelines.")
            
    appts = pd.DataFrame(st.session_state.appointments)
    if not appts.empty:
        st.markdown("### Active Leads Showing Activity Board")
        st.dataframe(appts, use_container_width=True)

# --- TAB 6: FINANCE REPORTS ---
with tabs[5]:
    st.subheader("Singapore Property Analysis & Commission Revenue Dashboard")
    
    val_base = parse_price_to_float(listing.get("price", "0"))
    st.metric(label="Focused Valuation Reference Target Base (Derived dynamically from active listing asset parameters)", value=f"SGD ${val_base:,.2f}")
    
    st.markdown("---")
    st.markdown("### 1. ABSD Liability Projections Engine")
    rc1, rc2 = st.columns(2)
    with rc1:
        buyer_profile = st.selectbox("Target Demographics Profile Bracket", ["Singapore Citizen", "Singapore Permanent Resident", "Foreigner"])
        property_holding = st.selectbox("Current Household Asset Inventory Holding Tally", ["1st Property", "2nd Property", "3rd Property+"])
    with rc2:
        absd_fee, active_rate = calculate_singapore_absd(val_base, buyer_profile, property_holding)
        st.metric(label="ABSD Tax Scale Applied Rate", value=f"{active_rate * 100:.1f}%")
        st.metric(label="Total Estimated ABSD Liability Overhead Charge", value=f"SGD ${absd_fee:,.2f}")
        
    st.markdown("---")
    st.markdown("### 2. Transaction Summary Desk: Listing vs. Actual Price Tracking")
    st.markdown("Net Received Revenue calculates automatically from listings marked as **Sold** using final closed transactional valuations.")
    
    sold_records_reconciliation = []
    total_net_received_commissions = 0.0
    
    for p in st.session_state.properties:
        if p.get("status") == "Sold":
            list_price_num = parse_price_to_float(p.get("price", "0"))
            actual_price_num = parse_price_to_float(p.get("actual_sold_price", "0"))
            
            # Use listing price fallback baseline if actual sold price is unset
            final_basis_price = actual_price_num if actual_price_num > 0.0 else list_price_num
            
            commission_percentage = float(p.get("commission_rate", 2.5))
            calculated_payout_fee = final_basis_price * (commission_percentage / 100.0)
            total_net_received_commissions += calculated_payout_fee
            
            sold_records_reconciliation.append({
                "Property ID": p["id"],
                "Headline": p["headline"],
                "Listing Target Price": f"${list_price_num:,.2f}",
                "Actual Sold Valuation Price": f"${final_basis_price:,.2f}",
                "Contract Split Rate": f"{commission_percentage}%",
                "Net Commission Received": calculated_payout_fee
            })
            
    # Display aggregated metric indicators
    st.metric(label="Net Commission Received Revenue Flow (End-Of-Day Actual Asset Inflow)", value=f"SGD ${total_net_received_commissions:,.2f}", delta="Reconciled Net Realized Yield")
    
    if sold_records_reconciliation:
        recon_df = pd.DataFrame(sold_records_reconciliation)
        st.dataframe(
            recon_df,
            column_config={
                "Net Commission Received": st.column_config.NumberColumn("Your Net Commission Yield Payout", format="SGD $%hf.2f")
            },
            use_container_width=True,
            hide_index=True
        )
    else:
        st.info("No transaction assets currently configured as 'Sold'. Move your property profiles into 'Sold' parameters in the 'Property Portfolio Ledger' or 'Listing Entry' dashboards to update ledger revenue logs.")
