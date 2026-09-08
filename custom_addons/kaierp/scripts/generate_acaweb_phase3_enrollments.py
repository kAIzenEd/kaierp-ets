#!/usr/bin/env python3
"""Generate Odoo import CSVs for ACAWEB migration - Phase 3 (enrollments).

Links CourseRegistration rows to:
  - students via RegNo == school.student external id / student_id
  - classes via class_legacy_map.csv (year + semester + course_no + sl_no,
    with fallbacks on course name / course_no)
"""
from __future__ import annotations

import argparse
import csv
import re
import unicodedata
from collections import Counter, defaultdict
from pathlib import Path

csv.field_size_limit(10_000_000)

ROOT = Path(__file__).resolve().parents[3] / "ACAWEB"
MAP_PATH = ROOT / "import_phase1" / "class_legacy_map.csv"
STUDENTS_DIR = ROOT / "import_phase2"
OUT = ROOT / "import_phase3"

ENROLL_FIELDS = [
    "id",
    "student_id/id",
    "class_id/id",
    "enrollment_date",
    "state",
    "notes",
]
REPORT_FIELDS = [
    "reg_no",
    "academic_year",
    "semester",
    "course_no",
    "sl_no",
    "course_name",
    "batch",
    "instructor_name",
    "reason",
]


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


def read_utf8_csv(path: Path):
    return list(csv.DictReader(path.read_text(encoding="utf-8-sig").splitlines()))


def write_csv(path: Path, fieldnames, rows):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
        w.writeheader()
        w.writerows(rows)


def slugify(value, max_len=40):
    value = unicodedata.normalize("NFKD", value or "")
    value = value.encode("ascii", "ignore").decode("ascii")
    value = re.sub(r"[^a-zA-Z0-9]+", "_", value.strip().lower()).strip("_")
    return (value or "x")[:max_len]


def enrollment_date(year: str, semester: str) -> str:
    """Approximate term start date when legacy data has no enrollment date."""
    try:
        y = int(year)
    except ValueError:
        return ""
    sem = (semester or "").strip().lower()
    if sem == "summer":
        return f"{y}-06-01"
    if sem == "spring":
        return f"{y}-01-15"
    # Fall + legacy First/Second/Third/Fourth
    return f"{y}-08-01"


def load_student_ids(year: str | None) -> set[str]:
    ids: set[str] = set()
    if year:
        paths = [STUDENTS_DIR / f"students_{year}.csv"]
    else:
        paths = [STUDENTS_DIR / "students_all.csv"]
        # Fall back to any per-year files if students_all is missing.
        if not paths[0].exists():
            paths = sorted(STUDENTS_DIR.glob("students_2*.csv"))
    for path in paths:
        if not path.exists():
            continue
        for row in read_utf8_csv(path):
            sid = (row.get("student_id") or row.get("id") or "").strip()
            if sid:
                ids.add(sid)
    return ids


def build_class_indexes(map_rows):
    by_ycs = defaultdict(list)
    by_ycn = defaultdict(list)
    by_ycno = defaultdict(list)
    for m in map_rows:
        y = (m.get("academic_year") or "").strip()
        s = (m.get("semester") or "").strip()
        cno = (m.get("course_no") or "").strip()
        sl = (m.get("sl_no") or "").strip()
        name = (m.get("course_name") or "").strip().lower()
        by_ycs[(y, s, cno, sl)].append(m)
        if name:
            by_ycn[(y, s, name)].append(m)
        if cno:
            by_ycno[(y, s, cno)].append(m)
    return by_ycs, by_ycn, by_ycno


def pick_class(hits, reg_row):
    if not hits:
        return None
    if len(hits) == 1:
        return hits[0]
    instr = (reg_row.get("InstructorName") or "").strip()
    batch = (reg_row.get("Batch") or "").strip()
    sl = (reg_row.get("SlNo") or "").strip()
    name = (reg_row.get("CourseName") or "").strip().lower()
    prefer = [h for h in hits if h.get("instructor_name") == instr and h.get("batch") == batch]
    if not prefer:
        prefer = [h for h in hits if h.get("instructor_name") == instr]
    if not prefer:
        prefer = [h for h in hits if h.get("batch") == batch]
    if not prefer:
        prefer = [h for h in hits if h.get("sl_no") == sl]
    if not prefer and name:
        prefer = [h for h in hits if (h.get("course_name") or "").strip().lower() == name]
    return (prefer or hits)[0]


def resolve_class(reg_row, by_ycs, by_ycn, by_ycno):
    y = (reg_row.get("AcademicYear") or "").strip()
    s = (reg_row.get("Semester") or "").strip()
    cno = (reg_row.get("CourseNo") or "").strip()
    sl = (reg_row.get("SlNo") or "").strip()
    name = (reg_row.get("CourseName") or "").strip().lower()

    hit = pick_class(by_ycs.get((y, s, cno, sl), []), reg_row)
    if hit:
        return hit, "year_sem_course_sl"
    hit = pick_class(by_ycn.get((y, s, name), []), reg_row)
    if hit:
        return hit, "year_sem_course_name"
    hit = pick_class(by_ycno.get((y, s, cno), []), reg_row)
    if hit:
        return hit, "year_sem_course_no"
    return None, "unmatched_class"


def build_enrollments(reg_rows, map_rows, student_ids, year_filter=None):
    by_ycs, by_ycn, by_ycno = build_class_indexes(map_rows)
    enrollments = []
    skipped = []
    methods = Counter()
    seen = set()

    for row in reg_rows:
        year = (row.get("AcademicYear") or "").strip()
        if year_filter and year != year_filter:
            continue
        reg_no = (row.get("RegNo") or "").strip()
        semester = (row.get("Semester") or "").strip()
        course_no = (row.get("CourseNo") or "").strip()
        sl_no = (row.get("SlNo") or "").strip()
        course_name = (row.get("CourseName") or "").strip()
        batch = (row.get("Batch") or "").strip()
        instructor = (row.get("InstructorName") or "").strip()

        base_report = {
            "reg_no": reg_no,
            "academic_year": year,
            "semester": semester,
            "course_no": course_no,
            "sl_no": sl_no,
            "course_name": course_name,
            "batch": batch,
            "instructor_name": instructor,
        }

        if not reg_no:
            skipped.append({**base_report, "reason": "missing_reg_no"})
            continue
        if student_ids and reg_no not in student_ids:
            skipped.append({**base_report, "reason": "student_not_in_phase2"})
            continue

        cls, method = resolve_class(row, by_ycs, by_ycn, by_ycno)
        if not cls:
            skipped.append({**base_report, "reason": "class_not_in_legacy_map"})
            continue

        class_ext = cls["odoo_class_id"]
        dedupe = (reg_no, class_ext)
        if dedupe in seen:
            skipped.append({**base_report, "reason": f"duplicate_student_class:{class_ext}"})
            continue
        seen.add(dedupe)

        # Deterministic external id (student + class). Do not use per-class
        # sequence counters — those shift when more students are included.
        enr_id = f"acaweb_enr_{year}_{slugify(reg_no)}_{slugify(class_ext, 48)}"

        methods[method] += 1
        enrollments.append({
            "id": enr_id,
            "student_id/id": reg_no,
            "class_id/id": class_ext,
            "enrollment_date": enrollment_date(year, semester),
            "state": "completed",
            "notes": f"ACAWEB {year} {semester} {course_no or course_name}".strip(),
        })

    return enrollments, skipped, methods


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--year", default="2017", help="Pilot year (default 2017). Use 'all' for every year.")
    parser.add_argument(
        "--require-students",
        action="store_true",
        default=True,
        help="Only emit rows whose RegNo exists in phase-2 student CSVs (default).",
    )
    parser.add_argument(
        "--include-missing-students",
        action="store_true",
        help="Also emit enrollments for RegNos not yet in phase-2 (will fail import until students exist).",
    )
    args = parser.parse_args()

    year_filter = None if args.year.lower() == "all" else args.year
    student_ids = set()
    if not args.include_missing_students:
        student_ids = load_student_ids(year_filter)
        if not student_ids:
            raise SystemExit(
                f"No students found under {STUDENTS_DIR}. "
                "Run phase 2 first, or pass --include-missing-students."
            )

    reg_rows = read_acaweb_csv("ACAWEB_tbl_CourseRegistration.csv")
    map_rows = read_utf8_csv(MAP_PATH)
    enrollments, skipped, methods = build_enrollments(
        reg_rows, map_rows, student_ids, year_filter=year_filter,
    )

    label = year_filter or "all"
    write_csv(OUT / f"enrollments_{label}.csv", ENROLL_FIELDS, enrollments)
    write_csv(OUT / f"enrollments_skipped_{label}.csv", REPORT_FIELDS, skipped)

    print(f"Wrote Phase 3 files to {OUT}")
    print(f"  Enrollments ({label}): {len(enrollments)}")
    print(f"  Skipped:               {len(skipped)}")
    print(f"  Match methods:         {dict(methods)}")
    reasons = Counter(r["reason"].split(":")[0] for r in skipped)
    print(f"  Skip reasons:          {dict(reasons)}")
    print()
    print("Import into Odoo model school.enrollment with columns:")
    print("  id, student_id/id, class_id/id, enrollment_date, state, notes")
    print("Use state=completed so historical rows bypass seat capacity checks.")


if __name__ == "__main__":
    main()
