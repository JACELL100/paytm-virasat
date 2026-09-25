# extract_death_certificate (v1, task=vision -> OCR + extract)

Extract `{deceased_name, date_of_death, place, registration_no, issuing_authority, confidence}`.
See `app/schemas/documents.py::DeathCertificateExtraction` and
`app/services/ai/extractor.py::extract_death_certificate`.
