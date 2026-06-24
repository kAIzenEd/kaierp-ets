/** @odoo-module **/

import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { Component, useState, onMounted, onWillUnmount } from "@odoo/owl";
import { rpc } from '@web/core/network/rpc';

// ---------------------------------------------------------------------------
// OWL XML Template
// ---------------------------------------------------------------------------
const DASHBOARD_TEMPLATE = /* xml */ `
<div class="school-dashboard">

    <!-- ════════════════════════════════════════════════════
         HERO BANNER  –  logo · title · live clock
    ════════════════════════════════════════════════════ -->
    <div class="school-hero">
        <div class="school-hero-bg-circle school-hero-bg-circle--tl"/>
        <div class="school-hero-bg-circle school-hero-bg-circle--br"/>

        <div class="school-hero-content">

            <!-- Left: branding -->
            <div class="school-logo-area">
                <div class="school-logo-icon" aria-hidden="true"><img t-att-src="'/kaierp/static/src/image/ets_logo.png'" class="school-logo-img" alt="School logo"/></div>
                <div>
                    <h1 class="school-title">EVANGELICAL THEOLOGICAL SEMINARY</h1>
                    <p class="school-subtitle">TEACH. PRACTICE. THE WORD</p>
                </div>
            </div>

            <!-- Right: clock -->
            <div class="school-clock" aria-live="polite" aria-atomic="true">
                <div class="school-time" t-esc="state.currentTime"/>
                <div class="school-date" t-esc="state.currentDate"/>
            </div>

        </div>
    </div>

    <!-- ════════════════════════════════════════════════════
         BODY
    ════════════════════════════════════════════════════ -->
    <div class="school-body">

        <section class="school-panel school-announcements-panel">

            <div class="panel-header-row">
                <h2 class="panel-title">
                    <i class="fa fa-bullhorn" aria-hidden="true"/> Announcements
                </h2>
                <button class="btn-view-all" t-on-click="openAnnouncements">
                    View All <i class="fa fa-chevron-right" aria-hidden="true"/>
                </button>
            </div>

            <!-- Loading state -->
            <t t-if="state.loading">
                <div class="ann-skeleton">
                    <div class="skeleton-row"/>
                    <div class="skeleton-row short"/>
                    <div class="skeleton-row"/>
                    <div class="skeleton-row short"/>
                </div>
            </t>

            <!-- Empty state -->
            <t t-elif="state.stats.announcements.length === 0">
                <div class="ann-empty">
                    <div class="ann-empty-icon" aria-hidden="true"><i class="fa fa-inbox"/></div>
                    <p>No active announcements right now.</p>
                </div>
            </t>

            <!-- Announcement cards -->
            <t t-else="">
                <t t-foreach="state.stats.announcements"
                    t-as="ann"
                    t-key="ann.id">
                    <button t-attf-class="ann-card ann-priority-{{ ann.priority }}"
                            t-att-data-ann-id="ann.id"
                            t-on-click="onAnnounceClick"
                            t-attf-aria-label="Open announcement: {{ ann.name }}">
                        <div class="ann-card-header">
                            <span class="ann-card-title" t-esc="ann.name"/>
                            <t t-if="ann.priority === '2'">
                                <span class="ann-pill ann-pill--urgent">URGENT</span>
                            </t>
                            <t t-elif="ann.priority === '1'">
                                <span class="ann-pill ann-pill--important">IMPORTANT</span>
                            </t>
                        </div>
                        <div class="ann-card-meta">
                            <span t-esc="ann.audience"/>
                            <span class="ann-sep" aria-hidden="true">·</span>
                            <span t-esc="ann.date_publish"/>
                        </div>
                    </button>
                </t>
            </t>
        </section>

        <!-- ── KPI stat cards ─────────────────────────── -->
        <div class="school-stats-grid" role="list">

            <button class="school-stat-card stat-brand-red"
                    t-on-click="openStudents"
                    aria-label="View students">
                <div class="stat-icon" aria-hidden="true"><i class="fa fa-graduation-cap"/></div>
                <div class="stat-info">
                    <div class="stat-number" t-esc="state.stats.active_students"/>
                    <div class="stat-label">Active Students</div>
                    <div class="stat-sub"
                         t-esc="'of ' + state.stats.total_students + ' total'"/>
                </div>
                <div class="stat-arrow"><i class="fa fa-chevron-right"/></div>
            </button>

            <button class="school-stat-card stat-brand-navy"
                    t-on-click="openClasses"
                    aria-label="View classes">
                <div class="stat-icon" aria-hidden="true"><i class="fa fa-book"/></div>
                <div class="stat-info">
                    <div class="stat-number" t-esc="state.stats.open_classes"/>
                    <div class="stat-label">Active Classes</div>
                    <div class="stat-sub"
                         t-esc="'of ' + state.stats.total_classes + ' total'"/>
                </div>
                <div class="stat-arrow"><i class="fa fa-chevron-right"/></div>
            </button>

            <button class="school-stat-card stat-brand-red"
                    t-on-click="openAdmissions"
                    aria-label="View admissions">
                <div class="stat-icon" aria-hidden="true"><i class="fa fa-file-text-o"/></div>
                <div class="stat-info">
                    <div class="stat-number" t-esc="state.stats.pending_admissions"/>
                    <div class="stat-label">Pending Admissions</div>
                    <div class="stat-sub"
                         t-esc="state.stats.approved_admissions + ' approved'"/>
                </div>
                <div class="stat-arrow"><i class="fa fa-chevron-right"/></div>
            </button>

            <button class="school-stat-card stat-brand-navy"
                    t-on-click="openGrades"
                    aria-label="View grades">
                <div class="stat-icon" aria-hidden="true"><i class="fa fa-bar-chart"/></div>
                <div class="stat-info">
                    <div class="stat-number">GPA</div>
                    <div class="stat-label">Grades &amp; Reports</div>
                    <div class="stat-sub">View all grades</div>
                </div>
                <div class="stat-arrow"><i class="fa fa-chevron-right"/></div>
            </button>

        </div>

        <!-- ── Two-column layout ──────────────────────── -->
        <div class="school-main-grid">

            <!-- LEFT: Quick-access shortcuts -->
            <section class="school-panel school-shortcuts-panel">
                <h2 class="panel-title">
                    <i class="fa fa-th-large" aria-hidden="true"/> Quick Access
                </h2>

                <div class="shortcuts-grid">
                    <button class="shortcut-btn sc-brand-red"   t-on-click="openStudents">
                        <span class="sc-icon" aria-hidden="true"><i class="fa fa-graduation-cap"/></span>
                        <span class="sc-label">Students</span>
                    </button>
                    <button class="shortcut-btn sc-brand-navy"  t-on-click="openAdmissions">
                        <span class="sc-icon" aria-hidden="true"><i class="fa fa-file-text-o"/></span>
                        <span class="sc-label">Admissions</span>
                    </button>
                    <button class="shortcut-btn sc-brand-cream" t-on-click="openClasses">
                        <span class="sc-icon" aria-hidden="true"><i class="fa fa-book"/></span>
                        <span class="sc-label">Classes</span>
                    </button>
                    <button class="shortcut-btn sc-brand-red"   t-on-click="openGrades">
                        <span class="sc-icon" aria-hidden="true"><i class="fa fa-bar-chart"/></span>
                        <span class="sc-label">Grades</span>
                    </button>
                    <button class="shortcut-btn sc-brand-navy"  t-on-click="openTranscripts">
                        <span class="sc-icon" aria-hidden="true"><i class="fa fa-file-text"/></span>
                        <span class="sc-label">Transcripts</span>
                    </button>
                    <button class="shortcut-btn sc-brand-cream" t-on-click="openAttendance">
                        <span class="sc-icon" aria-hidden="true"><i class="fa fa-calendar-check-o"/></span>
                        <span class="sc-label">Attendance</span>
                    </button>
                    <button class="shortcut-btn sc-brand-red"   t-on-click="openTeachers">
                        <span class="sc-icon" aria-hidden="true"><i class="fa fa-black-tie"/></span>
                        <span class="sc-label">Faculty</span>
                    </button>
                    <button class="shortcut-btn sc-brand-navy"  t-on-click="openFees">
                        <span class="sc-icon" aria-hidden="true"><i class="fa fa-usd"/></span>
                        <span class="sc-label">Fees</span>
                    </button>
                    <button class="shortcut-btn sc-brand-cream" t-on-click="openCalendar">
                        <span class="sc-icon" aria-hidden="true"><i class="fa fa-calendar"/></span>
                        <span class="sc-label">Calendar</span>
                    </button>
                    <button class="shortcut-btn sc-brand-red"   t-on-click="openTodo">
                        <span class="sc-icon" aria-hidden="true"><i class="fa fa-tasks"/></span>
                        <span class="sc-label">To-Do</span>
                    </button>
                </div>
            </section>
            
        </div><!-- /.school-main-grid -->

    </div><!-- /.school-body -->
</div><!-- /.school-dashboard -->
`;

// ---------------------------------------------------------------------------
// Component class
// ---------------------------------------------------------------------------
class SchoolDashboard extends Component {
    static template = owl.xml`${DASHBOARD_TEMPLATE}`;

    setup() {
        this.action = useService("action");
        this.orm    = useService("orm");

        this.state = useState({
            currentTime : "",
            currentDate : "",
            loading     : true,
            aiPrompt    : "",
            aiLoading   : false,
            aiAnswer    : "",
            stats: {
                total_students      : 0,
                active_students     : 0,
                total_classes       : 0,
                open_classes        : 0,
                pending_admissions  : 0,
                approved_admissions : 0,
                announcements       : [],
            },
        });

        // Start live clock
        this._tick();
        this._clockTimer = setInterval(() => this._tick(), 1000);

        onMounted(async () => {
            await this._loadStats();
        });

        onWillUnmount(() => {
            clearInterval(this._clockTimer);
        });
    }

    // ── Clock ────────────────────────────────────────────────────
    _tick() {
        const now = new Date();
        this.state.currentTime = now.toLocaleTimeString("en-US", {
            hour   : "2-digit",
            minute : "2-digit",
            second : "2-digit",
        });
        this.state.currentDate = now.toLocaleDateString("en-US", {
            weekday : "long",
            year    : "numeric",
            month   : "long",
            day     : "numeric",
        });
    }

    // ── Data ─────────────────────────────────────────────────────
    async _loadStats() {
        const queries = [
            { key: "total_students",      fallback: 0, fn: () => this.orm.searchCount("school.student", []) },
            { key: "active_students",     fallback: 0, fn: () => this.orm.searchCount("school.student", [["state", "=", "active"]]) },
            { key: "total_classes",       fallback: 0, fn: () => this.orm.searchCount("school.class", []) },
            { key: "open_classes",        fallback: 0, fn: () => this.orm.searchCount("school.class", [["state", "in", ["open", "in_progress"]]]) },
            { key: "pending_admissions",  fallback: 0, fn: () => this.orm.searchCount("school.admission", [["state", "in", ["initial_review", "pending_applicant", "pending_exam_interview"]]]) },
            { key: "approved_admissions", fallback: 0, fn: () => this.orm.searchCount("school.admission", [["state", "=", "accepted"]]) },
            {
                key: "announcements",
                fallback: [],
                fn: () => this.orm.searchRead(
                    "school.announcement",
                    [["is_active", "=", true]],
                    ["name", "priority", "date_publish", "audience"],
                    { limit: 6, order: "date_publish desc" }
                ),
            },
        ];

        const results = await Promise.allSettled(queries.map((q) => q.fn()));
        const updates = {};
        results.forEach((result, index) => {
            const { key, fallback } = queries[index];
            if (result.status === "fulfilled") {
                updates[key] = result.value;
            } else {
                updates[key] = fallback;
                console.error(`[SchoolDashboard] Failed to load ${key}:`, result.reason);
            }
        });
        Object.assign(this.state.stats, updates);
        this.state.loading = false;
    }

    // ── AI Assistant ─────────────────────────────────────────────
    async submitAI(ev) {
        ev.preventDefault && ev.preventDefault();
        const prompt = this.state.aiPrompt && this.state.aiPrompt.trim();
        if (!prompt) return;
        this.state.aiLoading = true;
        this.state.aiAnswer = '';
        try {
            const result = await rpc('/kaierp/ai_query', {
                model: 'school.student',
                prompt: prompt,
                domain: [],
                fields: ['name','id'],
            });
            if (result && result.ok) {
                this.state.aiAnswer = result.answer || JSON.stringify(result);
            } else {
                this.state.aiAnswer = '[Error] ' + (result && result.error ? result.error : 'unknown');
            }
        } catch (err) {
            this.state.aiAnswer = '[Error] ' + err;
        } finally {
            this.state.aiLoading = false;
        }
    }

    // ── Navigation ───────────────────────────────────────────────
    openStudents()      { this.action.doAction("kaierp.action_school_student"); }
    openClasses()       { this.action.doAction("kaierp.action_school_class"); }
    openAdmissions()    { this.action.doAction("kaierp.action_school_admission"); }
    openGrades()        { this.action.doAction("kaierp.action_school_grade"); }
    openTranscripts()   { this.action.doAction("kaierp.action_school_transcript"); }
    openAttendance()    { this.action.doAction("kaierp.action_school_attendance"); }
    openTeachers()      { this.action.doAction("kaierp.action_school_teacher"); }
    openFees()          { this.action.doAction("kaierp.action_school_fee"); }
    openAnnouncements() { this.action.doAction("kaierp.action_school_announcement"); }
    onAnnounceClick(ev) {
        const annId = parseInt(ev.currentTarget.getAttribute("data-ann-id"));
        this.openAnnouncement(annId);
    }
    openAnnouncement(annId) { 
        this.action.doAction({
            type: "ir.actions.act_window",
            res_model: "school.announcement",
            res_id: annId,
            views: [[false, "form"]],
            target: "current",
        });
    }
    openCalendar()      { this.action.doAction("calendar.action_calendar_event"); }
    openTodo()          { this.action.doAction("project.action_view_all_task"); }
}

// ---------------------------------------------------------------------------
// Register as a client-action tag
// ---------------------------------------------------------------------------
registry.category("actions").add("school_dashboard", SchoolDashboard);