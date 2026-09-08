/** @odoo-module **/

import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { useSortable } from "@web/core/utils/sortable_owl";
import { user } from "@web/core/user";
import { Component, useState, useRef, onMounted, onWillUnmount } from "@odoo/owl";

const ETS_LOGO_STATIC = "/kaierp/static/src/image/ETS_logo.png";

const G_STUDENTS = [
    "kaierp.group_school_registrar",
    "kaierp.group_school_secretary",
    "kaierp.group_school_teacher",
    "kaierp.group_school_ta",
    "kaierp.group_school_finance",
    "kaierp.group_school_academic_dean",
    "kaierp.group_school_president",
    "kaierp.group_school_chaplain",
    "kaierp.group_school_dean_students",
    "kaierp.group_school_manager",
];
const G_ACADEMICS = [
    "kaierp.group_school_teacher",
    "kaierp.group_school_ta",
    "kaierp.group_school_registrar",
    "kaierp.group_school_secretary",
    "kaierp.group_school_academic_dean",
    "kaierp.group_school_president",
    "kaierp.group_school_manager",
];
const G_ADMISSIONS = [
    "kaierp.group_school_registrar",
    "kaierp.group_school_secretary",
    "kaierp.group_school_academic_dean",
    "kaierp.group_school_president",
    "kaierp.group_school_manager",
];
const G_PROGRAM_MAP = [
    "kaierp.group_school_registrar",
    "kaierp.group_school_secretary",
    "kaierp.group_school_academic_dean",
    "kaierp.group_school_president",
    "kaierp.group_school_manager",
];
const G_TRANSCRIPTS = [
    "kaierp.group_school_secretary",
    "kaierp.group_school_registrar",
    "kaierp.group_school_teacher",
    "kaierp.group_school_academic_dean",
    "kaierp.group_school_president",
    "kaierp.group_school_manager",
];
const G_STAFF = [
    "kaierp.group_school_registrar",
    "kaierp.group_school_secretary",
    "kaierp.group_school_manager",
];
const G_FINANCE = [
    "kaierp.group_school_finance",
    "kaierp.group_school_secretary",
    "kaierp.group_school_registrar",
    "kaierp.group_school_academic_dean",
    "kaierp.group_school_president",
    "kaierp.group_school_manager",
];

const DASHBOARD_TILES = {
    active_students: {
        key: "active_students",
        label: "Active Students",
        icon: "fa-graduation-cap",
        color: "red",
        kind: "kpi",
        action: "kaierp.action_school_student_active",
        groups: G_STUDENTS,
        default: true,
        numberKey: "active_students",
        subFn: (stats) => `of ${stats.total_students} total`,
        statKeys: ["active_students", "total_students"],
    },
    active_courses: {
        key: "active_courses",
        label: "Active Courses",
        icon: "fa-book",
        color: "navy",
        kind: "kpi",
        action: "kaierp.action_school_class",
        groups: G_ACADEMICS,
        default: true,
        numberKey: "open_classes",
        subFn: (stats) => `of ${stats.total_classes} total`,
        statKeys: ["open_classes", "total_classes"],
    },
    pending_admissions: {
        key: "pending_admissions",
        label: "Pending Admissions",
        icon: "fa-file-text-o",
        color: "red",
        kind: "kpi",
        action: "kaierp.action_school_admission",
        groups: G_ADMISSIONS,
        default: true,
        numberKey: "pending_admissions",
        subFn: (stats) => `${stats.approved_admissions} approved`,
        statKeys: ["pending_admissions", "approved_admissions"],
    },
    program_map: {
        key: "program_map",
        label: "Program Map",
        icon: "fa-sitemap",
        color: "red",
        kind: "kpi",
        action: "kaierp.action_school_program_requirements_explorer",
        groups: G_PROGRAM_MAP,
        default: true,
        numberKey: "catalog_courses",
        subFn: () => "Courses ↔ programs",
        statKeys: ["catalog_courses"],
    },
    grades: {
        key: "grades",
        label: "Grades",
        icon: "fa-bar-chart",
        color: "navy",
        kind: "shortcut",
        action: "kaierp.action_school_grade",
        groups: G_ACADEMICS,
        sub: "View all grades",
    },
    transcripts: {
        key: "transcripts",
        label: "Transcripts",
        icon: "fa-file-text",
        color: "red",
        kind: "shortcut",
        action: "kaierp.action_school_transcript",
        groups: G_TRANSCRIPTS,
        sub: "Generate and view",
    },
    attendance: {
        key: "attendance",
        label: "Attendance",
        icon: "fa-calendar-check-o",
        color: "navy",
        kind: "shortcut",
        action: "kaierp.action_school_attendance",
        groups: G_ACADEMICS,
        sub: "Daily records",
    },
    faculty: {
        key: "faculty",
        label: "Faculty",
        icon: "fa-black-tie",
        color: "red",
        kind: "shortcut",
        action: "kaierp.action_school_teacher",
        groups: G_STAFF,
        sub: "Teachers",
    },
    fees: {
        key: "fees",
        label: "Fees",
        icon: "fa-usd",
        color: "navy",
        kind: "shortcut",
        action: "kaierp.action_school_fee",
        groups: G_FINANCE,
        sub: "Pending fees",
    },
    calendar: {
        key: "calendar",
        label: "Calendar",
        icon: "fa-calendar",
        color: "red",
        kind: "shortcut",
        action: "calendar.action_calendar_event",
        groups: [],
        sub: "Events",
    },
    todo: {
        key: "todo",
        label: "To-Do",
        icon: "fa-tasks",
        color: "navy",
        kind: "shortcut",
        action: "project.action_view_all_task",
        groups: [],
        sub: "Tasks",
    },
};

const DEFAULT_TILE_ORDER = [
    "active_students",
    "active_courses",
    "pending_admissions",
    "program_map",
];

const SECTION_STYLE = {
    Students: { icon: "fa-graduation-cap", color: "red" },
    Academics: { icon: "fa-book", color: "navy" },
    Staff: { icon: "fa-black-tie", color: "red" },
    Finance: { icon: "fa-usd", color: "navy" },
    Communication: { icon: "fa-bullhorn", color: "red" },
    Reports: { icon: "fa-bar-chart", color: "navy" },
    More: { icon: "fa-th-large", color: "red" },
};

const STAT_QUERIES = {
    total_students: { fallback: 0, fn: (orm) => orm.searchCount("school.student", []) },
    active_students: {
        fallback: 0,
        fn: (orm) => orm.searchCount("school.student", [["state", "=", "active"]]),
    },
    total_classes: { fallback: 0, fn: (orm) => orm.searchCount("school.class", []) },
    open_classes: {
        fallback: 0,
        fn: (orm) => orm.searchCount("school.class", [["state", "in", ["open", "in_progress"]]]),
    },
    pending_admissions: {
        fallback: 0,
        fn: (orm) => orm.searchCount("school.admission", [
            ["state", "in", ["initial_review", "pending_applicant", "pending_exam_interview"]],
        ]),
    },
    approved_admissions: {
        fallback: 0,
        fn: (orm) => orm.searchCount("school.admission", [["state", "=", "accepted"]]),
    },
    catalog_courses: {
        fallback: 0,
        fn: (orm) => orm.searchCount("school.course.catalog", [["active", "=", true]]),
    },
};

const DASHBOARD_TEMPLATE = /* xml */ `
<div class="school-dashboard">

    <div class="school-hero">
        <div class="school-hero-bg-circle school-hero-bg-circle--tl"/>
        <div class="school-hero-bg-circle school-hero-bg-circle--br"/>
        <div class="school-hero-content">
            <div class="school-logo-area">
                <div t-if="state.logoUrl" class="school-logo-icon" aria-hidden="true">
                    <img t-att-src="state.logoUrl" class="school-logo-img" alt="Evangelical Theological Seminary logo" t-on-error="onLogoError"/>
                </div>
                <div>
                    <h1 class="school-title">Evangelical Theological Seminary</h1>
                </div>
            </div>
            <div class="school-clock" aria-live="polite" aria-atomic="true">
                <div class="school-time" t-esc="state.currentTime"/>
                <div class="school-date" t-esc="state.currentDate"/>
            </div>
        </div>
    </div>

    <div class="school-body">

        <div class="school-tiles-toolbar">
            <p class="school-tiles-hint">
                Drag the grip to reorder. Add shortcuts you use often — saved for you only.
            </p>
            <button t-if="state.usingCustomLayout" type="button" class="school-tiles-reset"
                    t-on-click="resetLayout">
                Reset to default
            </button>
        </div>

        <div class="school-stats-grid" t-ref="statsGrid" role="list">
            <t t-foreach="visibleTiles" t-as="tile" t-key="tile.key">
                <button type="button"
                        t-attf-class="school-stat-card stat-brand-{{ tile.color }}"
                        t-att-data-tile-key="tile.key"
                        t-on-click="onTileClick"
                        t-att-aria-label="tile.label">
                    <span class="stat-drag-handle" title="Drag to reorder" aria-hidden="true">
                        <i class="fa fa-bars"/>
                    </span>
                    <span class="stat-remove" title="Remove"
                          t-on-click.stop="removeTile"
                          t-att-aria-label="'Remove ' + tile.label">
                        <i class="fa fa-times"/>
                    </span>
                    <div class="stat-icon" aria-hidden="true">
                        <i t-attf-class="fa {{ tile.icon }}"/>
                    </div>
                    <div class="stat-info">
                        <t t-if="tile.kind === 'kpi'">
                            <div class="stat-number" t-esc="tileNumber(tile)"/>
                        </t>
                        <t t-else="">
                            <div class="stat-number stat-number--shortcut">Open</div>
                        </t>
                        <div class="stat-label" t-esc="tile.label"/>
                        <div class="stat-sub" t-esc="tileSub(tile)"/>
                    </div>
                    <div class="stat-arrow"><i class="fa fa-chevron-right"/></div>
                </button>
            </t>

            <button t-if="pickerHasItems"
                    type="button"
                    class="school-stat-card school-stat-card--add"
                    t-on-click="togglePicker"
                    aria-label="Add shortcut">
                <div class="stat-icon" aria-hidden="true"><i class="fa fa-plus"/></div>
                <div class="stat-info">
                    <div class="stat-number stat-number--shortcut">Add</div>
                    <div class="stat-label">Shortcut</div>
                    <div class="stat-sub">Choose a screen</div>
                </div>
            </button>
        </div>

        <div t-if="state.pickerOpen and pickerHasItems" class="school-tile-picker" role="listbox">
            <div class="school-tile-picker-title">Add a shortcut</div>
            <input type="search" class="school-tile-picker-search"
                   placeholder="Search all menus…"
                   t-att-value="state.pickerQuery"
                   t-on-input="onPickerQuery"
                   aria-label="Search menus"/>
            <t t-foreach="pickerSections" t-as="sec" t-key="sec.name">
                <div class="school-tile-picker-section">
                    <div class="school-tile-picker-section-title" t-esc="sec.name"/>
                    <div class="school-tile-picker-grid">
                        <t t-foreach="sec.items" t-as="opt" t-key="opt.key">
                            <button type="button" class="school-tile-picker-item"
                                    t-att-data-tile-key="opt.key"
                                    t-on-click="addFromPicker">
                                <i t-attf-class="fa {{ opt.icon }}" aria-hidden="true"/>
                                <span t-esc="opt.label"/>
                            </button>
                        </t>
                    </div>
                </div>
            </t>
            <div t-if="!pickerSections.length" class="school-tile-picker-empty">
                No matching menus.
            </div>
        </div>

    </div>
</div>
`;

class SchoolDashboard extends Component {
    static template = owl.xml`${DASHBOARD_TEMPLATE}`;

    setup() {
        this.action = useService("action");
        this.orm = useService("orm");
        this.notification = useService("notification");
        this.statsGridRef = useRef("statsGrid");

        this.state = useState({
            currentTime: "",
            currentDate: "",
            logoUrl: "",
            pickerOpen: false,
            pickerQuery: "",
            usingCustomLayout: false,
            allowedKeys: [],
            tileKeys: [],
            catalog: [],
            stats: {
                total_students: 0,
                active_students: 0,
                total_classes: 0,
                open_classes: 0,
                pending_admissions: 0,
                approved_admissions: 0,
                catalog_courses: 0,
            },
        });

        this._tick();
        this._clockTimer = setInterval(() => this._tick(), 1000);

        useSortable({
            ref: this.statsGridRef,
            elements: ".school-stat-card[data-tile-key]",
            handle: ".stat-drag-handle",
            ignore: ".stat-remove, .school-stat-card--add",
            cursor: "grabbing",
            delay: 0,
            touchDelay: 180,
            onDrop: (params) => this._onTileDrop(params),
        });

        onMounted(async () => {
            await this._loadBranding();
            await this._loadCatalog();
            await this._loadAllowedKeys();
            await this._loadLayout();
            await this._loadStats();
        });

        onWillUnmount(() => {
            clearInterval(this._clockTimer);
        });
    }

    get visibleTiles() {
        return this.state.tileKeys
            .map((key) => this._tileForKey(key))
            .filter((tile) => tile && this.state.allowedKeys.includes(tile.key));
    }

    get pickerHasItems() {
        return this._unfilteredPickerSections().length > 0;
    }

    get pickerSections() {
        const query = this.state.pickerQuery.trim().toLowerCase();
        if (!query) {
            return this._unfilteredPickerSections();
        }
        return this._unfilteredPickerSections()
            .map((sec) => ({
                name: sec.name,
                items: sec.items.filter((item) => item.label.toLowerCase().includes(query)),
            }))
            .filter((sec) => sec.items.length);
    }

    tileNumber(tile) {
        if (!tile.numberKey) {
            return 0;
        }
        return this.state.stats[tile.numberKey] ?? 0;
    }

    tileSub(tile) {
        if (tile.subFn) {
            return tile.subFn(this.state.stats);
        }
        return tile.sub || "";
    }

    _tileForKey(key) {
        return DASHBOARD_TILES[key] || this._menuTileMap()[key];
    }

    _menuTileMap() {
        const map = {};
        for (const section of this.state.catalog) {
            for (const item of section.items || []) {
                map[item.key] = item;
            }
        }
        return map;
    }

    _placedActions() {
        const xmlids = new Set();
        const ids = new Set();
        for (const key of this.state.tileKeys) {
            const tile = this._tileForKey(key);
            if (!tile) {
                continue;
            }
            if (tile.action) {
                xmlids.add(tile.action);
            }
            if (tile.actionXmlid) {
                xmlids.add(tile.actionXmlid);
            }
            if (tile.actionId) {
                ids.add(tile.actionId);
            }
        }
        return { xmlids, ids };
    }

    _unfilteredPickerSections() {
        const placedKeys = new Set(this.state.tileKeys);
        const placed = this._placedActions();
        const overview = Object.values(DASHBOARD_TILES).filter((tile) => {
            if (tile.kind !== "kpi") {
                return false;
            }
            if (!this.state.allowedKeys.includes(tile.key)) {
                return false;
            }
            if (placedKeys.has(tile.key)) {
                return false;
            }
            if (tile.action && placed.xmlids.has(tile.action)) {
                return false;
            }
            return true;
        });
        const overviewActions = new Set(overview.map((tile) => tile.action).filter(Boolean));
        const sections = [];
        if (overview.length) {
            sections.push({ name: "Overview", items: overview });
        }
        for (const sec of this.state.catalog) {
            const items = (sec.items || []).filter((item) => {
                if (placedKeys.has(item.key)) {
                    return false;
                }
                if (item.actionXmlid && placed.xmlids.has(item.actionXmlid)) {
                    return false;
                }
                if (item.actionId && placed.ids.has(item.actionId)) {
                    return false;
                }
                if (item.actionXmlid && overviewActions.has(item.actionXmlid)) {
                    return false;
                }
                return true;
            });
            if (items.length) {
                sections.push({ name: sec.name, items });
            }
        }
        return sections;
    }

    _hydrateMenuItem(item) {
        const style = SECTION_STYLE[item.section] || SECTION_STYLE.More;
        return {
            key: item.key,
            label: item.label,
            icon: style.icon,
            color: style.color,
            kind: "shortcut",
            action: item.action_xmlid || false,
            actionId: item.action_id,
            actionXmlid: item.action_xmlid || "",
            sub: item.section,
        };
    }

    async _loadCatalog() {
        let sections = [];
        try {
            sections = await this.orm.call("res.users", "kaierp_get_dashboard_shortcut_catalog", []) || [];
        } catch (err) {
            console.error("[SchoolDashboard] Failed to load shortcut catalog:", err);
        }
        this.state.catalog = sections.map((sec) => ({
            name: sec.name,
            items: (sec.items || []).map((item) => this._hydrateMenuItem(item)),
        }));
    }

    _defaultKeys() {
        return DEFAULT_TILE_ORDER.filter((key) => this.state.allowedKeys.includes(key));
    }

    _tick() {
        const now = new Date();
        this.state.currentTime = now.toLocaleTimeString("en-US", {
            hour: "2-digit",
            minute: "2-digit",
            second: "2-digit",
        });
        this.state.currentDate = now.toLocaleDateString("en-US", {
            weekday: "long",
            year: "numeric",
            month: "long",
            day: "numeric",
        });
    }

    async _loadBranding() {
        const companyId = user.activeCompany?.id || user.companyId;
        if (!companyId) {
            this.state.logoUrl = ETS_LOGO_STATIC;
            return;
        }
        try {
            const [company] = await this.orm.read("res.company", [companyId], ["logo"]);
            this.state.logoUrl = company?.logo
                ? `/web/image/res.company/${companyId}/logo`
                : ETS_LOGO_STATIC;
        } catch {
            this.state.logoUrl = ETS_LOGO_STATIC;
        }
    }

    onLogoError() {
        if (this.state.logoUrl !== ETS_LOGO_STATIC) {
            this.state.logoUrl = ETS_LOGO_STATIC;
        } else {
            this.state.logoUrl = "";
        }
    }

    async _loadAllowedKeys() {
        const entries = Object.values(DASHBOARD_TILES);
        const allowed = [];
        for (const tile of entries) {
            if (!tile.groups.length) {
                allowed.push(tile.key);
                continue;
            }
            try {
                const flags = await Promise.all(tile.groups.map((xmlid) => user.hasGroup(xmlid)));
                if (flags.some(Boolean)) {
                    allowed.push(tile.key);
                }
            } catch (err) {
                console.error(`[SchoolDashboard] Group check failed for ${tile.key}:`, err);
            }
        }
        for (const sec of this.state.catalog) {
            for (const item of sec.items || []) {
                if (!allowed.includes(item.key)) {
                    allowed.push(item.key);
                }
            }
        }
        this.state.allowedKeys = allowed;
    }

    async _loadLayout() {
        let saved = false;
        try {
            saved = await this.orm.call("res.users", "kaierp_get_dashboard_layout", []);
        } catch (err) {
            console.error("[SchoolDashboard] Failed to load layout:", err);
        }
        if (Array.isArray(saved)) {
            const keys = saved.filter((key) => this.state.allowedKeys.includes(key));
            this.state.tileKeys = keys;
            this.state.usingCustomLayout = true;
        } else {
            this.state.tileKeys = this._defaultKeys();
            this.state.usingCustomLayout = false;
        }
    }

    async _setKeys(keys, { custom = true } = {}) {
        const next = [];
        const seen = new Set();
        for (const key of keys) {
            if (!this.state.allowedKeys.includes(key) || seen.has(key)) {
                continue;
            }
            seen.add(key);
            next.push(key);
        }
        this.state.tileKeys = next;
        this.state.usingCustomLayout = custom;
        try {
            await this.orm.call(
                "res.users",
                "kaierp_set_dashboard_layout",
                [custom ? next : false]
            );
        } catch (err) {
            console.error("[SchoolDashboard] Failed to save layout:", err);
            this.notification.add("Could not save your dashboard layout.", { type: "danger" });
        }
        await this._loadStats();
    }

    async _loadStats() {
        const needed = new Set();
        for (const tile of this.visibleTiles) {
            for (const key of tile.statKeys || []) {
                needed.add(key);
            }
        }
        const keys = [...needed];
        if (!keys.length) {
            return;
        }
        const results = await Promise.allSettled(
            keys.map((key) => STAT_QUERIES[key].fn(this.orm))
        );
        const updates = {};
        results.forEach((result, index) => {
            const key = keys[index];
            if (result.status === "fulfilled") {
                updates[key] = result.value;
            } else {
                updates[key] = STAT_QUERIES[key].fallback;
                console.error(`[SchoolDashboard] Failed to load ${key}:`, result.reason);
            }
        });
        Object.assign(this.state.stats, updates);
    }

    _onTileDrop({ element, previous, next }) {
        const key = element?.dataset?.tileKey;
        if (!key) {
            return;
        }
        const keys = this.state.tileKeys.filter((k) => k !== key);
        let insertAt = keys.length;
        if (next?.dataset?.tileKey) {
            const idx = keys.indexOf(next.dataset.tileKey);
            insertAt = idx < 0 ? keys.length : idx;
        } else if (previous?.dataset?.tileKey) {
            const idx = keys.indexOf(previous.dataset.tileKey);
            insertAt = idx < 0 ? keys.length : idx + 1;
        }
        keys.splice(insertAt, 0, key);
        this._setKeys(keys);
    }

    onTileClick(ev) {
        if (ev.target.closest(".stat-remove, .stat-drag-handle")) {
            return;
        }
        const key = ev.currentTarget.dataset.tileKey;
        const tile = this._tileForKey(key);
        if (tile?.action) {
            this.action.doAction(tile.action);
        } else if (tile?.actionId) {
            this.action.doAction(tile.actionId);
        }
    }

    removeTile(ev) {
        const card = ev.currentTarget.closest("[data-tile-key]");
        const key = card?.dataset?.tileKey;
        if (!key) {
            return;
        }
        this._setKeys(this.state.tileKeys.filter((k) => k !== key));
    }

    togglePicker() {
        this.state.pickerOpen = !this.state.pickerOpen;
        if (!this.state.pickerOpen) {
            this.state.pickerQuery = "";
        }
    }

    onPickerQuery(ev) {
        this.state.pickerQuery = ev.target.value || "";
    }

    addFromPicker(ev) {
        const key = ev.currentTarget.dataset.tileKey;
        if (!key || this.state.tileKeys.includes(key)) {
            return;
        }
        this._setKeys([...this.state.tileKeys, key]);
        if (!this.pickerHasItems) {
            this.state.pickerOpen = false;
            this.state.pickerQuery = "";
        }
    }

    resetLayout() {
        this.state.pickerOpen = false;
        this._setKeys(this._defaultKeys(), { custom: false });
    }
}

registry.category("actions").add("school_dashboard", SchoolDashboard);
