"""
app.py
======
Streamlit front-end for Solar Advisor Bot.
Run with:  streamlit run src/app.py
"""

import os
import sys
import tempfile

import streamlit as st

# ---------------------------------------------------------------------------
# Path setup — make sure src/ siblings are importable
# ---------------------------------------------------------------------------
sys.path.insert(0, os.path.dirname(__file__))

from solar_math import (
    get_full_estimate,
    CITY_PEAK_SUN_HOURS,
    ROOF_STRUCTURE,
    IP_RATING,
    get_mounting_recommendation,
    APPLIANCE_WATTAGE,
    calculate_units_from_appliances,
)
from main import get_explanation, extract_units_from_bill
from pdf_export import generate_proposal_pdf

# ---------------------------------------------------------------------------
# Page config
# ---------------------------------------------------------------------------
st.set_page_config(
    page_title="Solar Advisor Bot",
    page_icon="☀️",
    layout="centered",
    initial_sidebar_state="collapsed",
)

# ---------------------------------------------------------------------------
# Custom CSS — premium dark theme
# ---------------------------------------------------------------------------
st.markdown(
    """
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&family=Space+Grotesk:wght@400;500;600;700&display=swap');

    /* ══════════════════════════════════════
       BASE TYPOGRAPHY
    ══════════════════════════════════════ */
    html, body, [class*="css"] {
        font-family: 'Inter', sans-serif;
    }
    h1, h2, h3, h4 {
        font-family: 'Space Grotesk', sans-serif !important;
    }

    /* ══════════════════════════════════════
       ANIMATED BACKGROUND
    ══════════════════════════════════════ */
    .stApp {
        background:
            radial-gradient(ellipse 80% 50% at 20% 10%, rgba(251,146,60,0.07) 0%, transparent 60%),
            radial-gradient(ellipse 60% 40% at 80% 80%, rgba(34,197,94,0.05) 0%, transparent 55%),
            radial-gradient(ellipse 70% 60% at 50% 50%, rgba(250,204,21,0.04) 0%, transparent 70%),
            linear-gradient(160deg, #080c14 0%, #0d1117 40%, #0b1a0f 80%, #080c14 100%);
        min-height: 100vh;
    }

    /* ══════════════════════════════════════
       HERO HEADER
    ══════════════════════════════════════ */
    .hero-title {
        font-family: 'Space Grotesk', sans-serif;
        font-size: 2.9rem;
        font-weight: 800;
        background: linear-gradient(90deg, #facc15 0%, #fb923c 45%, #f97316 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        background-clip: text;
        text-align: left;
        margin-bottom: 0.3rem;
        letter-spacing: -1px;
        line-height: 1.15;
        filter: drop-shadow(0 0 32px rgba(250,204,21,0.18));
    }
    .hero-caption {
        text-align: left;
        color: #6b7280;
        font-size: 0.92rem;
        margin-bottom: 0;
        font-style: italic;
        letter-spacing: 0.2px;
    }

    /* ══════════════════════════════════════
       GLASSMORPHISM CARD
    ══════════════════════════════════════ */
    .card {
        background: linear-gradient(135deg,
            rgba(255,255,255,0.055) 0%,
            rgba(255,255,255,0.025) 100%);
        border: 1px solid rgba(255,255,255,0.10);
        border-top: 1px solid rgba(255,255,255,0.16);
        border-radius: 20px;
        padding: 1.6rem 1.9rem;
        margin-bottom: 1.4rem;
        backdrop-filter: blur(20px);
        -webkit-backdrop-filter: blur(20px);
        box-shadow:
            0 4px 6px rgba(0,0,0,0.3),
            0 20px 40px rgba(0,0,0,0.2),
            inset 0 1px 0 rgba(255,255,255,0.06);
        position: relative;
        overflow: hidden;
    }
    .card::before {
        content: '';
        position: absolute;
        top: 0; left: 0; right: 0;
        height: 1px;
        background: linear-gradient(90deg,
            transparent 0%,
            rgba(250,204,21,0.4) 50%,
            transparent 100%);
    }
    .card-title {
        font-size: 0.7rem;
        font-weight: 700;
        text-transform: uppercase;
        letter-spacing: 2px;
        color: rgba(250,204,21,0.7);
        margin-bottom: 1.1rem;
    }

    /* ══════════════════════════════════════
       METRIC TILES
    ══════════════════════════════════════ */
    [data-testid="metric-container"] {
        background: linear-gradient(135deg,
            rgba(250,204,21,0.08) 0%,
            rgba(249,115,22,0.05) 100%);
        border: 1px solid rgba(250,204,21,0.18);
        border-radius: 16px;
        padding: 1.1rem 1.3rem !important;
        transition: transform 0.25s cubic-bezier(.34,1.56,.64,1),
                    box-shadow 0.25s ease,
                    border-color 0.25s ease;
        position: relative;
        overflow: hidden;
    }
    [data-testid="metric-container"]::after {
        content: '';
        position: absolute;
        top: -50%; left: -50%;
        width: 200%; height: 200%;
        background: radial-gradient(circle at center,
            rgba(250,204,21,0.04) 0%, transparent 65%);
        pointer-events: none;
    }
    [data-testid="metric-container"]:hover {
        transform: translateY(-4px) scale(1.01);
        box-shadow:
            0 12px 32px rgba(250,204,21,0.15),
            0 4px 12px rgba(0,0,0,0.3);
        border-color: rgba(250,204,21,0.35);
    }
    [data-testid="stMetricValue"] {
        color: #facc15 !important;
        font-family: 'Space Grotesk', sans-serif !important;
        font-weight: 700 !important;
        font-size: 1.55rem !important;
        letter-spacing: -0.5px;
    }
    [data-testid="stMetricLabel"] {
        color: #9ca3af !important;
        font-size: 0.78rem !important;
        font-weight: 500 !important;
        text-transform: uppercase;
        letter-spacing: 0.8px;
    }

    /* ══════════════════════════════════════
       MAIN CTA BUTTON
    ══════════════════════════════════════ */
    div.stButton > button[kind="secondary"],
    div.stButton > button {
        width: 100%;
        background: linear-gradient(90deg, #f97316 0%, #facc15 100%);
        color: #0d1117;
        font-family: 'Space Grotesk', sans-serif;
        font-weight: 700;
        font-size: 1.05rem;
        letter-spacing: 0.3px;
        border: none;
        border-radius: 12px;
        padding: 0.8rem 1.5rem;
        cursor: pointer;
        transition: all 0.2s cubic-bezier(.34,1.56,.64,1);
        box-shadow:
            0 4px 20px rgba(249,115,22,0.35),
            0 2px 6px rgba(0,0,0,0.3);
        margin-top: 0.6rem;
        position: relative;
        overflow: hidden;
    }
    div.stButton > button:hover {
        transform: translateY(-2px) scale(1.01);
        box-shadow:
            0 8px 30px rgba(250,204,21,0.4),
            0 4px 12px rgba(0,0,0,0.4);
    }
    div.stButton > button:active {
        transform: translateY(0) scale(0.99);
    }

    /* ══════════════════════════════════════
       TABS
    ══════════════════════════════════════ */
    .stTabs [data-baseweb="tab-list"] {
        background: rgba(255,255,255,0.03);
        border-radius: 12px;
        padding: 4px;
        border: 1px solid rgba(255,255,255,0.07);
        gap: 2px;
    }
    .stTabs [data-baseweb="tab"] {
        border-radius: 9px;
        padding: 0.5rem 1.1rem;
        color: #6b7280;
        font-weight: 500;
        font-size: 0.88rem;
        transition: all 0.18s ease;
        border: none !important;
        background: transparent !important;
    }
    .stTabs [data-baseweb="tab"]:hover {
        color: #d1d5db;
        background: rgba(255,255,255,0.05) !important;
    }
    .stTabs [aria-selected="true"] {
        background: linear-gradient(135deg,
            rgba(250,204,21,0.18) 0%,
            rgba(249,115,22,0.12) 100%) !important;
        color: #facc15 !important;
        font-weight: 600 !important;
        box-shadow: 0 2px 10px rgba(250,204,21,0.12);
    }
    .stTabs [data-baseweb="tab-highlight"] {
        display: none !important;
    }
    .stTabs [data-baseweb="tab-panel"] {
        padding-top: 1.1rem !important;
    }

    /* ══════════════════════════════════════
       INPUTS & SELECTS
    ══════════════════════════════════════ */
    .stNumberInput input,
    .stTextInput input,
    .stSelectbox > div > div,
    .stMultiSelect > div > div {
        background: rgba(255,255,255,0.04) !important;
        border: 1px solid rgba(255,255,255,0.10) !important;
        border-radius: 10px !important;
        color: #f3f4f6 !important;
        transition: border-color 0.18s ease, box-shadow 0.18s ease;
    }
    .stNumberInput input:focus,
    .stTextInput input:focus {
        border-color: rgba(250,204,21,0.45) !important;
        box-shadow: 0 0 0 3px rgba(250,204,21,0.08) !important;
        outline: none !important;
    }

    /* ══════════════════════════════════════
       CHECKBOX
    ══════════════════════════════════════ */
    .stCheckbox label span {
        color: #d1d5db !important;
        font-size: 0.93rem;
    }

    /* ══════════════════════════════════════
       ALERT & INFO BOXES
    ══════════════════════════════════════ */
    [data-testid="stAlert"] {
        border-radius: 12px !important;
        border-width: 1px !important;
    }
    [data-testid="stAlert"][data-baseweb="notification"] {
        background: rgba(59,130,246,0.07) !important;
        border-color: rgba(59,130,246,0.25) !important;
    }

    /* ══════════════════════════════════════
       DOWNLOAD BUTTON — gold pill
    ══════════════════════════════════════ */
    [data-testid="stDownloadButton"] > button {
        background: linear-gradient(90deg,
            rgba(250,204,21,0.15) 0%,
            rgba(249,115,22,0.10) 100%) !important;
        border: 1px solid rgba(250,204,21,0.35) !important;
        color: #facc15 !important;
        border-radius: 12px !important;
        font-weight: 600 !important;
        font-size: 0.95rem !important;
        transition: all 0.2s ease !important;
        box-shadow: 0 2px 12px rgba(250,204,21,0.10) !important;
    }
    [data-testid="stDownloadButton"] > button:hover {
        background: linear-gradient(90deg,
            rgba(250,204,21,0.25) 0%,
            rgba(249,115,22,0.18) 100%) !important;
        box-shadow: 0 6px 24px rgba(250,204,21,0.2) !important;
        transform: translateY(-1px);
    }

    /* ══════════════════════════════════════
       DIVIDER
    ══════════════════════════════════════ */
    hr {
        border: none !important;
        height: 1px !important;
        background: linear-gradient(90deg,
            transparent 0%,
            rgba(255,255,255,0.08) 20%,
            rgba(250,204,21,0.15) 50%,
            rgba(255,255,255,0.08) 80%,
            transparent 100%) !important;
        margin: 1.5rem 0 !important;
    }

    /* ══════════════════════════════════════
       FILE UPLOADER
    ══════════════════════════════════════ */
    [data-testid="stFileUploadDropzone"] {
        background: rgba(250,204,21,0.02) !important;
        border: 2px dashed rgba(250,204,21,0.22) !important;
        border-radius: 16px !important;
        transition: border-color 0.2s ease, background 0.2s ease;
    }
    [data-testid="stFileUploadDropzone"]:hover {
        background: rgba(250,204,21,0.04) !important;
        border-color: rgba(250,204,21,0.4) !important;
    }

    /* ══════════════════════════════════════
       SUBHEADERS
    ══════════════════════════════════════ */
    h2, h3 {
        background: linear-gradient(90deg, #f3f4f6, #d1d5db);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        background-clip: text;
        font-weight: 700 !important;
        letter-spacing: -0.3px;
    }

    /* ══════════════════════════════════════
       CAPTION / SMALL TEXT
    ══════════════════════════════════════ */
    small, .stCaption, [data-testid="stCaptionContainer"] {
        color: #6b7280 !important;
        font-size: 0.82rem !important;
    }

    /* ══════════════════════════════════════
       SCROLLBAR
    ══════════════════════════════════════ */
    ::-webkit-scrollbar { width: 6px; height: 6px; }
    ::-webkit-scrollbar-track { background: transparent; }
    ::-webkit-scrollbar-thumb {
        background: rgba(250,204,21,0.25);
        border-radius: 3px;
    }
    ::-webkit-scrollbar-thumb:hover {
        background: rgba(250,204,21,0.45);
    }

    /* ══════════════════════════════════════
       EXPANDER
    ══════════════════════════════════════ */
    [data-testid="stExpander"] {
        background: rgba(255,255,255,0.025) !important;
        border: 1px solid rgba(255,255,255,0.07) !important;
        border-radius: 12px !important;
    }
    [data-testid="stExpander"] summary {
        color: #9ca3af !important;
        font-size: 0.88rem !important;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

# ---------------------------------------------------------------------------
# Hero header
# ---------------------------------------------------------------------------
_hero_col, _tag_col = st.columns([3, 1], gap="small")
with _hero_col:
    st.markdown('<div class="hero-title">☀️ Solar Advisor Bot</div>', unsafe_allow_html=True)
    st.markdown(
        '<div class="hero-caption">Real math, honest numbers. No hallucinated savings.</div>',
        unsafe_allow_html=True,
    )
with _tag_col:
    st.caption("Built for honest solar\ndecisions in Pakistan 🇵🇰")

# ---------------------------------------------------------------------------
# Session state init
# ---------------------------------------------------------------------------
if "units_override" not in st.session_state:
    st.session_state["units_override"] = None
if "last_estimate" not in st.session_state:
    st.session_state["last_estimate"] = None

# ---------------------------------------------------------------------------
# Input form
# ---------------------------------------------------------------------------
st.markdown('<div class="card"><div class="card-title">Your Details</div>', unsafe_allow_html=True)

city_list = sorted(CITY_PEAK_SUN_HOURS.keys())

st.info(
    "Currently verified for IESCO (Islamabad) using official SRO\u00a0279(I)/2026 tariff "
    "data, with live-fetch cross-checking against iesco.com.pk/tariff-guide. "
    "We looked into LESCO and FESCO too \u2014 LESCO\u2019s published sources conflict with "
    "each other on current rates, and FESCO\u2019s tariff page blocks automated access. "
    "Rather than guess, we kept this version IESCO-only so every number you see "
    "stays verifiably accurate. Other DISCOs are the natural next step."
)

# City is shared across all three input modes
city = st.selectbox(
    "Your city",
    options=city_list,
    index=city_list.index("Islamabad"),
    key="city_input",
)

# ── Three input modes as tabs ──
tab1, tab2, tab3 = st.tabs(["📋 Enter Units Manually", "🔌 Estimate from Appliances", "📄 Upload Bill Photo"])

with tab1:
    default_units = int(st.session_state["units_override"]) if st.session_state["units_override"] else 300
    monthly_units_tab1 = st.number_input(
        "Monthly electricity usage (units / kWh)",
        min_value=1,
        max_value=10_000,
        value=default_units,
        step=10,
        help="Check your last bill — look for 'Units Consumed' or 'kWh'.",
        key="units_input",
    )

with tab2:
    try:
        selected_appliances = st.multiselect(
            "Select the appliances you use:",
            options=list(APPLIANCE_WATTAGE.keys()),
            key="appliance_select",
        )
        items = []
        if selected_appliances:
            st.markdown("**Adjust quantities and daily hours:**")
            for appliance in selected_appliances:
                defaults = APPLIANCE_WATTAGE[appliance]
                acol1, acol2, acol3 = st.columns([3, 1, 1], gap="small")
                with acol1:
                    st.markdown(
                        f"**{appliance}** &nbsp; <span style='color:#9ca3af;font-size:0.85rem'>({defaults['watts']} W)</span>",
                        unsafe_allow_html=True,
                    )
                with acol2:
                    qty = st.number_input(
                        "Qty",
                        min_value=0,
                        value=1,
                        step=1,
                        key=f"qty_{appliance}",
                        label_visibility="collapsed",
                    )
                with acol3:
                    hrs = st.number_input(
                        "Hrs/day",
                        min_value=0.0,
                        value=float(defaults["default_hours"]),
                        step=0.5,
                        key=f"hrs_{appliance}",
                        label_visibility="collapsed",
                    )
                items.append({
                    "name": appliance,
                    "watts": defaults["watts"],
                    "quantity": qty,
                    "hours_per_day": hrs,
                })

            appl_result = calculate_units_from_appliances(items)
            st.session_state["appliance_computed_units"] = max(1, appl_result["monthly_units"])
            st.info(f"\u26a1 Estimated monthly usage: **{st.session_state['appliance_computed_units']} units** ({appl_result['daily_kwh']} kWh/day)")

            with st.expander("See appliance breakdown"):
                for row in appl_result["breakdown"]:
                    st.write(
                        f"- **{row['name']}** \u00d7 {row['quantity']} "
                        f"@ {row['hours_per_day']} h/day = {row['daily_kwh']} kWh/day"
                    )
        else:
            st.session_state["appliance_computed_units"] = None
            st.caption("Select appliances above \u2014 quantities and hours will appear here.")
    except Exception as appl_err:
        st.error(f"Appliance estimator error: {appl_err}")
        st.session_state["appliance_computed_units"] = None

with tab3:
    uploaded_file = st.file_uploader(
        "Upload a photo of your electricity bill (JPEG or PNG)",
        type=["jpg", "jpeg", "png"],
        label_visibility="collapsed",
        key="bill_upload",
    )

    if uploaded_file is not None:
        with st.spinner("Reading your bill photo\u2026"):
            try:
                suffix = ".jpg" if uploaded_file.type in ("image/jpeg", "image/jpg") else ".png"
                with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
                    tmp.write(uploaded_file.getbuffer())
                    tmp_path = tmp.name

                ocr_result = extract_units_from_bill(tmp_path)

                if ocr_result.get("units_found"):
                    detected = ocr_result["monthly_units"]
                    confidence = ocr_result.get("confidence", "")
                    raw = ocr_result.get("raw_text_seen", "")

                    st.info(
                        f"\U0001f4cb Detected **{detected:.0f} units** "
                        f"(confidence: {confidence}).  \n"
                        f"Raw text seen: *\"{raw}\"*"
                    )

                    btn_col1, btn_col2 = st.columns(2, gap="small")
                    with btn_col1:
                        if st.button("Use This Number", key="ocr_accept_btn"):
                            st.session_state["units_override"] = detected
                            st.success(f"Units updated to {detected:.0f}")
                    with btn_col2:
                        if st.button("Enter Manually Instead", key="ocr_reject_btn"):
                            st.info("No problem, type the correct units in the first tab.")
                else:
                    err = ocr_result.get("error", "")
                    raw = ocr_result.get("raw_text_seen", "")
                    st.warning(
                        f"\u26a0\ufe0f Could not clearly read units from the bill image. "
                        f"Raw text seen: *\"{raw}\"*{(chr(10) + 'Error: ' + err) if err else ''}  \n"
                        "Please enter your units manually in the first tab."
                    )
            except Exception as e:
                st.error(f"Error processing uploaded image: {e}")

# ── Resolve which monthly_units to use ──
# Appliance tab wins if appliances are selected; otherwise use manual input
# (which already reflects any bill-photo-accepted units_override as its default)
if st.session_state.get("appliance_select") and st.session_state.get("appliance_computed_units"):
    monthly_units = st.session_state["appliance_computed_units"]
else:
    monthly_units = monthly_units_tab1

is_tou = st.checkbox(
    "My sanctioned load is 5 kW or above (Time of Use meter)",
    value=False,
    key="tou_input",
    help="If your meter has two rates (peak / off-peak), tick this box.",
)

col_roof, col_inv = st.columns([1, 1], gap="medium")

with col_roof:
    roof_type = st.selectbox(
        "Roof type",
        options=list(ROOF_STRUCTURE.keys()),
        key="roof_type_input",
    )

with col_inv:
    inverter_location = st.selectbox(
        "Inverter mounting location",
        options=list(IP_RATING.keys()),
        key="inverter_location_input",
    )

st.markdown("</div>", unsafe_allow_html=True)

st.divider()

# ---------------------------------------------------------------------------
# Estimate button
# ---------------------------------------------------------------------------
run_estimate = st.button("⚡ Get My Solar Estimate", key="run_btn")

# ── Empty state shown before any estimate has been run ──
if not run_estimate and not st.session_state.get("last_estimate"):
    st.markdown(
        "<div style='text-align:center;color:#6b7280;padding:2.5rem 0 1rem;font-size:1rem;'>"
        "Fill in your details above and click "
        "<strong style='color:#facc15;'>⚡ Get My Solar Estimate</strong> to see your results."
        "</div>",
        unsafe_allow_html=True,
    )

# ---------------------------------------------------------------------------
# Results
# ---------------------------------------------------------------------------
if run_estimate:
    try:
        with st.spinner("Crunching the numbers…"):
            estimate = get_full_estimate(monthly_units, city, is_tou)
        st.session_state["last_estimate"] = estimate

        st.divider()
        st.markdown('<div class="card"><div class="card-title">📊 Your Estimate</div>', unsafe_allow_html=True)

        c1, c2, c3 = st.columns(3)
        c1.metric("System Size", f"{estimate['system_kw']} kW")
        c2.metric("Number of Panels", f"{estimate['num_panels']}")
        c3.metric("Estimated Cost", f"₨ {estimate['system_cost_pkr']:,}")

        c4, c5 = st.columns(2)
        c4.metric("Monthly Savings", f"₨ {estimate['monthly_savings_pkr']:,}")
        payback_display = (
            f"{estimate['payback_years']} yrs"
            if estimate.get("payback_years") is not None
            else "N/A"
        )
        c5.metric("Payback Period", payback_display)

        st.markdown("</div>", unsafe_allow_html=True)

        with st.spinner("Writing your explanation…"):
            explanation = get_explanation(estimate)
        st.session_state["last_explanation"] = explanation

        st.info(f"💡 {explanation}")

        # ── Mounting & protection recommendation ──
        st.divider()
        st.subheader("🏠 Recommended Mounting & Protection")
        try:
            mount = get_mounting_recommendation(roof_type, inverter_location)
            st.session_state["last_mount"] = mount
            st.markdown(
                f"**Mounting structure:**  \n{mount['structure_recommendation']}"
            )
            st.markdown(
                f"**Inverter protection rating:** **{mount['ip_rating']}**  \n"
                f"{mount['ip_reason']}"
            )
        except Exception as mount_err:
            st.error(f"Could not load mounting recommendation: {mount_err}")

        st.divider()

    except Exception as e:
        st.error(f"Something went wrong while calculating your estimate: {e}")

# ---------------------------------------------------------------------------
# Vendor quote checker — only shown after an estimate exists
# ---------------------------------------------------------------------------
if st.session_state.get("last_estimate"):
    st.divider()
    st.subheader("🔍 Vendor Quote Checker")

    vendor_price = st.number_input(
        "Vendor's quoted price (PKR)",
        min_value=0,
        max_value=100_000_000,
        value=0,
        step=10_000,
        key="vendor_price_input",
        help="Enter the total system price the vendor quoted you.",
    )

    check_quote = st.button("Check This Quote", key="check_quote_btn")

    if check_quote:
        if vendor_price <= 0:
            st.warning("Please enter a vendor price greater than 0 to check it.")
        else:
            try:
                stored = st.session_state["last_estimate"]
                honest_cost = stored["system_cost_pkr"]

                if not honest_cost or honest_cost == 0:
                    st.error("Could not retrieve the honest cost estimate. Please run the estimate again.")
                else:
                    price_gap_pkr     = vendor_price - honest_cost
                    price_gap_percent = round((price_gap_pkr / honest_cost) * 100, 1)

                    # ── Verdict thresholds ──
                    if price_gap_percent < -10:
                        verdict = "SUSPICIOUSLY CHEAP — verify equipment quality"
                        verdict_type = "warning_cheap"
                    elif price_gap_percent <= 10:
                        verdict = "FAIR"
                        verdict_type = "fair"
                    elif price_gap_percent <= 30:
                        verdict = "SLIGHTLY OVERSOLD"
                        verdict_type = "slightly_over"
                    else:
                        verdict = "OVERCHARGED"
                        verdict_type = "overcharged"

                    # ── Plain-language explanations ──
                    explanations = {
                        "fair": (
                            "This quote is within a reasonable range of our honest estimate for this system size. "
                            "You can proceed with confidence, but still ask for a detailed breakdown of equipment brands and warranty terms."
                        ),
                        "slightly_over": (
                            "This quote is a bit higher than our estimate. This could be due to higher-quality panels, "
                            "a battery backup, or simply a markup. Ask the vendor to itemize the quote so you know exactly what you're paying for."
                        ),
                        "overcharged": (
                            "This vendor's quote is significantly higher than a fair estimate for this system size. "
                            "Ask them to itemize costs or get a second quote before committing."
                        ),
                        "warning_cheap": (
                            "A price this far below market rate is a red flag. The vendor may be using low-grade panels, "
                            "undersized inverters, or cutting corners on installation. Always verify the brand, wattage, and warranty before signing."
                        ),
                    }
                    explanation_text = explanations[verdict_type]

                    # ── Display ──
                    gap_sign = "+" if price_gap_pkr >= 0 else ""
                    summary = (
                        f"**Verdict: {verdict}**\n\n"
                        f"- 🧮 Our honest estimate: **₨ {honest_cost:,}**\n"
                        f"- 🏷️ Vendor's quoted price: **₨ {vendor_price:,}**\n"
                        f"- 📊 Price gap: **{gap_sign}₨ {price_gap_pkr:,}** "
                        f"({gap_sign}{price_gap_percent}%)\n\n"
                        f"{explanation_text}"
                    )

                    if verdict_type == "fair":
                        st.success(summary)
                    elif verdict_type == "slightly_over":
                        st.warning(summary)
                    else:
                        # overcharged or suspiciously cheap
                        st.error(summary)

            except Exception as e:
                st.error(f"Could not evaluate the vendor quote: {e}")

# ---------------------------------------------------------------------------
# PDF Download — shown whenever an estimate exists in session_state
# ---------------------------------------------------------------------------
if st.session_state.get("last_estimate"):
    st.divider()
    st.subheader("📥 Download Your Proposal")
    try:
        _est  = st.session_state["last_estimate"]
        _expl = st.session_state.get("last_explanation", "See the numbers above for your solar estimate.")
        _mnt  = st.session_state.get("last_mount", {
            "structure_recommendation": "See estimate above.",
            "ip_rating": "IP65",
            "ip_reason": "Standard outdoor protection.",
        })
        _vc   = st.session_state.get("last_vendor_check", None)

        pdf_bytes = generate_proposal_pdf(_est, _expl, _mnt, _vc)
        st.download_button(
            label="⬇️ Download Proposal as PDF",
            data=pdf_bytes,
            file_name="solar_proposal.pdf",
            mime="application/pdf",
            key="pdf_download_btn",
        )
    except Exception as pdf_err:
        st.error(f"Could not generate PDF: {pdf_err}")
