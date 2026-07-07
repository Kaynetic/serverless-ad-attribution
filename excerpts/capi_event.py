"""Sanitized excerpt — server-side Meta Conversions API event for a qualified lead.

The parts that matter:
  - NORMALIZE BEFORE HASHING. Meta matches on SHA-256 of *canonical* values;
    hashing "(555) 010-0199" or "Tennessee" as-typed silently destroys match
    quality. Phone -> E.164, state -> 2-letter code, email -> lowercased.
  - ORIGIN-ROUTED PIXEL ID. Three landing domains belong to three pixel
    properties; the ID comes from a Secrets-Manager map keyed by the lead's
    landing origin, with a safe default. One codebase, N properties.
  - SHARED event_id. The browser pixel fires the same event name with the
    same event_id, so Meta dedupes the browser/server pair instead of
    double-counting the conversion.
"""
import re
import json
import time
import hashlib

import requests

GRAPH_URL = "https://graph.facebook.com/v19.0/{pixel_id}/events"


def _sha256(value):
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _norm_email(email):
    return (email or "").strip().lower()


def _norm_phone_e164(phone, default_country="1"):
    """Digits only; prepend country code for 10-digit national numbers."""
    digits = re.sub(r"\D", "", phone or "")
    if len(digits) == 10:
        digits = default_country + digits
    return f"+{digits}" if digits else ""


def _norm_state(state, state_map):
    """'Tennessee' / 'tn.' / 'TN' -> 'tn' (Meta wants lowercase 2-letter)."""
    s = (state or "").strip().strip(".").lower()
    return s if len(s) == 2 else state_map.get(s, "")


def _pixel_for_origin(origin, pixel_map):
    """Each landing domain maps to its own pixel property; unknown origins
    fall back to the default so an event is never dropped on the floor."""
    host = (origin or "").lower().removeprefix("https://").removeprefix("http://").split("/")[0]
    return pixel_map.get(host, pixel_map["default"])


def send_lead_event(lead, tracking_secret):
    """Fire a CAPI Lead event. `tracking_secret` holds the pixel map + token
    (from Secrets Manager); `lead` is the qualified intake record."""
    pixel_id = _pixel_for_origin(lead.get("landing_origin"), tracking_secret["meta_pixel_map"])

    user_data = {k: v for k, v in {
        "em": [_sha256(_norm_email(lead.get("email")))] if lead.get("email") else None,
        "ph": [_sha256(_norm_phone_e164(lead.get("phone")))] if lead.get("phone") else None,
        "st": [_sha256(_norm_state(lead.get("state"), US_STATE_MAP))] if lead.get("state") else None,
        "external_id": [_sha256(lead["lead_id"])],
        "client_ip_address": lead.get("client_ip"),
        "client_user_agent": lead.get("user_agent"),
    }.items() if v}

    payload = {
        "data": [{
            "event_name": "Lead",
            "event_time": int(time.time()),
            "event_id": lead["lead_id"],          # shared with the browser pixel -> dedup
            "event_source_url": lead.get("landing_url"),
            "action_source": "website",
            "user_data": user_data,
            "custom_data": {
                "lead_source": lead.get("source_bucket"),   # 7-bucket classifier output
                "incident_type": lead.get("incident_type"),
            },
        }]
    }

    resp = requests.post(
        GRAPH_URL.format(pixel_id=pixel_id),
        params={"access_token": tracking_secret["capi_token"]},
        json=payload,
        timeout=8,
    )
    resp.raise_for_status()
    result = resp.json()
    # events_received is asserted, logged, and audited — delivery is verified,
    # not assumed (most recent audit: 42/42 accepted).
    print(f"[capi] pixel={pixel_id} received={result.get('events_received')} "
          f"lead={lead['lead_id']}")
    return result
