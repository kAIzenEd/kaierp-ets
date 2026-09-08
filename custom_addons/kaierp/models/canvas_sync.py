# -*- coding: utf-8 -*-
import logging
from datetime import date

from odoo import api, fields, models, _
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)

STUDENT_ENROLL_STATES = {
    'active': 'enrolled',
    'invited': 'enrolled',
    'creation_pending': 'enrolled',
    'completed': 'completed',
    'inactive': 'dropped',
    'deleted': 'dropped',
    'rejected': 'dropped',
}


class SchoolCanvasSyncRun(models.Model):
    _name = 'school.canvas.sync.run'
    _description = 'Canvas Sync Run'
    _order = 'started_at desc'

    started_at = fields.Datetime(string='Started', default=fields.Datetime.now, required=True)
    finished_at = fields.Datetime(string='Finished')
    state = fields.Selection([
        ('running', 'Running'),
        ('done', 'Done'),
        ('failed', 'Failed'),
    ], default='running', required=True)
    summary = fields.Text(string='Summary')
    terms_synced = fields.Integer()
    classes_synced = fields.Integer(string='Courses Synced')
    enrollments_synced = fields.Integer()
    teachers_assigned = fields.Integer()
    issues_open = fields.Integer()

    @api.model
    def cron_sync(self):
        if self.env['ir.config_parameter'].sudo().get_param(
            'kaierp.canvas_sync_enabled', 'False',
        ) != 'True':
            return
        if not self.env['school.canvas.api'].is_connected():
            _logger.info('Canvas cron skipped: not connected.')
            return
        self.run_sync()

    @api.model
    def run_sync(self):
        run = self.create({'started_at': fields.Datetime.now(), 'state': 'running'})
        try:
            summary = self.env['school.canvas.sync']._run(run)
            run.write({
                'state': 'done',
                'finished_at': fields.Datetime.now(),
                'summary': summary,
            })
        except UserError as err:
            _logger.exception('Canvas sync failed')
            run.write({
                'state': 'failed',
                'finished_at': fields.Datetime.now(),
                'summary': str(err),
            })
            self.env['school.canvas.sync.issue'].log_issue(
                'api_error',
                message=str(err),
            )
            raise
        except Exception as err:
            _logger.exception('Canvas sync failed')
            run.write({
                'state': 'failed',
                'finished_at': fields.Datetime.now(),
                'summary': str(err),
            })
            self.env['school.canvas.sync.issue'].log_issue(
                'api_error',
                message=str(err),
            )
            raise UserError(_('Canvas sync failed: %s') % err) from err
        return run


class SchoolCanvasSync(models.AbstractModel):
    _name = 'school.canvas.sync'
    _description = 'Canvas LMS Sync'

    @api.model
    def _icp_bool(self, key, default=False):
        raw = self.env['ir.config_parameter'].sudo().get_param(key, 'True' if default else 'False')
        return (raw or '').strip() == 'True'

    @api.model
    def _run(self, run):
        api = self.env['school.canvas.api']
        terms = self._sync_terms()
        courses = api.list_courses(
            include_unpublished=self._icp_bool('kaierp.canvas_sync_unpublished', False),
            include_completed=self._icp_bool('kaierp.canvas_sync_completed_courses', True),
        )
        classes_synced = 0
        enrollments_synced = 0
        teachers_assigned = 0
        for course in courses:
            if self._should_skip_course(course):
                continue
            school_class = self._sync_course(course)
            if not school_class:
                continue
            classes_synced += 1
            users = api.list_course_users(course.get('id'))
            e_count, t_count = self._sync_course_people(school_class, course, users)
            enrollments_synced += e_count
            teachers_assigned += t_count

        open_issues = self.env['school.canvas.sync.issue'].search_count([('state', '=', 'open')])
        run.write({
            'terms_synced': len(terms),
            'classes_synced': classes_synced,
            'enrollments_synced': enrollments_synced,
            'teachers_assigned': teachers_assigned,
            'issues_open': open_issues,
        })
        self.env['ir.config_parameter'].sudo().set_param(
            'kaierp.canvas_last_sync_at',
            fields.Datetime.now(),
        )
        summary = _(
            'Terms: %(terms)s. Courses: %(classes)s. '
            'Student enrollments: %(enrollments)s. Teachers assigned: %(teachers)s. '
            'Open issues: %(issues)s.',
            terms=len(terms),
            classes=classes_synced,
            enrollments=enrollments_synced,
            teachers=teachers_assigned,
            issues=open_issues,
        )
        self.env['ir.config_parameter'].sudo().set_param(
            'kaierp.canvas_last_sync_summary',
            summary,
        )
        return summary

    @api.model
    def _should_skip_course(self, course):
        if course.get('blueprint'):
            self.env['school.canvas.sync.issue'].log_issue(
                'skipped_course',
                canvas_course_id=str(course.get('id') or ''),
                canvas_course_name=course.get('name') or '',
                message=_('Blueprint / template course skipped.'),
            )
            return True
        name = (course.get('name') or '').lower()
        if 'template' in name or name.startswith('sandbox'):
            self.env['school.canvas.sync.issue'].log_issue(
                'skipped_course',
                canvas_course_id=str(course.get('id') or ''),
                canvas_course_name=course.get('name') or '',
                message=_('Template or sandbox course skipped by name.'),
            )
            return True
        return False

    @api.model
    def _sync_terms(self):
        Term = self.env['school.canvas.term']
        synced = self.env['school.canvas.term']
        for payload in self.env['school.canvas.api'].list_terms():
            canvas_id = str(payload.get('id') or '')
            if not canvas_id:
                continue
            start_date = Term.parse_canvas_date(payload.get('start_at'))
            end_date = Term.parse_canvas_date(payload.get('end_at'))
            name = payload.get('name') or f'Term {canvas_id}'
            guessed_year, guessed_semester = Term.guess_mapping(name, start_date)
            existing = Term.search([('canvas_term_id', '=', canvas_id)], limit=1)
            vals = {
                'name': name,
                'sis_term_id': payload.get('sis_term_id') or False,
                'start_date': start_date,
                'end_date': end_date,
                'workflow_state': payload.get('workflow_state') or False,
                'last_sync_at': fields.Datetime.now(),
            }
            if existing:
                if not existing.academic_year:
                    vals['academic_year'] = guessed_year
                if not existing.semester:
                    vals['semester'] = guessed_semester
                existing.write(vals)
                synced |= existing
            else:
                vals.update({
                    'canvas_term_id': canvas_id,
                    'academic_year': guessed_year,
                    'semester': guessed_semester,
                })
                synced |= Term.create(vals)
        return synced

    @api.model
    def _sync_course(self, course):
        Class = self.env['school.class']
        Term = self.env['school.canvas.term']
        canvas_id = str(course.get('id') or '')
        if not canvas_id:
            return Class.browse()

        term_payload = course.get('term') or {}
        term_id = str(term_payload.get('id') or course.get('enrollment_term_id') or '')
        term = Term.search([('canvas_term_id', '=', term_id)], limit=1) if term_id else Term.browse()

        academic_year = term.academic_year if term else False
        semester = term.semester if term else False
        if not academic_year:
            academic_year = Class._default_academic_year()
        if not semester:
            semester = 'fall'

        code = (
            course.get('sis_course_id')
            or course.get('course_code')
            or f'C{canvas_id}'
        )
        name = course.get('name') or code
        start_date = Term.parse_canvas_date(course.get('start_at')) or (term.start_date if term else False)
        end_date = Term.parse_canvas_date(course.get('end_at')) or (term.end_date if term else False)
        catalog = self._find_catalog(course.get('course_code') or '')

        vals = {
            'name': name,
            'code': code,
            'academic_year': academic_year,
            'semester': semester,
            'start_date': start_date,
            'end_date': end_date,
            'canvas_course_id': canvas_id,
            'canvas_term_id': term_id or False,
            'canvas_sis_course_id': course.get('sis_course_id') or False,
            'state': self._class_state(course, start_date),
        }
        if catalog:
            vals['catalog_id'] = catalog.id

        existing = Class.search([('canvas_course_id', '=', canvas_id)], limit=1)
        if existing:
            existing.with_context(canvas_sync=True).write(vals)
            return existing
        return Class.with_context(canvas_sync=True).create(vals)

    @api.model
    def _find_catalog(self, course_code):
        code = (course_code or '').strip()
        if not code:
            return self.env['school.course.catalog']
        return self.env['school.course.catalog'].search([('code', '=ilike', code)], limit=1)

    @api.model
    def _class_state(self, course, start_date):
        workflow = course.get('workflow_state') or ''
        if workflow == 'unpublished':
            return 'draft'
        if workflow == 'completed':
            return 'completed'
        if start_date and start_date <= date.today():
            return 'in_progress'
        return 'open'

    @api.model
    def _sync_course_people(self, school_class, course, users):
        teachers = []
        enrollments_synced = 0
        for user in users:
            enrollments = user.get('enrollments') or []
            course_id = str(course.get('id') or '')
            for enrollment in enrollments:
                enr_course = enrollment.get('course_id')
                if enr_course not in (None, False, '') and str(enr_course) != course_id:
                    continue
                etype = enrollment.get('type') or enrollment.get('role') or ''
                if etype == 'TeacherEnrollment':
                    teachers.append((enrollment, user))
                elif etype == 'StudentEnrollment':
                    if self._sync_student_enrollment(school_class, course, enrollment, user):
                        enrollments_synced += 1
        teachers_assigned = 1 if self._assign_teachers(school_class, course, teachers) else 0
        if school_class.enrolled_count > school_class.max_students:
            school_class.with_context(canvas_sync=True).max_students = school_class.enrolled_count
        return enrollments_synced, teachers_assigned

    @api.model
    def _sync_student_enrollment(self, school_class, course, enrollment, user):
        student, issue_type, detail = self._match_student(user)
        canvas_enrollment_id = str(enrollment.get('id') or '')
        if not student:
            self.env['school.canvas.sync.issue'].log_issue(
                issue_type or 'unmatched_student',
                canvas_user_id=str(user.get('id') or ''),
                canvas_course_id=str(course.get('id') or ''),
                canvas_enrollment_id=canvas_enrollment_id,
                canvas_user_name=user.get('name') or '',
                canvas_login_id=user.get('login_id') or '',
                canvas_email=user.get('email') or '',
                canvas_course_name=course.get('name') or school_class.name,
                class_id=school_class.id,
                message=detail or _('No Odoo student matched this Canvas email/login.'),
            )
            return False

        canvas_state = enrollment.get('enrollment_state') or 'active'
        odoo_state = STUDENT_ENROLL_STATES.get(canvas_state, 'enrolled')
        Enrollment = self.env['school.enrollment'].with_context(canvas_sync=True)
        existing = Enrollment.search([
            ('student_id', '=', student.id),
            ('class_id', '=', school_class.id),
        ], limit=1)
        vals = {
            'student_id': student.id,
            'class_id': school_class.id,
            'state': odoo_state,
            'canvas_enrollment_id': canvas_enrollment_id or False,
        }
        if existing:
            existing.write(vals)
        else:
            Enrollment.create(vals)

        if not student.canvas_user_id:
            student.canvas_user_id = str(user.get('id') or '')
        return True

    @api.model
    def _assign_teachers(self, school_class, course, teacher_rows):
        if not teacher_rows:
            return False
        teacher_rows = sorted(teacher_rows, key=lambda row: row[0].get('id') or 0)
        primary_enrollment, primary_user = teacher_rows[0]
        teacher, issue_type, detail = self._match_teacher(primary_user)
        if teacher:
            school_class.with_context(canvas_sync=True).teacher_id = teacher.id
            if not teacher.canvas_user_id:
                teacher.canvas_user_id = str(primary_user.get('id') or '')
        else:
            self.env['school.canvas.sync.issue'].log_issue(
                issue_type or 'unmatched_teacher',
                canvas_user_id=str(primary_user.get('id') or ''),
                canvas_course_id=str(course.get('id') or ''),
                canvas_enrollment_id=str(primary_enrollment.get('id') or ''),
                canvas_user_name=primary_user.get('name') or '',
                canvas_login_id=primary_user.get('login_id') or '',
                canvas_email=primary_user.get('email') or '',
                canvas_course_name=course.get('name') or school_class.name,
                class_id=school_class.id,
                message=detail or _('No Odoo teacher matched this Canvas email/login.'),
            )

        for extra_enrollment, extra_user in teacher_rows[1:]:
            extra_teacher, _, extra_detail = self._match_teacher(extra_user)
            self.env['school.canvas.sync.issue'].log_issue(
                'extra_teacher',
                canvas_user_id=str(extra_user.get('id') or ''),
                canvas_course_id=str(course.get('id') or ''),
                canvas_enrollment_id=str(extra_enrollment.get('id') or ''),
                canvas_user_name=extra_user.get('name') or '',
                canvas_login_id=extra_user.get('login_id') or '',
                canvas_email=extra_user.get('email') or '',
                canvas_course_name=course.get('name') or school_class.name,
                class_id=school_class.id,
                teacher_id=extra_teacher.id if extra_teacher else False,
                message=extra_detail or _(
                    'Odoo courses have one teacher. This additional Canvas teacher was not assigned.',
                ),
            )
        return bool(teacher)

    @api.model
    def _normalize_email(self, value):
        return (value or '').strip().lower()

    @api.model
    def _user_emails(self, user):
        emails = []
        for key in ('login_id', 'email'):
            value = self._normalize_email(user.get(key))
            if value and '@' in value and value not in emails:
                emails.append(value)
        return emails

    @api.model
    def _match_student(self, user):
        Student = self.env['school.student']
        canvas_id = str(user.get('id') or '')
        if canvas_id:
            found = Student.search([('canvas_user_id', '=', canvas_id)], limit=2)
            if len(found) == 1:
                return found, False, False
            if len(found) > 1:
                return Student.browse(), 'ambiguous_match', _(
                    'Multiple Odoo students already have Canvas user ID %s.',
                ) % canvas_id

        sis_id = (user.get('sis_user_id') or '').strip()
        if sis_id:
            found = Student.search([('person_key', '=', sis_id)], limit=2)
            if len(found) == 1:
                return found, False, False

        emails = self._user_emails(user)
        if not emails:
            return Student.browse(), 'unmatched_student', _(
                'Canvas user has no login_id or email to match.',
            )

        matched = Student.browse()
        for email in emails:
            found = Student.search([
                '|',
                ('ets_email', '=ilike', email),
                ('email', '=ilike', email),
            ])
            matched |= found
        if len(matched) == 1:
            return matched, False, False
        if len(matched) > 1:
            return Student.browse(), 'ambiguous_match', _(
                'Multiple Odoo students match Canvas emails %s.',
            ) % ', '.join(emails)
        return Student.browse(), 'unmatched_student', _(
            'No Odoo student has ets_email or email matching %s.',
        ) % ', '.join(emails)

    @api.model
    def _match_teacher(self, user):
        Teacher = self.env['school.teacher']
        canvas_id = str(user.get('id') or '')
        if canvas_id:
            found = Teacher.search([('canvas_user_id', '=', canvas_id)], limit=2)
            if len(found) == 1:
                return found, False, False
            if len(found) > 1:
                return Teacher.browse(), 'ambiguous_match', _(
                    'Multiple Odoo teachers already have Canvas user ID %s.',
                ) % canvas_id

        sis_id = (user.get('sis_user_id') or '').strip()
        if sis_id:
            found = Teacher.search([('employee_id', '=', sis_id)], limit=2)
            if len(found) == 1:
                return found, False, False

        emails = self._user_emails(user)
        if not emails:
            return Teacher.browse(), 'unmatched_teacher', _(
                'Canvas user has no login_id or email to match.',
            )

        matched = Teacher.browse()
        for email in emails:
            matched |= Teacher.search([('email', '=ilike', email)])
        if len(matched) == 1:
            return matched, False, False
        if len(matched) > 1:
            return Teacher.browse(), 'ambiguous_match', _(
                'Multiple Odoo teachers match Canvas emails %s.',
            ) % ', '.join(emails)
        return Teacher.browse(), 'unmatched_teacher', _(
            'No Odoo teacher has email matching %s.',
        ) % ', '.join(emails)
