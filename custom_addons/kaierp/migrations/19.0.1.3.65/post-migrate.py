# -*- coding: utf-8 -*-
"""Register product.product XML IDs for ETS fee variants (CSV import by /id)."""
import logging

_logger = logging.getLogger(__name__)

# product.template xml id → product.product xml id to create
TEMPLATE_TO_VARIANT = {
    'product_application_fee': 'product_application_fee_product',
    'product_exam_accommodation': 'product_exam_accommodation_product',
    'product_admission_fee': 'product_admission_fee_product',
    'product_tuition': 'product_tuition_product',
    'product_accommodation': 'product_accommodation_product',
    'product_food': 'product_food_product',
    'product_family_quarters': 'product_family_quarters_product',
    'product_library_deposit': 'product_library_deposit_product',
    'product_library_user_fee': 'product_library_user_fee_product',
    'product_sports_fee': 'product_sports_fee_product',
    'product_technology_fee': 'product_technology_fee_product',
    'product_medical_single': 'product_medical_single_product',
    'product_medical_family': 'product_medical_family_product',
    'product_caution_single': 'product_caution_single_product',
    'product_caution_family': 'product_caution_family_product',
    'product_exam_fee': 'product_exam_fee_product',
    'product_thesis_fee': 'product_thesis_fee_product',
    'product_dissertation_fee': 'product_dissertation_fee_product',
    'product_graduation_fee': 'product_graduation_fee_product',
    'product_continuation_fee': 'product_continuation_fee_product',
    'product_transcript_fee': 'product_transcript_fee_product',
    'product_other_fee': 'product_other_fee_product',
    'product_previous_dues': 'product_previous_dues_product',
    'product_fine': 'product_fine_product',
}


def migrate(cr, version):
    from odoo import api, SUPERUSER_ID
    env = api.Environment(cr, SUPERUSER_ID, {})
    Imd = env['ir.model.data']
    created = 0
    for tmpl_xml, prod_xml in TEMPLATE_TO_VARIANT.items():
        tmpl = env.ref(f'kaierp.{tmpl_xml}', raise_if_not_found=False)
        if not tmpl:
            continue
        variant = tmpl.product_variant_id
        if not variant:
            continue
        existing = Imd.search([
            ('module', '=', 'kaierp'),
            ('name', '=', prod_xml),
            ('model', '=', 'product.product'),
        ], limit=1)
        if existing:
            if existing.res_id != variant.id:
                existing.write({'res_id': variant.id})
            continue
        Imd.create({
            'module': 'kaierp',
            'name': prod_xml,
            'model': 'product.product',
            'res_id': variant.id,
            'noupdate': True,
        })
        created += 1
    _logger.info('ETS fee product.product XML IDs ensured (%s new).', created)
