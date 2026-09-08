/** @odoo-module **/

import { Chatter } from "@mail/chatter/web_portal/chatter";
import { FormRenderer } from "@web/views/form/form_renderer";
import { browser } from "@web/core/browser/browser";
import { patch } from "@web/core/utils/patch";
import { onMounted, onPatched } from "@odoo/owl";

const STORAGE_KEY = "kaierp.chatter_collapsed";

function isCollapsed() {
    return browser.localStorage.getItem(STORAGE_KEY) === "1";
}

function setCollapsed(collapsed) {
    browser.localStorage.setItem(STORAGE_KEY, collapsed ? "1" : "0");
}

function applyCollapsedClass(collapsed) {
    document.querySelectorAll(".o_form_view").forEach((el) => {
        el.classList.toggle("kaierp_chatter_collapsed", collapsed);
    });
}

function ensureExpandButton() {
    const form =
        document.querySelector(".o_content .o_form_view") ||
        document.querySelector(".o_form_view");
    if (!form) {
        return;
    }
    let btn = form.querySelector(".kaierp-chatter-expand");
    if (!btn) {
        btn = document.createElement("button");
        btn.type = "button";
        btn.className = "kaierp-chatter-expand btn btn-secondary";
        btn.title = "Show messages";
        btn.setAttribute("aria-label", "Show messages");
        btn.innerHTML = '<i class="fa fa-comments me-1"></i>Messages';
        btn.addEventListener("click", () => {
            setCollapsed(false);
            applyCollapsedClass(false);
            browser.dispatchEvent(new Event("resize"));
        });
        form.appendChild(btn);
    }
}

function syncChatterUi() {
    applyCollapsedClass(isCollapsed());
    ensureExpandButton();
}

function injectCollapseButton(rootEl, onCollapse) {
    if (!rootEl) {
        return;
    }
    const topbar = rootEl.querySelector(".o-mail-Chatter-topbar");
    if (!topbar || topbar.querySelector(".kaierp-chatter-collapse")) {
        return;
    }
    const grow = topbar.querySelector(".o-mail-Chatter-topbarGrow");
    const btn = document.createElement("button");
    btn.type = "button";
    btn.className = "btn btn-link text-action kaierp-chatter-collapse px-2";
    btn.title = "Hide messages";
    btn.setAttribute("aria-label", "Hide messages");
    btn.innerHTML = '<i class="fa fa-chevron-right" role="img"></i>';
    btn.addEventListener("click", (ev) => {
        ev.preventDefault();
        ev.stopPropagation();
        onCollapse();
    });
    if (grow && grow.parentNode === topbar) {
        grow.insertAdjacentElement("afterend", btn);
    } else {
        topbar.appendChild(btn);
    }
}

patch(FormRenderer.prototype, {
    setup() {
        super.setup(...arguments);
        onMounted(syncChatterUi);
        onPatched(syncChatterUi);
    },
});

patch(Chatter.prototype, {
    setup() {
        super.setup(...arguments);
        const collapse = () => {
            setCollapsed(true);
            applyCollapsedClass(true);
            ensureExpandButton();
            browser.dispatchEvent(new Event("resize"));
        };
        onMounted(() => {
            injectCollapseButton(this.rootRef && this.rootRef.el, collapse);
            // Fallback: chatter root may mount one tick later
            browser.setTimeout(() => {
                injectCollapseButton(this.rootRef && this.rootRef.el, collapse);
                syncChatterUi();
            }, 0);
            syncChatterUi();
        });
        onPatched(() => {
            injectCollapseButton(this.rootRef && this.rootRef.el, collapse);
            syncChatterUi();
        });
    },
});
