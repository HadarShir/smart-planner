import streamlit as st
import datetime
from datetime import time

st.set_page_config(
    page_title="Smart Planner",
    page_icon="🗓",
    layout="wide",
    initial_sidebar_state="collapsed",
)
from db.database import (
    create_user,
    get_all_users,
    save_preferences,
    add_study_block,
    get_study_blocks,
    delete_study_block,
    update_study_block,
    get_workouts,
    add_workout,
    delete_workout,
    update_workout,
    mark_workout_completed,
    get_preferences,
    add_task,
    get_tasks,
    update_task_status,
    update_task,
    delete_task,
    add_task_session,
    get_task_sessions,
    delete_task_session,
)
from db.schema import create_tables
from logic.scheduler import recommend_workouts, recommend_task_sessions, detect_overloaded_days, get_week_plan, suggest_slots_for_task
from logic.weather import get_weekly_weather

# Ensure all tables exist (safe to call on every startup)
create_tables()

# -------------------
# Constants & Helpers
# -------------------

DAYS = ["Sunday", "Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"]

DAY_START_MIN = 8 * 60   # 08:00
DAY_END_MIN = 22 * 60    # 22:00


def hhmm_to_min(hhmm: str) -> int:
    h, m = map(int, hhmm.split(":"))
    return h * 60 + m


def min_to_hhmm(minutes: int) -> str:
    h = minutes // 60
    m = minutes % 60
    return f"{h:02d}:{m:02d}"


def compute_free_windows(blocks_for_day):
    """
    blocks_for_day: list of tuples (start_str, end_str, label, block_id) sorted by start time
    returns list of tuples (free_start_str, free_end_str)
    """
    free = []
    current = DAY_START_MIN

    for s, e, _, _ in blocks_for_day:
        s_min = hhmm_to_min(s)
        e_min = hhmm_to_min(e)

        if s_min > current:
            free.append((min_to_hhmm(current), min_to_hhmm(s_min)))

        current = max(current, e_min)

    if current < DAY_END_MIN:
        free.append((min_to_hhmm(current), min_to_hhmm(DAY_END_MIN)))

    return free


# -------------------
# Session State
# -------------------
def ensure_selected_user(user_dict):
    if "selected_user_name" not in st.session_state:
        st.session_state.selected_user_name = None

    if st.session_state.selected_user_name not in user_dict:
        # default to first user if exists
        if user_dict:
            st.session_state.selected_user_name = list(user_dict.keys())[0]
        else:
            st.session_state.selected_user_name = None


# -------------------
# App UI
# -------------------

# ── Full-width CSS override ────────────────────────────────────────────────────
st.markdown("""
<style>
    /* Remove Streamlit's default max-width and side padding */
    .block-container {
        max-width: 100% !important;
        padding-left: 2rem !important;
        padding-right: 2rem !important;
        padding-top: 1rem !important;
    }
    /* Make tabs span the full width */
    .stTabs [data-baseweb="tab-list"] {
        gap: 0px;
        width: 100%;
        background: #0f1117;
        border-bottom: 2px solid #2d3748;
    }
    .stTabs [data-baseweb="tab"] {
        flex: 1;
        justify-content: center;
        padding: 18px 0px;
        letter-spacing: 0.3px;
    }
    /* Target the actual text inside tabs */
    .stTabs [data-baseweb="tab"] p,
    .stTabs [data-baseweb="tab"] span,
    .stTabs button[role="tab"],
    .stTabs button[role="tab"] p,
    div[data-baseweb="tab-list"] button,
    div[data-baseweb="tab-list"] button p {
        font-size: 22px !important;
        font-weight: 700 !important;
    }
    /* Active tab indicator thicker */
    .stTabs [aria-selected="true"] {
        border-bottom: 3px solid #e05252 !important;
    }
    /* Tighten top margin */
    header[data-testid="stHeader"] {
        height: 0rem;
    }
    /* Metric card styling */
    [data-testid="stMetric"] {
        background: #1a1f2e;
        border: 1px solid #2d3a52;
        border-radius: 10px;
        padding: 12px 16px;
    }
    [data-testid="stMetricValue"] {
        font-size: 22px !important;
        font-weight: 700 !important;
    }
    [data-testid="stMetricLabel"] {
        font-size: 13px !important;
        opacity: 0.8;
    }
</style>
""", unsafe_allow_html=True)

# Load users first (needed for header)
users    = get_all_users()
user_dict = {user_name: user_id for user_id, user_name in users}
ensure_selected_user(user_dict)

selected_user_name = st.session_state.selected_user_name
selected_user_id   = user_dict[selected_user_name] if selected_user_name else None

# ── Top header row ─────────────────────────────────────────────────────────────
title_col, user_col = st.columns([3, 1])
with title_col:
    st.title("🗓 Smart Planner")
with user_col:
    if user_dict:
        st.selectbox(
            "Active user",
            list(user_dict.keys()),
            key="selected_user_name",
            label_visibility="collapsed",
        )
    # Compact "add user" expander
    with st.expander("➕ New user", expanded=not bool(user_dict)):
        new_name = st.text_input("Name", key="new_user_name_top", label_visibility="collapsed",
                                  placeholder="Your name…")
        if st.button("Create", key="create_user_top"):
            if new_name.strip():
                create_user(new_name.strip())
                st.success(f"Welcome, {new_name.strip()}!")
                st.rerun()
            else:
                st.error("Please enter a name.")

st.divider()

# Re-read after possible new user
selected_user_name = st.session_state.selected_user_name
selected_user_id   = user_dict[selected_user_name] if selected_user_name else None

# ── Horizontal tab navigation ──────────────────────────────────────────────────
tab_weekly, tab_tasks, tab_workouts, tab_schedule, tab_prefs = st.tabs([
    "🗓 Weekly View",
    "✅ Tasks",
    "🏃 Workouts",
    "📅 Study Schedule",
    "⚙️ Preferences",
])

# Alias so the rest of the code uses `page` checks → replaced by tab context managers
# (each tab renders its own content below)

# ══════════════════════════════════════════════════════════════════════
# Tab: Study Schedule
# ══════════════════════════════════════════════════════════════════════
with tab_schedule:
    if not selected_user_id:
        st.info("Create a user first (top-right corner).")
    else:
        st.subheader("Add a study block")
        col1, col2 = st.columns(2)
        with col1:
            day_name = st.selectbox("Day", DAYS, key="add_day")
            start_t  = st.time_input("Start time", value=time(10, 0), key="add_start")
            end_t    = st.time_input("End time",   value=time(12, 0), key="add_end")
        with col2:
            label       = st.text_input("Course / Label", value="Course name", key="add_label")
            sb_location = st.text_input("📍 Location (optional)", placeholder="e.g. Campus, Building 72", key="add_sb_loc")
            sb_commute  = st.number_input("🚗 Commute time (min)", min_value=0, max_value=120,
                                          value=0, step=5, key="add_sb_commute")

        if st.button("Add study block"):
            if end_t <= start_t:
                st.error("End time must be after start time")
            else:
                add_study_block(selected_user_id, DAYS.index(day_name),
                                start_t.strftime("%H:%M"), end_t.strftime("%H:%M"),
                                label, sb_location, int(sb_commute))
                st.success("Study block added!")
                st.rerun()

        st.subheader("Your study blocks")
        blocks = get_study_blocks(selected_user_id)
        if not blocks:
            st.info("No study blocks yet.")
        else:
            for block_id, dow, s, e, lbl, location, commute_min in blocks:
                bc1, bc2, bc3 = st.columns([4, 1, 1])
                with bc1:
                    loc_str = f" · 📍 {location}" if location else ""
                    com_str = f" · 🚗 {commute_min}min" if commute_min else ""
                    st.write(f"**{DAYS[dow]}** {s}–{e} · {lbl}{loc_str}{com_str}")
                with bc3:
                    if st.button("🗑️", key=f"del_sb_{block_id}"):
                        delete_study_block(block_id)
                        st.rerun()

            with st.expander("✏️ Edit a study block"):
                edit_id      = st.number_input("Block ID to edit", min_value=1, value=blocks[0][0])
                edit_day     = st.selectbox("New day", DAYS, key="edit_sb_day")
                edit_start_t = st.time_input("New start time", value=time(10, 0), key="edit_sb_s")
                edit_end_t   = st.time_input("New end time",   value=time(12, 0), key="edit_sb_e")
                edit_label   = st.text_input("New label", value="Course name", key="edit_sb_lbl")
                edit_sb_loc  = st.text_input("📍 Location", key="edit_sb_loc")
                edit_sb_com  = st.number_input("🚗 Commute (min)", min_value=0, max_value=120,
                                               value=0, step=5, key="edit_sb_com")
                if st.button("Update study block"):
                    if edit_end_t <= edit_start_t:
                        st.error("End time must be after start time")
                    else:
                        update_study_block(int(edit_id), DAYS.index(edit_day),
                                           edit_start_t.strftime("%H:%M"),
                                           edit_end_t.strftime("%H:%M"),
                                           edit_label, edit_sb_loc, int(edit_sb_com))
                        st.success("Updated!")
                        st.rerun()

# ══════════════════════════════════════════════════════════════════════
# Tab: Tasks
# ══════════════════════════════════════════════════════════════════════
with tab_tasks:
    st.header("Tasks")

    if not selected_user_id:
        st.info("Create a user first (top-right corner).")
    else:

        PRIORITY_COLORS = {"high": "#7f1d1d", "medium": "#78350f", "low": "#14532d"}
        PRIORITY_BORDER = {"high": "#ef4444", "medium": "#f59e0b", "low": "#22c55e"}
        PRIORITY_EMOJI  = {"high": "🔴", "medium": "🟡", "low": "🟢"}

        # ── Add task form ──────────────────────────────────────────────
        with st.expander("➕ Add new task", expanded=False):
            t_title = st.text_input("Title", key="t_title")
            t_desc  = st.text_area("Description (optional)", key="t_desc", height=80)
            col1, col2, col3 = st.columns(3)
            with col1:
                t_due = st.date_input("Due date", key="t_due")
            with col2:
                t_priority = st.selectbox("Priority", ["high", "medium", "low"], key="t_priority")
            with col3:
                t_hours = st.number_input("Estimated hours", min_value=0.5, max_value=20.0,
                                           value=1.0, step=0.5, key="t_hours")

            if st.button("Add task", key="btn_add_task"):
                if not t_title.strip():
                    st.error("Please enter a title.")
                else:
                    add_task(
                        selected_user_id,
                        t_title.strip(),
                        t_desc.strip(),
                        t_due.strftime("%Y-%m-%d"),
                        t_priority,
                        float(t_hours),
                    )
                    st.success("Task added!")
                    st.rerun()

        # ── Pending tasks ──────────────────────────────────────────────
        st.subheader("Open tasks")
        pending = get_tasks(selected_user_id, status_filter="pending")

        if not pending:
            st.info("No open tasks. Add one above!")
        else:
            for task in pending:
                bg    = PRIORITY_COLORS[task["priority"]]
                bdr   = PRIORITY_BORDER[task["priority"]]
                emoji = PRIORITY_EMOJI[task["priority"]]
                due_str = task["due_date"] if task["due_date"] else "No due date"

                col_card, col_done, col_del = st.columns([6, 1, 1])
                with col_card:
                    st.markdown(
                        f"""
                        <div style="
                            padding:12px 14px;
                            border-radius:10px;
                            margin-bottom:6px;
                            background-color:{bg};
                            border:1px solid {bdr};">
                            <div style="font-size:15px;opacity:0.7;">
                                {emoji} {task['priority'].upper()} &nbsp;|&nbsp;
                                Due: {due_str} &nbsp;|&nbsp;
                                ~{task['estimated_hours']}h
                            </div>
                            <div style="font-weight:700;font-size:19px;margin-top:4px;">
                                {task['title']}
                            </div>
                            {"<div style='font-size:16px;opacity:0.75;margin-top:4px;'>" + task['description'] + "</div>" if task['description'] else ""}
                        </div>
                        """,
                        unsafe_allow_html=True,
                    )
                with col_done:
                    if st.button("✅", key=f"done_{task['id']}", help="Mark as done"):
                        update_task_status(task["id"], "done")
                        st.rerun()
                with col_del:
                    if st.button("🗑️", key=f"del_t_{task['id']}", help="Delete task"):
                        delete_task(task["id"])
                        st.rerun()

                # ── Slot suggestions for this task ─────────────────────
                result = suggest_slots_for_task(selected_user_id, task, n_suggestions=3)
                suggestions       = result["suggestions"]
                slot_warning      = result["warning"]
                existing_sessions = [
                    s for s in get_task_sessions(selected_user_id)
                    if s["task_id"] == task["id"]
                ]

                with st.expander(f"🕐 Schedule '{task['title']}'", expanded=False):
                    # Warning: not enough time before deadline
                    if slot_warning:
                        st.error(f"⚠️ {slot_warning}")

                    if existing_sessions:
                        st.markdown("**Already scheduled:**")
                        for s in existing_sessions:
                            sc1, sc2 = st.columns([5, 1])
                            with sc1:
                                st.markdown(
                                    f"📅 **{DAYS[s['day_of_week']]}** &nbsp; "
                                    f"{s['start_time']} – {s['end_time']}"
                                )
                            with sc2:
                                if st.button("✕", key=f"del_sess_{s['id']}", help="Remove"):
                                    delete_task_session(s["id"])
                                    st.rerun()
                        st.divider()

                    if not suggestions and not slot_warning:
                        st.info("No free slots found before the deadline. Try adjusting your schedule.")
                    elif suggestions:
                        st.markdown("**Pick a time slot:**")
                        for idx, slot in enumerate(suggestions):
                            s1, s2 = st.columns([5, 1])
                            with s1:
                                st.markdown(
                                    f"📅 **{slot['day_name']}** &nbsp; "
                                    f"{slot['start_time']} – {slot['end_time']}"
                                )
                            with s2:
                                if st.button("Accept", key=f"acc_{task['id']}_{idx}"):
                                    add_task_session(
                                        selected_user_id, task["id"],
                                        slot["day_of_week"],
                                        slot["start_time"], slot["end_time"],
                                    )
                                    st.success("Added to your schedule!")
                                    st.rerun()

        # ── Edit task ──────────────────────────────────────────────────
        if pending:
            with st.expander("✏️ Edit a task"):
                task_ids   = [t["id"] for t in pending]
                task_titles = [f"#{t['id']} – {t['title']}" for t in pending]
                edit_idx = st.selectbox("Select task to edit", range(len(task_titles)),
                                         format_func=lambda i: task_titles[i], key="edit_task_sel")
                et = pending[edit_idx]

                e_title    = st.text_input("Title", value=et["title"], key="e_title")
                e_desc     = st.text_area("Description", value=et["description"], key="e_desc", height=80)
                import datetime
                e_due_val  = datetime.date.fromisoformat(et["due_date"]) if et["due_date"] else datetime.date.today()
                e_due      = st.date_input("Due date", value=e_due_val, key="e_due")
                e_priority = st.selectbox("Priority", ["high", "medium", "low"],
                                           index=["high","medium","low"].index(et["priority"]), key="e_prio")
                e_hours    = st.number_input("Estimated hours", min_value=0.5, max_value=20.0,
                                              value=float(et["estimated_hours"]), step=0.5, key="e_hours")
                if st.button("Save changes", key="btn_edit_task"):
                    update_task(et["id"], e_title.strip(), e_desc.strip(),
                                e_due.strftime("%Y-%m-%d"), e_priority, float(e_hours))
                    st.success("Task updated!")
                    st.rerun()

        # ── Completed tasks ────────────────────────────────────────────
        done_tasks = get_tasks(selected_user_id, status_filter="done")
        if done_tasks:
            with st.expander(f"✅ Completed tasks ({len(done_tasks)})"):
                for task in done_tasks:
                    col_card, col_undo, col_del = st.columns([6, 1, 1])
                    with col_card:
                        st.markdown(
                            f"""
                            <div style="
                                padding:10px 14px;
                                border-radius:10px;
                                margin-bottom:6px;
                                background-color:#1a1a2e;
                                border:1px solid #333;
                                opacity:0.7;">
                                <div style="font-size:15px;opacity:0.6;">
                                    Due: {task['due_date'] or 'N/A'} | ~{task['estimated_hours']}h
                                </div>
                                <div style="font-weight:600;font-size:18px;
                                            text-decoration:line-through;margin-top:3px;">
                                    {task['title']}
                                </div>
                            </div>
                            """,
                            unsafe_allow_html=True,
                        )
                    with col_undo:
                        if st.button("↩️", key=f"undo_{task['id']}", help="Mark as pending"):
                            update_task_status(task["id"], "pending")
                            st.rerun()
                    with col_del:
                        if st.button("🗑️", key=f"del_done_{task['id']}", help="Delete task"):
                            delete_task(task["id"])
                            st.rerun()

# ══════════════════════════════════════════════════════════════════════
# Tab: Workouts
# ══════════════════════════════════════════════════════════════════════
with tab_workouts:
    st.header("Workouts & Recommendations")

    if not selected_user_id:
        st.info("Create a user first (top-right corner).")
    else:

        workouts = get_workouts(selected_user_id)

        # ── Scheduled workouts with completion tracking ────────────────
        st.subheader("Your scheduled workouts")

        if not workouts:
            st.info("No workouts scheduled yet. Accept a recommendation below!")
        else:
            completed_count = sum(1 for w in workouts if w[5])
            total_count     = len(workouts)
            st.progress(completed_count / total_count,
                        text=f"{completed_count}/{total_count} completed this week")

            missed = []
            for w_id, dow, s, e, lbl, completed, w_loc, w_com in workouts:
                is_done = bool(completed)

                if is_done:
                    bg, bdr, status_icon = "#0d2b1a", "#22c55e", "✅"
                else:
                    bg, bdr, status_icon = "#1e3a5f", "#3b82f6", "🏃"

                col_card, col_done, col_del = st.columns([5, 1, 1])
                with col_card:
                    st.markdown(
                        f"""
                        <div style="padding:10px 14px;border-radius:10px;margin-bottom:6px;
                            background:{bg};border:1px solid {bdr};
                            {'opacity:0.6;text-decoration:line-through;' if is_done else ''}">
                            <div style="font-size:15px;opacity:0.6;">{DAYS[dow]} · {s} – {e}{(' · 📍 ' + w_loc) if w_loc else ''}{(' · 🚗 ' + str(w_com) + 'min') if w_com else ''}</div>
                            <div style="font-weight:700;font-size:18px;margin-top:3px;">
                                {status_icon} {lbl}
                            </div>
                        </div>
                        """,
                        unsafe_allow_html=True,
                    )
                with col_done:
                    if is_done:
                        if st.button("↩️", key=f"undo_w_{w_id}", help="Mark as not done"):
                            mark_workout_completed(w_id, False)
                            st.rerun()
                    else:
                        if st.button("✅", key=f"done_w_{w_id}", help="Mark as completed"):
                            mark_workout_completed(w_id, True)
                            st.rerun()
                        missed.append((w_id, dow, s, e, lbl, w_loc, w_com))
                with col_del:
                    if st.button("🗑️", key=f"del_w_{w_id}", help="Delete workout"):
                        delete_workout(w_id)
                        st.rerun()

            # ── Reschedule missed workouts ─────────────────────────────
            if missed:
                st.divider()
                st.subheader("🔄 Reschedule missed workouts")
                st.caption("These workouts haven't been marked done yet. Want to move them?")

                recs = recommend_workouts(selected_user_id)

                for w_id, dow, s, e, lbl, w_loc, w_com in missed:
                    with st.expander(f"Reschedule: {DAYS[dow]} {s}–{e} ({lbl})"):
                        if not recs:
                            st.info("No free slots found. Adjust your schedule or preferences.")
                        else:
                            for i, rec in enumerate(recs[:3]):
                                r1, r2 = st.columns([5, 1])
                                with r1:
                                    st.write(f"📅 **{DAYS[rec['day_of_week']]}** {rec['start_time']} – {rec['end_time']}")
                                with r2:
                                    if st.button("Move", key=f"reschedule_{w_id}_{i}"):
                                        update_workout(
                                            w_id,
                                            rec["day_of_week"],
                                            rec["start_time"],
                                            rec["end_time"],
                                            lbl,
                                        )
                                        st.success(f"Moved to {DAYS[rec['day_of_week']]} {rec['start_time']}!")
                                        st.rerun()

        # ── Smart recommendations ──────────────────────────────────────
        st.divider()
        st.subheader("💡 Smart Recommendations")
        recs = recommend_workouts(selected_user_id)

        if not recs:
            st.info("No open slots found. Make sure preferences are set and your schedule has free time!")
        else:
            for i, rec in enumerate(recs):
                col1, col2 = st.columns([4, 1])
                with col1:
                    st.write(f"**{DAYS[rec['day_of_week']]}** · {rec['start_time']} – {rec['end_time']}")
                with col2:
                    if st.button("Accept", key=f"rec_{i}"):
                        add_workout(
                            selected_user_id,
                            rec["day_of_week"],
                            rec["start_time"],
                            rec["end_time"],
                            "Workout",
                        )
                        st.success("Workout added!")
                        st.rerun()

# ══════════════════════════════════════════════════════════════════════
# Tab: Weekly View
# ══════════════════════════════════════════════════════════════════════
with tab_weekly:
    if not selected_user_id:
        st.info("Create a user first (top-right corner).")
    else:

        try:
            from streamlit_calendar import calendar as st_calendar
            HAS_CALENDAR = True
        except ImportError:
            HAS_CALENDAR = False

        # ── Load data first ────────────────────────────────────────────
        blocks            = get_study_blocks(selected_user_id)
        workouts          = get_workouts(selected_user_id)
        accepted_sessions = get_task_sessions(selected_user_id)
        plan              = get_week_plan(selected_user_id)
        overloaded_days   = plan["overloaded"]
        all_tasks_wi      = get_tasks(selected_user_id)
        done_tasks_wi     = [t for t in all_tasks_wi if t["status"] == "done"]
        pend_tasks_wi     = [t for t in all_tasks_wi if t["status"] == "pending"]
        today_dow         = (datetime.date.today().weekday() + 1) % 7

        # ── Daily Check-in ─────────────────────────────────────────────
        today_str   = datetime.date.today().isoformat()
        checkin_key = f"checkin_{selected_user_id}_{today_str}"
        if checkin_key not in st.session_state:
            st.session_state[checkin_key] = None

        ENERGY_OPTIONS = ["😴 Drained", "😪 Low", "😐 Okay", "😊 Good", "⚡ Energized"]
        MOOD_OPTIONS   = ["😰 Stressed", "😐 Neutral", "🙂 Calm", "😄 Great"]

        if st.session_state[checkin_key] is None:
            st.markdown(
                "<div style='background:#1a1f2e;border:1px solid #2d3a52;border-radius:12px;"
                "padding:16px 20px;margin-bottom:4px;'>"
                "<div style='font-size:19px;font-weight:700;margin-bottom:4px;'>"
                "☀️ Daily Check-in — How are you feeling today?</div></div>",
                unsafe_allow_html=True,
            )
            ci1, ci2, ci3 = st.columns([3, 2, 1])
            with ci1:
                energy_val = st.select_slider(
                    "Energy level",
                    options=ENERGY_OPTIONS,
                    value="😐 Okay",
                    key=f"energy_sl_{checkin_key}",
                )
            with ci2:
                mood_val = st.selectbox(
                    "Mood",
                    MOOD_OPTIONS,
                    index=2,
                    key=f"mood_sel_{checkin_key}",
                )
            with ci3:
                st.markdown("<div style='height:28px'></div>", unsafe_allow_html=True)
                if st.button("Check in ✓", key=f"btn_ci_{checkin_key}", use_container_width=True):
                    st.session_state[checkin_key] = {"energy": energy_val, "mood": mood_val}
                    st.rerun()
        else:
            ci             = st.session_state[checkin_key]
            energy_idx     = ENERGY_OPTIONS.index(ci["energy"])
            is_heavy_today = today_dow in overloaded_days
            has_high_tasks = any(t["priority"] == "high" for t in pend_tasks_wi)

            if energy_idx <= 1 and is_heavy_today:
                tip = "You're low on energy on a heavy day. Consider postponing non-urgent tasks and taking short breaks."
            elif energy_idx <= 1:
                tip = "Low energy today — a good rest day. Focus on light, low-priority tasks and avoid overloading."
            elif energy_idx == 2 and ci["mood"] == "😰 Stressed":
                tip = "Feeling stressed? Break your work into 25-minute Pomodoro sessions with 5-min breaks. One step at a time!"
            elif energy_idx >= 3 and has_high_tasks:
                tip = "Great energy! Perfect time to tackle your high-priority tasks. Strike while the iron is hot 🔥"
            elif energy_idx >= 3:
                tip = "Feeling great and no urgent tasks — use this energy to get ahead on upcoming work or squeeze in a workout 💪"
            else:
                tip = "Steady day ahead. Work through your task list and keep the momentum going."

            tip_color  = "#0d2b1a" if energy_idx >= 3 else "#1e1e00" if energy_idx == 2 else "#2b0d0d"
            tip_border = "#22c55e" if energy_idx >= 3 else "#f59e0b" if energy_idx == 2 else "#ef4444"
            col_tip, col_reset = st.columns([9, 1])
            with col_tip:
                st.markdown(
                    f"<div style='background:{tip_color};border:1px solid {tip_border};"
                    f"border-radius:10px;padding:12px 16px;margin-bottom:8px;'>"
                    f"<span style='font-size:16px;opacity:0.75;'>{ci['energy']} &nbsp;·&nbsp; {ci['mood']}</span><br>"
                    f"<span style='font-size:18px;font-weight:600;'>💡 {tip}</span>"
                    f"</div>",
                    unsafe_allow_html=True,
                )
            with col_reset:
                if st.button("↩️", key=f"reset_ci_{checkin_key}", help="Check in again"):
                    st.session_state[checkin_key] = None
                    st.rerun()

        # ── Weekly Insights panel ──────────────────────────────────────
        from logic.scheduler import get_all_events_by_day, _free_slots as _fs
        prefs_wi       = get_preferences(selected_user_id)
        buf_wi         = prefs_wi[3] if prefs_wi else 30
        evts_by_day_wi = get_all_events_by_day(selected_user_id)
        total_free_min = sum(
            sum(e - s for s, e in _fs(
                sorted(evts_by_day_wi[d], key=lambda x: hhmm_to_min(x["start"])),
                buf_wi,
            ))
            for d in range(7)
        )
        total_study_min = sum(hhmm_to_min(b[3]) - hhmm_to_min(b[2]) for b in blocks)
        done_wo_cnt     = sum(1 for w in workouts if w[5])

        m1, m2, m3, m4 = st.columns(4)
        m1.metric("📚 Study / week",   f"{round(total_study_min / 60, 1)}h")
        m2.metric("🕊 Free this week", f"{round(total_free_min  / 60, 1)}h")
        m3.metric("🏃 Workouts",       f"{done_wo_cnt}/{len(workouts)} done")
        m4.metric("✅ Tasks",          f"{len(done_tasks_wi)}/{len(all_tasks_wi)} done")

        # ── Overload warnings ──────────────────────────────────────────
        if overloaded_days:
            names = ", ".join(DAYS[d] for d in overloaded_days)
            st.warning(f"⚠️ Heavy days detected: **{names}**. Consider moving some tasks.")

        # ── Controls ───────────────────────────────────────────────────
        ctrl1, ctrl2, ctrl3, ctrl4, ctrl5 = st.columns(5)
        show_free     = ctrl1.checkbox("Free windows",        value=True)
        show_workouts = ctrl2.checkbox("Workouts",            value=True)
        show_tasks    = ctrl3.checkbox("Task sessions",       value=True)
        show_recs     = ctrl4.checkbox("Show recommendations",value=True)
        show_commute  = ctrl5.checkbox("🚗 Commute time",     value=True)

        # ── Map day_of_week → dates across 10 weeks ───────────────────
        WEEKS_AHEAD = 10
        today      = datetime.date.today()
        week_start = today - datetime.timedelta(days=(today.weekday() + 1) % 7)

        def to_dates(dow: int) -> list:
            """Return dates for this dow across the next WEEKS_AHEAD weeks."""
            return [
                week_start + datetime.timedelta(weeks=w, days=dow)
                for w in range(WEEKS_AHEAD)
            ]

        # ── Build FullCalendar events list (10 weeks of recurring data) ─
        cal_events = []

        # Study blocks — recurring across 10 weeks
        for block_id, dow, s, e, lbl, *_ in blocks:
            for week_idx, d in enumerate(to_dates(dow)):
                cal_events.append({
                    "id":              f"study_{block_id}_w{week_idx}",
                    "title":           f"📖 {lbl}",
                    "start":           f"{d}T{s}:00",
                    "end":             f"{d}T{e}:00",
                    "backgroundColor": "#1e293b",
                    "borderColor":     "#475569",
                    "textColor":       "#cbd5e1",
                    # Only week-0 events carry the real id for drag-save
                    "extendedProps":   {"dbId": block_id if week_idx == 0 else None,
                                        "type": "study"},
                    "editable":        week_idx == 0,
                })

        # Confirmed workouts — recurring across 10 weeks
        if show_workouts:
            for w_id, dow, s, e, lbl, *_ in workouts:
                for week_idx, d in enumerate(to_dates(dow)):
                    cal_events.append({
                        "id":              f"workout_{w_id}_w{week_idx}",
                        "title":           f"🏃 {lbl}",
                        "start":           f"{d}T{s}:00",
                        "end":             f"{d}T{e}:00",
                        "backgroundColor": "#0f2d4a",
                        "borderColor":     "#2563eb",
                        "textColor":       "#93c5fd",
                        "extendedProps":   {"dbId": w_id if week_idx == 0 else None,
                                            "type": "workout"},
                        "editable":        week_idx == 0,
                    })

        # Recommendations — current week only, not draggable
        TASK_BG = {"high": "#3b0a0a", "medium": "#2d1f00", "low": "#052e16"}
        TASK_BR = {"high": "#dc2626", "medium": "#d97706", "low": "#16a34a"}
        TASK_TX = {"high": "#fca5a5", "medium": "#fcd34d", "low": "#86efac"}

        if show_recs:
            for rec in plan["workouts"]:
                d = week_start + datetime.timedelta(days=rec["day_of_week"])
                cal_events.append({
                    "id":              f"rec_wo_{rec['day_of_week']}_{rec['start_time']}",
                    "title":           "💡 Workout?",
                    "start":           f"{d}T{rec['start_time']}:00",
                    "end":             f"{d}T{rec['end_time']}:00",
                    "backgroundColor": "#0c1e36",
                    "borderColor":     "#1d4ed8",
                    "textColor":       "#60a5fa",
                    "editable":        False,
                    "classNames":      ["suggested-event"],
                })
            if show_tasks:
                for sess in plan["task_sessions"]:
                    # Skip any malformed sessions
                    if hhmm_to_min(sess["end_time"]) <= hhmm_to_min(sess["start_time"]):
                        continue
                    d = week_start + datetime.timedelta(days=sess["day_of_week"])
                    p = sess["priority"]
                    cal_events.append({
                        "id":              f"task_{sess['task_id']}_{sess['start_time']}",
                        "title":           f"📚 {sess['task_title']}",
                        "start":           f"{d}T{sess['start_time']}:00",
                        "end":             f"{d}T{sess['end_time']}:00",
                        "backgroundColor": TASK_BG.get(p, "#1e293b"),
                        "borderColor":     TASK_BR.get(p, "#475569"),
                        "textColor":       TASK_TX.get(p, "#cbd5e1"),
                        "editable":        False,
                        "classNames":      ["suggested-event"],
                    })

        # ── View toggle ────────────────────────────────────────────────
        tog_col, mode_col = st.columns([1, 3])
        with tog_col:
            interactive_mode = st.toggle(
                "🗓 Drag & drop",
                value=False,
                help="Switch to FullCalendar for drag-and-drop editing across 10 weeks"
            )
        with mode_col:
            if not interactive_mode:
                view_mode = st.radio(
                    "View",
                    ["📅 Weekly", "📆 Daily"],
                    horizontal=True,
                    label_visibility="collapsed",
                    key="grid_view_mode",
                )

        # ══════════════════════════════════════════════════════════════
        # STATIC GRID VIEW  (default — the beautiful card layout)
        # ══════════════════════════════════════════════════════════════
        if not interactive_mode:

            # Build by_day — including visible commute blocks
            by_day = {i: [] for i in range(7)}

            def _add_with_commute(dow, s, e, lbl, bid, etype, location, commute_min):
                """Append the event plus small commute blocks before/after if needed."""
                s_min, e_min = hhmm_to_min(s), hhmm_to_min(e)
                if show_commute and commute_min > 0 and location:
                    before_s = max(DAY_START_MIN, s_min - commute_min)
                    if before_s < s_min:
                        by_day[dow].append((min_to_hhmm(before_s), s,
                                            f"{location}", None, "commute"))
                by_day[dow].append((s, e, lbl, bid, etype))
                if show_commute and commute_min > 0 and location:
                    after_e = min(DAY_END_MIN, e_min + commute_min)
                    if after_e > e_min:
                        by_day[dow].append((e, min_to_hhmm(after_e),
                                            f"{location}", None, "commute"))

            for block_id, dow, s, e, lbl, location, commute_min in blocks:
                _add_with_commute(dow, s, e, lbl, block_id, "study", location, commute_min)

            if show_workouts:
                for w_id, dow, s, e, lbl, completed, w_loc, w_com in workouts:
                    _add_with_commute(dow, s, e, lbl, w_id, "workout", w_loc, w_com)

            # Accepted task sessions — solid blocks
            if show_tasks:
                PRIO_TYPE = {"high": "task_high", "medium": "task_medium", "low": "task_low"}
                for sess in accepted_sessions:
                    by_day[sess["day_of_week"]].append((
                        sess["start_time"], sess["end_time"],
                        sess["title"], sess["id"],
                        PRIO_TYPE.get(sess["priority"], "task_medium")
                    ))

            if show_recs:
                for rec in plan["workouts"]:
                    by_day[rec["day_of_week"]].append(
                        (rec["start_time"], rec["end_time"], "Workout", None, "rec_workout")
                    )
                if show_tasks:
                    for sess in plan["task_sessions"]:
                        # Skip malformed sessions
                        if hhmm_to_min(sess["end_time"]) <= hhmm_to_min(sess["start_time"]):
                            continue
                        by_day[sess["day_of_week"]].append(
                            (sess["start_time"], sess["end_time"],
                             sess["task_title"], None,
                             f"rec_task_{sess['priority']}")
                        )

            for dow in by_day:
                by_day[dow].sort(key=lambda x: x[0])

            # Legend
            st.markdown(
                """
                <div style="display:flex;gap:10px;flex-wrap:wrap;margin-bottom:14px;font-size:16px;">
                    <span style="background:#2b2b2b;border:1px solid #555;padding:3px 9px;border-radius:6px;">📖 Study</span>
                    <span style="background:#1e3a5f;border:1px solid #3b82f6;padding:3px 9px;border-radius:6px;">🏃 Workout</span>
                    <span style="background:#4a1a1a;border:1px solid #ef4444;padding:3px 9px;border-radius:6px;">🔴 Task (high)</span>
                    <span style="background:#3d2c00;border:1px solid #f59e0b;padding:3px 9px;border-radius:6px;">🟡 Task (med)</span>
                    <span style="background:#0f2d1a;border:1px solid #22c55e;padding:3px 9px;border-radius:6px;">🟢 Task (low)</span>
                    <span style="background:#1f3a2a;border:1px solid #2e6b44;padding:3px 9px;border-radius:6px;">🕊 Free</span>
                    <span style="background:#1c1a2e;border:1px dashed #7c6fcd;padding:3px 9px;border-radius:6px;">🚗 Commute</span>
                </div>
                """,
                unsafe_allow_html=True,
            )

            TASK_COLORS = {
                # Recommended (dashed)
                "rec_task_high":   ("#4a1a1a", "#ef4444", "🔴"),
                "rec_task_medium": ("#3d2c00", "#f59e0b", "🟡"),
                "rec_task_low":    ("#0f2d1a", "#22c55e", "🟢"),
                # Accepted (solid, brighter)
                "task_high":   ("#7f1d1d", "#ef4444", "🔴"),
                "task_medium": ("#78350f", "#f59e0b", "🟡"),
                "task_low":    ("#14532d", "#22c55e", "🟢"),
            }

            # ── Load weather (shared by both views) ───────────────────
            prefs_for_weather = get_preferences(selected_user_id)
            home_city_w = prefs_for_weather[4] if prefs_for_weather else ""
            weather_by_dow = {}
            if home_city_w:
                weather_list = get_weekly_weather(home_city_w)
                weather_by_dow = {w["dow"]: w for w in weather_list}
                if not weather_list:
                    wcol1, wcol2 = st.columns([6, 1])
                    with wcol1:
                        st.warning(
                            f"⚠️ לא ניתן לטעון מזג אוויר עבור **'{home_city_w}'**. "
                            f"נסי עם שמות כמו: Beersheba, Tel Aviv, Jerusalem, Haifa. "
                            f"(עברית גם עובדת: באר שבע, תל אביב, ירושלים, חיפה)"
                        )
                    with wcol2:
                        if st.button("🔄 Retry", key="weather_retry"):
                            get_weekly_weather.clear()
                            st.rerun()

            # ── Outfit recommendation engine ───────────────────────────
            def _outfit_recommendation(w: dict) -> str:
                """
                Build a simple outfit recommendation in Hebrew
                based on temperature and precipitation.
                Returns an HTML string.
                """
                t_max  = w["temp_max"]
                t_min  = w["temp_min"]
                precip = w.get("precip", 0)
                avg    = (t_max + t_min) / 2

                wmo  = w.get("condition", "")
                is_sunny = any(s in wmo for s in ("Clear", "Mainly clear", "Partly cloudy"))

                # Clothing
                if avg < 8:
                    clothing = "🧥 מעיל חורף כבד + מכנסיים ארוכים"
                elif avg < 14:
                    clothing = "🧥 ג'קט חם + מכנסיים ארוכים"
                elif avg < 19:
                    clothing = "🧣 ג'קט קל + שכבה מתחת + מכנסיים ארוכים"
                elif avg < 25:
                    clothing = "👕 חולצה + שכבה קלה לערב + מכנסיים ארוכים"
                else:
                    clothing = "👕 חולצה קלה + מכנסיים קצרים"

                # Shoes
                if precip > 1:
                    shoes = "👟 נעליים עמידות למים"
                elif avg < 14:
                    shoes = "👞 נעליים סגורות"
                else:
                    shoes = "👟 סניקרס / נעליים נוחות"

                # Accessories
                extras = []
                if precip > 1:
                    extras.append("☂️ מטרייה חובה")
                if is_sunny and t_max > 18:
                    extras.append("🕶️ משקפי שמש")
                if avg > 28:
                    extras.append("🧴 קרם הגנה")
                if avg < 10:
                    extras.append("🧤 כפפות + כובע")
                elif avg < 16:
                    extras.append("🧣 צעיף קל")

                lines = [
                    f"<div style='margin-bottom:10px;'><span style='font-size:15px;opacity:0.55;'>לבוש</span><br>"
                    f"<span style='font-size:19px;font-weight:600;'>{clothing}</span></div>",
                    f"<div style='margin-bottom:10px;'><span style='font-size:15px;opacity:0.55;'>נעליים</span><br>"
                    f"<span style='font-size:19px;font-weight:600;'>{shoes}</span></div>",
                ]
                if extras:
                    lines.append(
                        f"<div><span style='font-size:15px;opacity:0.55;'>אביזרים</span><br>"
                        f"<span style='font-size:19px;font-weight:600;'>"
                        f"{' &nbsp;·&nbsp; '.join(extras)}</span></div>"
                    )

                return (
                    f"<div style='text-align:right;direction:rtl;'>"
                    + "".join(lines) +
                    f"</div>"
                )

            # ── Helper: render events for one day column ───────────────
            def _render_day_events(i, card_padding="10px 8px",
                                   time_size="13px", label_size="16px"):
                events = [{"type": t, "start": s, "end": e, "label": lbl}
                          for s, e, lbl, bid, t in by_day[i]]
                if show_free:
                    confirmed = [
                        (s, e, lbl, bid)
                        for s, e, lbl, bid, t in by_day[i]
                        if not t.startswith("rec_") and t != "commute"
                    ]
                    for fs, fe in compute_free_windows(confirmed):
                        events.append({"type": "free", "start": fs, "end": fe, "label": "FREE"})
                events.sort(key=lambda ev: hhmm_to_min(ev["start"]))
                if not events:
                    st.write("—")
                    return
                for ev in events:
                    t = ev["type"]
                    is_rec = t.startswith("rec_")
                    border_style = "dashed" if is_rec else "solid"
                    opacity      = "0.78"   if is_rec else "1"
                    if t == "study":
                        bg, bdr, icon = "#2b2b2b", "#555", "📖"
                    elif t in ("workout", "rec_workout"):
                        bg, bdr, icon = "#1e3a5f", "#3b82f6", "🏃"
                    elif t in TASK_COLORS:
                        bg, bdr, icon = TASK_COLORS[t]
                    elif t == "free":
                        bg, bdr, icon = "#1f3a2a", "#2e6b44", "🕊"
                    elif t == "commute":
                        bg, bdr, icon = "#1c1a2e", "#7c6fcd", "🚗"
                    else:
                        bg, bdr, icon = "#2b2b2b", "#555", ""
                    st.markdown(
                        f"""<div style="padding:{card_padding};border-radius:10px;
                            margin-bottom:7px;background:{bg};
                            border:1px {border_style} {bdr};opacity:{opacity};
                            text-align:center;">
                            <div style="font-size:{time_size};opacity:0.7;margin-bottom:5px;">
                                {ev['start']} – {ev['end']}
                            </div>
                            <div style="font-weight:700;font-size:{label_size};line-height:1.4;">
                                {icon} {ev['label']}
                            </div>
                        </div>""",
                        unsafe_allow_html=True,
                    )

            # ══════════════════════════════════════════════════════════
            # DAILY VIEW
            # ══════════════════════════════════════════════════════════
            if view_mode == "📆 Daily":
                if "daily_view_dow" not in st.session_state:
                    st.session_state.daily_view_dow = today_dow

                d_dow = st.session_state.daily_view_dow

                # Navigation bar
                nav1, nav2, nav3, nav4, nav5 = st.columns([1, 1, 4, 1, 1])
                with nav1:
                    if st.button("⬅️ Prev", use_container_width=True):
                        st.session_state.daily_view_dow = (d_dow - 1) % 7
                        st.rerun()
                with nav2:
                    if st.button("Today", use_container_width=True):
                        st.session_state.daily_view_dow = today_dow
                        st.rerun()
                with nav3:
                    # Day selector
                    chosen = st.selectbox(
                        "Jump to day", DAYS,
                        index=d_dow,
                        label_visibility="collapsed",
                        key="daily_jump",
                    )
                    if DAYS.index(chosen) != d_dow:
                        st.session_state.daily_view_dow = DAYS.index(chosen)
                        st.rerun()
                with nav5:
                    if st.button("Next ➡️", use_container_width=True):
                        st.session_state.daily_view_dow = (d_dow + 1) % 7
                        st.rerun()

                # Day header + weather
                is_today_marker = " 📍 Today" if d_dow == today_dow else ""
                fire_marker = " 🔥" if d_dow in overloaded_days else ""
                w = weather_by_dow.get(d_dow)
                if w:
                    st.markdown(
                        f"<div style='text-align:center;font-size:30px;font-weight:800;"
                        f"margin:8px 0 4px;'>{DAYS[d_dow]}{fire_marker}{is_today_marker}</div>"
                        f"<div style='text-align:center;font-size:36px;margin:4px 0;'>{w['icon']}</div>"
                        f"<div style='text-align:center;font-size:20px;font-weight:600;margin-bottom:2px;'>"
                        f"{w['temp_min']}°–{w['temp_max']}°C &nbsp;·&nbsp; {w['condition']}</div>"
                        f"<div style='text-align:center;font-size:18px;opacity:0.7;margin-bottom:14px;'>{w['tip']}</div>",
                        unsafe_allow_html=True,
                    )
                else:
                    st.markdown(
                        f"<div style='text-align:center;font-size:30px;font-weight:800;"
                        f"margin:8px 0 14px;'>{DAYS[d_dow]}{fire_marker}{is_today_marker}</div>",
                        unsafe_allow_html=True,
                    )

                # Outfit button (only when weather is available)
                if w:
                    outfit_key = f"show_outfit_{d_dow}"
                    if outfit_key not in st.session_state:
                        st.session_state[outfit_key] = False

                    _, btn_col, _ = st.columns([2, 2, 2])
                    with btn_col:
                        if st.button("👗 לבוש מומלץ", key=f"outfit_btn_{d_dow}",
                                     use_container_width=True):
                            st.session_state[outfit_key] = not st.session_state[outfit_key]

                    if st.session_state[outfit_key]:
                        _, outfit_col, _ = st.columns([1, 4, 1])
                        with outfit_col:
                            st.markdown(
                                f"<div style='background:#1a1f2e;border:1px solid #3b4a6b;"
                                f"border-radius:12px;padding:16px 20px;margin-bottom:14px;'>"
                                f"<div style='font-size:15px;font-weight:700;margin-bottom:12px;"
                                f"text-align:center;'>👗 המלצת לבוש ל-{DAYS[d_dow]}</div>"
                                f"{_outfit_recommendation(w)}"
                                f"</div>",
                                unsafe_allow_html=True,
                            )

                # Single wide column
                _, center, _ = st.columns([1, 4, 1])
                with center:
                    _render_day_events(d_dow, card_padding="14px 16px",
                                       time_size="15px", label_size="20px")

            # ══════════════════════════════════════════════════════════
            # WEEKLY VIEW (7 columns)
            # ══════════════════════════════════════════════════════════
            else:
                cols = st.columns(7)
                for i, col in enumerate(cols):
                    with col:
                        day_label = DAYS[i] + (" 🔥" if i in overloaded_days else "")
                        w = weather_by_dow.get(i)
                        if w:
                            st.markdown(
                                f"<div style='text-align:center;font-size:21px;font-weight:700;"
                                f"margin-bottom:2px;padding-bottom:4px;border-bottom:1px solid #333;'>"
                                f"{day_label}</div>"
                                f"<div style='text-align:center;font-size:26px;margin:3px 0;'>{w['icon']}</div>"
                                f"<div style='text-align:center;font-size:17px;font-weight:600;"
                                f"opacity:0.85;margin-bottom:2px;'>{w['temp_min']}°–{w['temp_max']}°C</div>"
                                f"<div style='text-align:center;font-size:16px;opacity:0.7;"
                                f"margin-bottom:10px;'>{w['tip']}</div>",
                                unsafe_allow_html=True,
                            )
                        else:
                            st.markdown(
                                f"<div style='text-align:center;font-size:21px;"
                                f"font-weight:700;margin-bottom:10px;padding-bottom:5px;"
                                f"border-bottom:1px solid #333;'>{day_label}</div>",
                                unsafe_allow_html=True
                            )
                        _render_day_events(i)

        # ══════════════════════════════════════════════════════════════
        # INTERACTIVE FULLCALENDAR VIEW  (drag & drop, 10 weeks)
        # ══════════════════════════════════════════════════════════════
        else:
            if not HAS_CALENDAR:
                st.warning("Run `pip install streamlit-calendar` then restart the app.")
            else:
                calendar_options = {
                    "initialView":      "timeGridWeek",
                    "firstDay":         0,
                    "editable":         True,
                    "selectable":       True,
                    "nowIndicator":     True,
                    "slotMinTime":      "07:00:00",
                    "slotMaxTime":      "23:00:00",
                    "allDaySlot":       False,
                    "height":           700,
                    "expandRows":       True,
                    "headerToolbar": {
                        "left":   "prev,next today",
                        "center": "title",
                        "right":  "timeGridWeek,timeGridDay",
                    },
                    "slotLabelFormat":  {"hour": "2-digit", "minute": "2-digit", "hour12": False},
                    "eventTimeFormat":  {"hour": "2-digit", "minute": "2-digit", "hour12": False},
                    "slotDuration":     "00:30:00",
                    "slotLabelInterval":"01:00:00",
                    "dayHeaderFormat":  {"weekday": "short", "month": "numeric", "day": "numeric"},
                }

                custom_css = """
                    .fc { font-family: system-ui, sans-serif !important; }
                    .fc-theme-standard td, .fc-theme-standard th,
                    .fc-theme-standard .fc-scrollgrid { border-color: #2d3748 !important; }
                    .fc-col-header-cell {
                        background: #1a202c !important; padding: 6px 0 !important;
                        font-size: 12px !important; font-weight: 600 !important;
                        border-bottom: 2px solid #4a5568 !important;
                    }
                    .fc-col-header-cell a { color: #e2e8f0 !important; text-decoration: none !important; }
                    .fc-timegrid-slot       { height: 32px !important; }
                    .fc-timegrid-slot-minor { border-color: #1e2533 !important; }
                    .fc-timegrid-slot-label { font-size: 11px !important; color: #718096 !important; }
                    .fc-timegrid-col        { background: #0f1117 !important; }
                    .fc-timegrid-now-indicator-line  { border-color: #f56565 !important; border-width: 2px !important; }
                    .fc-timegrid-now-indicator-arrow { border-top-color: #f56565 !important; border-bottom-color: #f56565 !important; }
                    .fc-event {
                        border-radius: 6px !important; font-size: 11px !important;
                        font-weight: 600 !important; padding: 2px 5px !important;
                        box-shadow: 0 1px 4px rgba(0,0,0,0.4) !important; cursor: grab !important;
                    }
                    .fc-event:active { cursor: grabbing !important; }
                    .suggested-event { opacity: 0.55 !important; border-style: dashed !important; border-width: 2px !important; }
                    .fc-button-primary {
                        background: #2d3748 !important; border-color: #4a5568 !important;
                        color: #e2e8f0 !important; border-radius: 6px !important;
                        font-size: 12px !important; padding: 4px 10px !important;
                    }
                    .fc-button-primary:hover { background: #4a5568 !important; }
                    .fc-button-primary:not(:disabled).fc-button-active { background: #3182ce !important; }
                    .fc-toolbar-title { font-size: 16px !important; font-weight: 700 !important; color: #e2e8f0 !important; }
                """

                state = st_calendar(
                    events=cal_events,
                    options=calendar_options,
                    custom_css=custom_css,
                    key="main_calendar",
                )

                if state and state.get("eventChange"):
                    changed   = state["eventChange"]["event"]
                    event_id  = changed.get("id", "")
                    new_start = changed.get("start", "")
                    new_end   = changed.get("end", "")
                    try:
                        ns = datetime.datetime.fromisoformat(new_start[:19])
                        ne = datetime.datetime.fromisoformat(new_end[:19])
                        new_dow       = (ns.weekday() + 1) % 7
                        new_start_str = ns.strftime("%H:%M")
                        new_end_str   = ne.strftime("%H:%M")
                        parts = event_id.split("_")
                        if event_id.startswith("study_"):
                            bid = int(parts[1])
                            lbl = {b[0]: b[4] for b in blocks}.get(bid, "Study")
                            update_study_block(bid, new_dow, new_start_str, new_end_str, lbl)
                            st.success(f"📖 Moved to {DAYS[new_dow]} {new_start_str}–{new_end_str}")
                            st.rerun()
                        elif event_id.startswith("workout_"):
                            wid = int(parts[1])
                            lbl = {w[0]: w[4] for w in workouts}.get(wid, "Workout")
                            update_workout(wid, new_dow, new_start_str, new_end_str, lbl)
                            st.success(f"🏃 Moved to {DAYS[new_dow]} {new_start_str}–{new_end_str}")
                            st.rerun()
                    except Exception as ex:
                        st.error(f"Could not save: {ex}")

                st.caption("💡 Drag events to reschedule. Dashed = suggestions (accept in Workouts page).")

# ══════════════════════════════════════════════════════════════════════
# Tab: Preferences
# ══════════════════════════════════════════════════════════════════════
with tab_prefs:
    if not selected_user_id:
        st.info("Create a user first (top-right corner).")
    else:
        prefs = get_preferences(selected_user_id)
        default_wpw  = prefs[0] if prefs else 3
        default_dur  = prefs[1] if prefs else 60
        default_time = prefs[2] if prefs else "any"
        default_buf  = prefs[3] if prefs else 45
        default_city = prefs[4] if prefs else ""

        st.subheader("📍 Personal details")
        home_city = st.text_input("City of residence", value=default_city,
                                   placeholder="e.g. Beer Sheva, Tel Aviv…",
                                   key="pref_city")
        st.caption("Used for weather forecasts in the weekly view.")

        st.subheader("🏃 Workout preferences")
        col1, col2 = st.columns(2)
        with col1:
            workouts_per_week = st.number_input(
                "Workouts per week", min_value=1, max_value=14, value=default_wpw)
            workout_duration = st.number_input(
                "Workout duration (minutes)", min_value=15, max_value=180, value=default_dur)
        with col2:
            preferred_time = st.selectbox(
                "Preferred time of day", ["morning", "afternoon", "evening", "any"],
                index=["morning", "afternoon", "evening", "any"].index(default_time))
            buffer_min = st.number_input(
                "Buffer around events (minutes)", min_value=0, max_value=180, value=default_buf)

        if st.button("Save preferences"):
            save_preferences(selected_user_id, int(workouts_per_week),
                             int(workout_duration), preferred_time, int(buffer_min),
                             home_city.strip())
            st.success("✅ Preferences saved!")