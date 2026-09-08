#!/usr/bin/env python3
"""Generate Odoo import CSVs for ACAWEB migration - Phase 4 (final grades).

Source: ACAWEB_tbl_GradeRecordInfo.csv
Links:
  - students via RegNo == school.student external id / student_id
  - classes via class_legacy_map.csv (same matching as Phase 3)
Stores FinalGrade as score midpoints so Odoo recomputes the same letter
on the ETS scale (assessment_type=final_grade).
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
OUT = ROOT / "import_phase4"

# Midpoints that fall inside each ETS letter band in school.grade.GPA_SCALE.
LETTER_TO_SCORE = {
    "A+": 99.0,
    "A": 96.0,
    "A-": 92.0,
    "B+": 88.0,
    "B": 84.5,
    "B-": 81.5,
    "C+": 78.5,
    "C": 75.5,
    "C-": 72.0,
    "F": 50.0,
}
SKIP_LETTERS = {"IC", ""}  # Incomplete / blank — report, do not import as F

GRADE_FIELDS = [
    "id",
    "student_id/id",
    "class_id/id",
    "assessment_type",
    "date",
    "max_score",
    "score",
    "weight",
    "is_published",
    "remarks",
]
REPORT_FIELDS = [
    "reg_no",
    "academic_year",
    "semester",
    "course_no",
    "sl_no",
    "course_name",
    "final_grade",
    "gpa",
    "credit_hours",
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


def grade_date(year: str, semester: str) -> str:
    try:
        y = int(year)
    except ValueError:
        return ""
    sem = (semester or "").strip().lower()
    if sem == "summer":
        return f"{y}-07-15"
    if sem == "spring":
        return f"{y}-04-30"
    return f"{y}-12-15"


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


def pick_class(hits, row):
    if not hits:
        return None
    if len(hits) == 1:
        return hits[0]
    sl = (row.get("Slno") or row.get("SlNo") or "").strip()
    name = (row.get("CourseName") or "").strip().lower()
    prefer = [h for h in hits if h.get("sl_no") == sl]
    if not prefer and name:
        prefer = [h for h in hits if (h.get("course_name") or "").strip().lower() == name]
    return (prefer or hits)[0]


def resolve_class(row, by_ycs, by_ycn, by_ycno):
    y = (row.get("AcademicYear") or "").strip()
    s = (row.get("Semester") or "").strip()
    cno = (row.get("CourseNo") or "").strip()
    sl = (row.get("Slno") or row.get("SlNo") or "").strip()
    name = (row.get("CourseName") or "").strip().lower()

    hit = pick_class(by_ycs.get((y, s, cno, sl), []), row)
    if hit:
        return hit, "year_sem_course_sl"
    hit = pick_class(by_ycn.get((y, s, name), []), row)
    if hit:
        return hit, "year_sem_course_name"
    hit = pick_class(by_ycno.get((y, s, cno), []), row)
    if hit:
        return hit, "year_sem_course_no"
    return None, "unmatched_class"


def normalize_letter(raw: str) -> str:
    return (raw or "").strip().upper().replace(" ", "")


def build_grades(grade_rows, map_rows, student_ids, year_filter=None):
    by_ycs, by_ycn, by_ycno = build_class_indexes(map_rows)
    # Prefer last usable letter per student+class (file order).
    best = {}  # (reg_no, class_ext) -> dict payload
    skipped = []
    methods = Counter()

    for row in grade_rows:
        year = (row.get("AcademicYear") or "").strip()
        if year_filter and year != year_filter:
            continue
        reg_no = (row.get("RegNo") or "").strip()
        semester = (row.get("Semester") or "").strip()
        course_no = (row.get("CourseNo") or "").strip()
        sl_no = (row.get("Slno") or row.get("SlNo") or "").strip()
        course_name = (row.get("CourseName") or "").strip()
        letter = normalize_letter(row.get("FinalGrade") or "")
        gpa = (row.get("GPA") or "").strip()
        credits = (row.get("CreditHours") or "").strip()

        base_report = {
            "reg_no": reg_no,
            "academic_year": year,
            "semester": semester,
            "course_no": course_no,
            "sl_no": sl_no,
            "course_name": course_name,
            "final_grade": letter,
            "gpa": gpa,
            "credit_hours": credits,
        }

        if not reg_no:
            skipped.append({**base_report, "reason": "missing_reg_no"})
            continue
        if student_ids and reg_no not in student_ids:
            skipped.append({**base_report, "reason": "student_not_in_phase2"})
            continue
        if letter in SKIP_LETTERS:
            skipped.append({**base_report, "reason": "incomplete_or_blank"})
            continue
        if letter not in LETTER_TO_SCORE:
            skipped.append({**base_report, "reason": f"unsupported_letter:{letter}"})
            continue

        cls, method = resolve_class(row, by_ycs, by_ycn, by_ycno)
        if not cls:
            skipped.append({**base_report, "reason": "class_not_in_legacy_map"})
            continue

        class_ext = cls["odoo_class_id"]
        key = (reg_no, class_ext)
        methods[method] += 1
        score = LETTER_TO_SCORE[letter]
        payload = {
            "id": f"acaweb_grd_{year}_{slugify(reg_no)}_{slugify(class_ext, 48)}",
            "student_id/id": reg_no,
            "class_id/id": class_ext,
            "assessment_type": "final_grade",
            "date": grade_date(year, semester),
            "max_score": "100",
            "score": f"{score:g}",
            "weight": "100",
            "is_published": "True",
            "remarks": (
                f"ACAWEB FinalGrade={letter}"
                + (f"; quality_points={gpa}" if gpa else "")
                + (f"; credits={credits}" if credits else "")
            ),
            "_letter": letter,
        }
        prev = best.get(key)
        if prev and prev.get("_letter") != letter:
            skipped.append({
                **base_report,
                "reason": f"superseded_conflict:{prev['_letter']}->{letter}",
            })
        best[key] = payload

    grades = []
    for payload in best.values():
        payload.pop("_letter", None)
        grades.append(payload)
    return grades, skipped, methods


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--year", default="2017", help="Pilot year (default 2017). Use 'all' for every year.")
    parser.add_argument(
        "--include-missing-students",
        action="store_true",
        help="Also emit grades for RegNos not yet in phase-2 (will fail import until students exist).",
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

    grade_rows = read_acaweb_csv("ACAWEB_tbl_GradeRecordInfo.csv")
    map_rows = read_utf8_csv(MAP_PATH)
    grades, skipped, methods = build_grades(
        grade_rows, map_rows, student_ids, year_filter=year_filter,
    )

    label = year_filter or "all"
    write_csv(OUT / f"grades_{label}.csv", GRADE_FIELDS, grades)
    write_csv(OUT / f"grades_skipped_{label}.csv", REPORT_FIELDS, skipped)

    print(f"Wrote Phase 4 files to {OUT}")
    print(f"  Grades ({label}): {len(grades)}")
    print(f"  Skipped:          {len(skipped)}")
    print(f"  Match methods:    {dict(methods)}")
    reasons = Counter(r["reason"].split(":")[0] for r in skipped)
    print(f"  Skip reasons:     {dict(reasons)}")
    letters = Counter()
    for g in grades:
        # recover letter from remarks prefix
        rem = g.get("remarks") or ""
        if "FinalGrade=" in rem:
            letters[rem.split("FinalGrade=", 1)[1].split(";", 1)[0]] += 1
    print(f"  Letter mix:       {dict(letters)}")
    print()
    print("Import into Odoo model school.grade with columns:")
    print("  id, student_id/id, class_id/id, assessment_type, date, max_score, score, weight, is_published, remarks")
    print("assessment_type=final_grade feeds transcripts.")


if __name__ == "__main__":
    main()
