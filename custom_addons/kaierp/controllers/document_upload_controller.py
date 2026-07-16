# -*- coding: utf-8 -*-
import logging

from odoo import http, _
from odoo.exceptions import ValidationError
from odoo.http import request

_logger = logging.getLogger(__name__)


class AdmissionDocumentUploadController(http.Controller):
    """Public, token-gated page for applicants to resubmit admission documents."""

    def _admission_from_token(self, token):
        return request.env['school.admission'].sudo()._find_by_document_upload_token(token)

    @http.route(
        '/admission/upload/<string:token>',
        type='http',
        auth='public',
        methods=['GET'],
        csrf=False,
        save_session=False,
    )
    def upload_form(self, token, **kwargs):
        admission = self._admission_from_token(token)
        if not admission:
            return request.render('kaierp.admission_document_upload_invalid', {
                'error_title': _('Link unavailable'),
                'error_message': _(
                    'This upload link is invalid, expired, or no longer active. '
                    'Please contact the admissions office if you still need to send documents.'
                ),
            })
        issue_docs = admission._get_documents_needing_upload()
        return request.render('kaierp.admission_document_upload_form', {
            'admission': admission,
            'issue_docs': issue_docs,
            'token': token,
            'success': False,
            'error': False,
            'uploaded_labels_text': '',
        })

    @http.route(
        '/admission/upload/<string:token>',
        type='http',
        auth='public',
        methods=['POST'],
        csrf=False,
        save_session=False,
    )
    def upload_submit(self, token, **kwargs):
        admission = self._admission_from_token(token)
        if not admission:
            return request.render('kaierp.admission_document_upload_invalid', {
                'error_title': _('Link unavailable'),
                'error_message': _(
                    'This upload link is invalid, expired, or no longer active. '
                    'Please contact the admissions office if you still need to send documents.'
                ),
            })

        issue_docs = admission._get_documents_needing_upload()
        uploads = []
        files = request.httprequest.files
        for line in issue_docs:
            field_name = 'file_%s' % line.document_code
            storage = files.get(field_name)
            if not storage or not storage.filename:
                continue
            content = storage.read()
            if not content:
                continue
            uploads.append({
                'document_code': line.document_code,
                'filename': storage.filename,
                'content': content,
            })

        try:
            uploaded_labels = admission.apply_public_document_uploads(uploads)
        except ValidationError as exc:
            return request.render('kaierp.admission_document_upload_form', {
                'admission': admission,
                'issue_docs': admission._get_documents_needing_upload(),
                'token': token,
                'success': False,
                'error': str(exc),
                'uploaded_labels_text': '',
            })
        except Exception:
            _logger.exception(
                'Public document upload failed for admission %s',
                admission.id,
            )
            return request.render('kaierp.admission_document_upload_form', {
                'admission': admission,
                'issue_docs': admission._get_documents_needing_upload(),
                'token': token,
                'success': False,
                'error': _('Something went wrong while saving your files. Please try again.'),
                'uploaded_labels_text': '',
            })

        remaining = admission._get_documents_needing_upload()
        return request.render('kaierp.admission_document_upload_form', {
            'admission': admission,
            'issue_docs': remaining,
            'token': token,
            'success': True,
            'error': False,
            'uploaded_labels_text': ', '.join(uploaded_labels),
        })
