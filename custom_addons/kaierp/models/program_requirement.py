# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


# Keep in sync with school.student / school.admission `course` selection.
PROGRAM_SELECTION = [
    ('macs', 'Master of Arts in Christian Studies (MACS)'),
    ('pgdbs', 'Postgraduate Diploma in Biblical Studies (PGDBS)'),
    ('mabs', 'Master of Arts in Biblical Studies (MABS)'),
    ('mdiv', 'Master of Divinity (MDIV)'),
    ('macc', 'Master of Arts in Christian Counselling (MACC)'),
    ('mth', 'Master of Theology (MTH)'),
    ('dmin', 'Doctor of Ministry (D.Min)'),
    ('bth', 'Bachelor of Theology (B.Th)'),
]

REQUIREMENT_TYPE_SELECTION = [
    ('required', 'Required'),
    ('core', 'Core'),
    ('elective', 'Elective'),
    ('concentration', 'Concentration'),
]


class SchoolProgramRequirement(models.Model):
    _name = 'school.program.requirement'
    _description = 'Program Course Requirement'
    _order = 'program, sequence, catalog_id'
    _rec_name = 'display_name'

    program = fields.Selection(
        PROGRAM_SELECTION, string='Program', required=True, index=True,
    )
    catalog_id = fields.Many2one(
        'school.course.catalog', string='Catalog Course',
        required=True, ondelete='cascade', index=True,
    )
    requirement_type = fields.Selection(
        REQUIREMENT_TYPE_SELECTION, string='Requirement Type',
        default='required', required=True,
    )
    credits = fields.Integer(
        string='Credits Toward Program',
        help='Defaults to the catalog course credit hours if left empty.',
    )
    sequence = fields.Integer(string='Sequence', default=10)
    notes = fields.Char(string='Notes')
    active = fields.Boolean(string='Active', default=True)

    catalog_code = fields.Char(related='catalog_id.code', store=True, string='Course Code')
    catalog_name = fields.Char(related='catalog_id.name', store=True, string='Course Title')
    catalog_area = fields.Selection(related='catalog_id.area', store=True, string='Area')
    display_name = fields.Char(
        string='Display Name', compute='_compute_display_name', store=True,
    )

    _program_catalog_uniq = models.Constraint(
        'unique(program, catalog_id)',
        'This course is already mapped to that program.',
    )

    @api.depends('program', 'catalog_id', 'catalog_id.code', 'requirement_type')
    def _compute_display_name(self):
        program_labels = dict(PROGRAM_SELECTION)
        type_labels = dict(REQUIREMENT_TYPE_SELECTION)
        for rec in self:
            prog = program_labels.get(rec.program, rec.program or '')
            code = rec.catalog_id.code or ''
            rtype = type_labels.get(rec.requirement_type, '')
            rec.display_name = f'{prog}: {code} ({rtype})' if code else prog

    @api.onchange('catalog_id')
    def _onchange_catalog_id(self):
        for rec in self:
            if rec.catalog_id and not rec.credits:
                rec.credits = rec.catalog_id.credit_hours

    @api.model_create_multi
    def create(self, vals_list):
        Catalog = self.env['school.course.catalog']
        for vals in vals_list:
            if not vals.get('credits') and vals.get('catalog_id'):
                cat = Catalog.browse(vals['catalog_id'])
                vals['credits'] = cat.credit_hours or 0
        return super().create(vals_list)

    @api.constrains('credits')
    def _check_credits(self):
        for rec in self:
            if rec.credits is not False and rec.credits < 0:
                raise ValidationError(_('Credits cannot be negative.'))

    # ── Explorer API ──────────────────────────────────────────────

    @api.model
    def _program_label(self, code):
        return dict(PROGRAM_SELECTION).get(code, code or '')

    @api.model
    def _type_label(self, code):
        return dict(REQUIREMENT_TYPE_SELECTION).get(code, code or '')

    @api.model
    def get_program_options(self):
        used = set(self.search([]).mapped('program'))
        # Always show main demo programs even if empty
        preferred = ['mabs', 'mdiv', 'macs', 'mth', 'pgdbs', 'macc', 'dmin', 'bth']
        ordered = [p for p in preferred if p in used or p in ('mabs', 'mdiv', 'macs')]
        for p in preferred:
            if p not in ordered and p in used:
                ordered.append(p)
        for p, _label in PROGRAM_SELECTION:
            if p not in ordered and p in used:
                ordered.append(p)
        return [{'code': p, 'label': self._program_label(p)} for p in ordered]

    @api.model
    def get_explorer_by_program(self, program):
        """Courses that count toward a program, with cross-program badges."""
        if not program:
            return {'program': False, 'label': '', 'courses': [], 'summary': {}}

        reqs = self.search([
            ('program', '=', program),
            ('active', '=', True),
            ('catalog_id.active', '=', True),
        ], order='sequence, catalog_code')

        # Preload other programs per catalog course
        catalog_ids = reqs.mapped('catalog_id').ids
        other_reqs = self.search([
            ('catalog_id', 'in', catalog_ids),
            ('active', '=', True),
        ])
        by_catalog = {}
        for r in other_reqs:
            by_catalog.setdefault(r.catalog_id.id, []).append(r)

        courses = []
        type_counts = {}
        total_credits = 0
        for req in reqs:
            cat = req.catalog_id
            also = []
            for r in by_catalog.get(cat.id, []):
                if r.program != program:
                    also.append({
                        'program': r.program,
                        'label': self._program_label(r.program),
                        'requirement_type': r.requirement_type,
                        'requirement_type_label': self._type_label(r.requirement_type),
                    })
            credits = req.credits or cat.credit_hours or 0
            total_credits += credits
            type_counts[req.requirement_type] = type_counts.get(req.requirement_type, 0) + 1
            courses.append({
                'requirement_id': req.id,
                'catalog_id': cat.id,
                'code': cat.code,
                'name': cat.name,
                'area': cat.area,
                'area_label': dict(cat._fields['area'].selection).get(cat.area, ''),
                'credits': credits,
                'requirement_type': req.requirement_type,
                'requirement_type_label': self._type_label(req.requirement_type),
                'notes': req.notes or '',
                'also_counts_toward': also,
            })

        return {
            'program': program,
            'label': self._program_label(program),
            'courses': courses,
            'summary': {
                'course_count': len(courses),
                'total_credits': total_credits,
                'by_type': [
                    {'type': t, 'label': self._type_label(t), 'count': c}
                    for t, c in sorted(type_counts.items())
                ],
            },
        }

    @api.model
    def get_explorer_by_course(self, catalog_id):
        """Programs that a catalog course counts toward."""
        catalog_id = int(catalog_id or 0)
        if not catalog_id:
            return {'course': False, 'programs': []}

        cat = self.env['school.course.catalog'].browse(catalog_id)
        if not cat.exists():
            return {'course': False, 'programs': []}

        reqs = self.search([
            ('catalog_id', '=', catalog_id),
            ('active', '=', True),
        ], order='program')

        programs = [{
            'requirement_id': r.id,
            'program': r.program,
            'label': self._program_label(r.program),
            'requirement_type': r.requirement_type,
            'requirement_type_label': self._type_label(r.requirement_type),
            'credits': r.credits or cat.credit_hours or 0,
            'notes': r.notes or '',
        } for r in reqs]

        return {
            'course': {
                'id': cat.id,
                'code': cat.code,
                'name': cat.name,
                'credit_hours': cat.credit_hours,
                'area': cat.area,
                'area_label': dict(cat._fields['area'].selection).get(cat.area, ''),
                'description': cat.description or '',
            },
            'programs': programs,
        }

    @api.model
    def get_explorer_by_student(self, student_id):
        """Student progress against their program requirements."""
        student_id = int(student_id or 0)
        Student = self.env['school.student']
        student = Student.browse(student_id) if student_id else Student.browse()
        if not student.exists():
            return {
                'student': False,
                'program': False,
                'items': [],
                'summary': {'completed': 0, 'in_progress': 0, 'remaining': 0, 'percent': 0},
            }

        program = student.course
        if not program:
            return {
                'student': {
                    'id': student.id,
                    'name': student.name or student.full_name or '',
                    'student_id': student.student_id or '',
                    'person_key': student.person_key or '',
                },
                'program': False,
                'label': '',
                'items': [],
                'summary': {'completed': 0, 'in_progress': 0, 'remaining': 0, 'percent': 0},
                'message': _('This student has no program assigned.'),
            }

        reqs = self.search([
            ('program', '=', program),
            ('active', '=', True),
            ('catalog_id.active', '=', True),
        ], order='sequence, catalog_code')

        enrollments = self.env['school.enrollment'].search([
            ('student_id', '=', student.id),
            ('state', 'in', ('enrolled', 'completed', 'failed')),
        ])

        # Map catalog_id -> best enrollment status
        status_by_catalog = {}
        for en in enrollments:
            cls = en.class_id
            cat_id = cls.catalog_id.id if cls.catalog_id else False
            if not cat_id and cls.code:
                # Fallback: match class code to catalog code
                cat = self.env['school.course.catalog'].search([
                    ('code', '=', cls.code.strip()),
                ], limit=1)
                cat_id = cat.id if cat else False
            if not cat_id:
                continue
            current = status_by_catalog.get(cat_id)
            # Prefer completed > enrolled > failed
            rank = {'completed': 3, 'enrolled': 2, 'failed': 1}.get(en.state, 0)
            if not current or rank > current['rank']:
                status_by_catalog[cat_id] = {
                    'rank': rank,
                    'state': en.state,
                    'class_name': cls.display_name_full or cls.name,
                    'class_code': cls.code,
                }

        items = []
        completed = in_progress = remaining = 0
        for req in reqs:
            cat = req.catalog_id
            hit = status_by_catalog.get(cat.id)
            if hit and hit['state'] == 'completed':
                status = 'completed'
                completed += 1
            elif hit and hit['state'] == 'enrolled':
                status = 'in_progress'
                in_progress += 1
            else:
                status = 'remaining'
                remaining += 1
            items.append({
                'requirement_id': req.id,
                'catalog_id': cat.id,
                'code': cat.code,
                'name': cat.name,
                'credits': req.credits or cat.credit_hours or 0,
                'requirement_type': req.requirement_type,
                'requirement_type_label': self._type_label(req.requirement_type),
                'status': status,
                'class_name': hit['class_name'] if hit else '',
            })

        total = len(items)
        percent = int(round((completed / total) * 100)) if total else 0

        return {
            'student': {
                'id': student.id,
                'name': student.name or student.full_name or '',
                'student_id': student.student_id or '',
                'person_key': student.person_key or '',
            },
            'program': program,
            'label': self._program_label(program),
            'items': items,
            'summary': {
                'completed': completed,
                'in_progress': in_progress,
                'remaining': remaining,
                'total': total,
                'percent': percent,
            },
        }

    @api.model
    def get_explorer_bootstrap(self):
        """Initial payload for the OWL explorer."""
        Catalog = self.env['school.course.catalog']
        programs = self.get_program_options()
        courses = Catalog.get_explorer_catalog_list()
        students = self.env['school.student'].search_read(
            [('state', 'in', ('active', 'graduated', 'on_hold'))],
            ['id', 'name', 'full_name', 'student_id', 'person_key', 'course'],
            limit=80,
            order='name asc',
        )
        # Normalize student rows
        student_rows = []
        for s in students:
            student_rows.append({
                'id': s['id'],
                'name': s.get('name') or s.get('full_name') or '',
                'student_id': s.get('student_id') or '',
                'person_key': s.get('person_key') or '',
                'program': s.get('course') or False,
                'program_label': self._program_label(s.get('course')) if s.get('course') else '',
            })

        default_program = 'mabs'
        if programs and not any(p['code'] == default_program for p in programs):
            default_program = programs[0]['code']

        return {
            'programs': programs,
            'courses': courses,
            'students': student_rows,
            'default_program': default_program,
            'default_catalog_id': courses[0]['id'] if courses else False,
            'is_demo': True,
        }
