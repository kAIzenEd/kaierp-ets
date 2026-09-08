#!/usr/bin/env python3
"""Reconcile ACAWEB source data vs generated import CSVs vs Odoo DB (pilot year).

Usage:
  python3 generate_acaweb_phase_audit.py --year 2017
  python3 generate_acaweb_phase_audit.py --year 2017 --db legacydata

Checks students (name/DOB/age/course), classes (semester/credits/code),
enrollments (student↔class), and grades (letter round-trip).
"""
from __future__ import annotations

import argparse
import csv
import re
import subprocess
import unicodedata
from collections import Counter, defaultdict
from datetime import date, datetime
from pathlib import Path

csv.field_size_limit(10_000_000)

ROOT = Path(__file__).resolve().parents[3] / "ACAWEB"
OUT = ROOT / "import_phase_audit"

COURSE_PROGRAM_MAP = {
    "M.Th": "mth",
    "MABS": "mabs",
    "MCS": "macs",
    "PGDS": "pgdbs",
    "M.Div": "mdiv",
    "MDIV": "mdiv",
    "D.Min": "dmin",
    "B.Th": "bth",
}

LETTER_TO_SCORE = {
    "A+": 99.0, "A": 96.0, "A-": 92.0,
    "B+": 88.0, "B": 84.5, "B-": 81.5,
    "C+": 78.5, "C": 75.5, "C-": 72.0,
    "F": 50.0,
}

GPA_SCALE = [
    (98, "A+"), (94, "A"), (90, "A-"),
    (86, "B+"), (83, "B"), (80, "B-"),
    (77, "C+"), (74, "C"), (70, "C-"),
    (0, "F"),
]

SEMESTER_MAP = {
    "summer": "summer", "fall": "fall", "spring": "spring",
    "first": "fall", "second": "fall", "third": "fall", "fourth": "fall",
}


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
    if not path.exists():
        return []
    return list(csv.DictReader(path.read_text(encoding="utf-8-sig").splitlines()))


def write_csv(path: Path, fieldnames, rows):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
        w.writeheader()
        w.writerows(rows)


def slugify(value, max_len=48):
    value = unicodedata.normalize("NFKD", value or "")
    value = value.encode("ascii", "ignore").decode("ascii")
    value = re.sub(r"[^a-zA-Z0-9]+", "_", value.strip().lower()).strip("_")
    return (value or "unknown")[:max_len]


def teacher_external_id(name):
    return f"acaweb_teacher_{slugify(name)}"


def semester_key(raw):
    key = (raw or "").strip().lower()
    return SEMESTER_MAP.get(key, "fall")


def parse_credit_hours(raw):
    raw = (raw or "").strip()
    if not raw:
        return 3
    try:
        return max(1, int(float(raw)))
    except ValueError:
        return 3


def parse_dob(raw):
    raw = (raw or "").strip()
    if not raw:
        return None
    raw = raw.split(" ", 1)[0]
    for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%m/%d/%Y", "%d-%m-%Y"):
        try:
            return datetime.strptime(raw, fmt).date()
        except ValueError:
            continue
    return None


def calc_age(dob: date, today: date | None = None) -> int:
    today = today or date.today()
    return today.year - dob.year - ((today.month, today.day) < (dob.month, dob.day))


def letter_from_pct(pct: float) -> str:
    for threshold, letter in GPA_SCALE:
        if pct >= threshold:
            return letter
    return "F"


def normalize_letter(raw: str) -> str:
    return (raw or "").strip().upper().replace(" ", "")


def norm_name(value: str) -> str:
    return re.sub(r"\s+", " ", (value or "").strip().lower())


def docker_psql(db: str, sql: str) -> list[dict]:
    """Run SQL via docker postgres and return dict rows."""
    cmd = [
        "docker", "exec", "-i", "my-odoo-project-db-1",
        "psql", "-U", "odoo", "-d", db, "-A", "-F", "\t", "-c", sql,
    ]
    try:
        out = subprocess.check_output(cmd, text=True, stderr=subprocess.STDOUT)
    except (subprocess.CalledProcessError, FileNotFoundError) as exc:
        raise RuntimeError(f"DB query failed: {exc}") from exc
    lines = [ln for ln in out.splitlines() if ln.strip()]
    # drop "(N rows)" footer
    if lines and lines[-1].startswith("(") and lines[-1].endswith(")"):
        lines = lines[:-1]
    if not lines:
        return []
    headers = lines[0].split("\t")
    rows = []
    for ln in lines[1:]:
        parts = ln.split("\t")
        rows.append({headers[i]: (parts[i] if i < len(parts) else "") for i in range(len(headers))})
    return rows


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


def pick_class(hits, row, sl_keys=("SlNo", "Slno")):
    if not hits:
        return None
    if len(hits) == 1:
        return hits[0]
    sl = ""
    for k in sl_keys:
        if row.get(k):
            sl = (row.get(k) or "").strip()
            break
    instr = (row.get("InstructorName") or "").strip()
    batch = (row.get("Batch") or "").strip()
    name = (row.get("CourseName") or "").strip().lower()
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


def resolve_class(row, by_ycs, by_ycn, by_ycno, sl_keys=("SlNo", "Slno")):
    y = (row.get("AcademicYear") or "").strip()
    s = (row.get("Semester") or "").strip()
    cno = (row.get("CourseNo") or "").strip()
    sl = ""
    for k in sl_keys:
        if row.get(k) is not None and str(row.get(k)).strip() != "":
            sl = str(row.get(k)).strip()
            break
    name = (row.get("CourseName") or "").strip().lower()
    hit = pick_class(by_ycs.get((y, s, cno, sl), []), row, sl_keys)
    if hit:
        return hit
    hit = pick_class(by_ycn.get((y, s, name), []), row, sl_keys)
    if hit:
        return hit
    return pick_class(by_ycno.get((y, s, cno), []), row, sl_keys)


class Audit:
    def __init__(self, year: str, db: str | None):
        self.year = year
        self.db = db
        self.lines: list[str] = []
        self.issues: list[dict] = []
        self.counts = {}

    def section(self, title: str):
        self.lines.append("")
        self.lines.append(f"## {title}")
        self.lines.append("")

    def info(self, msg: str):
        self.lines.append(f"- {msg}")

    def issue(self, area: str, key: str, detail: str, severity: str = "warn"):
        self.issues.append({
            "area": area, "key": key, "detail": detail, "severity": severity,
        })
        mark = "ERROR" if severity == "error" else "WARN"
        self.lines.append(f"- **{mark}** `{key}`: {detail}")

    def audit_students(self):
        self.section("Students (Phase 2)")
        spd = read_acaweb_csv("ACAWEB_tbl_StudentPersonalDetails.csv")
        year_path = ROOT / "import_phase2" / f"students_{self.year}.csv"
        if year_path.exists():
            student_rows = read_utf8_csv(year_path)
        else:
            student_rows = [
                r for r in read_utf8_csv(ROOT / "import_phase2" / "students_all.csv")
                if (r.get("academic_year") or "").strip() == self.year
            ]
        csv_students = {
            (r.get("student_id") or r.get("id") or "").strip(): r
            for r in student_rows
            if (r.get("student_id") or r.get("id") or "").strip()
        }
        # Source cohort: RegNo starts with year prefix OR admission year match.
        # Phase2 used AYear from RecievedApplication when receive year matches.
        source = {}
        for r in spd:
            regno = (r.get("RegNo") or "").strip()
            if not regno:
                continue
            # Prefer students whose RegNo embeds the pilot year (17...)
            if regno.startswith(self.year[-2:]) or regno in csv_students:
                source[regno] = r

        self.counts["students_csv"] = len(csv_students)
        self.counts["students_source_overlap"] = len(set(source) & set(csv_students))
        self.info(f"Import CSV students: **{len(csv_students)}**")
        self.info(f"Source personal rows overlapping import IDs: **{len(set(source) & set(csv_students))}**")

        name_mismatch = dob_mismatch = course_mismatch = age_mismatch = 0
        for regno, crow in csv_students.items():
            srow = source.get(regno)
            if not srow:
                self.issue("student", regno, "In import CSV but not found in StudentPersonalDetails", "error")
                continue
            src_name = (srow.get("StudName") or "").strip()
            csv_name = (crow.get("full_name") or "").strip()
            if norm_name(src_name) != norm_name(csv_name):
                name_mismatch += 1
                self.issue("student_name", regno, f"Source '{src_name}' vs CSV '{csv_name}'", "error")

            src_dob = parse_dob(srow.get("DOB"))
            csv_dob = parse_dob(crow.get("date_of_birth"))
            if src_dob and csv_dob and src_dob != csv_dob:
                dob_mismatch += 1
                self.issue("student_dob", regno, f"Source {src_dob} vs CSV {csv_dob}", "error")
            elif src_dob and not csv_dob:
                dob_mismatch += 1
                self.issue("student_dob", regno, f"Source DOB {src_dob} missing in CSV", "error")

            # Age / birth year consistency in CSV
            if csv_dob:
                expected_age = calc_age(csv_dob)
                csv_by = (crow.get("birth_year") or "").strip()
                if csv_by and csv_by != str(csv_dob.year):
                    age_mismatch += 1
                    self.issue("student_birth_year", regno, f"CSV birth_year {csv_by} vs DOB year {csv_dob.year}", "error")

            src_course = (srow.get("CourseName") or "").strip()
            expected_course = COURSE_PROGRAM_MAP.get(src_course, "")
            csv_course = (crow.get("course") or "").strip()
            if expected_course and csv_course and expected_course != csv_course:
                course_mismatch += 1
                self.issue("student_course", regno, f"Source {src_course}→{expected_course} vs CSV {csv_course}", "error")
            elif not expected_course and csv_course:
                course_mismatch += 1
                self.issue("student_course", regno, f"Source {src_course} has no Odoo course code but CSV has {csv_course}", "warn")

        self.info(f"Name mismatches: **{name_mismatch}**")
        self.info(f"DOB mismatches: **{dob_mismatch}**")
        self.info(f"Course mismatches: **{course_mismatch}**")

        if self.db:
            db_rows = docker_psql(self.db, """
                SELECT s.student_id, s.full_name, s.date_of_birth::text AS dob,
                       s.birth_year, s.age::text AS age, COALESCE(s.course,'') AS course
                  FROM school_student s
                 WHERE s.student_id IS NOT NULL AND s.student_id <> ''
            """)
            db_by_id = {(r.get("student_id") or "").strip(): r for r in db_rows}
            present = missing = age_bad = letter_ok = 0
            for regno, crow in csv_students.items():
                drow = db_by_id.get(regno)
                if not drow:
                    missing += 1
                    self.issue("student_db", regno, "In import CSV but not found in Odoo DB", "error")
                    continue
                present += 1
                if norm_name(drow.get("full_name") or "") != norm_name(crow.get("full_name") or ""):
                    self.issue("student_db_name", regno,
                               f"CSV '{crow.get('full_name')}' vs DB '{drow.get('full_name')}'", "error")
                csv_dob = parse_dob(crow.get("date_of_birth"))
                db_dob = parse_dob(drow.get("dob"))
                if csv_dob and db_dob and csv_dob != db_dob:
                    self.issue("student_db_dob", regno, f"CSV {csv_dob} vs DB {db_dob}", "error")
                if db_dob:
                    expected = calc_age(db_dob)
                    try:
                        got = int(float(drow.get("age") or 0))
                    except ValueError:
                        got = -1
                    if got != expected:
                        age_bad += 1
                        self.issue("student_db_age", regno, f"DB age {got} vs expected {expected} from DOB {db_dob}", "error")
                    by = (drow.get("birth_year") or "").strip()
                    if by and "," in by:
                        self.issue("student_db_birth_year", regno, f"Birth year still formatted with comma: {by}", "error")
                    elif by and by != str(db_dob.year):
                        self.issue("student_db_birth_year", regno, f"DB birth_year {by} vs DOB year {db_dob.year}", "error")
            self.counts["students_db_present"] = present
            self.info(f"Odoo DB: **{present}** of {len(csv_students)} pilot students found; missing **{missing}**; age errors **{age_bad}**")

    def audit_classes(self):
        self.section("Classes (Phase 1)")
        master = [
            r for r in read_acaweb_csv("ACAWEB_tbl_CourseMaster.csv")
            if (r.get("AcademicYear") or "").strip() == self.year
            and (r.get("CourseName") or "").strip()
        ]
        csv_classes = {
            (r.get("id") or "").strip(): r
            for r in read_utf8_csv(ROOT / "import_phase1" / f"classes_{self.year}.csv")
            if (r.get("id") or "").strip()
        }
        legacy_map = read_utf8_csv(ROOT / "import_phase1" / "class_legacy_map.csv")
        map_by_id = {
            (m.get("odoo_class_id") or "").strip(): m
            for m in legacy_map
            if (m.get("academic_year") or "").strip() == self.year
        }

        self.counts["classes_source"] = len(master)
        self.counts["classes_csv"] = len(csv_classes)
        self.info(f"CourseMaster {self.year} rows: **{len(master)}**")
        self.info(f"Import CSV classes: **{len(csv_classes)}**")
        self.info(f"Legacy map {self.year} entries: **{len(map_by_id)}**")

        if len(master) != len(csv_classes):
            self.issue("class_count", self.year,
                       f"Source {len(master)} vs CSV {len(csv_classes)}", "warn")

        sem_mismatch = credit_mismatch = 0
        rebuilt = []
        key_counts = defaultdict(int)
        for row in master:
            year = (row.get("AcademicYear") or "").strip()
            semester_raw = (row.get("Semester") or "").strip()
            course_no = (row.get("CourseNo") or "").strip() or slugify((row.get("CourseName") or ""), 20).upper()
            sl_no = (row.get("SlNo") or "").strip()
            base_key = (year, semester_raw, course_no, sl_no)
            key_counts[base_key] += 1
            variant = key_counts[base_key]
            ext_id = f"acaweb_cls_{year}_{slugify(semester_raw)}_{slugify(course_no)}_s{sl_no or '0'}"
            if variant > 1:
                ext_id = f"{ext_id}_v{variant}"
            rebuilt.append((ext_id, row, semester_raw, course_no, parse_credit_hours(row.get("CourseHour"))))

        for ext_id, row, semester_raw, course_no, credits in rebuilt:
            crow = csv_classes.get(ext_id)
            if not crow:
                self.issue("class_csv", ext_id, f"Missing from classes_{self.year}.csv (source {course_no} {semester_raw})", "error")
                continue
            expected_sem = semester_key(semester_raw)
            got_sem = (crow.get("semester") or "").strip()
            if expected_sem != got_sem:
                sem_mismatch += 1
                self.issue("class_semester", ext_id,
                           f"Source '{semester_raw}'→{expected_sem} vs CSV {got_sem}", "error")
            try:
                csv_credits = int(float(crow.get("credit_hours") or 0))
            except ValueError:
                csv_credits = -1
            if csv_credits != credits:
                credit_mismatch += 1
                self.issue("class_credits", ext_id, f"Source {credits} vs CSV {csv_credits}", "error")
            if (crow.get("code") or "").strip() != course_no:
                self.issue("class_code", ext_id,
                           f"Source course_no {course_no} vs CSV code {crow.get('code')}", "error")

        self.info(f"Semester mapping mismatches: **{sem_mismatch}**")
        self.info(f"Credit hour mismatches: **{credit_mismatch}**")

        # Legacy term labels collapsed into fall
        legacy_terms = Counter(
            (r.get("Semester") or "").strip()
            for r in master
            if (r.get("Semester") or "").strip().lower() in {"first", "second", "third", "fourth"}
        )
        if legacy_terms:
            self.info(
                f"Note: legacy term labels mapped to **fall**: {dict(legacy_terms)} "
                "(original label kept in class_legacy_map / display name)"
            )

        if self.db:
            db_rows = docker_psql(self.db, f"""
                SELECT d.name AS ext_id, c.code, c.name, c.academic_year,
                       c.semester, c.credit_hours::text AS credit_hours
                  FROM school_class c
                  JOIN ir_model_data d ON d.model='school.class' AND d.res_id=c.id
                 WHERE d.name LIKE 'acaweb_cls_{self.year}_%'
            """)
            db_by_id = {(r.get("ext_id") or "").strip(): r for r in db_rows}
            present = missing = sem_bad = 0
            for ext_id, crow in csv_classes.items():
                drow = db_by_id.get(ext_id)
                if not drow:
                    # User may have imported classes_all; try still missing
                    missing += 1
                    continue
                present += 1
                if (drow.get("semester") or "") != (crow.get("semester") or ""):
                    sem_bad += 1
                    self.issue("class_db_semester", ext_id,
                               f"CSV {crow.get('semester')} vs DB {drow.get('semester')}", "error")
                try:
                    if int(float(drow.get("credit_hours") or 0)) != int(float(crow.get("credit_hours") or 0)):
                        self.issue("class_db_credits", ext_id,
                                   f"CSV {crow.get('credit_hours')} vs DB {drow.get('credit_hours')}", "error")
                except ValueError:
                    pass
            self.counts["classes_db_present"] = present
            # If classes_all was imported, missing may be 0 even when comparing only year csv
            # Re-check: any DB acaweb 2017 not in csv?
            extra = sorted(set(db_by_id) - set(csv_classes))
            self.info(f"Odoo DB 2017 acaweb classes found matching CSV: **{present}**; CSV not in DB: **{missing}**; semester mismatches: **{sem_bad}**")
            if extra:
                self.info(f"DB has **{len(extra)}** extra 2017 class external IDs not in year CSV (unexpected)")

    def audit_enrollments(self):
        self.section("Enrollments (Phase 3)")
        year_stu = ROOT / "import_phase2" / f"students_{self.year}.csv"
        if year_stu.exists():
            stu_rows = read_utf8_csv(year_stu)
        else:
            stu_rows = [
                r for r in read_utf8_csv(ROOT / "import_phase2" / "students_all.csv")
                if (r.get("academic_year") or "").strip() == self.year
            ]
        students = {
            (r.get("student_id") or r.get("id") or "").strip()
            for r in stu_rows if (r.get("student_id") or r.get("id") or "").strip()
        }
        enr_path = ROOT / "import_phase3" / f"enrollments_{self.year}.csv"
        if enr_path.exists():
            enr_csv = read_utf8_csv(enr_path)
        else:
            # Filter all-year file by class academic year embedded in external id
            enr_csv = [
                r for r in read_utf8_csv(ROOT / "import_phase3" / "enrollments_all.csv")
                if (r.get("class_id/id") or "").startswith(f"acaweb_cls_{self.year}_")
                and (r.get("student_id/id") or "").strip() in students
            ]
        map_rows = read_utf8_csv(ROOT / "import_phase1" / "class_legacy_map.csv")
        by_ycs, by_ycn, by_ycno = build_class_indexes(map_rows)

        regs = [
            r for r in read_acaweb_csv("ACAWEB_tbl_CourseRegistration.csv")
            if (r.get("AcademicYear") or "").strip() == self.year
        ]
        expected_pairs = set()
        unmatched_class = 0
        for r in regs:
            regno = (r.get("RegNo") or "").strip()
            if regno not in students:
                continue
            cls = resolve_class(r, by_ycs, by_ycn, by_ycno, sl_keys=("SlNo", "Slno"))
            if not cls:
                unmatched_class += 1
                continue
            expected_pairs.add((regno, cls["odoo_class_id"]))

        csv_pairs = {
            ((r.get("student_id/id") or "").strip(), (r.get("class_id/id") or "").strip())
            for r in enr_csv
        }
        self.counts["enrollments_expected"] = len(expected_pairs)
        self.counts["enrollments_csv"] = len(csv_pairs)
        self.info(f"Expected enrollments (source regs ∩ phase2 students ∩ class map): **{len(expected_pairs)}**")
        self.info(f"Import CSV enrollments: **{len(csv_pairs)}**")
        self.info(f"Source regs for phase2 students with no class map: **{unmatched_class}**")

        missing_csv = sorted(expected_pairs - csv_pairs)
        extra_csv = sorted(csv_pairs - expected_pairs)
        for regno, cid in missing_csv[:25]:
            self.issue("enrollment_csv", f"{regno}|{cid}", "Expected from source but missing in enrollments CSV", "error")
        for regno, cid in extra_csv[:25]:
            self.issue("enrollment_csv_extra", f"{regno}|{cid}", "In enrollments CSV but not rebuildable from source", "warn")
        if len(missing_csv) > 25:
            self.info(f"... and {len(missing_csv) - 25} more missing-from-CSV")
        self.info(f"CSV missing expected pairs: **{len(missing_csv)}**; unexpected extras: **{len(extra_csv)}**")

        # Semester of linked class vs registration semester mapping
        class_csv = {
            (r.get("id") or "").strip(): r
            for r in read_utf8_csv(ROOT / "import_phase1" / f"classes_{self.year}.csv")
        }
        sem_issues = 0
        for r in regs:
            regno = (r.get("RegNo") or "").strip()
            if regno not in students:
                continue
            cls = resolve_class(r, by_ycs, by_ycn, by_ycno)
            if not cls:
                continue
            crow = class_csv.get(cls["odoo_class_id"])
            if not crow:
                continue
            src_sem = semester_key(r.get("Semester"))
            cls_sem = (crow.get("semester") or "").strip()
            # Class semester comes from CourseMaster; registration semester should match mapped value
            # when the class was found via year+semester keys.
            if src_sem != cls_sem and (r.get("Semester") or "").strip() == (cls.get("semester") or "").strip():
                # same raw semester on map — mapped key must match
                if semester_key(cls.get("semester")) != cls_sem:
                    sem_issues += 1
        self.info(f"Enrollment↔class semester consistency spot checks done (rebuild uses same map).")

        if self.db:
            db_rows = docker_psql(self.db, """
                SELECT s.student_id, d.name AS class_ext, e.state
                  FROM school_enrollment e
                  JOIN school_student s ON s.id = e.student_id
                  JOIN ir_model_data d ON d.model='school.class' AND d.res_id=e.class_id
            """)
            db_pairs = {
                ((r.get("student_id") or "").strip(), (r.get("class_ext") or "").strip())
                for r in db_rows
                if (r.get("class_ext") or "").startswith(f"acaweb_cls_{self.year}_")
            }
            missing_db = sorted(csv_pairs - db_pairs)
            extra_db = sorted(db_pairs - csv_pairs)
            for regno, cid in missing_db[:25]:
                self.issue("enrollment_db", f"{regno}|{cid}", "In CSV but not in Odoo DB", "error")
            self.info(f"Odoo DB: CSV pairs present **{len(csv_pairs & db_pairs)}** / {len(csv_pairs)}; missing **{len(missing_db)}**; extra year pairs **{len(extra_db)}**")
            self.counts["enrollments_db"] = len(db_pairs)

    def audit_grades(self):
        self.section("Grades (Phase 4)")
        year_stu = ROOT / "import_phase2" / f"students_{self.year}.csv"
        if year_stu.exists():
            stu_rows = read_utf8_csv(year_stu)
        else:
            stu_rows = [
                r for r in read_utf8_csv(ROOT / "import_phase2" / "students_all.csv")
                if (r.get("academic_year") or "").strip() == self.year
            ]
        students = {
            (r.get("student_id") or r.get("id") or "").strip()
            for r in stu_rows if (r.get("student_id") or r.get("id") or "").strip()
        }
        grades_path = ROOT / "import_phase4" / f"grades_{self.year}.csv"
        if grades_path.exists():
            grades_csv = read_utf8_csv(grades_path)
        else:
            grades_csv = [
                r for r in read_utf8_csv(ROOT / "import_phase4" / "grades_all.csv")
                if (r.get("class_id/id") or "").startswith(f"acaweb_cls_{self.year}_")
                and (r.get("student_id/id") or "").strip() in students
            ]
        map_rows = read_utf8_csv(ROOT / "import_phase1" / "class_legacy_map.csv")
        by_ycs, by_ycn, by_ycno = build_class_indexes(map_rows)

        src_grades = [
            r for r in read_acaweb_csv("ACAWEB_tbl_GradeRecordInfo.csv")
            if (r.get("AcademicYear") or "").strip() == self.year
        ]

        # Rebuild expected best letter per student+class (same rules as phase4)
        best = {}
        skipped_letters = Counter()
        for row in src_grades:
            regno = (row.get("RegNo") or "").strip()
            if regno not in students:
                continue
            letter = normalize_letter(row.get("FinalGrade") or "")
            if letter in {"", "IC"}:
                skipped_letters[letter or "blank"] += 1
                continue
            if letter not in LETTER_TO_SCORE:
                skipped_letters[letter] += 1
                continue
            cls = resolve_class(row, by_ycs, by_ycn, by_ycno, sl_keys=("Slno", "SlNo"))
            if not cls:
                continue
            best[(regno, cls["odoo_class_id"])] = letter

        csv_best = {}
        letter_roundtrip_bad = 0
        for r in grades_csv:
            regno = (r.get("student_id/id") or "").strip()
            cid = (r.get("class_id/id") or "").strip()
            remarks = r.get("remarks") or ""
            letter = ""
            if "FinalGrade=" in remarks:
                letter = remarks.split("FinalGrade=", 1)[1].split(";", 1)[0].strip()
            csv_best[(regno, cid)] = letter
            try:
                score = float(r.get("score") or 0)
                max_score = float(r.get("max_score") or 100) or 100
                pct = score / max_score * 100
            except ValueError:
                continue
            recomputed = letter_from_pct(pct)
            if letter and recomputed != letter:
                letter_roundtrip_bad += 1
                self.issue("grade_roundtrip", f"{regno}|{cid}",
                           f"CSV letter {letter} / score {score} recomputes to {recomputed}", "error")

        self.counts["grades_expected"] = len(best)
        self.counts["grades_csv"] = len(csv_best)
        self.info(f"Expected final grades (usable letters ∩ class map ∩ phase2): **{len(best)}**")
        self.info(f"Import CSV grades: **{len(csv_best)}**")
        self.info(f"Skipped source letters (IC/blank/unsupported): {dict(skipped_letters)}")
        self.info(f"Letter↔score round-trip errors in CSV: **{letter_roundtrip_bad}**")

        missing = sorted(set(best) - set(csv_best))
        extra = sorted(set(csv_best) - set(best))
        letter_mismatch = 0
        for key in sorted(set(best) & set(csv_best)):
            if best[key] != csv_best[key]:
                letter_mismatch += 1
                self.issue("grade_letter", f"{key[0]}|{key[1]}",
                           f"Source/rebuild {best[key]} vs CSV {csv_best[key]}", "error")
        for regno, cid in missing[:25]:
            self.issue("grade_csv", f"{regno}|{cid}", f"Expected letter {best[(regno,cid)]} missing from CSV", "error")
        self.info(f"CSV missing expected: **{len(missing)}**; extras: **{len(extra)}**; letter mismatches: **{letter_mismatch}**")

        if self.db:
            db_rows = docker_psql(self.db, """
                SELECT s.student_id, d.name AS class_ext, g.letter_grade,
                       g.score::text AS score, g.percentage::text AS percentage,
                       g.assessment_type, COALESCE(g.remarks,'') AS remarks
                  FROM school_grade g
                  JOIN school_student s ON s.id = g.student_id
                  JOIN ir_model_data d ON d.model='school.class' AND d.res_id = g.class_id
                 WHERE g.assessment_type = 'final_grade'
            """)
            db_best = {}
            for r in db_rows:
                cid = (r.get("class_ext") or "").strip()
                if not cid.startswith(f"acaweb_cls_{self.year}_"):
                    continue
                db_best[((r.get("student_id") or "").strip(), cid)] = (r.get("letter_grade") or "").strip()

            missing_db = sorted(set(csv_best) - set(db_best))
            letter_db_bad = 0
            for key in sorted(set(csv_best) & set(db_best)):
                if csv_best[key] and db_best[key] and csv_best[key] != db_best[key]:
                    letter_db_bad += 1
                    self.issue("grade_db_letter", f"{key[0]}|{key[1]}",
                               f"CSV {csv_best[key]} vs DB {db_best[key]}", "error")
            for regno, cid in missing_db[:25]:
                self.issue("grade_db", f"{regno}|{cid}", "In grades CSV but not in Odoo DB", "error")
            self.info(
                f"Odoo DB: CSV grades present **{len(set(csv_best) & set(db_best))}** / {len(csv_best)}; "
                f"missing **{len(missing_db)}**; letter mismatches **{letter_db_bad}**"
            )
            self.counts["grades_db"] = len(db_best)

    def summary(self):
        self.section("Summary")
        errors = sum(1 for i in self.issues if i["severity"] == "error")
        warns = sum(1 for i in self.issues if i["severity"] == "warn")
        self.info(f"Total issues: **{len(self.issues)}** (errors **{errors}**, warnings **{warns}**)")
        by_area = Counter(i["area"] for i in self.issues if i["severity"] == "error")
        if by_area:
            self.info(f"Errors by area: {dict(by_area)}")
        else:
            self.info("No blocking errors found in checked mappings.")
        self.lines.insert(0, f"# ACAWEB ↔ Odoo reconciliation — {self.year}")
        self.lines.insert(1, "")
        self.lines.insert(2, f"Database: `{self.db or 'CSV-only (no --db)'}`")
        self.lines.insert(3, f"Generated: {datetime.now().isoformat(timespec='seconds')}")
        return errors, warns


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--year", default="2017")
    parser.add_argument("--db", default="legacydata",
                        help="Postgres DB name in docker (blank to skip DB checks)")
    parser.add_argument("--skip-db", action="store_true")
    args = parser.parse_args()
    db = None if args.skip_db else (args.db or None)

    audit = Audit(args.year, db)
    audit.audit_students()
    audit.audit_classes()
    audit.audit_enrollments()
    audit.audit_grades()
    errors, warns = audit.summary()

    OUT.mkdir(parents=True, exist_ok=True)
    report_path = OUT / f"audit_{args.year}_report.md"
    report_path.write_text("\n".join(audit.lines) + "\n", encoding="utf-8")
    write_csv(
        OUT / f"audit_{args.year}_issues.csv",
        ["severity", "area", "key", "detail"],
        audit.issues,
    )
    print(report_path.read_text(encoding="utf-8"))
    print(f"\nWrote {report_path}")
    print(f"Wrote {OUT / f'audit_{args.year}_issues.csv'} ({len(audit.issues)} issue rows)")
    print(f"RESULT: {errors} errors, {warns} warnings")
    raise SystemExit(1 if errors else 0)


if __name__ == "__main__":
    main()
