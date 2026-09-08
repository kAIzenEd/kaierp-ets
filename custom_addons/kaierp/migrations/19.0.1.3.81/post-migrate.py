# -*- coding: utf-8 -*-


def migrate(cr, version):
    """Stop upgrades from overwriting the admission webhook secret.

    Older builds seeded kaierp.admission_webhook_secret from XML with
    noupdate=0. Mark that XML id as noupdate and leave the DB value alone
    (staff set it in Settings). Do not reset the secret here.
    """
    cr.execute(
        """
        UPDATE ir_model_data
           SET noupdate = TRUE
         WHERE module = 'kaierp'
           AND name = 'kaierp_admission_webhook_secret'
        """
    )
