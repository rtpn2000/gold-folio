from datetime import datetime

import requests

from config import nebula_api_key, nebula_api_url, nebula_city


def _to_float(value):
    if value is None:
        return None
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str):
        cleaned = value.replace(",", "").replace("₹", "").strip()
        if not cleaned:
            return None
        try:
            return float(cleaned)
        except ValueError:
            return None
    return None


def _find_purity_block(payload, candidates=None):
    if candidates is None:
        candidates = ("24k", "24kt", "gold24k", "24carat")

    if isinstance(payload, dict):
        normalized_keys = {str(key).lower().replace(" ", ""): key for key in payload.keys()}
        for candidate in candidates:
            if candidate in normalized_keys:
                key = normalized_keys[candidate]
                value = payload[key]
                if isinstance(value, dict):
                    return value
                numeric = _to_float(value)
                if numeric is not None:
                    return {"per_gram": numeric}

        for value in payload.values():
            found = _find_purity_block(value, candidates=candidates)
            if found:
                return found

    if isinstance(payload, list):
        for item in payload:
            found = _find_purity_block(item, candidates=candidates)
            if found:
                return found

    return None


def _extract_per_gram(block):
    if not isinstance(block, dict):
        return None

    normalized_keys = {str(key).lower().replace(" ", "").replace("-", "").replace("/", ""): key for key in block.keys()}
    for candidate in (
        "pergram",
        "gram",
        "pricepergram",
        "pricegram",
        "onegram",
        "1g",
        "price_gram",
    ):
        if candidate in normalized_keys:
            value = block[normalized_keys[candidate]]
            numeric = _to_float(value)
            if numeric is not None:
                return numeric

    for value in block.values():
        numeric = _to_float(value)
        if numeric is not None:
            return numeric

    return None


def fetch_nebula_retail(city=nebula_city):
    if not nebula_api_key:
        raise ValueError("NEBULA_API_KEY is missing in .env")

    headers = {
        "Authorization": f"Bearer {nebula_api_key}",
    }
    params = {"city": city} if city else None
    response = requests.get(nebula_api_url, headers=headers, params=params, timeout=15)
    response.raise_for_status()
    data = response.json()

    payload = data.get("data", data)
    if isinstance(payload, dict) and payload.get("success") is False:
        raise ValueError(f"Nebula API returned no retail data for city '{city}'")

    prices = payload.get("prices", {}) if isinstance(payload, dict) else {}
    block_24k = None
    block_22k = None
    if isinstance(prices, dict):
        block_24k = prices.get("gold24k")
        block_22k = prices.get("gold22k")
    if block_24k is None:
        block_24k = _find_purity_block(payload, candidates=("24k", "24kt", "gold24k", "24carat"))
    if block_22k is None:
        block_22k = _find_purity_block(payload, candidates=("22k", "22kt", "gold22k", "22carat"))

    retail_24k = _extract_per_gram(block_24k)
    retail_22k = _extract_per_gram(block_22k)
    if retail_24k is None or retail_24k <= 0:
        raise ValueError("Nebula API response did not contain a 24K per-gram retail price")

    timestamp = None
    if isinstance(payload, dict):
        timestamp = payload.get("timestamp") or payload.get("updated_at") or payload.get("date")
    if timestamp is None:
        timestamp = datetime.utcnow().isoformat() + "Z"

    return {
        "city": payload.get("city", city) if isinstance(payload, dict) else city,
        "price_per_gram_inr_24k": round(retail_24k, 2),
        "price_per_gram_inr_22k": round(retail_22k, 2) if retail_22k and retail_22k > 0 else None,
        "source": "nebulaapi-retail",
        "timestamp": timestamp,
        "raw": data,
    }
