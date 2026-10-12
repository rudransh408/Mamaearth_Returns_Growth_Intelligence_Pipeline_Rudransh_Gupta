import json
import os
from pathlib import Path

from google import genai
from google.genai import types


# Resolve file paths relative to this script.
BASE_DIR = Path(__file__).resolve().parent
FINDINGS_PATH = BASE_DIR / "findings.json"
SAMPLE_OUTPUT_PATH = BASE_DIR / "sample_output.txt"


def load_findings():
    """Load verified findings from findings.json."""
    with open(FINDINGS_PATH, "r", encoding="utf-8") as file:
        return json.load(file)


def generate_scr_narrative_offline(findings: dict) -> dict:
    """
    Generate a deterministic Situation-Complication-Resolution narrative.
    Works without an API key, internet access, or API expenditure.
    """

    revenue = findings["cleaned_total_revenue_inr"]
    raw_revenue = findings["raw_total_revenue_inr"]
    duplicate_delta = findings["duplicate_reconciliation_delta_inr"]

    payment_rates = findings["return_rate_by_payment"]
    risk = findings["highest_risk_segment"]
    peak = findings["true_peak_month"]
    inflated = findings["outlier_inflated_month"]

    peak_month = peak["month"]
    peak_month_name = "March" if peak_month.endswith("-03") else peak_month

    narrative = f"""
SITUATION

Mamaearth's cleaned order data records total revenue of ₹{revenue:,.2f},
compared with raw revenue of ₹{raw_revenue:,.2f}. After removing duplicate
orders and treating missing values, the cleaned dataset provides a more
reliable basis for operational and financial analysis. The outlier-corrected
monthly revenue series identifies {peak_month_name} as the peak month,
with revenue of ₹{peak["revenue_inr"]:,.2f}.

COMPLICATION

Return rates differ considerably by payment method. Cash on Delivery (COD)
has a return rate of {payment_rates["COD"]:.1f}%, compared with
{payment_rates["UPI"]:.1f}% for UPI and {payment_rates["CARD"]:.1f}% for CARD.
The highest-risk segment is COD in Tier-{risk["city_tier"]} cities, with a
return rate of {risk["return_rate_pct"]:.1f}%.

The difference between raw and cleaned revenue is ₹{duplicate_delta:,.2f}.
This difference is attributable to the five duplicate orders removed during
cleaning, rather than discount or rating imputation. January's apparent
revenue was ₹{inflated["apparent_revenue_inr"]:,.2f}; after excluding the
two bulk-order outliers, January revenue is ₹{inflated["corrected_revenue_inr"]:,.2f}.
This shows how unusual orders can distort monthly performance comparisons.

RESOLUTION

Prioritize COD order verification and delivery confirmation, particularly
in Tier-{risk["city_tier"]} cities. Investigate the operational reasons
behind COD returns before changing payment policies.

Use cleaned revenue of ₹{revenue:,.2f} for reconciled reporting. Retain
outlier flags so unusual bulk orders can be investigated instead of silently
deleted. For monthly performance comparisons, use the corrected peak in
{peak_month_name}, at ₹{peak["revenue_inr"]:,.2f}. These actions focus
attention on the highest-risk segment while preserving an auditable
data-cleaning process.
""".strip()

    return {
        "status": "success",
        "narrative": narrative,
        "tokens": None
    }


def check_numeric_accuracy(narrative: str) -> bool:
    """
    Check the five required numerical facts.
    Commas are removed before checking financial figures.
    """

    normalized = narrative.replace(",", "")
    normalized_lower = normalized.lower()

    checks = {
        "Cleaned revenue: 97,358.30": (
            "97358.30" in normalized
            or "97358.3" in normalized
        ),

        "COD return rate: 44.4%": (
            "44.4" in normalized
        ),

        "COD + Tier-2 return rate: 54.5%": (
            "54.5" in normalized
        ),

        "Duplicate reconciliation delta: 2,501.90": (
            "2501.90" in normalized
            or "2501.9" in normalized
        ),

        "March peak revenue: 20,318.90": (
            "march" in normalized_lower
            and (
                "20318.90" in normalized
                or "20318.9" in normalized
            )
        )
    }

    all_passed = True

    for description, passed in checks.items():
        if passed:
            print(f"PASS: {description}")
        else:
            print(f"FAIL: {description}")
            all_passed = False

    return all_passed


def generate_scr_narrative(findings: dict) -> dict:
    """
    Generate the narrative with Gemini.
    If no API key exists or the request fails, use the offline fallback.
    """

    api_key = os.getenv("GEMINI_API_KEY")

    # The offline path requires no API key or network connection.
    if not api_key:
        print("No GEMINI_API_KEY configured.")
        print("Generating narrative using the offline fallback.")

        return generate_scr_narrative_offline(findings)

    system_instruction = """
You are a senior data analyst writing for Mamaearth's regional operations
and finance heads.

Write a business narrative using exactly three labeled sections:
Situation, Complication, and Resolution.

Every number in your response must come from the supplied findings and
retain the same numerical value. Do not invent statistics, counts,
percentages, dates, financial figures, or other numerical claims.

Explain the business implications and recommend practical actions based
only on the supplied findings.
"""

    # Build the prompt dynamically from the supplied findings.
    user_prompt = f"""
Write a business narrative for Mamaearth's regional ops and finance heads.

Use exactly three sections:
SITUATION
COMPLICATION
RESOLUTION

Include all these verified numerical facts exactly:
1. Cleaned total revenue: INR {findings['cleaned_total_revenue_inr']:,.2f}
2. COD return rate: {findings['return_rate_by_payment']['COD']}%
3. COD + Tier-2 return rate: {findings['highest_risk_segment']['return_rate_pct']}%
4. Duplicate reconciliation difference: INR {findings['duplicate_reconciliation_delta_inr']:,.2f}
5. True peak month: {findings['true_peak_month']['month']},
   revenue INR {findings['true_peak_month']['revenue_inr']:,.2f}

Do not omit, alter, or round these numbers.
Explain the business implications and recommend practical actions.
Use only the supplied findings. Do not invent statistics.
Return only the three-section narrative.

Verified findings:
{json.dumps(findings, indent=2, ensure_ascii=False)}
"""
    

    try:
        client = genai.Client(api_key=api_key)

        response = client.models.generate_content(
            model=os.getenv("GEMINI_MODEL", "gemini-3.5-flash"),
            contents=user_prompt,
            config=types.GenerateContentConfig(
                system_instruction=system_instruction,

                # Temperature zero is suitable for a factual business report.
                temperature=0.0,

                # Explicit token limit for the three-section narrative.
                max_output_tokens=800,

                # Request timeout: 30 seconds.
                http_options=types.HttpOptions(timeout=30000)
            )
        )

        narrative = response.text or ""

        if not narrative.strip():
            raise ValueError("Gemini returned an empty narrative.")

        usage = getattr(response, "usage_metadata", None)
        token_count = (
            getattr(usage, "total_token_count", None)
            if usage is not None
            else None
        )

        return {
            "status": "success",
            "narrative": narrative,
            "tokens": token_count
        }

    except Exception as err:
        print(f"Gemini API request failed: {err}")
        print("Falling back to offline narrative generation.")

        return {
            "status": "error",
            "narrative": None,
            "message": str(err)
        }
def main():
    """Run the complete narrative generation and validation process."""

    findings = load_findings()

    # Try Gemini first.
    result = generate_scr_narrative(findings)

    # If the API request fails, use the offline narrative.
    if result["status"] != "success":
        print("Gemini API failed. Using offline narrative.")
        result = generate_scr_narrative_offline(findings)

    narrative = result["narrative"]

    # Validate numerical accuracy.
    if not check_numeric_accuracy(narrative):
        print("Numeric validation failed. Using offline narrative.")
        result = generate_scr_narrative_offline(findings)
        narrative = result["narrative"]

    print("\n" + "=" * 65)
    print("MAMAEARTH — SCR BUSINESS NARRATIVE")
    print("=" * 65)
    print(narrative)

    print("\n" + "=" * 65)
    print("NUMERIC ACCURACY CHECK")
    print("=" * 65)

    if not check_numeric_accuracy(narrative):
        raise ValueError(
            "Numeric accuracy validation failed. Review the narrative."
        )

    SAMPLE_OUTPUT_PATH.write_text(
        narrative + "\n",
        encoding="utf-8"
    )

    print("\nAll required numerical checks passed.")
    print(f"Sample output saved to: {SAMPLE_OUTPUT_PATH}")
    print(f"Generation status: {result['status']}")


if __name__ == "__main__":
    main()
