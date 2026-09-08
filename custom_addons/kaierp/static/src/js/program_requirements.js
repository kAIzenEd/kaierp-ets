/** @odoo-module **/

import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { Component, useState, onMounted } from "@odoo/owl";

const TEMPLATE = /* xml */ `
<div class="pr-explorer">

    <div class="pr-hero">
        <div class="pr-hero-inner">
            <div>
                <p class="pr-eyebrow">Academics · Provisional demo</p>
                <h1 class="pr-title">Program Requirements</h1>
                <p class="pr-subtitle">
                    See how catalog courses map to programs, and what a student still needs.
                    Curriculum below is sample data for college feedback — not the final ETS map.
                </p>
            </div>
            <div class="pr-hero-actions">
                <button class="pr-link-btn" t-on-click="openCatalog">Course Catalog</button>
                <button class="pr-link-btn pr-link-btn--ghost" t-on-click="openMappings">Edit mappings</button>
            </div>
        </div>
    </div>

    <div class="pr-body">

        <div class="pr-mode-switch" role="tablist">
            <button t-attf-class="pr-mode-btn {{ state.mode === 'program' ? 'is-active' : '' }}"
                    t-on-click="onModeProgram" role="tab">
                By Program
            </button>
            <button t-attf-class="pr-mode-btn {{ state.mode === 'course' ? 'is-active' : '' }}"
                    t-on-click="onModeCourse" role="tab">
                By Course
            </button>
            <button t-attf-class="pr-mode-btn {{ state.mode === 'student' ? 'is-active' : '' }}"
                    t-on-click="onModeStudent" role="tab">
                By Student
            </button>
        </div>

        <t t-if="state.loading">
            <div class="pr-loading">Loading explorer…</div>
        </t>

        <t t-elif="state.error">
            <div class="pr-empty pr-empty--error">
                <p t-esc="state.error"/>
            </div>
        </t>

        <t t-else="">

            <t t-if="state.mode === 'program'">
                <div class="pr-toolbar">
                    <label class="pr-label" for="pr-program-select">Program</label>
                    <select id="pr-program-select" class="pr-select"
                            t-on-change="onProgramChange">
                        <t t-foreach="state.programs" t-as="p" t-key="p.code">
                            <option t-att-value="p.code"
                                    t-att-selected="p.code === state.selectedProgram ? true : undefined"
                                    t-esc="p.label"/>
                        </t>
                    </select>
                </div>

                <t t-if="state.programData">
                    <div class="pr-summary-row">
                        <div class="pr-summary-card">
                            <div class="pr-summary-num" t-esc="state.programData.summary.course_count"/>
                            <div class="pr-summary-lbl">Courses</div>
                        </div>
                        <div class="pr-summary-card">
                            <div class="pr-summary-num" t-esc="state.programData.summary.total_credits"/>
                            <div class="pr-summary-lbl">Credits mapped</div>
                        </div>
                        <t t-foreach="state.programData.summary.by_type" t-as="bt" t-key="bt.type">
                            <div t-attf-class="pr-summary-card pr-type-{{ bt.type }}">
                                <div class="pr-summary-num" t-esc="bt.count"/>
                                <div class="pr-summary-lbl" t-esc="bt.label"/>
                            </div>
                        </t>
                    </div>

                    <div class="pr-legend">
                        <span class="pr-pill pr-pill--required">Required</span>
                        <span class="pr-pill pr-pill--core">Core</span>
                        <span class="pr-pill pr-pill--elective">Elective</span>
                        <span class="pr-pill pr-pill--concentration">Concentration</span>
                        <span class="pr-legend-note">Also badges = counts toward other programs too</span>
                    </div>

                    <div class="pr-course-grid">
                        <t t-foreach="state.programData.courses" t-as="c" t-key="c.requirement_id">
                            <article t-attf-class="pr-course-card type-{{ c.requirement_type }}">
                                <div class="pr-course-top">
                                    <span class="pr-course-code" t-esc="c.code"/>
                                    <span t-attf-class="pr-pill pr-pill--{{ c.requirement_type }}"
                                          t-esc="c.requirement_type_label"/>
                                </div>
                                <h3 class="pr-course-name" t-esc="c.name"/>
                                <div class="pr-course-meta">
                                    <span t-esc="c.area_label"/>
                                    <span aria-hidden="true">·</span>
                                    <span t-esc="c.credits + ' cr'"/>
                                </div>
                                <t t-if="c.also_counts_toward.length">
                                    <div class="pr-also">
                                        <span class="pr-also-label">Also counts toward</span>
                                        <div class="pr-also-tags">
                                            <t t-foreach="c.also_counts_toward" t-as="a" t-key="a.program">
                                                <button class="pr-also-tag"
                                                        t-att-data-program="a.program"
                                                        t-on-click="onAlsoProgramClick"
                                                        t-esc="a.label"/>
                                            </t>
                                        </div>
                                    </div>
                                </t>
                                <t t-if="c.notes">
                                    <p class="pr-course-notes" t-esc="c.notes"/>
                                </t>
                            </article>
                        </t>
                    </div>

                    <t t-if="!state.programData.courses.length">
                        <div class="pr-empty">
                            <p>No courses mapped to this program yet.</p>
                        </div>
                    </t>
                </t>
            </t>

            <t t-elif="state.mode === 'course'">
                <div class="pr-toolbar">
                    <label class="pr-label" for="pr-course-select">Catalog course</label>
                    <select id="pr-course-select" class="pr-select"
                            t-on-change="onCourseChange">
                        <t t-foreach="state.courses" t-as="c" t-key="c.id">
                            <option t-att-value="c.id"
                                    t-att-selected="c.id === state.selectedCatalogId ? true : undefined"
                                    t-esc="'[' + c.code + '] ' + c.name"/>
                        </t>
                    </select>
                </div>

                <t t-if="state.courseData and state.courseData.course">
                    <div class="pr-course-spotlight">
                        <div>
                            <span class="pr-course-code" t-esc="state.courseData.course.code"/>
                            <h2 class="pr-spotlight-title" t-esc="state.courseData.course.name"/>
                            <div class="pr-course-meta">
                                <span t-esc="state.courseData.course.area_label"/>
                                <span aria-hidden="true">·</span>
                                <span t-esc="state.courseData.course.credit_hours + ' credit hours'"/>
                            </div>
                            <t t-if="state.courseData.course.description">
                                <p class="pr-spotlight-desc" t-esc="state.courseData.course.description"/>
                            </t>
                        </div>
                        <div class="pr-summary-card">
                            <div class="pr-summary-num" t-esc="state.courseData.programs.length"/>
                            <div class="pr-summary-lbl">Programs</div>
                        </div>
                    </div>

                    <div class="pr-program-list">
                        <t t-foreach="state.courseData.programs" t-as="p" t-key="p.requirement_id">
                            <button class="pr-program-row"
                                    t-att-data-program="p.program"
                                    t-on-click="onAlsoProgramClick">
                                <div>
                                    <div class="pr-program-row-title" t-esc="p.label"/>
                                    <div class="pr-course-meta">
                                        <span t-esc="p.credits + ' cr toward this program'"/>
                                        <t t-if="p.notes">
                                            <span aria-hidden="true">·</span>
                                            <span t-esc="p.notes"/>
                                        </t>
                                    </div>
                                </div>
                                <span t-attf-class="pr-pill pr-pill--{{ p.requirement_type }}"
                                      t-esc="p.requirement_type_label"/>
                            </button>
                        </t>
                    </div>

                    <t t-if="!state.courseData.programs.length">
                        <div class="pr-empty">
                            <p>This catalog course is not mapped to any program yet.</p>
                        </div>
                    </t>
                </t>
            </t>

            <t t-elif="state.mode === 'student'">
                <div class="pr-toolbar">
                    <label class="pr-label" for="pr-student-select">Student</label>
                    <select id="pr-student-select" class="pr-select"
                            t-on-change="onStudentChange">
                        <option value="">Select a student…</option>
                        <t t-foreach="state.students" t-as="s" t-key="s.id">
                            <option t-att-value="s.id"
                                    t-att-selected="s.id === state.selectedStudentId ? true : undefined"
                                    t-esc="studentOptionLabel(s)"/>
                        </t>
                    </select>
                </div>

                <t t-if="!state.students.length">
                    <div class="pr-empty">
                        <p>No students found yet. Add students (with a program) to preview progress.</p>
                    </div>
                </t>

                <t t-elif="state.studentData and state.studentData.student">
                    <div class="pr-student-header">
                        <div>
                            <h2 class="pr-spotlight-title" t-esc="state.studentData.student.name"/>
                            <div class="pr-course-meta">
                                <t t-if="state.studentData.student.student_id">
                                    <span t-esc="state.studentData.student.student_id"/>
                                    <span aria-hidden="true">·</span>
                                </t>
                                <t t-if="state.studentData.student.person_key">
                                    <span t-esc="state.studentData.student.person_key"/>
                                    <span aria-hidden="true">·</span>
                                </t>
                                <t t-if="state.studentData.label">
                                    <span t-esc="state.studentData.label"/>
                                </t>
                                <t t-else="">
                                    <span>No program assigned</span>
                                </t>
                            </div>
                            <t t-if="state.studentData.message">
                                <p class="pr-course-notes" t-esc="state.studentData.message"/>
                            </t>
                        </div>

                        <t t-if="state.studentData.summary and state.studentData.summary.total">
                            <div class="pr-progress-ring" t-att-aria-label="state.studentData.summary.percent + '% complete'">
                                <svg viewBox="0 0 36 36" class="pr-ring-svg">
                                    <path class="pr-ring-bg"
                                          d="M18 2.0845 a 15.9155 15.9155 0 0 1 0 31.831 a 15.9155 15.9155 0 0 1 0 -31.831"/>
                                    <path class="pr-ring-fg"
                                          t-attf-stroke-dasharray="{{ state.studentData.summary.percent }}, 100"
                                          d="M18 2.0845 a 15.9155 15.9155 0 0 1 0 31.831 a 15.9155 15.9155 0 0 1 0 -31.831"/>
                                    <text x="18" y="20.5" class="pr-ring-text"
                                          t-esc="state.studentData.summary.percent + '%'"/>
                                </svg>
                                <div class="pr-ring-caption">of required map</div>
                            </div>
                        </t>
                    </div>

                    <t t-if="state.studentData.summary and state.studentData.summary.total">
                        <div class="pr-summary-row">
                            <div class="pr-summary-card pr-status-completed">
                                <div class="pr-summary-num" t-esc="state.studentData.summary.completed"/>
                                <div class="pr-summary-lbl">Completed</div>
                            </div>
                            <div class="pr-summary-card pr-status-in_progress">
                                <div class="pr-summary-num" t-esc="state.studentData.summary.in_progress"/>
                                <div class="pr-summary-lbl">In progress</div>
                            </div>
                            <div class="pr-summary-card pr-status-remaining">
                                <div class="pr-summary-num" t-esc="state.studentData.summary.remaining"/>
                                <div class="pr-summary-lbl">Still needed</div>
                            </div>
                        </div>

                        <div class="pr-progress-list">
                            <t t-foreach="state.studentData.items" t-as="item" t-key="item.requirement_id">
                                <div t-attf-class="pr-progress-row status-{{ item.status }}">
                                    <div class="pr-progress-status" t-esc="statusLabel(item.status)"/>
                                    <div class="pr-progress-main">
                                        <div class="pr-progress-code-row">
                                            <span class="pr-course-code" t-esc="item.code"/>
                                            <span t-attf-class="pr-pill pr-pill--{{ item.requirement_type }}"
                                                  t-esc="item.requirement_type_label"/>
                                        </div>
                                        <div class="pr-course-name" t-esc="item.name"/>
                                        <t t-if="item.class_name">
                                            <div class="pr-course-meta" t-esc="item.class_name"/>
                                        </t>
                                    </div>
                                    <div class="pr-progress-credits" t-esc="item.credits + ' cr'"/>
                                </div>
                            </t>
                        </div>
                    </t>
                </t>
            </t>

        </t>
    </div>
</div>
`;

class ProgramRequirementsExplorer extends Component {
    static template = owl.xml`${TEMPLATE}`;

    setup() {
        this.action = useService("action");
        this.orm = useService("orm");
        this.state = useState({
            loading: true,
            error: "",
            mode: "program",
            programs: [],
            courses: [],
            students: [],
            selectedProgram: "mabs",
            selectedCatalogId: false,
            selectedStudentId: false,
            programData: null,
            courseData: null,
            studentData: null,
        });
        onMounted(() => this._bootstrap());
    }

    studentOptionLabel(s) {
        const id = s.student_id || s.person_key || "";
        const prog = s.program_label ? ` · ${s.program_label}` : "";
        return id ? `${s.name} (${id})${prog}` : `${s.name}${prog}`;
    }

    statusLabel(status) {
        return ({
            completed: "Done",
            in_progress: "In progress",
            remaining: "Needed",
        })[status] || status;
    }

    async _bootstrap() {
        this.state.loading = true;
        this.state.error = "";
        try {
            const data = await this.orm.call(
                "school.program.requirement",
                "get_explorer_bootstrap",
                []
            );
            this.state.programs = data.programs || [];
            this.state.courses = data.courses || [];
            this.state.students = data.students || [];
            this.state.selectedProgram =
                data.default_program ||
                (this.state.programs[0] && this.state.programs[0].code) ||
                false;
            this.state.selectedCatalogId = data.default_catalog_id || false;
            if (this.state.students.length) {
                this.state.selectedStudentId = this.state.students[0].id;
            }
            await this._loadModeData();
        } catch (err) {
            console.error(err);
            this.state.error =
                "Could not load program requirements. Upgrade the module and try again.";
        } finally {
            this.state.loading = false;
        }
    }

    onModeProgram() { return this.setMode("program"); }
    onModeCourse() { return this.setMode("course"); }
    onModeStudent() { return this.setMode("student"); }

    async setMode(mode) {
        this.state.mode = mode;
        await this._loadModeData();
    }

    async _loadModeData() {
        if (this.state.mode === "program" && this.state.selectedProgram) {
            this.state.programData = await this.orm.call(
                "school.program.requirement",
                "get_explorer_by_program",
                [this.state.selectedProgram]
            );
        } else if (this.state.mode === "course" && this.state.selectedCatalogId) {
            this.state.courseData = await this.orm.call(
                "school.program.requirement",
                "get_explorer_by_course",
                [this.state.selectedCatalogId]
            );
        } else if (this.state.mode === "student" && this.state.selectedStudentId) {
            this.state.studentData = await this.orm.call(
                "school.program.requirement",
                "get_explorer_by_student",
                [this.state.selectedStudentId]
            );
        }
    }

    async onProgramChange(ev) {
        this.state.selectedProgram = ev.target.value;
        await this._loadModeData();
    }

    async onCourseChange(ev) {
        this.state.selectedCatalogId = parseInt(ev.target.value, 10);
        await this._loadModeData();
    }

    async onStudentChange(ev) {
        const val = ev.target.value;
        this.state.selectedStudentId = val ? parseInt(val, 10) : false;
        if (this.state.selectedStudentId) {
            await this._loadModeData();
        } else {
            this.state.studentData = null;
        }
    }

    async onAlsoProgramClick(ev) {
        const program = ev.currentTarget.getAttribute("data-program");
        if (!program) {
            return;
        }
        this.state.mode = "program";
        this.state.selectedProgram = program;
        await this._loadModeData();
    }

    openCatalog() {
        this.action.doAction("kaierp.action_school_course_catalog");
    }

    openMappings() {
        this.action.doAction("kaierp.action_school_program_requirement");
    }
}

registry.category("actions").add("school_program_requirements", ProgramRequirementsExplorer);
