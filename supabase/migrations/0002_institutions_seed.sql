-- =============================================================================
-- Paytm Virasat — 0002_institutions_seed.sql
--
-- Seeds the `institutions` knowledge base per Implementation_Plan.md section
-- 12.6: ~20 real Indian institutions across life insurance, health insurance,
-- banking, mutual-fund registrars, EPFO, NPS, a lender, and Paytm Money.
--
-- *** IMPORTANT ***
-- Contact emails, grievance emails, portal URLs and SLA days below are
-- PLAUSIBLE PLACEHOLDERS built from each institution's publicly-known claim
-- desk / corporate domain naming conventions (e.g. `claims@hdfclife.com`).
-- They are NOT guaranteed to be the live, current addresses. Per the
-- Implementation Plan ("Verify SLAs and document lists against official
-- sites before the demo."), RE-VERIFY every claim_email, grievance_email,
-- portal_url and sla_days value against each institution's official website
-- before relying on them in a live demo or any real claim filing flow.
--
-- Escalation ladder (for reference, not stored per-row): insurer GRO ->
-- IRDAI Bima Bharosa -> Insurance Ombudsman. Banks -> RBI Integrated
-- Ombudsman (CMS). Mutual funds -> SEBI SCORES. Unknown-institution deposits
-- -> RBI UDGAM.
-- =============================================================================

-- -----------------------------------------------------------------------------
-- Generic required_docs templates (section 12.6), inlined per row below and
-- lightly adapted per institution kind.
-- -----------------------------------------------------------------------------

insert into institutions (slug, name, kind, aliases, claim_email, grievance_email, portal_url, sla_days, required_docs, source_url, last_verified)
values
-- ---------------------------------------------------------------------------
-- Life insurers
-- ---------------------------------------------------------------------------
(
  'lic', 'Life Insurance Corporation of India', 'life_insurer',
  array['LIC','LIC OF INDIA','LIFE INSURANCE CORP','LIC INDIA'],
  'claims@licindia.com', 'grievance@licindia.com', 'https://www.licindia.in', 30,
  '["Claim form (LIC Form No. 3783 - Death claim)", "Original death certificate", "Original policy document / policy bond", "Nominee KYC (PAN + Aadhaar)", "Nominee bank account proof (cancelled cheque / passbook copy)", "NEFT mandate form", "Medical attendant''s certificate (if death due to illness)", "FIR copy and post-mortem report (if death due to accident)"]'::jsonb,
  'https://www.licindia.in', '2026-09-01'
),
(
  'hdfc-life', 'HDFC Life Insurance', 'life_insurer',
  array['HDFC LIFE','HDFCLIFE','HDFC LIFE INS','HDFC STD LIFE'],
  'claims@hdfclife.com', 'grievance.redressal@hdfclife.com', 'https://www.hdfclife.com', 30,
  '["Claim intimation and claim form", "Original death certificate", "Original policy document", "Nominee KYC (PAN + Aadhaar)", "Nominee bank account proof (cancelled cheque)", "NEFT/ECS mandate form", "Medical attendant''s certificate (if death due to illness)", "FIR copy and post-mortem report (if death due to accident)"]'::jsonb,
  'https://www.hdfclife.com', '2026-09-01'
),
(
  'icici-prudential-life', 'ICICI Prudential Life Insurance', 'life_insurer',
  array['ICICI PRU LIFE','ICICI PRUDENTIAL','ICICIPRULI','ICICI PRU'],
  'claimsupport@iciciprulife.com', 'customer.first@iciciprulife.com', 'https://www.iciciprulife.com', 30,
  '["Claim form (death claim)", "Original death certificate", "Original policy bond", "Nominee KYC (PAN + Aadhaar)", "Nominee bank account proof", "NEFT mandate form", "Medical attendant''s certificate (if death due to illness)", "FIR copy and post-mortem report (if death due to accident)"]'::jsonb,
  'https://www.iciciprulife.com', '2026-09-01'
),
(
  'sbi-life', 'SBI Life Insurance', 'life_insurer',
  array['SBI LIFE','SBILIFE','SBI LIFE INS'],
  'claims@sbilife.co.in', 'grievance@sbilife.co.in', 'https://www.sbilife.co.in', 30,
  '["Claim form (death claim)", "Original death certificate", "Original policy document", "Nominee KYC (PAN + Aadhaar)", "Nominee bank account proof (cancelled cheque)", "NEFT mandate form", "Medical attendant''s certificate (if death due to illness)", "FIR copy and post-mortem report (if death due to accident)"]'::jsonb,
  'https://www.sbilife.co.in', '2026-09-01'
),
(
  'axis-max-life', 'Axis Max Life Insurance', 'life_insurer',
  array['MAX LIFE','AXIS MAX LIFE','MAXLIFE','MAX LIFE INS'],
  'service.helpdesk@maxlifeinsurance.com', 'grievance.redressal@maxlifeinsurance.com', 'https://www.axismaxlife.com', 30,
  '["Claim intimation form", "Original death certificate", "Original policy document", "Nominee KYC (PAN + Aadhaar)", "Nominee bank account proof", "NEFT mandate form", "Medical attendant''s certificate (if death due to illness)", "FIR copy and post-mortem report (if death due to accident)"]'::jsonb,
  'https://www.axismaxlife.com', '2026-09-01'
),

-- ---------------------------------------------------------------------------
-- Health insurers
-- ---------------------------------------------------------------------------
(
  'star-health', 'Star Health and Allied Insurance', 'health_insurer',
  array['STAR HEALTH','STAR HEALTH INS','STARHEALTH','STAR ALLIED'],
  'claims@starhealth.in', 'grievance@starhealth.in', 'https://www.starhealth.in', 15,
  '["Claim form", "Attested death certificate (for death claims under floater cover)", "Original policy document / policy schedule", "Claimant/nominee KYC (PAN + Aadhaar)", "Hospital discharge summary and bills (for hospitalisation claims)", "Nominee bank account proof (cancelled cheque)"]'::jsonb,
  'https://www.starhealth.in', '2026-09-01'
),
(
  'niva-bupa', 'Niva Bupa Health Insurance', 'health_insurer',
  array['NIVA BUPA','MAX BUPA','NIVABUPA','NIVA BUPA HEALTH'],
  'claimsupport@nivabupa.com', 'grievance@nivabupa.com', 'https://www.nivabupa.com', 15,
  '["Claim form", "Attested death certificate", "Original policy document", "Claimant/nominee KYC (PAN + Aadhaar)", "Hospital discharge summary and bills (for hospitalisation claims)", "Nominee bank account proof"]'::jsonb,
  'https://www.nivabupa.com', '2026-09-01'
),
(
  'care-health', 'Care Health Insurance', 'health_insurer',
  array['CARE HEALTH','RELIGARE HEALTH','CAREHEALTH','CARE HEALTH INS'],
  'claims@careinsurance.com', 'grievance@careinsurance.com', 'https://www.careinsurance.com', 15,
  '["Claim form", "Attested death certificate", "Original policy document", "Claimant/nominee KYC (PAN + Aadhaar)", "Hospital discharge summary and bills (for hospitalisation claims)", "Nominee bank account proof"]'::jsonb,
  'https://www.careinsurance.com', '2026-09-01'
),

-- ---------------------------------------------------------------------------
-- Banks
-- ---------------------------------------------------------------------------
(
  'sbi-bank', 'State Bank of India', 'bank',
  array['SBI','STATE BANK OF INDIA','SBIN','SBI BANK'],
  'nodalofficer.corporate@sbi.co.in', 'customercare@sbi.co.in', 'https://www.onlinesbi.sbi', 21,
  '["Claim form for settlement of deceased depositor''s account", "Original death certificate", "Nominee KYC (PAN + Aadhaar)", "Nominee bank account proof (for fund transfer, if different bank)", "Legal heir certificate / succession certificate (only if no nominee registered)", "Indemnity bond (only if no nominee registered)"]'::jsonb,
  'https://www.onlinesbi.sbi', '2026-09-01'
),
(
  'hdfc-bank', 'HDFC Bank', 'bank',
  array['HDFC BANK','HDFCBANK'],
  'deceasedclaims@hdfcbank.com', 'grievance.redressal@hdfcbank.com', 'https://www.hdfcbank.com', 21,
  '["Claim form for settlement of deceased depositor''s account", "Original death certificate", "Nominee KYC (PAN + Aadhaar)", "Nominee bank account proof", "Legal heir certificate / succession certificate (only if no nominee registered)", "Indemnity bond (only if no nominee registered)"]'::jsonb,
  'https://www.hdfcbank.com', '2026-09-01'
),
(
  'icici-bank', 'ICICI Bank', 'bank',
  array['ICICI BANK','ICICIBANK'],
  'customer.care@icicibank.com', 'headservicequality@icicibank.com', 'https://www.icicibank.com', 21,
  '["Claim form for settlement of deceased depositor''s account", "Original death certificate", "Nominee KYC (PAN + Aadhaar)", "Nominee bank account proof", "Legal heir certificate / succession certificate (only if no nominee registered)", "Indemnity bond (only if no nominee registered)"]'::jsonb,
  'https://www.icicibank.com', '2026-09-01'
),
(
  'axis-bank', 'Axis Bank', 'bank',
  array['AXIS BANK','AXISBANK'],
  'deceasedclaims@axisbank.com', 'nodal.officer@axisbank.com', 'https://www.axisbank.com', 21,
  '["Claim form for settlement of deceased depositor''s account", "Original death certificate", "Nominee KYC (PAN + Aadhaar)", "Nominee bank account proof", "Legal heir certificate / succession certificate (only if no nominee registered)", "Indemnity bond (only if no nominee registered)"]'::jsonb,
  'https://www.axisbank.com', '2026-09-01'
),

-- ---------------------------------------------------------------------------
-- Mutual fund registrars
-- ---------------------------------------------------------------------------
(
  'cams', 'CAMS (Computer Age Management Services)', 'mf_registrar',
  array['CAMS','COMPUTER AGE MANAGEMENT','CAMSONLINE'],
  'enq_h@camsonline.com', 'investorservices@camsonline.com', 'https://www.camsonline.com', 21,
  '["Transmission request form (TRF)", "Original/attested death certificate", "Claimant KYC (PAN + Aadhaar)", "Claimant bank account proof (cancelled cheque)", "Indemnity bond (only if no nominee registered)", "Affidavit / legal heir proof (only if no nominee registered)"]'::jsonb,
  'https://www.camsonline.com', '2026-09-01'
),
(
  'kfintech', 'KFin Technologies (KFintech)', 'mf_registrar',
  array['KFINTECH','KARVY FINTECH','KFIN','KARVY'],
  'einward.ris@kfintech.com', 'investor@kfintech.com', 'https://www.kfintech.com', 21,
  '["Transmission request form (TRF)", "Original/attested death certificate", "Claimant KYC (PAN + Aadhaar)", "Claimant bank account proof (cancelled cheque)", "Indemnity bond (only if no nominee registered)", "Affidavit / legal heir proof (only if no nominee registered)"]'::jsonb,
  'https://www.kfintech.com', '2026-09-01'
),

-- ---------------------------------------------------------------------------
-- Retirement bodies
-- ---------------------------------------------------------------------------
(
  'epfo', 'Employees'' Provident Fund Organisation', 'epfo',
  array['EPFO','EMPLOYEES PROVIDENT FUND','EPF','PF OFFICE'],
  'employeefeedback@epfindia.gov.in', 'epfigms@epfindia.gov.in', 'https://www.epfindia.gov.in', 30,
  '["Form 20 (EPF final settlement - death case)", "Form 10D/10C (pension claim, if applicable)", "Original death certificate", "Succession certificate / legal heir certificate", "Nominee KYC (PAN + Aadhaar)", "Nominee bank account proof", "Guardianship certificate (if nominee is a minor)"]'::jsonb,
  'https://www.epfindia.gov.in', '2026-09-01'
),
(
  'nps', 'National Pension System (NSDL CRA / PFRDA)', 'nps',
  array['NPS','NSDL NPS','PFRDA','CRA NSDL','NPS TRUST'],
  'info@cra-nsdl.com', 'grievance@cra-nsdl.com', 'https://www.npscra.nsdl.co.in', 30,
  '["Withdrawal/claim form for death of subscriber (Form for death claim)", "Original death certificate", "Claimant KYC (PAN + Aadhaar)", "Claimant bank account proof (cancelled cheque)", "PRAN card / PRAN details", "Nomination details / legal heir proof (if no nomination registered)"]'::jsonb,
  'https://www.npscra.nsdl.co.in', '2026-09-01'
),

-- ---------------------------------------------------------------------------
-- Lender
-- ---------------------------------------------------------------------------
(
  'bajaj-finance', 'Bajaj Finance Limited', 'lender',
  array['BAJAJ FINANCE','BAJAJ FINSERV','BAJFIN','BAJAJ FINANCE LTD'],
  'customercare@bajajfinserv.in', 'grievanceredressal@bajajfinserv.in', 'https://www.bajajfinserv.in', 15,
  '["Loan protection / credit shield claim form", "Original death certificate", "Loan account statement / loan closure letter", "Claimant/nominee KYC (PAN + Aadhaar)", "Medical attendant''s certificate (if death due to illness)", "FIR copy and post-mortem report (if death due to accident)", "Nominee bank account proof (for any excess payout)"]'::jsonb,
  'https://www.bajajfinserv.in', '2026-09-01'
),

-- ---------------------------------------------------------------------------
-- Brokers / Paytm ecosystem
-- ---------------------------------------------------------------------------
(
  'paytm-money', 'Paytm Money Limited', 'broker',
  array['PAYTM MONEY','PAYTMMONEY','PAYTM MONEY LTD'],
  'support@paytmmoney.com', 'grievance@paytmmoney.com', 'https://www.paytmmoney.com', 21,
  '["Transmission request form", "Original death certificate", "Claimant KYC (PAN + Aadhaar)", "Claimant demat and bank account proof", "Indemnity bond (only if no nominee registered)", "Affidavit / legal heir proof (only if no nominee registered)"]'::jsonb,
  'https://www.paytmmoney.com', '2026-09-01'
),
(
  'paytm-insurance', 'Paytm Insurance (Paytm General Insurance Broking)', 'broker',
  array['PAYTM INSURANCE','PAYTM INSURANCE BROKING'],
  'insurance.support@paytm.com', 'grievance@paytm.com', 'https://www.paytminsurance.co', 21,
  '["Claim intimation form", "Original death certificate", "Policy document", "Claimant/nominee KYC (PAN + Aadhaar)", "Claimant bank account proof"]'::jsonb,
  'https://www.paytminsurance.co', '2026-09-01'
),

-- ---------------------------------------------------------------------------
-- General insurer (covers motor / accident-linked claims)
-- ---------------------------------------------------------------------------
(
  'icici-lombard', 'ICICI Lombard General Insurance', 'general_insurer',
  array['ICICI LOMBARD','ICICILOMBARD','ICICI LOMBARD GIC'],
  'customersupport@icicilombard.com', 'grievanceredressal@icicilombard.com', 'https://www.icicilombard.com', 30,
  '["Claim form", "Death certificate (if applicable to the claim)", "Policy document / RC copy (for motor claims)", "FIR copy (for accident/theft claims)", "Repair estimate and bills (for motor claims)", "Claimant bank account proof"]'::jsonb,
  'https://www.icicilombard.com', '2026-09-01'
)
on conflict (slug) do nothing;
