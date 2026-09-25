# escalation_letter (v1, task=extract)

Formal English letter using facts from `claim_events`, addressed per the
escalation ladder (insurer GRO -> IRDAI Bima Bharosa -> Ombudsman; RBI CMS
for banks; SEBI SCORES for mutual funds). See
`app/services/pdf/claim_pack.py` and `app/api/v1/claims.py::draft_escalation`.
