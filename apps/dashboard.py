"""
Kimi Agent Pack Dashboard v3.0
Local quick-validation mode

Run: streamlit run apps/dashboard.py
"""

import streamlit as st
import requests
import json
import os
from datetime import datetime

API_BASE = os.environ.get("API_URL", "http://localhost:8000")

st.set_page_config(
    page_title="Agent Pack Dashboard",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ─── Custom CSS ─────────────────────────────────────────

st.markdown("""
<style>
    .block-container {
        padding-top: 1rem;
        padding-bottom: 1rem;
    }
    .stMetric {
        background-color: #f8f9fa;
        border-radius: 8px;
        padding: 10px;
    }
    .log-container {
        background-color: #0f172a;
        color: #e2e8f0;
        padding: 12px;
        border-radius: 8px;
        font-family: monospace;
        font-size: 12px;
        max-height: 400px;
        overflow-y: auto;
        line-height: 1.5;
    }
    .gate-pass { color: #22c55e; font-weight: 600; }
    .gate-fail { color: #ef4444; font-weight: 600; }
    .gate-pending { color: #f59e0b; font-weight: 600; }
    .status-badge {
        display: inline-block;
        padding: 2px 10px;
        border-radius: 12px;
        font-size: 11px;
        font-weight: 600;
    }
    .status-idle { background-color: #f3f4f6; color: #6b7280; }
    .status-running { background-color: #d1fae5; color: #166534; }
    .status-blocked { background-color: #fef3c7; color: #92400e; }
    .status-completed { background-color: #dbeafe; color: #1e40af; }
    .status-failed { background-color: #fee2e2; color: #991b1b; }
</style>
""", unsafe_allow_html=True)

# ─── Sidebar Navigation ─────────────────────────────────

st.sidebar.markdown("## 🧭 Navigation")
page = st.sidebar.radio("", [
    "Home", "Current Project", "Current Run", "Task Board",
    "Recent Artifacts", "Agents & Skills", "Eval Dashboard",
    "Memory Review", "Gate Status", "Script Console"
])

st.sidebar.markdown("---")
st.sidebar.markdown(f"**API Base:** `{API_BASE}`")
st.sidebar.markdown(f"**Time:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

# ─── Helper Functions ───────────────────────────────────

def api_get(endpoint: str, params: dict = None):
    """GET request to backend API."""
    try:
        resp = requests.get(f"{API_BASE}{endpoint}", params=params, timeout=10)
        if resp.status_code == 200:
            return resp.json()
        return {"error": f"HTTP {resp.status_code}: {resp.text}"}
    except Exception as e:
        return {"error": str(e)}

def api_post(endpoint: str, json_data: dict = None):
    """POST request to backend API."""
    try:
        resp = requests.post(f"{API_BASE}{endpoint}", json=json_data, timeout=10)
        if resp.status_code in (200, 201):
            return resp.json()
        return {"error": f"HTTP {resp.status_code}: {resp.text}"}
    except Exception as e:
        return {"error": str(e)}

def render_status_badge(status: str):
    """Render HTML status badge."""
    css_class = f"status-{status.lower()}" if status.lower() in ["idle", "running", "blocked", "completed", "failed"] else "status-idle"
    return f'<span class="status-badge {css_class}">{status.upper()}</span>'

# ═════════════════════════════════════════════════════════
# HOME PAGE
# ═════════════════════════════════════════════════════════

if page == "Home":
    st.title("🏠 Agent Pack Dashboard")
    st.caption("Kimi Production-Grade Agent System v3.0 — L3 Frontend")

    # Fetch data
    col1, col2, col3, col4 = st.columns(4)

    project = api_get("/api/project-state")
    if "error" not in project:
        col1.metric("Version", project.get("version", "N/A"))
        col2.metric("Phase", project.get("phase", "N/A"))
        col3.metric("Level", f"L{project.get('current_level', '?')}")
    else:
        col1.info("Project data unavailable")

    run = api_get("/api/run-state")
    if "error" not in run:
        status = run.get("status", "idle")
        col4.metric("Run Status", status.upper())
    else:
        col4.info("Run data unavailable")

    st.divider()

    # Quick Actions
    st.subheader("⚡ Quick Actions")
    qa_col1, qa_col2, qa_col3, qa_col4, qa_col5 = st.columns(5)
    with qa_col1:
        if st.button("▶ Start Run", use_container_width=True):
            result = api_post("/api/run/start")
            st.success(result.get("message", "Run started")) if "error" not in result else st.error(result["error"])
    with qa_col2:
        if st.button("⏸ Pause Run", use_container_width=True):
            result = api_post("/api/run/pause")
            st.info(result.get("message", "Run paused")) if "error" not in result else st.error(result["error"])
    with qa_col3:
        if st.button("📋 View Tasks", use_container_width=True):
            st.switch_page("Task Board")
    with qa_col4:
        if st.button("📊 Run Eval", use_container_width=True):
            st.switch_page("Eval Dashboard")
    with qa_col5:
        if st.button("🧠 Review Memory", use_container_width=True):
            st.switch_page("Memory Review")

    st.divider()

    # Recent Activity
    st.subheader("📋 Recent Activity")
    artifacts = api_get("/api/recent-artifacts", {"limit": 5})
    if "error" not in artifacts and isinstance(artifacts, list) and len(artifacts) > 0:
        for art in artifacts:
            icon = {"report": "📄", "ppt": "📊", "spreadsheet": "📈", "code": "💻", "image": "🖼️"}.get(art.get("type"), "📎")
            st.markdown(f"{icon} **{art.get('name', 'Unnamed')}** — `{art.get('type', 'unknown')}` — {art.get('created_at', '')}")
    else:
        st.info("No recent artifacts. Run the agent to generate outputs.")

# ═════════════════════════════════════════════════════════
# CURRENT PROJECT PAGE
# ═════════════════════════════════════════════════════════

elif page == "Current Project":
    st.title("📁 Current Project")

    project = api_get("/api/project-state")
    if "error" in project:
        st.error(f"Failed to load project: {project['error']}")
    else:
        col1, col2 = st.columns([2, 1])
        with col1:
            st.subheader("Project Info")
            info_data = {
                "Version": project.get("version", "N/A"),
                "Phase": project.get("phase", "N/A"),
                "Status": project.get("status", "N/A"),
                "Current Level": f"L{project.get('current_level', '?')}",
                "Last Updated": project.get("last_updated", "N/A"),
            }
            for k, v in info_data.items():
                st.markdown(f"**{k}:** {v}")

        with col2:
            st.subheader("Level Progression")
            current = project.get("current_level", "L1")
            levels = ["L1", "L2", "L3", "L4"]
            for lvl in levels:
                idx = levels.index(lvl)
                current_idx = levels.index(current) if current in levels else 0
                if idx < current_idx:
                    st.success(f"✅ {lvl} — Completed")
                elif idx == current_idx:
                    st.info(f"🔄 {lvl} — Current")
                else:
                    st.caption(f"⏳ {lvl} — Pending")

        st.divider()
        st.subheader("⚙️ Configuration Parameters")
        config = project.get("config", {})
        if config:
            st.json(config)
        else:
            st.info("No configuration parameters available.")

# ═════════════════════════════════════════════════════════
# CURRENT RUN PAGE
# ═════════════════════════════════════════════════════════

elif page == "Current Run":
    st.title("▶ Current Run")

    run = api_get("/api/run-state")
    if "error" in run:
        st.error(f"Failed to load run state: {run['error']}")
    else:
        status = run.get("status", "idle")

        # Status & Controls
        col1, col2, col3 = st.columns([2, 2, 1])
        with col1:
            st.markdown(f"### Status: {render_status_badge(status)}", unsafe_allow_html=True)
            st.markdown(f"**Current Step:** {run.get('current_step', 'None')}")
        with col2:
            completed = run.get("completed_steps", 0)
            total = run.get("total_steps", 1)
            progress = min(completed / total, 1.0) if total > 0 else 0
            st.progress(progress, text=f"{completed}/{total} steps")
        with col3:
            st.markdown("#### Controls")
            if status == "idle":
                if st.button("▶ Start", use_container_width=True, type="primary"):
                    result = api_post("/api/run/start")
                    st.rerun()
            elif status == "running":
                if st.button("⏸ Pause", use_container_width=True):
                    result = api_post("/api/run/pause")
                    st.rerun()
            elif status == "blocked":
                if st.button("▶ Resume", use_container_width=True, type="primary"):
                    result = api_post("/api/run/resume")
                    st.rerun()
            elif status in ["completed", "failed"]:
                if st.button("🔄 Restart", use_container_width=True):
                    result = api_post("/api/run/start")
                    st.rerun()

        # Timing
        timing_col1, timing_col2, timing_col3 = st.columns(3)
        with timing_col1:
            st.caption(f"Started: {run.get('start_time', 'N/A')}")
        with timing_col2:
            st.caption(f"Ended: {run.get('end_time', 'N/A')}")
        with timing_col3:
            if run.get("start_time") and not run.get("end_time"):
                try:
                    start = datetime.fromisoformat(run["start_time"].replace("Z", "+00:00"))
                    elapsed = (datetime.now().astimezone() - start).total_seconds()
                    st.caption(f"Elapsed: {int(elapsed)}s")
                except:
                    pass

        st.divider()

        # Live Logs
        st.subheader("📝 Run Logs")
        logs = run.get("logs", [])
        if logs:
            log_html = ""
            for i, log in enumerate(logs):
                log_html += f"<div><span style='color:#64748b'>[{i+1}]</span> {log}</div>"
            st.markdown(f'<div class="log-container">{log_html}</div>', unsafe_allow_html=True)
        else:
            st.info("No logs yet. Start a run to see output.")

        # Auto-refresh for running state
        if status == "running":
            st.caption("Auto-refreshing every 3 seconds...")
            import time
            time.sleep(3)
            st.rerun()


# ═════════════════════════════════════════════════════════
# TASK BOARD PAGE
# ═════════════════════════════════════════════════════════

elif page == "Task Board":
    st.title("📋 Task Board")

    board = api_get("/api/task-board")
    if "error" in board:
        st.error(f"Failed to load task board: {board['error']}")
    else:
        columns = board.get("columns", {})
        total = sum(len(v) for v in columns.values())
        st.caption(f"Total tasks: **{total}**")

        col_todo, col_running, col_blocked, col_done = st.columns(4)

        status_config = {
            "todo": (col_todo, "📝 To Do", "#6b7280"),
            "running": (col_running, "🏃 Running", "#3b82f6"),
            "blocked": (col_blocked, "🚧 Blocked", "#ef4444"),
            "done": (col_done, "✅ Done", "#22c55e"),
        }

        for status_key, (col, label, color) in status_config.items():
            with col:
                st.markdown(f"<h4 style='color:{color};margin-bottom:8px'>{label} ({len(columns.get(status_key, []))})</h4>", unsafe_allow_html=True)
                for task in columns.get(status_key, []):
                    priority = task.get("priority", "medium")
                    priority_emoji = {"high": "🔴", "medium": "🟡", "low": "🟢"}.get(priority, "⚪")
                    with st.container(border=True):
                        st.markdown(f"{priority_emoji} **{task.get('title', 'Untitled')}**")
                        st.caption(task.get("description", "")[:100])
                        if task.get("assignee"):
                            st.caption(f"👤 @{task['assignee']}")
                        tags = task.get("tags", [])
                        if tags:
                            st.markdown(" ".join([f"`{t}`" for t in tags]))

# ═════════════════════════════════════════════════════════
# RECENT ARTIFACTS PAGE
# ═════════════════════════════════════════════════════════

elif page == "Recent Artifacts":
    st.title("📁 Recent Artifacts")

    type_filter = st.selectbox("Filter by type", ["all", "report", "ppt", "spreadsheet", "code", "image", "other"])
    limit = st.slider("Limit", 5, 100, 20)

    artifacts = api_get("/api/recent-artifacts", {"limit": limit})
    if "error" in artifacts:
        st.error(f"Failed to load artifacts: {artifacts['error']}")
    else:
        filtered = artifacts if type_filter == "all" else [a for a in artifacts if a.get("type") == type_filter]
        filtered = sorted(filtered, key=lambda x: x.get("created_at", ""), reverse=True)

        st.caption(f"Showing {len(filtered)} artifacts")

        if not filtered:
            st.info("No artifacts found.")
        else:
            icon_map = {"report": "📄", "ppt": "📊", "spreadsheet": "📈", "code": "💻", "image": "🖼️", "other": "📎"}

            for art in filtered:
                icon = icon_map.get(art.get("type"), "📎")
                with st.container(border=True):
                    col1, col2, col3 = st.columns([3, 1, 1])
                    with col1:
                        st.markdown(f"{icon} **{art.get('name', 'Unnamed')}**")
                        st.caption(f"Path: `{art.get('path', 'N/A')}`")
                    with col2:
                        st.caption(f"Type: `{art.get('type', 'unknown')}`")
                        size = art.get("size", 0)
                        if size < 1024:
                            size_str = f"{size} B"
                        elif size < 1024 * 1024:
                            size_str = f"{size / 1024:.1f} KB"
                        else:
                            size_str = f"{size / (1024 * 1024):.1f} MB"
                        st.caption(f"Size: {size_str}")
                    with col3:
                        st.caption(art.get("created_at", "")[:10])
                        download_url = art.get("download_url", "")
                        if download_url:
                            st.link_button("⬇ Download", download_url, use_container_width=True)

# ═════════════════════════════════════════════════════════
# AGENTS & SKILLS PAGE
# ═════════════════════════════════════════════════════════

elif page == "Agents & Skills":
    st.title("🤖 Agents & Skills")

    st.info("ℹ️ This is a **read-only** view. Agent and skill configurations are managed via the backend.", icon="ℹ️")

    # Level Legend
    legend_col1, legend_col2, legend_col3, legend_col4 = st.columns(4)
    with legend_col1:
        st.success("🟢 L1 — Enabled")
    with legend_col2:
        st.info("🔵 L2 — Reserved")
    with legend_col3:
        st.warning("🟡 L3 — Reserved")
    with legend_col4:
        st.error("🟣 L4 — Reserved")

    st.divider()

    # Agents
    st.subheader("👤 Agents")
    agents = api_get("/api/agents")
    if "error" in agents:
        st.error(f"Failed to load agents: {agents['error']}")
    elif not agents:
        st.info("No agents configured.")
    else:
        agent_data = []
        for a in agents:
            agent_data.append({
                "Name": a.get("name", "?"),
                "Level": a.get("level", "?"),
                "Enabled": "✅" if a.get("enabled") else "❌",
                "Tools": ", ".join(a.get("tools", [])) or "None",
                "Description": a.get("description", "")[:60],
            })
        st.dataframe(agent_data, use_container_width=True, hide_index=True)

    st.divider()

    # Skills
    st.subheader("🛠️ Skills")
    skills = api_get("/api/skills")
    if "error" in skills:
        st.error(f"Failed to load skills: {skills['error']}")
    elif not skills:
        st.info("No skills configured.")
    else:
        skill_data = []
        for s in skills:
            skill_data.append({
                "Name": s.get("name", "?"),
                "Type": s.get("type", "?"),
                "Available": "✅" if s.get("available") else "❌",
                "Description": s.get("description", "")[:60],
            })
        st.dataframe(skill_data, use_container_width=True, hide_index=True)

# ═════════════════════════════════════════════════════════
# EVAL DASHBOARD PAGE
# ═════════════════════════════════════════════════════════

elif page == "Eval Dashboard":
    st.title("📊 Eval Dashboard")

    results = api_get("/api/eval-results")
    if "error" in results:
        st.error(f"Failed to load eval results: {results['error']}")
    else:
        # Summary Stats
        smoke = [r for r in results if r.get("type") == "smoke"]
        unit = [r for r in results if r.get("type") == "unit-smoke"]
        integration = [r for r in results if r.get("type") == "integration-smoke"]
        regression = [r for r in results if r.get("type") == "regression"]

        pass_total = sum(1 for r in results if r.get("status") == "pass")
        fail_total = sum(1 for r in results if r.get("status") == "fail")
        skip_total = sum(1 for r in results if r.get("status") == "skip")
        error_total = sum(1 for r in results if r.get("status") == "error")
        grand_total = len(results) or 1

        col1, col2, col3, col4, col5 = st.columns(5)
        col1.metric("Total", len(results))
        col2.metric("Passed", pass_total, f"{pass_total / grand_total * 100:.0f}%")
        col3.metric("Failed", fail_total, f"{fail_total / grand_total * 100:.0f}%")
        col4.metric("Skipped", skip_total, f"{skip_total / grand_total * 100:.0f}%")
        col5.metric("Errors", error_total, f"{error_total / grand_total * 100:.0f}%")

        st.divider()

        # Pass/Fail Bar Chart
        st.subheader("📈 Pass/Fail Distribution")
        chart_data = {
            "Status": ["Pass", "Fail", "Skip", "Error"],
            "Count": [pass_total, fail_total, skip_total, error_total],
        }
        import pandas as pd
        df_chart = pd.DataFrame(chart_data)
        st.bar_chart(df_chart.set_index("Status"), use_container_width=True, color=["#22c55e", "#ef4444", "#f59e0b", "#dc2626"])

        st.divider()

        # Category Tables
        status_colors = {"pass": "🟢", "fail": "🔴", "skip": "🟡", "error": "⭕"}

        def show_table(title: str, items: list):
            if not items:
                return
            st.subheader(title)
            table_data = []
            for item in items:
                table_data.append({
                    "Name": item.get("name", "?"),
                    "Status": f"{status_colors.get(item.get('status', ''), '⚪')} {item.get('status', '?').upper()}",
                    "Duration (s)": f"{item.get('duration', 0):.2f}",
                    "Run At": item.get("run_at", "")[:16],
                })
            st.dataframe(table_data, use_container_width=True, hide_index=True)

        show_table("🧪 Smoke Tests", smoke)
        show_table("🔬 Unit-Smoke Tests", unit)
        show_table("🔗 Integration-Smoke Tests", integration)
        show_table("🔄 Regression Tests", regression)

# ═════════════════════════════════════════════════════════
# MEMORY REVIEW PAGE
# ═════════════════════════════════════════════════════════

elif page == "Memory Review":
    st.title("🧠 Memory Review")

    st.warning("⚠️ This UI is **read-only**. Memory candidates must be approved or rejected via the backend API. Use `POST /api/memory-candidates/{id}/approve` or `POST /api/memory-candidates/{id}/reject`.", icon="⚠️")

    candidates = api_get("/api/memory-candidates")
    if "error" in candidates:
        st.error(f"Failed to load memory candidates: {candidates['error']}")
    else:
        status_filter = st.selectbox("Filter by status", ["all", "pending", "approved", "rejected"])
        filtered = candidates if status_filter == "all" else [c for c in candidates if c.get("review_status") == status_filter]

        st.caption(f"Showing {len(filtered)} candidates (total: {len(candidates)})")

        if not filtered:
            st.info("No memory candidates found.")
        else:
            risk_emoji = {"low": "🟢", "medium": "🟡", "high": "🔴"}
            status_emoji = {"pending": "⏳", "approved": "✅", "rejected": "❌"}

            for c in filtered:
                with st.container(border=True):
                    col1, col2, col3, col4 = st.columns([3, 1, 1, 1])
                    with col1:
                        st.markdown(f"**Source:** `{c.get('source', '?')}`")
                        st.caption(c.get("content", "")[:200])
                    with col2:
                        confidence = c.get("confidence", 0)
                        st.progress(confidence, text=f"{(confidence * 100):.0f}%")
                    with col3:
                        risk = c.get("risk", "unknown")
                        st.markdown(f"{risk_emoji.get(risk, '⚪')} **{risk.upper()}**")
                    with col4:
                        review_status = c.get("review_status", "unknown")
                        st.markdown(f"{status_emoji.get(review_status, '⚪')} **{review_status.upper()}**")

# ═════════════════════════════════════════════════════════
# GATE STATUS PAGE
# ═════════════════════════════════════════════════════════

elif page == "Gate Status":
    st.title("🚪 Gate Status")

    gates = api_get("/api/gate-status")
    if "error" in gates:
        st.error(f"Failed to load gate status: {gates['error']}")
    else:
        status_emoji = {"locked": "🔒", "unlocked": "🔓", "passed": "✅"}

        for gate in gates:
            gate_name = gate.get("name", "Unknown Gate")
            gate_status = gate.get("status", "locked")

            with st.container(border=True):
                st.markdown(f"## {status_emoji.get(gate_status, '❓')} {gate_name}")

                checks = gate.get("checks", [])
                if checks:
                    for check in checks:
                        check_name = check.get("name", "?")
                        check_passed = check.get("passed", False)
                        check_msg = check.get("message", "")

                        if check_passed:
                            st.success(f"✅ **{check_name}** — {check_msg}")
                        else:
                            st.error(f"❌ **{check_name}** — {check_msg}")

                recommendation = gate.get("recommendation", "")
                if recommendation:
                    st.info(f"💡 **Recommendation:** {recommendation}")

# ═════════════════════════════════════════════════════════
# SCRIPT CONSOLE PAGE
# ═════════════════════════════════════════════════════════

elif page == "Script Console":
    st.title("💻 Script Console")

    st.info("ℹ️ Only whitelisted scripts can be executed. The whitelist is configured server-side.", icon="ℹ️")

    # Fetch whitelist
    scripts = api_get("/api/scripts/whitelist")
    if "error" in scripts:
        st.error(f"Failed to load script whitelist: {scripts['error']}")
        scripts = []

    script_names = [s.get("name", "unknown") for s in scripts]

    col1, col2 = st.columns([1, 2])

    with col1:
        st.subheader("Execute Script")
        selected_script = st.selectbox("Select Script", script_names if script_names else ["No scripts available"])

        # Dynamic parameter inputs
        params = {}
        selected_script_def = next((s for s in scripts if s.get("name") == selected_script), None)
        if selected_script_def:
            for param in selected_script_def.get("params", []):
                pname = param.get("name", "")
                ptype = param.get("type", "string")
                prequired = param.get("required", False)
                pdefault = param.get("default")

                label = f"{pname} {'*' if prequired else ''}"
                if ptype == "integer":
                    params[pname] = st.number_input(label, value=int(pdefault) if pdefault else 0, step=1)
                elif ptype == "number":
                    params[pname] = st.number_input(label, value=float(pdefault) if pdefault else 0.0)
                elif ptype == "boolean":
                    params[pname] = st.checkbox(label, value=bool(pdefault) if pdefault else False)
                else:
                    params[pname] = st.text_input(label, value=str(pdefault) if pdefault else "")

        if st.button("▶ Execute", use_container_width=True, type="primary"):
            if selected_script and selected_script != "No scripts available":
                # Filter out empty optional params
                clean_params = {k: v for k, v in params.items() if v != ""}
                result = api_post(f"/api/jobs/run-script?script_name={selected_script}", clean_params)
                if "error" in result:
                    st.error(f"Execution failed: {result['error']}")
                else:
                    st.success(f"Script queued! Job ID: {result.get('job_id', '?')}, Status: {result.get('status', '?')}")
            else:
                st.warning("Please select a valid script.")

    with col2:
        st.subheader("Output")
        # Show latest job history
        jobs = api_get("/api/jobs", {"limit": 10})
        if "error" not in jobs and isinstance(jobs, list):
            for job in reversed(jobs[:5]):
                job_status = job.get("status", "?")
                status_color = {"completed": "🟢", "running": "🔵", "failed": "🔴", "pending": "🟡", "timeout": "⭕"}
                with st.container(border=True):
                    st.markdown(f"{status_color.get(job_status, '⚪')} **Job #{job.get('id', '?')}** — `{job.get('job_type', '?')}` — **{job_status.upper()}**")
                    job_result = job.get("result")
                    if job_result:
                        st.json(job_result)
                    error_msg = job.get("error_message")
                    if error_msg:
                        st.error(f"Error: {error_msg}")
                    st.caption(f"Created: {job.get('created_at', 'N/A')}")
        else:
            st.info("No execution history available.")

        st.divider()
        st.caption("Script execution history (last 5 jobs)")
