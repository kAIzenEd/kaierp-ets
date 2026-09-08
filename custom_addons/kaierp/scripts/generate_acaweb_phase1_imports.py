#!/usr/bin/env python3
"""Generate Odoo import CSVs for ACAWEB migration - Phase 1."""
from __future__ import annotations
import argparse, csv, re, unicodedata
from collections import defaultdict
from pathlib import Path
ROOT = Path(__file__).resolve().parents[3] / "ACAWEB"
OUT = ROOT / "import_phase1"
SEMESTER_MAP = {"summer": "summer", "fall": "fall", "spring": "spring"}
COURSE_PROGRAM_MAP = {
    "M.Th": ("mth", "Master of Theology (MTH)"),
    "MABS": ("mabs", "Master of Arts in Biblical Studies (MABS)"),
    "MCS": ("macs", "Master of Arts in Christian Studies (MACS)"),
    "PGDS": ("pgdbs", "Postgraduate Diploma in Biblical Studies (PGDBS)"),
    "D.Min": ("dmin", "Doctor of Ministry (D.Min)"),
    "B.Th": ("bth", "Bachelor of Theology (B.Th)"),
}

def read_csv(name):
    data = (ROOT / name).read_bytes().replace(b"\x00", b"")
    return list(csv.DictReader(data.decode("utf-8-sig", errors="replace").splitlines()))

def slugify(value, max_len=48):
    value = unicodedata.normalize("NFKD", value)
    value = value.encode("ascii", "ignore").decode("ascii")
    value = re.sub(r"[^a-zA-Z0-9]+", "_", value.strip().lower()).strip("_")
    return (value or "unknown")[:max_len]

def teacher_external_id(name):
    return f"acaweb_teacher_{slugify(name)}"

def parse_credit_hours(raw):
    raw = (raw or "").strip()
    if not raw: return 3
    try: return max(1, int(float(raw)))
    except ValueError: return 3

def semester_key(raw):
    key = (raw or "").strip().lower()
    if key in SEMESTER_MAP:
        return SEMESTER_MAP[key]
    # Legacy labels like First/Second/Third/Fourth (year terms) -> fall bucket
    if key in {"first", "second", "third", "fourth"}:
        return "fall"
    return "fall"

def build_course_program_mapping():
    rows = []
    for legacy, (code, label) in COURSE_PROGRAM_MAP.items():
        rows.append({"legacy_course_name": legacy, "odoo_course_code": code, "odoo_course_label": label,
            "import_notes": "" if code else "Extend kaierp course selection before student import"})
    for row in read_csv("ACAWEB_tbl_MasterCourse.csv"):
        rows.append({"legacy_course_name": (row.get("COURSENAME") or "").strip(), "odoo_course_code": "",
            "odoo_course_label": "", "import_notes": f"MasterCourse CID={(row.get('CID') or '').strip()}"})
    return rows

def build_teachers(course_rows):
    names = sorted({(r.get("InstructorName") or "").strip() for r in course_rows if (r.get("InstructorName") or "").strip()})
    teachers, used = [], set()
    for name in names:
        ext_id = teacher_external_id(name)
        email = f"{slugify(name, 40)}@migration.ets.local"; n = 1
        while email in used:
            n += 1; email = f"{slugify(name, 36)}_{n}@migration.ets.local"
        used.add(email)
        teachers.append({"id": ext_id, "name": name, "employee_id": ext_id, "gender": "other", "email": email,
            "phone": "", "department": "Faculty", "specialization": "", "qualification": "", "join_date": "", "state": "active"})
    return teachers

def build_classes(course_rows, year_filter=None):
    key_counts = defaultdict(int); classes, legacy_map = [], []
    for row in course_rows:
        year = (row.get("AcademicYear") or "").strip()
        if year_filter and year != year_filter: continue
        semester_raw = (row.get("Semester") or "").strip()
        course_no = (row.get("CourseNo") or "").strip(); sl_no = (row.get("SlNo") or "").strip()
        course_name = (row.get("CourseName") or "").strip(); batch = (row.get("Batch") or "").strip()
        instructor = (row.get("InstructorName") or "").strip()
        if not course_name: continue
        if not course_no: course_no = slugify(course_name, 20).upper() or "NOCODE"
        base_key = (year, semester_raw, course_no, sl_no); key_counts[base_key] += 1; variant = key_counts[base_key]
        ext_id = f"acaweb_cls_{year}_{slugify(semester_raw)}_{slugify(course_no)}_s{sl_no or '0'}"
        if variant > 1: ext_id = f"{ext_id}_v{variant}"
        display_name = course_name
        if semester_raw.lower() not in SEMESTER_MAP:
            display_name = f"{display_name} [{semester_raw}]"
        if batch and variant > 1:
            display_name = f"{display_name} ({batch})"
        classes.append({"id": ext_id, "name": display_name, "code": course_no, "academic_year": year,
            "semester": semester_key(semester_raw), "teacher_id/id": teacher_external_id(instructor) if instructor else "",
            "room": "", "schedule": "", "credit_hours": str(parse_credit_hours(row.get("CourseHour"))),
            "max_students": "30", "state": "completed", "start_date": "", "end_date": ""})
        legacy_map.append({"odoo_class_id": ext_id, "academic_year": year, "semester": semester_raw,
            "course_no": course_no, "sl_no": sl_no, "course_name": course_name, "batch": batch,
            "instructor_name": instructor, "variant": str(variant)})
    return classes, legacy_map

def write_csv(path, fieldnames, rows):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore"); w.writeheader(); w.writerows(rows)

TEACHER_FIELDS = ["id","name","employee_id","gender","email","phone","department","specialization","qualification","join_date","state"]
CLASS_FIELDS = ["id","name","code","academic_year","semester","teacher_id/id","room","schedule","credit_hours","max_students","state","start_date","end_date"]
MAP_FIELDS = ["odoo_class_id","academic_year","semester","course_no","sl_no","course_name","batch","instructor_name","variant"]

def main():
    parser = argparse.ArgumentParser(); parser.add_argument("--year", help="Pilot year (default 2017)"); args = parser.parse_args()
    course_rows = read_csv("ACAWEB_tbl_CourseMaster.csv"); teachers = build_teachers(course_rows)
    classes, legacy_map = build_classes(course_rows)
    write_csv(OUT / "course_program_mapping.csv", ["legacy_course_name","odoo_course_code","odoo_course_label","import_notes"], build_course_program_mapping())
    write_csv(OUT / "teachers_all.csv", TEACHER_FIELDS, teachers)
    write_csv(OUT / "classes_all.csv", CLASS_FIELDS, classes)
    write_csv(OUT / "class_legacy_map.csv", MAP_FIELDS, legacy_map)
    pilot_year = args.year or "2017"; p_classes, p_map = build_classes(course_rows, year_filter=pilot_year)
    p_teacher_ids = {r["teacher_id/id"] for r in p_classes if r.get("teacher_id/id")}
    write_csv(OUT / f"teachers_{pilot_year}.csv", TEACHER_FIELDS, [t for t in teachers if t["id"] in p_teacher_ids])
    write_csv(OUT / f"classes_{pilot_year}.csv", CLASS_FIELDS, p_classes)
    write_csv(OUT / f"class_legacy_map_{pilot_year}.csv", MAP_FIELDS, p_map)
    print(f"Wrote Phase 1 files to {OUT}")
    print(f"  Teachers (all): {len(teachers)}")
    print(f"  Classes (all):  {len(classes)}")
    print(f"  Pilot {pilot_year}: {len(p_teacher_ids)} teachers, {len(p_classes)} classes")

if __name__ == "__main__":
    main()
