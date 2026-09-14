import re
from typing import Any, Dict, List, Optional


def extract_currencies(text: str) -> List[Dict[str, Any]]:
    """
    Deterministic extraction of monetary amounts in INR, USD, and other currencies.
    Detects formats: ₹25,000, Rs. 50,000, INR 1,00,000, 5 Lakhs, 2 Crores, $500, USD 1,000.
    """
    currencies = []
    # Pattern 1: Symbol or Code followed by digits: ₹ 25,000 / Rs. 25,000 / INR 50,000
    p1 = re.compile(
        r'(?:(?P<curr>₹|Rs\.?|INR|USD|\$)\s*(?P<amount>[0-9]{1,3}(?:,[0-9]{2,3})*(?:\.[0-9]{1,2})?))',
        re.IGNORECASE
    )
    for m in p1.finditer(text):
        curr_symbol = m.group("curr")
        raw_amt = m.group("amount").replace(",", "")
        curr_code = "INR" if any(c in curr_symbol.upper() for c in ["₹", "RS", "INR"]) else "USD"
        try:
            val = float(raw_amt)
            currencies.append({
                "currency": curr_code,
                "amount": val,
                "raw_text": m.group(0),
                "start_char": m.start(),
                "end_char": m.end()
            })
        except ValueError:
            continue

    # Pattern 2: Indian verbal units: 5 Lakhs / 2.5 Crores
    p2 = re.compile(
        r'(?:(?P<curr>₹|Rs\.?|INR)?\s*(?P<num>[0-9]+(?:\.[0-9]+)?)\s*(?P<unit>lakhs?|lac|crores?|cr))\b',
        re.IGNORECASE
    )
    for m in p2.finditer(text):
        num = float(m.group("num"))
        unit = m.group("unit").lower()
        multiplier = 100_000 if "la" in unit else 10_000_000
        val = num * multiplier
        currencies.append({
            "currency": "INR",
            "amount": val,
            "raw_text": m.group(0),
            "start_char": m.start(),
            "end_char": m.end()
        })

    return currencies


def extract_percentages(text: str) -> List[Dict[str, Any]]:
    """
    Deterministic extraction of percentage rates and annual frequencies.
    Detects: 18%, 18 percent, 18% p.a., 12.5% per annum, 2% compounding.
    """
    percentages = []
    pattern = re.compile(
        r'(?P<num>[0-9]+(?:\.[0-9]+)?)\s*(?P<pct>%|percent|per\s+cent)(?:\s*(?P<freq>p\.a\.|per\s+annum|annual|compounding|monthly))?',
        re.IGNORECASE
    )
    for m in pattern.finditer(text):
        val = float(m.group("num"))
        freq = m.group("freq").strip() if m.group("freq") else "flat"
        percentages.append({
            "value": val,
            "frequency": freq,
            "raw_text": m.group(0),
            "start_char": m.start(),
            "end_char": m.end()
        })
    return percentages


def extract_durations(text: str) -> List[Dict[str, Any]]:
    """
    Deterministic extraction of time limits and contract terms.
    Detects: 30 days, 11 months, 3 years, 48 hours, 2 weeks.
    """
    durations = []
    pattern = re.compile(
        r'\b(?P<count>[0-9]+)\s*(?P<unit>days?|weeks?|months?|years?|hours?)\b',
        re.IGNORECASE
    )
    unit_multipliers = {
        "hour": 1 / 24, "hours": 1 / 24,
        "day": 1, "days": 1,
        "week": 7, "weeks": 7,
        "month": 30, "months": 30,
        "year": 365, "years": 365
    }
    for m in pattern.finditer(text):
        count = int(m.group("count"))
        unit = m.group("unit").lower()
        mult = unit_multipliers.get(unit, 1)
        durations.append({
            "count": count,
            "unit": unit,
            "days_equivalent": count * mult,
            "raw_text": m.group(0),
            "start_char": m.start(),
            "end_char": m.end()
        })
    return durations


def extract_dates(text: str) -> List[Dict[str, Any]]:
    """
    Deterministic extraction of explicit calendar dates and deadlines.
    Detects: 15th August 2024, 15/08/2024, 2024-08-15, August 15, 2024.
    """
    dates = []
    # Numeric dates: DD/MM/YYYY or YYYY-MM-DD
    p1 = re.compile(r'\b(?P<date>(?:[0-3]?[0-9][/-][0-1]?[0-9][/-][12][0-9]{3})|(?:[12][0-9]{3}-[0-1][0-9]-[0-3][0-9]))\b')
    for m in p1.finditer(text):
        dates.append({
            "date_string": m.group("date"),
            "format": "numeric",
            "raw_text": m.group(0),
            "start_char": m.start(),
            "end_char": m.end()
        })

    # Verbal dates: 15th August 2024 / August 15, 2024 / October 2, 2024
    months = r'(?:January|February|March|April|May|June|July|August|September|October|November|December)'
    
    # Format: Day Month Year (e.g. 15th August 2024, 2 October 2024)
    p2 = re.compile(
        rf'\b(?P<day>[0-3]?[0-9])(?:st|nd|rd|th)?\s+(?P<month>{months})\s+(?P<year>[12][0-9]{{3}})\b',
        re.IGNORECASE
    )
    for m in p2.finditer(text):
        dates.append({
            "date_string": f"{m.group('day')} {m.group('month')} {m.group('year')}",
            "format": "verbal",
            "raw_text": m.group(0),
            "start_char": m.start(),
            "end_char": m.end()
        })

    # Format: Month Day, Year (e.g. October 2, 2024 / August 15th, 2024)
    p3 = re.compile(
        rf'\b(?P<month>{months})\s+(?P<day>[0-3]?[0-9])(?:st|nd|rd|th)?(?:,)?\s+(?P<year>[12][0-9]{{3}})\b',
        re.IGNORECASE
    )
    for m in p3.finditer(text):
        dates.append({
            "date_string": f"{m.group('day')} {m.group('month')} {m.group('year')}",
            "format": "verbal",
            "raw_text": m.group(0),
            "start_char": m.start(),
            "end_char": m.end()
        })

    return dates



def extract_section_numbers(text: str) -> List[Dict[str, Any]]:
    """
    Deterministic extraction of section, clause, and article numbers.
    Detects: Section 4.1, Clause 12, Article II, Section 27.
    """
    sections = []
    pattern = re.compile(
        r'\b(?P<type>Section|Clause|Article|Schedule|Part)\s+(?P<num>[0-9]+(?:\.[0-9]+)*|[IVXLCDM]+|[A-Z])\b',
        re.IGNORECASE
    )
    for m in pattern.finditer(text):
        sections.append({
            "prefix": m.group("type").title(),
            "number": m.group("num"),
            "full_reference": f"{m.group('type').title()} {m.group('num')}",
            "start_char": m.start(),
            "end_char": m.end()
        })
    return sections


def extract_deterministic_facts(text: str) -> Dict[str, Any]:
    """
    Aggregate all 5 deterministic extractions into a single structured payload.
    These values are guaranteed to NEVER be silently overwritten by AI.
    """
    return {
        "currencies": extract_currencies(text),
        "percentages": extract_percentages(text),
        "durations": extract_durations(text),
        "dates": extract_dates(text),
        "sections": extract_section_numbers(text)
    }
