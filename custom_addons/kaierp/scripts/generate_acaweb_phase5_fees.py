#!/usr/bin/env python3
"""Generate Odoo import CSVs for ACAWEB migration - Phase 5 (historical fees).

Explodes ACAWEB_tbl_FeesPaymentDetails receipt rows into school.fee lines.
Historical ledger only: amounts and status, no Accounting invoices/payments.
"""
from __future__ import annotations

import argparse
import csv
import re
from collections import Counter
from pathlib import Path

csv.field_size_limit(10_000_000)

ROOT = Path(__file__).resolve().parents[3] / "ACAWEB"
OUT = ROOT / "import_phase5"
STUDENTS_CSV = ROOT / "import_phase2" / "students_all.csv"

SEMESTER_MAP = {
    "summer": "summer", "fall": "fall", "spring": "spring",
    "Summer": "summer", "Fall": "fall", "Spring": "spring",
}

# (due_col, paid_col, bal_col, product_xml_id, label)
COMPONENTS = [
    ("SemCourseFees", "CoursePaid", "CourseBal", "kaierp.product_tuition_product", "Tuition"),
    ("Accomadation", "AccomodationPaid", "AccomodationBal", "kaierp.product_accommodation_product", "Accommodation"),
    ("Food", "FoodPaid", "FoodBal", "kaierp.product_food_product", "Food"),
    ("LibCaution", "LibraryPaid", "LibraryBal", "kaierp.product_library_deposit_product", "Library Caution"),
    ("GenCaution", "GeneralPaid", "GeneralBal", "kaierp.product_caution_single_product", "General Caution"),
    ("OnSiteFee", "OnSiteFeePaid", "OnSiteFeeBal", "kaierp.product_exam_accommodation_product", "On-Site / Exam Acc."),
    ("TechnologyFee", "TechnologyPaid", "TechnologyBal", "kaierp.product_technology_fee_product", "Technology Fee"),
    ("ExamFee", "ExamPaid", "ExamBal", "kaierp.product_exam_fee_product", "Exam Fee"),
    ("ThesisFee", "ThesisPaid", "ThesisBal", "kaierp.product_thesis_fee_product", "Thesis Fee"),
    ("OtherFees", "OtherPaid", "OthersBal", "kaierp.product_other_fee_product", "Other Fees"),
    ("AdmissionFee", "AdmissionPaid", "AdmissionBal", "kaierp.product_admission_fee_product", "Admission Fee"),
    ("ApplicationFee", "ApplicationPaid", "ApplicationBal", "kaierp.product_application_fee_product", "Application Fee"),
    ("GraduationFee", "GraduationPaid", "GraduationBal", "kaierp.product_graduation_fee_product", "Graduation Fee"),
    ("ContinuationFee", "ContinuationPaid", "ContinuationBal", "kaierp.product_continuation_fee_product", "Continuation Fee"),
    ("DissertationFee", "DissertationPaid", "DissertationBal", "kaierp.product_dissertation_fee_product", "Dissertation Fee"),
    ("TranscriptFee", "TranscriptPaid", "TranscriptBal", "kaierp.product_transcript_fee_product", "Transcript Fee"),
    ("LibraryUsage", "LibraryUsagePaid", "LibraryUsageBal", "kaierp.product_library_user_fee_product", "Library User Fee"),
    ("Medical", "MedicalPaid", "MedicalBal", "kaierp.product_medical_single_product", "Medical Fee"),
    ("Sports", "SportsPaid", "SportsBal", "kaierp.product_sports_fee_product", "Sports Fee"),
    ("Fine", "FinePaid", "FineBal", "kaierp.product_fine_product", "Fine"),
]

FEE_FIELDS = [
    "id",
    "name",
    "student_id/id",
    "product_id/id",
    "quantity",
    "unit_price",
    "amount_paid",
    "academic_year",
    "semester",
    "due_date",
    "payment_date",
    "state",
    "notes",
]
SKIP_FIELDS = ["reg_no", "receipt_no", "component", "reason", "ayear"]


def read_acaweb_csv(name: str):
    path = ROOT / name
    data = path.read_bytes()
    if data[:2] == b"\xff\xfe":
        text = data.decode("utf-16-le")
    elif data[:2] == b"\xfe\xff":
        text = data.decode("utf-16-be")
    else:
        text = data.decode("utf-8-sig", errors="replace")
    lines = text.splitlines()
    if lines and lines[0].startswith("\ufeff"):
        lines[0] = lines[0].lstrip("\ufeff")
    return list(csv.DictReader(lines))


def write_csv(path: Path, fieldnames, rows):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
        w.writeheader()
        w.writerows(rows)


def money(val) -> float:
    try:
        return float((val or "").strip() or 0)
    except ValueError:
        return 0.0


def parse_date(val: str) -> str:
    m = re.match(r"^(\d{4}-\d{2}-\d{2})", (val or "").strip())
    return m.group(1) if m else ""


def fee_state(due: float, paid: float) -> str:
    if due <= 0 and paid <= 0:
        return "pending"
    if paid + 0.009 >= due and due > 0:
        return "paid"
    if paid > 0:
        return "partial"
    return "pending"


def map_semester(raw: str) -> str:
    key = (raw or "").strip()
    if key in SEMESTER_MAP:
        return SEMESTER_MAP[key]
    low = key.lower()
    if low in SEMESTER_MAP:
        return SEMESTER_MAP[low]
    return ""



def fee_display_name(label: str, sem_label: str, ayear: str, year_study: str, year_study_no: str, receipt: str) -> str:
    """Human label: Food (Summer · Year 2 · R4169)."""
    parts = []
    if sem_label:
        parts.append(sem_label)
    ys = (year_study or "").strip()
    yn = (year_study_no or "").strip()
    if yn and yn.isdigit():
        parts.append(f"Year {yn}")
    elif ys:
        parts.append(f"Year {ys}")
    elif ayear:
        parts.append(ayear)
    if receipt and receipt != "noreceipt":
        parts.append(f"R{receipt}")
    suffix = " · ".join(parts) if parts else ayear
    return f"{label} ({suffix})".strip()

def sanitize_id(s: str) -> str:
    return re.sub(r"[^A-Za-z0-9_.-]+", "_", (s or "").strip()) or "x"


def load_imported_students():
    if not STUDENTS_CSV.exists():
        return set()
    with STUDENTS_CSV.open(encoding="utf-8") as f:
        return {(r.get("id") or r.get("student_id") or "").strip() for r in csv.DictReader(f)}


def build_notes(r: dict, label: str) -> str:
    parts = [
        f"ACAWEB historical | {label}",
        f"Receipt={ (r.get('ReceiptNo') or '').strip() }",
        f"BNo={ (r.get('BNo') or '').strip() }",
        f"Semester={ (r.get('Semester') or '').strip() }",
        f"Mode={ (r.get('ModeofPay') or '').strip() }",
        f"Type={ (r.get('PaymentType') or '').strip() }",
        f"LegacyStatus={ (r.get('Status') or '').strip() }",
    ]
    narr = (r.get("Narration") or "").strip()
    if narr:
        parts.append(f"Narration={narr[:200]}")
    bank = (r.get("BankName") or "").strip()
    dd = (r.get("DDNo") or "").strip()
    if bank or dd:
        parts.append(f"Bank={bank} DD={dd}")
    return " | ".join(parts)


def explode_receipt(r: dict, known_students, year_filter):
    out = []
    skipped = []
    ayear = (r.get("AYear") or "").strip()
    if year_filter and ayear != year_filter:
        return out, skipped
    if not re.fullmatch(r"\d{4}", ayear):
        skipped.append({
            "reg_no": (r.get("RegNo") or "").strip(),
            "receipt_no": (r.get("ReceiptNo") or "").strip(),
            "component": "",
            "ayear": ayear,
            "reason": "bad_ayear",
        })
        return out, skipped

    regno = (r.get("RegNo") or "").strip()
    if not regno:
        skipped.append({
            "reg_no": "",
            "receipt_no": (r.get("ReceiptNo") or "").strip(),
            "component": "",
            "ayear": ayear,
            "reason": "missing_regno",
        })
        return out, skipped
    if known_students and regno not in known_students:
        skipped.append({
            "reg_no": regno,
            "receipt_no": (r.get("ReceiptNo") or "").strip(),
            "component": "",
            "ayear": ayear,
            "reason": "student_not_imported",
        })
        return out, skipped

    pay_date = parse_date(r.get("PaymentMade") or "")
    due_date = pay_date or f"{ayear}-06-30"
    semester = map_semester(r.get("Semester") or "")
    sem_label = (r.get("Semester") or "").strip()
    year_study = (r.get("YearStudy") or "").strip()
    year_study_no = (r.get("YearStudyNo") or "").strip()
    receipt = (r.get("ReceiptNo") or "").strip() or (r.get("BNo") or "").strip() or "noreceipt"
    bno = (r.get("BNo") or "").strip() or "x"

    for due_col, paid_col, bal_col, product_xml, label in COMPONENTS:
        due = money(r.get(due_col))
        paid = money(r.get(paid_col))
        bal = money(r.get(bal_col))
        if due == 0 and paid == 0 and bal == 0:
            continue
        if due == 0 and (paid or bal):
            due = paid + bal if (paid or bal) else paid
        if due <= 0 and paid <= 0:
            continue
        if due <= 0 and paid > 0:
            due = paid

        comp_key = due_col.lower()
        ext_id = f"acaweb_fee_{ayear}_{sanitize_id(receipt)}_{sanitize_id(bno)}_{comp_key}"
        state = fee_state(due, paid)
        out.append({
            "id": ext_id,
            "name": fee_display_name(label, sem_label, ayear, year_study, year_study_no, receipt),
            "student_id/id": regno,
            "product_id/id": product_xml,
            "quantity": "1",
            "unit_price": f"{due:.2f}",
            "amount_paid": f"{paid:.2f}",
            "academic_year": ayear,
            "semester": semester,
            "due_date": due_date,
            "payment_date": pay_date if paid > 0 else "",
            "state": state,
            "notes": build_notes(r, label),
        })

    prev = money(r.get("PrevDues"))
    if prev > 0:
        receipt_bal = money(r.get("Balance"))
        paid_prev = prev if receipt_bal <= 0 and money(r.get("AmountPaid")) > 0 else 0.0
        ext_id = f"acaweb_fee_{ayear}_{sanitize_id(receipt)}_{sanitize_id(bno)}_prevdues"
        state = fee_state(prev, paid_prev)
        out.append({
            "id": ext_id,
            "name": fee_display_name("Previous Dues", sem_label, ayear, year_study, year_study_no, receipt),
            "student_id/id": regno,
            "product_id/id": "kaierp.product_previous_dues_product",
            "quantity": "1",
            "unit_price": f"{prev:.2f}",
            "amount_paid": f"{paid_prev:.2f}",
            "academic_year": ayear,
            "semester": semester,
            "due_date": due_date,
            "payment_date": pay_date if paid_prev > 0 else "",
            "state": state,
            "notes": build_notes(r, "Previous Dues"),
        })

    return out, skipped


def generate(year=None):
    rows = read_acaweb_csv("ACAWEB_tbl_FeesPaymentDetails.csv")
    known = load_imported_students()
    out = []
    skipped = []
    for r in rows:
        lines, skips = explode_receipt(r, known, year)
        out.extend(lines)
        skipped.extend(skips)

    suffix = year or "all"
    write_csv(OUT / f"fees_{suffix}.csv", FEE_FIELDS, out)
    write_csv(OUT / f"fees_skipped_{suffix}.csv", SKIP_FIELDS, skipped)

    by_state = Counter(r["state"] for r in out)
    by_prod = Counter(r["product_id/id"].split(".")[-1] for r in out)
    skip_reasons = Counter(r["reason"] for r in skipped)
    print(f"Phase 5 fees_{suffix}: {len(out)} lines from FeesPaymentDetails")
    print(f"  states: {dict(by_state)}")
    print(f"  skipped receipts/rows: {len(skipped)} {dict(skip_reasons)}")
    print(f"  top products: {by_prod.most_common(8)}")
    print(f"  wrote {OUT / f'fees_{suffix}.csv'}")


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--year", default=None, help="Academic year filter e.g. 2017 (default: all)")
    ap.add_argument("--pilot", action="store_true", help="Shortcut for --year 2017")
    args = ap.parse_args()
    year = "2017" if args.pilot else args.year
    generate(year)


if __name__ == "__main__":
    main()
