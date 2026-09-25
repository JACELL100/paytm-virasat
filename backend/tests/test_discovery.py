from __future__ import annotations

from app.services.discovery.recurring import detect_recurring_groups, match_institution
from app.services.discovery.sms_parser import parse_sms_text
from app.services.discovery.statement_parser import parse_csv_statement


def test_match_institution_finds_hdfc_life_via_alias():
    result = match_institution("HDFCLIFE PREMIUM PAYMENT")
    assert result is not None
    assert result["slug"] == "hdfc-life"


def test_match_institution_no_match_returns_none():
    result = match_institution("RANDOM UNKNOWN MERCHANT XYZ 12345")
    assert result is None or result["match_score"] < 100


def test_detect_recurring_groups_finds_monthly_premium():
    transactions = [
        {"date": "2026-01-05", "narration": "HDFCLIFE TERM PLAN PREMIUM", "debit": 4166.0, "credit": None},
        {"date": "2026-02-05", "narration": "HDFCLIFE TERM PLAN PREMIUM", "debit": 4166.0, "credit": None},
        {"date": "2026-03-05", "narration": "HDFCLIFE TERM PLAN PREMIUM", "debit": 4166.0, "credit": None},
    ]
    groups = detect_recurring_groups(transactions)
    assert len(groups) == 1
    assert groups[0]["occurrences"] == 3
    assert groups[0]["periodicity"] == "monthly"


def test_detect_recurring_groups_single_occurrence_with_keyword_still_flagged():
    transactions = [{"date": "2026-01-05", "narration": "LIC PREMIUM PAYMENT", "debit": 8333.0, "credit": None}]
    groups = detect_recurring_groups(transactions)
    assert len(groups) == 1
    assert groups[0]["has_strong_keyword"] is True


def test_detect_recurring_groups_ignores_one_off_non_keyword_txn():
    transactions = [{"date": "2026-01-05", "narration": "SWIGGY FOOD ORDER", "debit": 450.0, "credit": None}]
    groups = detect_recurring_groups(transactions)
    assert groups == []


def test_parse_sms_text_extracts_amount_and_merchant():
    text = "Rs.2340 debited from A/c XX1234 towards HDFCLIFE on 05-Jan-24"
    result = parse_sms_text(text)
    assert len(result["matched"]) == 1
    assert result["matched"][0]["amount"] == 2340.0
    assert result["matched"][0]["account_ref_masked"] == "XX1234"


def test_parse_csv_statement_parses_rows():
    csv_bytes = b"Date,Narration,Debit,Credit\n05/01/2026,LIC PREMIUM,8333.00,\n15/01/2026,SBI FD INTEREST,,2100.00\n"
    rows = parse_csv_statement(csv_bytes)
    assert len(rows) == 2
    assert rows[0]["narration"] == "LIC PREMIUM"
    assert rows[0]["debit"] == 8333.0
    assert rows[1]["credit"] == 2100.0
