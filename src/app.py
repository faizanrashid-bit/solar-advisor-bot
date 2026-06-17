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
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');

    html, body, [class*="css"] {
        font-family: 'Inter', sans-serif;
    }

    /* ── Page background ── */
    .stApp {
        background: linear-gradient(135deg, #0d1117 0%, #111827 60%, #0f1f12 100%);
        min-height: 100vh;
    }

    /* ── Hero header ── */
    .hero-title {
        font-size: 2.6rem;
        font-weight: 700;
        background: linear-gradient(90deg, #facc15, #fb923c, #f97316);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        background-clip: text;
        text-align: center;
        margin-bottom: 0.25rem;
        letter-spacing: -0.5px;
    }
    .hero-caption {
        text-align: center;
        color: #6b7280;
        font-size: 0.95rem;
        margin-bottom: 2rem;
        font-style: italic;
    }

    /* ── Card wrapper ── */
    .card {
        background: rgba(255, 255, 255, 0.04);
        border: 1px solid rgba(255, 255, 255, 0.08);
        border-radius: 16px;
        padding: 1.5rem 1.75rem;
        margin-bottom: 1.25rem;
        backdrop-filter: blur(8px);
    }
    .card-title {
        font-size: 0.75rem;
        font-weight: 600;
        text-transform: uppercase;
        letter-spacing: 1px;
        color: #9ca3af;
        margin-bottom: 1rem;
    }

    /* ── Metric overrides ── */
    [data-testid="metric-container"] {
        background: rgba(250, 204, 21, 0.06);
        border: 1px solid rgba(250, 204, 21, 0.15);
        border-radius: 12px;
        padding: 1rem 1.25rem !important;
        transition: transform 0.2s ease, box-shadow 0.2s ease;
    }
    [data-testid="metric-container"]:hover {
        transform: translateY(-2px);
        box-shadow: 0 8px 24px rgba(250, 204, 21, 0.12);
    }
    [data-testid="stMetricValue"] {
        color: #facc15 !important;
        font-weight: 700 !important;
    }
    [data-testid="stMetricLabel"] {
        color: #9ca3af !important;
        font-size: 0.82rem !important;
    }

    /* ── Button ── */
    div.stButton > button {
        width: 100%;
        background: linear-gradient(90deg, #f97316, #facc15);
        color: #0d1117;
        font-weight: 700;
        font-size: 1.05rem;
        border: none;
        border-radius: 10px;
        padding: 0.75rem 1.5rem;
        cursor: pointer;
        transition: opacity 0.2s ease, transform 0.15s ease;
        margin-top: 0.5rem;
    }
    div.stButton > button:hover {
        opacity: 0.9;
        transform: translateY(-1px);
    }

    /* ── Inputs ── */
    .stNumberInput input, .stSelectbox > div > div {
        background: rgba(255,255,255,0.05) !important;
        border: 1px solid rgba(255,255,255,0.12) !important;
        border-radius: 8px !important;
        color: #f3f4f6 !important;
    }

    /* ── Info box ── */
    .stInfo {
        background: rgba(59, 130, 246, 0.08) !important;
        border-left: 3px solid #3b82f6 !important;
        border-radius: 8px !important;
    }

    /* ── Divider ── */
    hr { border-color: rgba(255,255,255,0.07); }

    /* ── File uploader ── */
    [data-testid="stFileUploadDropzone"] {
        background: rgba(255,255,255,0.03) !important;
        border: 2px dashed rgba(250,204,21,0.25) !important;
        border-radius: 12px !important;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

# ---------------------------------------------------------------------------
# Hero header
# ---------------------------------------------------------------------------
st.markdown('<div class="hero-title">☀️ Solar Advisor Bot</div>', unsafe_allow_html=True)
st.markdown(
    '<div class="hero-caption">Real math, honest numbers. No hallucinated savings.</div>',
    unsafe_allow_html=True,
)

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

input_mode = st.radio(
    "How do you want to enter your usage?",
    ["I know my monthly units", "Help me estimate from appliances"],
    key="input_mode_radio",
    horizontal=True,
)

if input_mode == "I know my monthly units":
    col_left, col_right = st.columns([1, 1], gap="medium")
    with col_left:
        default_units = int(st.session_state["units_override"]) if st.session_state["units_override"] else 300
        monthly_units = st.number_input(
            "Monthly electricity usage (units / kWh)",
            min_value=1,
            max_value=10_000,
            value=default_units,
            step=10,
            help="Check your last bill — look for 'Units Consumed' or 'kWh'.",
            key="units_input",
        )
    with col_right:
        city = st.selectbox(
            "Your city",
            options=city_list,
            index=city_list.index("Islamabad"),
            key="city_input",
        )

else:  # appliance mode
    city = st.selectbox(
        "Your city",
        options=city_list,
        index=city_list.index("Islamabad"),
        key="city_input",
    )
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
                    st.markdown(f"**{appliance}** &nbsp; <span style='color:#9ca3af;font-size:0.85rem'>({defaults['watts']} W)</span>", unsafe_allow_html=True)
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
            monthly_units = max(1, appl_result["monthly_units"])
            st.info(f"⚡ Estimated monthly usage: **{monthly_units} units** ({appl_result['daily_kwh']} kWh/day)")

            with st.expander("See appliance breakdown"):
                for row in appl_result["breakdown"]:
                    st.write(
                        f"- **{row['name']}** × {row['quantity']} "
                        f"@ {row['hours_per_day']} h/day = {row['daily_kwh']} kWh/day"
                    )
        else:
            monthly_units = 300
            st.caption("Select appliances above — quantities and hours will appear here.")
    except Exception as appl_err:
        st.error(f"Appliance estimator error: {appl_err}")
        monthly_units = 300

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

# ---------------------------------------------------------------------------
# Optional bill photo upload
# ---------------------------------------------------------------------------
st.markdown('<div class="card"><div class="card-title">📄 Or Upload Your Bill Photo (Optional)</div>', unsafe_allow_html=True)

uploaded_file = st.file_uploader(
    "Upload a photo of your electricity bill (JPEG or PNG)",
    type=["jpg", "jpeg", "png"],
    label_visibility="collapsed",
    key="bill_upload",
)

if uploaded_file is not None:
    with st.spinner("Reading your bill photo…"):
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
                    f"📋 Detected **{detected:.0f} units** "
                    f"(confidence: {confidence}).  \n"
                    f"Raw text seen: *\"{raw}\"*"
                )

                btn_col1, btn_col2 = st.columns(2, gap="small")
                with btn_col1:
                    if st.button("✅ Use This Number", key="ocr_accept_btn"):
                        st.session_state["units_override"] = detected
                        st.success(f"Units updated to {detected:.0f}")
                with btn_col2:
                    if st.button("✏️ Enter Manually Instead", key="ocr_reject_btn"):
                        st.info("No problem, type the correct units in the field above.")
            else:
                err = ocr_result.get("error", "")
                raw = ocr_result.get("raw_text_seen", "")
                st.warning(
                    f"⚠️ Could not clearly read units from the bill image. "
                    f"Raw text seen: *\"{raw}\"*{(chr(10) + 'Error: ' + err) if err else ''}  \n"
                    "Please enter your units manually above."
                )
        except Exception as e:
            st.error(f"Error processing uploaded image: {e}")

st.markdown("</div>", unsafe_allow_html=True)

# ---------------------------------------------------------------------------
# Estimate button
# ---------------------------------------------------------------------------
run_estimate = st.button("⚡ Get My Solar Estimate", key="run_btn")

# ---------------------------------------------------------------------------
# Results
# ---------------------------------------------------------------------------
if run_estimate:
    try:
        with st.spinner("Crunching the numbers…"):
            estimate = get_full_estimate(monthly_units, city, is_tou)
        st.session_state["last_estimate"] = estimate

        st.markdown("---")
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

        # ── AI explanation ──
        with st.spinner("Writing your explanation…"):
            explanation = get_explanation(estimate)

        st.info(f"💡 {explanation}")

        # ── Mounting & protection recommendation ──
        st.markdown("---")
        st.subheader("🔩 Recommended mounting & protection")
        try:
            mount = get_mounting_recommendation(roof_type, inverter_location)
            st.markdown(
                f"**Mounting structure:**  \n{mount['structure_recommendation']}"
            )
            st.markdown(
                f"**Inverter protection rating:** **{mount['ip_rating']}**  \n"
                f"{mount['ip_reason']}"
            )
        except Exception as mount_err:
            st.error(f"Could not load mounting recommendation: {mount_err}")

    except Exception as e:
        st.error(f"Something went wrong while calculating your estimate: {e}")

# ---------------------------------------------------------------------------
# Vendor quote checker — only shown after an estimate exists
# ---------------------------------------------------------------------------
if st.session_state.get("last_estimate"):
    st.markdown("---")
    st.subheader("🔍 Got a quote from a vendor? Check if it's fair.")

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
