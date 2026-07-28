# kAI ERP — WhatsApp

Reusable Odoo 19 addon for Meta WhatsApp Cloud API messaging with kAI ERP admissions.

## Install

Place this module next to `kaierp` on your addons path:

```text
custom_addons/
  kaierp/
  kaierp_whatsapp/
```

Then install/upgrade:

```bash
odoo -d YOUR_DB -i kaierp_whatsapp -u kaierp_whatsapp --stop-after-init
```

`auto_install` is enabled when `kaierp` is present.

## Configure

1. **Settings → kAI-ERP → WhatsApp** — Meta token, Phone Number ID, webhook verify token
2. **Notification Rules** — map admission create / state changes to Meta template names and body parameters
3. Webhook callback stays at `/kaierp/whatsapp/webhook` (backward compatible)

## Dependencies

- `kaierp`
- `mail`
- `base`
