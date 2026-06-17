"""
solar_math.py
=============
Pure-Python solar sizing, cost and savings calculations.
No AI calls, no Streamlit, no UI dependencies.
"""

from math import ceil

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

PANEL_WATT = 585
PERFORMANCE_RATIO = 0.78
SELF_CONSUMPTION_RATIO = 0.50
BUYBACK_RATE = 11           # PKR/unit, net billing 2026
NEPRA_FEE_PER_KW = 1000    # PKR/kW

COST_PER_KW_TIERS = [
    (5,          140_000),
    (12,         120_000),
    (float("inf"), 105_000),
]

CITY_PEAK_SUN_HOURS = {
    "Quetta":      5.8,
    "Multan":      5.4,
    "Hyderabad":   5.5,
    "Sukkur":      5.5,
    "Karachi":     5.3,
    "D.I. Khan":   5.2,
    "Bahawalpur":  5.4,
    "Faisalabad":  5.0,
    "Peshawar":    5.0,
    "Islamabad":   4.9,
    "Rawalpindi":  4.9,
    "Lahore":      4.8,
}
DEFAULT_PEAK_SUN_HOURS = 5.0

# IESCO A-1 Residential, SRO 279(I)/2026, unprotected slabs, energy charge only
IESCO_UNPROTECTED_SLABS = [
    (100,          22.44),
    (200,          28.91),
    (300,          33.10),
    (400,          36.46),
    (500,          38.95),
    (600,          40.22),
    (700,          41.85),
    (float("inf"), 47.20),
]

TOU_OFFPEAK_RATE = 34.53   # for sanctioned load >= 5 kW, no battery
TOU_PEAK_RATE   = 46.85

DEFAULT_IMPORT_RATE_SLAB          = 52    # all-in PKR/unit after FPA + GST + duties
DEFAULT_IMPORT_RATE_TOU_OFFPEAK   = 45


# ---------------------------------------------------------------------------
# Helper / lookup functions
# ---------------------------------------------------------------------------

def get_peak_sun_hours(city: str) -> float:
    """Return peak sun hours for *city* (case-insensitive).

    Falls back to DEFAULT_PEAK_SUN_HOURS if the city is not in the lookup.
    """
    city_lower = city.strip().lower()
    for name, psh in CITY_PEAK_SUN_HOURS.items():
        if name.lower() == city_lower:
            return psh
    return DEFAULT_PEAK_SUN_HOURS


def get_cost_per_kw(system_kw: float) -> int:
    """Return the applicable cost-per-kW rate for *system_kw* from COST_PER_KW_TIERS."""
    for threshold, rate in COST_PER_KW_TIERS:
        if system_kw <= threshold:
            return rate
    # Should never reach here given float("inf") tier, but be safe
    return COST_PER_KW_TIERS[-1][1]


def get_marginal_slab_rate(monthly_units: float) -> float:
    """Return the per-unit energy charge (PKR) for the slab *monthly_units* falls into.

    Uses the slab's own rate (not blended/cumulative).
    Based on IESCO A-1 Residential unprotected slabs, SRO 279(I)/2026.
    """
    for upper_limit, rate in IESCO_UNPROTECTED_SLABS:
        if monthly_units <= upper_limit:
            return rate
    # Fallback to last slab (float("inf") slab covers all remaining)
    return IESCO_UNPROTECTED_SLABS[-1][1]


# ---------------------------------------------------------------------------
# Core calculation functions
# ---------------------------------------------------------------------------

def calculate_system_size(monthly_units: float, city: str) -> dict:
    """Determine the recommended solar system size.

    Args:
        monthly_units: Average monthly electricity consumption in kWh.
        city:          City name for peak-sun-hours lookup.

    Returns:
        dict with keys:
            daily_kwh        – average daily consumption (kWh)
            peak_sun_hours   – peak sun hours for the city
            system_kw        – recommended system size in kW (2 dp)
            num_panels       – number of panels (ceiled integer)
    """
    daily_kwh  = monthly_units / 30
    psh        = get_peak_sun_hours(city)
    system_kw  = daily_kwh / (psh * PERFORMANCE_RATIO)
    num_panels = ceil(system_kw * 1000 / PANEL_WATT)

    return {
        "daily_kwh":      daily_kwh,
        "peak_sun_hours": psh,
        "system_kw":      round(system_kw, 2),
        "num_panels":     num_panels,
    }


def calculate_cost(system_kw: float) -> dict:
    """Calculate total system cost including NEPRA registration fee.

    Args:
        system_kw: System size in kW.

    Returns:
        dict with keys:
            cost_per_kw      – applicable tier rate (PKR/kW)
            system_cost_pkr  – total cost rounded to nearest int
    """
    cost_per_kw     = get_cost_per_kw(system_kw)
    system_cost_pkr = system_kw * cost_per_kw + system_kw * NEPRA_FEE_PER_KW

    return {
        "cost_per_kw":     cost_per_kw,
        "system_cost_pkr": round(system_cost_pkr),
    }


def calculate_savings(
    system_kw: float,
    city: str,
    monthly_units: float,
    is_tou: bool = False,
) -> dict:
    """Estimate monthly bill savings from a solar installation.

    Args:
        system_kw:     System size in kW.
        city:          City name for peak-sun-hours lookup.
        monthly_units: Monthly consumption used to select import rate.
        is_tou:        True if the consumer is on a Time-of-Use tariff.

    Returns:
        dict with keys:
            monthly_generation_units – total monthly solar generation (kWh)
            import_rate_used         – PKR/unit rate applied for self-consumption
            self_consumed_units      – units consumed on-site (kWh)
            exported_units           – units exported to grid (kWh)
            monthly_savings_pkr      – estimated monthly bill saving (nearest int)
    """
    psh = get_peak_sun_hours(city)

    monthly_generation_units = system_kw * psh * 30 * PERFORMANCE_RATIO

    import_rate = DEFAULT_IMPORT_RATE_TOU_OFFPEAK if is_tou else DEFAULT_IMPORT_RATE_SLAB

    self_consumed_units = monthly_generation_units * SELF_CONSUMPTION_RATIO
    exported_units      = monthly_generation_units * (1 - SELF_CONSUMPTION_RATIO)

    monthly_savings_pkr = (
        self_consumed_units * import_rate
        + exported_units * BUYBACK_RATE
    )

    return {
        "monthly_generation_units": round(monthly_generation_units, 2),
        "import_rate_used":         round(import_rate, 2),
        "self_consumed_units":      round(self_consumed_units, 2),
        "exported_units":           round(exported_units, 2),
        "monthly_savings_pkr":      round(monthly_savings_pkr),
    }


def calculate_payback(system_cost_pkr: float, monthly_savings_pkr: float):
    """Return simple payback period in years.

    Args:
        system_cost_pkr:    Total upfront cost (PKR).
        monthly_savings_pkr: Average monthly saving (PKR).

    Returns:
        Payback in years (float, 2 dp), or None if monthly_savings_pkr is zero.
    """
    if not monthly_savings_pkr:
        return None
    return round(system_cost_pkr / (monthly_savings_pkr * 12), 2)


def get_full_estimate(monthly_units: float, city: str, is_tou: bool = False) -> dict:
    """Run the full solar estimation pipeline and return a single combined dict.

    Args:
        monthly_units: Average monthly electricity consumption in kWh.
        city:          City name.
        is_tou:        True if consumer is on TOU tariff.

    Returns:
        Combined dict with every field from calculate_system_size,
        calculate_cost, calculate_savings, plus "payback_years".
    """
    size_info    = calculate_system_size(monthly_units, city)
    cost_info    = calculate_cost(size_info["system_kw"])
    savings_info = calculate_savings(
        size_info["system_kw"], city, monthly_units, is_tou
    )
    payback_years = calculate_payback(
        cost_info["system_cost_pkr"], savings_info["monthly_savings_pkr"]
    )

    return {
        **size_info,
        **cost_info,
        **savings_info,
        "payback_years": payback_years,
    }


# ---------------------------------------------------------------------------
# Mounting & protection lookups
# ---------------------------------------------------------------------------

ROOF_STRUCTURE = {
    "RCC / Concrete flat roof": (
        "Galvanized iron (GI) elevated MS structure on chemical-anchored bases, "
        "tilted ~30 degrees facing south for best year-round output."
    ),
    "Metal / tin sheet roof": (
        "Aluminium mounting rails clamped to roof purlins using L-feet or "
        "standing-seam clamps, minimizing roof penetration to avoid leaks."
    ),
    "Ground mount": (
        "GI ground-mount frame on concrete foundation footings, "
        "tilted ~30 degrees facing south."
    ),
}

IP_RATING = {
    "Indoor (garage, utility room, covered area)": (
        "IP21",
        "Indoor, dry and dust-protected. Suitable for an inverter mounted inside "
        "a clean, covered space away from rain and direct sun.",
    ),
    "Outdoor (exposed wall or rooftop)": (
        "IP65",
        "Dust-tight and protected against water jets. Required when the inverter "
        "is exposed to rain, dust, and direct sunlight.",
    ),
    "Outdoor in coastal or high-dust area": (
        "IP66",
        "Higher protection against heavy dust and strong water exposure. "
        "Recommended near the coast or in very dusty industrial areas.",
    ),
}


def get_mounting_recommendation(roof_type: str, inverter_location: str) -> dict:
    """Return mounting structure and inverter IP-rating recommendation.

    Args:
        roof_type:         One of the keys in ROOF_STRUCTURE.
        inverter_location: One of the keys in IP_RATING.

    Returns:
        dict with keys: roof_type, structure_recommendation, ip_rating, ip_reason.
    """
    structure = ROOF_STRUCTURE.get(roof_type, ROOF_STRUCTURE["RCC / Concrete flat roof"])
    ip_code, ip_reason = IP_RATING.get(
        inverter_location, IP_RATING["Outdoor (exposed wall or rooftop)"]
    )
    return {
        "roof_type": roof_type,
        "structure_recommendation": structure,
        "ip_rating": ip_code,
        "ip_reason": ip_reason,
    }


# ---------------------------------------------------------------------------
# Appliance-based usage estimator
# ---------------------------------------------------------------------------

APPLIANCE_WATTAGE = {
    "Ceiling fan":               {"watts": 80,   "default_hours": 12},
    "LED bulb":                  {"watts": 12,   "default_hours": 6},
    "Energy saver / tube light": {"watts": 25,   "default_hours": 6},
    "LED TV":                    {"watts": 80,   "default_hours": 5},
    "Refrigerator (medium)":     {"watts": 200,  "default_hours": 8},
    "Deep freezer":              {"watts": 250,  "default_hours": 8},
    "AC 1 ton (non-inverter)":   {"watts": 1200, "default_hours": 8},
    "AC 1.5 ton (non-inverter)": {"watts": 1800, "default_hours": 8},
    "Inverter AC 1 ton":         {"watts": 900,  "default_hours": 8},
    "Inverter AC 1.5 ton":       {"watts": 1400, "default_hours": 8},
    "Washing machine":           {"watts": 500,  "default_hours": 1},
    "Water pump 0.5 hp":         {"watts": 375,  "default_hours": 1},
    "Water pump 1 hp":           {"watts": 750,  "default_hours": 1},
    "Iron":                      {"watts": 1000, "default_hours": 0.5},
    "Microwave oven":            {"watts": 1000, "default_hours": 0.3},
    "Electric geyser":           {"watts": 2000, "default_hours": 1},
    "Desktop computer":          {"watts": 200,  "default_hours": 4},
    "Laptop":                    {"watts": 65,   "default_hours": 4},
    "Water dispenser":           {"watts": 100,  "default_hours": 12},
}


def calculate_units_from_appliances(items: list) -> dict:
    """Estimate monthly units from a list of appliances.

    Args:
        items: list of dicts, each with keys:
               name (str), watts (float), quantity (int), hours_per_day (float)

    Returns:
        dict with keys:
            monthly_units  – rounded integer (units/month)
            daily_kwh      – total daily consumption (kWh)
            breakdown      – list of per-appliance dicts
    """
    total_daily_kwh = 0.0
    breakdown = []
    for it in items:
        daily_kwh = (it["watts"] * it["quantity"] * it["hours_per_day"]) / 1000
        total_daily_kwh += daily_kwh
        breakdown.append({
            "name":         it["name"],
            "quantity":     it["quantity"],
            "watts":        it["watts"],
            "hours_per_day": it["hours_per_day"],
            "daily_kwh":   round(daily_kwh, 2),
        })
    return {
        "monthly_units": round(total_daily_kwh * 30),
        "daily_kwh":     round(total_daily_kwh, 2),
        "breakdown":     breakdown,
    }


# ---------------------------------------------------------------------------
# Quick self-test
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    result = get_full_estimate(600, "Islamabad")
    import json
    print(json.dumps(result, indent=2))
