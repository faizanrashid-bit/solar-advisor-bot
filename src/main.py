import base64
import json
import os
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()

SAMPLE_INPUT = {"monthly_units": 600, "city": "Islamabad"}

api_key = os.getenv("OPENAI_API_KEY")

if api_key:
    client = OpenAI(api_key=api_key)
    print("Scaffold ready. API key loaded.")
else:
    print("ERROR: OPENAI_API_KEY not found in .env")


# ---------------------------------------------------------------------------
# Bill image OCR
# ---------------------------------------------------------------------------

def extract_units_from_bill(image_path: str) -> dict:
    """Read a photo of a Pakistani electricity bill and extract monthly units consumed.

    Args:
        image_path: Absolute or relative path to the bill image (JPEG / PNG).

    Returns:
        dict with keys:
            units_found   (bool)        – True if a value was identified
            monthly_units (float|None)  – Units consumed, or None
            confidence    (str)         – 'high', 'medium', or 'low'
            raw_text_seen (str)         – Any units/consumption text seen on the bill
            error         (str)         – Present only on failure
    """
    try:
        with open(image_path, "rb") as f:
            encoded = base64.b64encode(f.read()).decode("utf-8")

        system_prompt = (
            "You are reading a photo of a Pakistani electricity bill (IESCO, LESCO, or similar DISCO). "
            "Look specifically for a row or field labeled 'Units Consumed' — this is usually found "
            "in a charges/billing table, NOT in the meter reading history table (which shows "
            "'Previous Reading' and 'Present Reading' separately). "
            "If you see a 'Bill Calculation' section with a rate multiplied by a units number "
            "(e.g. 'Rate x Units'), that units number should match your answer — use it to "
            "double check. "
            "Respond ONLY with a valid JSON object with exactly these keys: "
            "units_found (boolean), monthly_units (number or null), confidence (string: 'high','medium','low'), "
            "raw_text_seen (string, the exact label and number you found, e.g. 'Units Consumed: 536'). "
            "If multiple different unit-like numbers appear and you are not confident which is correct, "
            "set confidence to 'low' and still return your best guess. "
            "Return only the JSON. No markdown, no backticks, no extra text."
        )

        response = client.chat.completions.create(
            model="gpt-4o",
            response_format={"type": "json_object"},
            messages=[
                {"role": "system", "content": system_prompt},
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/jpeg;base64,{encoded}",
                            },
                        },
                        {
                            "type": "text",
                            "text": "Extract the monthly units consumed from this bill.",
                        },
                    ],
                },
            ],
        )

        return json.loads(response.choices[0].message.content)

    except Exception as e:
        return {
            "units_found": False,
            "monthly_units": None,
            "confidence": "low",
            "raw_text_seen": "",
            "error": str(e),
        }


# ---------------------------------------------------------------------------
# AI explanation
# ---------------------------------------------------------------------------

def get_explanation(estimate: dict) -> str:
    """Return a plain-language explanation of the solar estimate for a layperson.

    Args:
        estimate: The dict returned by get_full_estimate().

    Returns:
        A short, plain-text explanation string.
    """
    try:
        system_prompt = (
            "You are a friendly Pakistani solar advisor. Given a JSON object of solar "
            "sizing results, explain it in 3-4 short, plain-language sentences for "
            "someone with no technical background. Mention system size, monthly savings, "
            "and payback period in simple terms. No jargon, no markdown, just plain text."
        )
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": json.dumps(estimate)},
            ],
        )
        return response.choices[0].message.content.strip()
    except Exception:
        return "Could not generate explanation right now, but the numbers above are accurate."


if __name__ == "__main__":
    print("Bill photo reading function ready. Call extract_units_from_bill('path/to/image.jpg') to test.")
