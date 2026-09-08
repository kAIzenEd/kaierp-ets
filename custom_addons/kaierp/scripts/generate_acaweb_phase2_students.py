#!/usr/bin/env python3
"""Generate Odoo import CSVs for ACAWEB migration - Phase 2 (students + personal data).

Merges StudentPersonalDetails with Church / Family / Spiritual / Health /
Work / Financial tables by RegNo.
"""
from __future__ import annotations

import argparse
import csv
import re
from collections import Counter
from pathlib import Path

csv.field_size_limit(10_000_000)

ROOT = Path(__file__).resolve().parents[3] / "ACAWEB"
OUT = ROOT / "import_phase2"

COURSE_MAP = {
    "M.Th": "mth", "M.TH": "mth", "M.TH.": "mth", "M.Th.": "mth",
    "MABS": "mabs",
    "MCS": "macs",
    "PGDS": "pgdbs", "PGDS.": "pgdbs",
    "D.Min": "dmin", "D.MIN": "dmin", "D.Min.": "dmin",
    "B.Th": "bth", "B.TH": "bth", "B.Th.": "bth",
}
GENDER_MAP = {"Male": "male", "Female": "female", "male": "male", "female": "female"}
NATIONALITY_MAP = {
    "Indian": "India", "India": "India",
    "Kachin": "Myanmar", "Myanmar": "Myanmar", "Chin": "Myanmar",
    "Burmese": "Myanmar", "Lai (Miza)": "Myanmar", "Kachin state": "Myanmar",
    "Rawang": "Myanmar", "Japan": "Japan",
}
MARITAL_MAP = {
    "Single": "single", "Married": "married", "Divorced": "divorced",
    "Separated": "separated", "Widowed": "widowed",
    "single": "single", "married": "married",
}
YES_NO = {"Yes": "yes", "No": "no", "yes": "yes", "no": "no", "YES": "yes", "NO": "no"}
DENOM_MAP = {
    "baptist": "baptist", "brethren": "brethren", "pentecostal": "pentecostal",
    "charismatic": "charismatic", "methodist": "methodist",
    "presbyterian": "presbyterian", "roman catholic": "roman_catholic",
    "catholic": "roman_catholic", "orthodox": "eastern_orthodox",
    "independent": "independent", "protestant": "other",
}
BLOOD_MAP = {
    "A": "A", "A+": "A+", "A-": "A-", "A+ve": "A+", "A-ve": "A-",
    "B": "B", "B+": "B+", "B-": "B-", "B+ve": "B+", "B-ve": "B-", "B+ove": "B+",
    "AB": "AB", "AB+": "AB+", "AB-": "AB-", "AB+ve": "AB+",
    "O": "O", "O+": "O+", "O-": "O-", "O+ve": "O+", "O-ve": "O-",
    "0": "O", "0+ve": "O+", "0+": "O+",
}

STUDENT_FIELDS = [
    "id", "student_id", "full_name", "gender", "date_of_birth", "email",
    "mobile_number", "phone_number", "postal_address", "city", "state_name",
    "country_id/id", "zip_code", "course", "study_mode", "admission_date",
    "academic_year", "state", "class_id", "nationality",
    # Personal / church / spiritual / family / work / finance / health
    "marital_status", "plan_married_during_study",
    "church_name", "church_location", "church_denomination", "church_ministry_type",
    "is_ordained", "is_commended", "church_financial_support",
    "believers_baptism", "called_to_ministry",
    "read_doctrinal_statement", "agree_doctrinal_statement",
    "father_name", "father_occupation", "mother_name", "mother_occupation",
    "parents_believers", "family_postal_addresses", "family_contact_details",
    "family_email_addresses", "has_children",
    "currently_employed", "working_for_organisation",
    "has_financial_sponsor", "monthly_support_inr", "monthly_support_usd",
    "blood_group", "height_cm", "weight_kg", "allergies",
    "chronic_illness", "prolonged_medication", "vision_hearing_problem",
    "uses_tobacco", "uses_intoxicants", "suffers_sleeplessness",
    "psychiatric_care_history", "other_medical_problems",
]
SKIP_FIELDS = ["reg_no", "full_name", "course_name", "ayear_raw", "reason"]


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


def index_by_regno(rows):
    out = {}
    for r in rows:
        regno = (r.get("RegNo") or "").strip()
        if regno and regno not in out:
            out[regno] = r
    return out


def derive_year(reg_no: str, ayear_raw: str) -> str:
    y = (ayear_raw or "").strip()
    if re.fullmatch(r"\d{4}", y):
        return y
    m = re.match(r"^(\d{2})[A-Za-z]", reg_no or "")
    if m:
        yy = int(m.group(1))
        return f"20{yy:02d}" if yy < 80 else f"19{yy:02d}"
    return ""


def yn(raw):
    return YES_NO.get((raw or "").strip(), "")


def map_denom(raw):
    text = (raw or "").strip().lower()
    if not text:
        return ""
    for key, code in DENOM_MAP.items():
        if key in text:
            return code
    if "not affiliated" in text:
        return "independent"
    return "other"


def map_blood(raw):
    return BLOOD_MAP.get((raw or "").strip(), "")


def map_doctrinal_agree(raw):
    v = (raw or "").strip()
    if v in ("Yes", "yes"):
        return "yes_agree"
    if v in ("No", "no"):
        return "no"
    return ""


def build_app_dates(apps):
    app_recv = {}
    for r in apps:
        appno = (r.get("ApplnNo") or "").strip()
        rd = (r.get("RecieveDate") or "").strip()
        if not appno or not rd:
            continue
        m = re.match(r"^(\d{4}-\d{2}-\d{2})", rd)
        if m:
            app_recv[appno] = m.group(1)
    return app_recv


def join_address(*parts):
    return " ".join(p for p in parts if (p or "").strip()).strip()


def build_students(rows, related, app_recv, year_filter=None):
    church = related["church"]
    family = related["family"]
    spiritual = related["spiritual"]
    health = related["health"]
    work = related["work"]
    finance = related["finance"]

    out = []
    skipped = []
    seen = set()
    for r in rows:
        regno = (r.get("RegNo") or "").strip()
        ayear_raw = (r.get("AYear") or "").strip()
        year = derive_year(regno, ayear_raw)
        if year_filter and year != year_filter:
            continue
        base = {
            "reg_no": regno,
            "full_name": (r.get("StudName") or "").strip(),
            "course_name": (r.get("CourseName") or "").strip(),
            "ayear_raw": ayear_raw,
        }
        if not regno:
            skipped.append({**base, "reason": "missing_reg_no"})
            continue
        if regno in seen:
            skipped.append({**base, "reason": "duplicate_reg_no"})
            continue
        gender = GENDER_MAP.get((r.get("Gender") or "").strip())
        if not gender:
            skipped.append({**base, "reason": "missing_gender"})
            continue
        m = re.match(r"^(\d{4}-\d{2}-\d{2})", (r.get("DOB") or "").strip())
        if not m:
            skipped.append({**base, "reason": "missing_or_bad_dob"})
            continue
        if not year:
            skipped.append({**base, "reason": "missing_academic_year"})
            continue

        course_raw = (r.get("CourseName") or "").strip()
        course = COURSE_MAP.get(course_raw, "")
        app_no = (r.get("AppNo") or "").strip()
        admission_date = ""
        if app_no in app_recv and app_recv[app_no].startswith(year):
            admission_date = app_recv[app_no]
        nat_raw = (r.get("Nationality") or "").strip()
        marital = MARITAL_MAP.get((r.get("MaritalStatus") or "").strip(), "")

        ch = church.get(regno, {})
        fa = family.get(regno, {})
        sp = spiritual.get(regno, {})
        he = health.get(regno, {})
        wo = work.get(regno, {})
        fi = finance.get(regno, {})

        # plan_married: only when SinglePlan is clean yes/no
        plan = yn(r.get("SinglePlan"))

        parents_believers = ""
        jb = (fa.get("JesusBeliever") or "").strip()
        if jb in YES_NO:
            parents_believers = YES_NO[jb]

        height = ""
        weight = ""
        try:
            if (he.get("Height") or "").strip():
                height = str(float((he.get("Height") or "").strip()))
        except ValueError:
            height = ""
        try:
            if (he.get("Weight") or "").strip():
                weight = str(float((he.get("Weight") or "").strip()))
        except ValueError:
            weight = ""

        seen.add(regno)
        out.append({
            "id": regno,
            "student_id": regno,
            "full_name": (r.get("StudName") or "").strip(),
            "gender": gender,
            "date_of_birth": m.group(1),
            "email": (r.get("EmailID") or "").strip(),
            "mobile_number": (r.get("MobileNo") or "").strip(),
            "phone_number": (r.get("PHNo") or "").strip(),
            "postal_address": join_address(r.get("PermentAddress1"), r.get("PermentAddress2")),
            "city": (r.get("PresentAddress2") or r.get("PresentAddress1") or "").strip(),
            "state_name": (r.get("State") or "").strip(),
            "country_id/id": "",
            "zip_code": "",
            "course": course,
            "study_mode": "",
            "admission_date": admission_date,
            "academic_year": year,
            "state": "active",
            "class_id": "",
            "nationality": NATIONALITY_MAP.get(nat_raw, ""),
            "marital_status": marital,
            "plan_married_during_study": plan,
            "church_name": (ch.get("ChurchName") or "").strip(),
            "church_location": (ch.get("ChurchLocation") or "").strip(),
            "church_denomination": map_denom(ch.get("ChurchAffilated")),
            "church_ministry_type": (ch.get("ChurchAppoinment") or "").strip(),
            "is_ordained": yn(ch.get("Ordained")),
            "is_commended": yn(ch.get("Comended")),
            "church_financial_support": yn(ch.get("FinancialSupported")),
            "believers_baptism": yn(sp.get("Baptism")),
            "called_to_ministry": yn(sp.get("GodService")),
            "read_doctrinal_statement": yn(sp.get("DoctrinalETS")),
            "agree_doctrinal_statement": map_doctrinal_agree(sp.get("DoctrinalAgree")),
            "father_name": (fa.get("FatherName") or "").strip(),
            "father_occupation": (fa.get("FatherOccupation") or "").strip(),
            "mother_name": (fa.get("MotherName") or "").strip(),
            "mother_occupation": (fa.get("MotherOccupation") or "").strip(),
            "parents_believers": parents_believers,
            "family_postal_addresses": join_address(fa.get("ContactAdd"), fa.get("ContactAdd1")),
            "family_contact_details": join_address(fa.get("ContactPhone"), fa.get("ContactMobile")),
            "family_email_addresses": (fa.get("ContactEmail") or "").strip(),
            "has_children": yn(fa.get("ChildAdmission")),
            "currently_employed": yn(wo.get("Employeement")),
            "working_for_organisation": yn(wo.get("Organization")),
            "has_financial_sponsor": yn(fi.get("FISponsor")),
            "monthly_support_inr": (fi.get("MFAmount") or "").strip(),
            "monthly_support_usd": (fi.get("MFDollar") or "").strip(),
            "blood_group": map_blood(he.get("BloodGroup")),
            "height_cm": height,
            "weight_kg": weight,
            "allergies": (he.get("Allergic") or "").strip(),
            "chronic_illness": yn(he.get("PhysicalDisabled")),
            "prolonged_medication": yn(he.get("Medicinal")),
            "vision_hearing_problem": yn(he.get("Vision")),
            "uses_tobacco": yn(he.get("Tobacco")),
            "uses_intoxicants": yn(he.get("Intoxicant")) or yn(he.get("Narcotic")),
            "suffers_sleeplessness": yn(he.get("Sleeplessness")),
            "psychiatric_care_history": yn(he.get("Psychaitric")),
            "other_medical_problems": yn(he.get("MedicalProblem")),
        })
    return out, skipped


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--year", default="all", help="Pilot year or 'all' (default all)")
    args = parser.parse_args()
    year_filter = None if args.year.lower() == "all" else args.year

    students_src = read_acaweb_csv("ACAWEB_tbl_StudentPersonalDetails.csv")
    apps = read_acaweb_csv("ACAWEB_tbl_RecievedApplication.csv")
    related = {
        "church": index_by_regno(read_acaweb_csv("ACAWEB_tbl_ChurchBackGround.csv")),
        "family": index_by_regno(read_acaweb_csv("ACAWEB_tbl_StudentFamilyInformation.csv")),
        "spiritual": index_by_regno(read_acaweb_csv("ACAWEB_tbl_StudentSpiritualIdentity.csv")),
        "health": index_by_regno(read_acaweb_csv("ACAWEB_tbl_StudentHealthInformation.csv")),
        "work": index_by_regno(read_acaweb_csv("ACAWEB_tbl_StudentWorkExperience.csv")),
        "finance": index_by_regno(read_acaweb_csv("ACAWEB_tbl_StudentFinancialInformation.csv")),
    }
    app_recv = build_app_dates(apps)
    rows, skipped = build_students(students_src, related, app_recv, year_filter=year_filter)

    label = year_filter or "all"
    write_csv(OUT / f"students_{label}.csv", STUDENT_FIELDS, rows)
    write_csv(OUT / f"students_skipped_{label}.csv", SKIP_FIELDS, skipped)

    # coverage stats for key personal fields
    filled = Counter()
    for r in rows:
        for f in ("marital_status", "is_ordained", "is_commended", "church_name",
                  "believers_baptism", "father_name", "uses_tobacco"):
            if r.get(f):
                filled[f] += 1

    print(f"Wrote Phase 2 files to {OUT}")
    print(f"  Students ({label}): {len(rows)}")
    print(f"  Skipped:            {len(skipped)}")
    print(f"  Filled personal:    {dict(filled)}")
    if skipped:
        print(f"  Skip reasons:      {dict(Counter(s['reason'] for s in skipped))}")
    # spot-check Roby
    for r in rows:
        if r["student_id"] == "17BTH001":
            print("  17BTH001 sample:",
                  {k: r[k] for k in (
                      "full_name", "marital_status", "is_ordained", "is_commended",
                      "church_financial_support", "believers_baptism", "uses_tobacco")})
            break


if __name__ == "__main__":
    main()
