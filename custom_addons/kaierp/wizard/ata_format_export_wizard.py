# -*- coding: utf-8 -*-
import base64
import io
import re
from datetime import date

from odoo import fields, models, _
from odoo.addons.kaierp.models.legacy_dates import age_in_years, is_missing_dob


def _year_token(value):
    """Return first 4-digit year found in a string, else empty."""
    if not value:
        return ''
    match = re.search(r'(?:19|20)\d{2}', str(value))
    return match.group(0) if match else ''


def _study_span(enroll, grad_month_year):
    """Build 'YYYY-YYYY' when both ends exist; else whatever we have."""
    start = _year_token(enroll) or (str(enroll).strip() if enroll else '')
    end = _year_token(grad_month_year)
    if start and end:
        return f'{start}-{end}'
    return start or end or ''


def _is_missing_dob(dob):
    return is_missing_dob(dob)


def _age_on(dob, on_date):
    """Age in full years on on_date, or empty when DOB is a legacy placeholder."""
    years = age_in_years(dob, on_date)
    return years or ''


def _sel_label(record, field_name):
    value = record[field_name]
    if not value:
        return ''
    field = record._fields[field_name]
    selection = field.selection
    if callable(selection):
        selection = selection(record)
    return dict(selection or []).get(value, value)


class SchoolAtaFormatExportWizard(models.TransientModel):
    _name = 'school.ata.format.export.wizard'
    _description = 'ATA Format Excel Export'

    admission_year = fields.Char(
        string='Admission Year',
        required=True,
        size=4,
        default=lambda self: str(date.today().year),
        help='Exports students whose admission date falls in this calendar year (YYYY).',
    )
    include_inactive = fields.Boolean(
        string='Include Inactive / Graduated',
        default=True,
        help='When unchecked, only active students are included.',
    )
    state = fields.Selection(
        [('draft', 'Draft'), ('done', 'Done')],
        default='draft',
    )
    file_data = fields.Binary(string='Export File', readonly=True)
    file_name = fields.Char(string='Filename', readonly=True)
    student_count = fields.Integer(string='Students Exported', readonly=True)

    def action_export(self):
        self.ensure_one()
        year_str = (self.admission_year or '').strip()
        if not year_str.isdigit() or len(year_str) != 4:
            raise UserError(_('Enter a 4-digit admission year (e.g. 2026).'))
        year = int(year_str)
        if year < 1990 or year > 2100:
            raise UserError(_('Enter a valid admission year.'))

        try:
            import xlsxwriter
        except ImportError as exc:
            raise UserError(_(
                'Excel export requires the xlsxwriter Python package on the server.',
            )) from exc

        domain = [
            ('admission_date', '>=', f'{year}-01-01'),
            ('admission_date', '<=', f'{year}-12-31'),
        ]
        if not self.include_inactive:
            domain.append(('state', '=', 'active'))

        students = self.env['school.student'].search(domain, order='name, id')
        if not students:
            raise UserError(_(
                'No students found with an admission date in %s.',
                year,
            ))

        content = self._build_xlsx(students, year)
        filename = f'ATA_Format_{year}.xlsx'
        self.write({
            'file_data': base64.b64encode(content),
            'file_name': filename,
            'student_count': len(students),
            'state': 'done',
        })
        return {
            'type': 'ir.actions.act_window',
            'res_model': self._name,
            'res_id': self.id,
            'view_mode': 'form',
            'target': 'new',
        }

    def action_download(self):
        self.ensure_one()
        if not self.file_data:
            raise UserError(_('Generate the export first.'))
        return {
            'type': 'ir.actions.act_url',
            'url': (
                f'/web/content/?model={self._name}&id={self.id}'
                f'&field=file_data&filename_field=file_name&download=true'
            ),
            'target': 'self',
        }

    # ── Excel layout ──────────────────────────────────────────

    def _headers(self):
        """Two-row cleaner headers aligned with ATA column groups."""
        # (section, column)
        return [
            ('Identity', 'SL #'),
            ('Identity', 'Name'),
            ('Identity', 'Gender'),
            ('Identity', 'Age (at admission)'),
            ('Identity', 'State'),
            ('Identity', 'Year of Admission'),
            ('Secular', 'Class X — Month & Year of Passing'),
            ('Secular', 'Class XI — Month & Year of Passing'),
            ('Secular', 'Class XII — Month & Year of Passing'),
            ('Secular', 'Diploma — Area'),
            ('Secular', 'Diploma — Year of Study'),
            ('Secular', 'Diploma — Month & Year of Passing'),
            ('Secular', 'UG Degree — Area'),
            ('Secular', 'UG Degree — Year of Study'),
            ('Secular', 'UG Degree — Month & Year of Passing'),
            ('Secular', 'UG Degree — Grade/Class'),
            ('Theological', 'Dip.Th — ATA/SSC/Other'),
            ('Theological', 'Dip.Th — ATA Regd #'),
            ('Theological', 'Dip.Th — Year of Study'),
            ('Theological', 'Dip.Th — Month & Year of Passing'),
            ('Theological', 'Dip.Th — Credit Hours & Letter Grade'),
            ('Theological', 'Dip.Th — ATA Emboss (Yes/No)'),
            ('Theological', 'Dip.Th — College / Institution'),
            ('Theological', 'B.Th — ATA/SSC/Other'),
            ('Theological', 'B.Th — ATA Regd #'),
            ('Theological', 'B.Th — Year of Study'),
            ('Theological', 'B.Th — Month & Year of Passing'),
            ('Theological', 'B.Th — Credit Hours & Letter Grade'),
            ('Theological', 'B.Th — ATA Emboss (Yes/No)'),
            ('Theological', 'B.Th — College / Institution'),
            ('Theological', 'MDiv/BD — ATA/SSC/Other'),
            ('Theological', 'MDiv/BD — ATA Regd #'),
            ('Theological', 'MDiv/BD — Year of Study'),
            ('Theological', 'MDiv/BD — Month & Year of Passing'),
            ('Theological', 'MDiv/BD — Credit Hours & Letter Grade'),
            ('Theological', 'MDiv/BD — ATA Emboss (Yes/No)'),
            ('Theological', 'MDiv/BD — Seminary / Institution'),
            ('ATA Process', 'Certificates Verified (Yes/No)'),
            ('ATA Process', 'Qualifying Year — Year of Study'),
            ('ATA Process', 'Qualifying Year — Credit Hours & Letter Grade'),
            ('ATA Process', 'Qualifying Exam (Yes/No)'),
            ('ATA Process', 'Qualifying Exam — Letter Grade'),
            ('ATA Process', 'ATA Reg. #'),
            ('ATA Process', 'Comments'),
            ('ATA Process', 'Comments — ATA'),
        ]

    def _build_xlsx(self, students, year):
        import xlsxwriter

        buffer = io.BytesIO()
        workbook = xlsxwriter.Workbook(buffer, {'in_memory': True})
        sheet = workbook.add_worksheet(f'ATA {year}')

        section_fmt = workbook.add_format({
            'bold': True,
            'bg_color': '#1F4E79',
            'font_color': '#FFFFFF',
            'align': 'center',
            'valign': 'vcenter',
        })
        header_fmt = workbook.add_format({
            'bold': True,
            'bg_color': '#D6E3F0',
            'text_wrap': True,
            'valign': 'vcenter',
            'border': 1,
        })
        cell_fmt = workbook.add_format({'border': 1, 'valign': 'vcenter'})
        note_fmt = workbook.add_format({'italic': True, 'font_color': '#666666'})

        headers = self._headers()
        sheet.merge_range(
            0, 0, 0, len(headers) - 1,
            _(
                'ATA Format export — Admission year %s. '
                'Empty columns are intentional (manual / ATA fill).'
            ) % year,
            note_fmt,
        )

        # Section row + column row
        col = 0
        while col < len(headers):
            section = headers[col][0]
            start = col
            while col + 1 < len(headers) and headers[col + 1][0] == section:
                col += 1
            if start == col:
                sheet.write(1, start, section, section_fmt)
            else:
                sheet.merge_range(1, start, 1, col, section, section_fmt)
            col += 1

        for idx, (_section, label) in enumerate(headers):
            sheet.write(2, idx, label, header_fmt)
            sheet.set_column(idx, idx, min(max(len(label) * 0.55, 12), 28))

        sheet.set_row(2, 36)

        for row_idx, student in enumerate(students, start=3):
            values = self._row_values(student, row_idx - 2, year)
            for col_idx, value in enumerate(values):
                sheet.write(row_idx, col_idx, value if value not in (False, None) else '', cell_fmt)

        workbook.close()
        return buffer.getvalue()

    def _certificates_verified(self, admission):
        if not admission or not admission.document_review_ids:
            return ''
        if admission.documents_pending_review or admission.documents_with_issues:
            return 'No'
        return 'Yes'

    def _row_values(self, student, serial, year):
        adm = student.admission_id
        admitted_on = student.admission_date
        dob = student.date_of_birth or (adm.date_of_birth if adm else False)
        if student.gender:
            gender = _sel_label(student, 'gender')
        elif adm and adm.gender:
            gender = _sel_label(adm, 'gender')
        else:
            gender = ''
        state_name = student.state_name or (adm.state_name if adm else '') or ''
        age = _age_on(dob, admitted_on) if admitted_on else ''

        # Secular
        class_x = (adm.class_x_month_year or adm.class_x_year or student.class_x_year) if adm else student.class_x_year
        class_xi = adm.class_xi_month_year if adm else ''
        class_xii = ''
        if adm:
            class_xii = adm.class_xii_month_year or adm.class_xii_diploma_year or ''
        else:
            class_xii = student.class_xii_diploma_year or ''

        diploma_area = adm.diploma_subject if adm else ''
        diploma_study = ''
        diploma_pass = ''
        if adm and adm.diploma_after_class_x == 'yes':
            diploma_study = _study_span(adm.diploma_enroll_year, adm.diploma_complete_month_year)
            diploma_pass = adm.diploma_complete_month_year or ''
            if not diploma_area:
                diploma_area = 'Diploma (after Class X)'

        ug_area = adm.ug_non_theo_program if adm else ''
        ug_study = _study_span(
            adm.ug_non_theo_enroll_year if adm else '',
            adm.ug_non_theo_grad_month_year if adm else '',
        )
        ug_pass = adm.ug_non_theo_grad_month_year if adm else ''
        ug_grade = adm.ug_non_theo_grade if adm else ''

        # Theological — Dip.Th
        dip_study = _study_span(
            adm.ug_theo_diploma_enroll_year if adm else '',
            adm.ug_theo_diploma_grad_month_year if adm else '',
        )
        dip_pass = adm.ug_theo_diploma_grad_month_year if adm else ''
        dip_grade = adm.ug_theo_diploma_grade if adm else ''
        dip_college = adm.ug_theo_diploma_bible_college if adm else ''

        # B.Th
        bth_study = _study_span(
            adm.ug_theo_bth_enroll_year if adm else '',
            adm.ug_theo_bth_grad_month_year if adm else '',
        )
        bth_pass = adm.ug_theo_bth_grad_month_year if adm else ''
        bth_grade = adm.ug_theo_bth_grade if adm else ''
        bth_college = adm.ug_theo_bth_bible_college if adm else ''

        # MDiv/BD
        mdiv_study = _study_span(
            adm.pg_theo_mdiv_enroll_year if adm else '',
            adm.pg_theo_mdiv_grad_month_year if adm else '',
        )
        mdiv_pass = adm.pg_theo_mdiv_grad_month_year if adm else ''
        mdiv_grade = adm.pg_theo_mdiv_grade if adm else ''
        mdiv_seminary = adm.pg_theo_mdiv_seminary if adm else ''

        return [
            serial,
            student.name or student.full_name or '',
            gender.capitalize() if isinstance(gender, str) else gender,
            age,
            state_name,
            year,
            class_x or '',
            class_xi or '',
            class_xii or '',
            diploma_area or '',
            diploma_study,
            diploma_pass or '',
            ug_area or '',
            ug_study,
            ug_pass or '',
            ug_grade or '',
            '',  # Dip.Th ATA/SSC/Other
            '',  # Dip.Th ATA Regd #
            dip_study,
            dip_pass or '',
            dip_grade or '',
            '',  # Dip.Th emboss
            dip_college or '',
            '',  # B.Th ATA/SSC/Other
            '',  # B.Th ATA Regd #
            bth_study,
            bth_pass or '',
            bth_grade or '',
            '',  # B.Th emboss
            bth_college or '',
            '',  # MDiv ATA/SSC/Other
            '',  # MDiv ATA Regd #
            mdiv_study,
            mdiv_pass or '',
            mdiv_grade or '',
            '',  # MDiv emboss
            mdiv_seminary or '',
            self._certificates_verified(adm),
            '',  # Qualifying year of study
            '',  # Qualifying credits/grade
            '',  # Qualifying exam Y/N
            '',  # Qualifying letter grade
            '',  # ATA Reg. # (filled by ATA)
            '',  # Comments
            '',  # Comments-ATA
        ]
