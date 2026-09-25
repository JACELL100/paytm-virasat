# classify_txn_group (v1, task=fast)

Classify a recurring payment group into a financial product type and institution.

Output JSON: `{product_type, institution_slug, confidence, rationale}`

See `app/services/ai/classifier.py::classify_txn_group` for the live prompt text.
