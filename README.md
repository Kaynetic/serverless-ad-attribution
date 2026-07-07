# Serverless Ad Attribution & Marketing Forensics — Case Study

The attribution layer of a production legal-intake platform: every paid click — Google, YouTube, Meta, TikTok — is traced from the ad through a three-domain landing topology, into the intake chatbot, and back out to the ad platforms as **server-side conversion events**. Plus a forensic methodology for the day the leads stop coming.

> **About this repo.** Case study of a live client system; identifying details anonymized, code in [`excerpts/`](excerpts/) sanitized and representative. Production source is private. All rights reserved — see the [copyright notice](#copyright--permitted-use) below.

---

## The problem

The firm runs paid acquisition across four channels, landing on **three different domains** (each channel maps to its own landing property). Before this work:

- Meta optimization was starved: browser pixels alone under-report (ad blockers, iOS), and there was no server-side signal at all.
- The dashboard couldn't answer "which channel produced this signed case?" — most leads arrived with no usable attribution.
- When lead volume dropped, nobody could tell whether the code, the tracking, or the campaigns had broken.

## Server-side Meta Conversions API

Every qualified lead fires a CAPI event from the backend, built to Meta's matching spec:

- **Origin-routed pixel IDs.** The three landing domains belong to different pixel properties. The pixel ID is selected per event from a Secrets-Manager map keyed by the lead's landing origin, with a safe default — one codebase, N properties, no cross-domain contamination.
- **Browser + server dedup.** The widget-side pixel and the server event share an `event_id`, so Meta dedupes the pair instead of double-counting — the standard trap with hybrid pixel/CAPI setups.
- **Match-quality engineering.** User data is normalized *before* SHA-256 hashing — phone to E.164, state to its 2-letter code, email lowercased — plus `external_id`, client IP/UA, and `event_source_url`, lifting Meta's event-match quality and therefore optimization performance.
- **Verified, not assumed.** The most recent pipeline audit confirmed **100% CAPI delivery** (42/42 events accepted) over the audit window.

## Lead-source classification

A seven-bucket classifier stamps every lead at ingestion: Google, YouTube, Meta, TikTok, third-party lead vendor, CRM import, or direct/organic — from UTM parameters, landing origin, and ingestion path, with the **ad name** surfaced under each lead row in the operations dashboard so staff see *which creative* produced the person they're talking to.

Two honest lessons from production:

- **The classifier is only as good as the tagging.** A large share of paid traffic arrived with no UTM parameters at all, and one campaign shipped a literal `{adname}` template token instead of the rendered value. Both are campaign-configuration bugs — the fix was UTM-tagged URLs handed to the marketing side, not more code guessing.
- **A bucket with zero traffic is a finding.** The TikTok bucket exists and works; it read zero because the bio links were never tagged. The classifier's zeros located the gap.

## Marketing forensics: the day the leads stopped

Mid-year, paid leads abruptly stopped. The chatbot had just shipped a major update — so the update was the obvious suspect. We ran the investigation as a structured audit (parallel evidence tracks, then adversarial review of the conclusion) rather than a hunt for a comforting answer:

- Reconstructed the timeline from ingestion records: the drop aligned with the **quarterly ad-campaign rollover** on both Google and Meta — *days before* the widget update actually went live (which itself shipped three days later than planned; assumed dates were replaced with deployed-artifact evidence).
- Verified the pipeline end-to-end for the window: CAPI 42/42 accepted, intake alert emails 100% delivered, every CRM case in the window accounted for.
- Found the smoking gun in the client's own correspondence: the new quarter's ad had shipped with a **malformed website URL** (the bare UTM string, no destination).

Conclusion — with receipts: the code was exonerated; the campaign configuration was the cause. The write-up separated "what we verified" from "what we infer," and each claim was re-tested by adversarial review passes before it was reported to the client.

## What this demonstrates

- Ad-platform integration done to spec: CAPI matching, hybrid dedup, multi-property routing.
- Attribution as a data-engineering problem: normalize → hash → classify → surface where decisions happen.
- Blameless-but-rigorous forensics: evidence over vibes, especially when the evidence clears your own code — a conclusion that's only credible because the methodology was adversarial.

## Sanitized excerpts

| File | Pattern it demonstrates |
|---|---|
| [`excerpts/capi_event.py`](excerpts/capi_event.py) | Building a Meta CAPI event: normalization, hashing, origin-routed pixel, dedup `event_id` |

---

*Built by [Kamogelo Mahlasela](https://github.com/Kaynetic) and [Masego Letsoko](https://github.com/SegoML).*

## Copyright & permitted use

© 2026 Kamogelo Mahlasela and Masego Letsoko. **All rights reserved.**

This repository is published for **viewing only**, so prospective employers, clients, and collaborators can evaluate our work. **No license is granted.** Beyond viewing on GitHub (and the limited on-platform rights GitHub's Terms of Service provide), no part of this repository — text, architecture diagrams, or code excerpts — may be copied, reproduced, modified, distributed, or used to create derivative works without our prior written permission.
