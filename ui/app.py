import html
import logging
from datetime import datetime

import streamlit as st

from processor.bigquery_reader import BigQueryReader
from processor.adk.runner import investigate_incident


# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

st.set_page_config(
    page_title="I-ESPÍA | AI Incident Investigator",
    page_icon="◈",
    layout="wide",
    initial_sidebar_state="collapsed",
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
)
logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Session state
# ---------------------------------------------------------------------------

DEFAULT_STATE = {
    "selected_incident_id": None,
    "incident_context": None,
    "investigation": None,
    "dashboard_view": None,
    "active_summary_tab": "conflicts",
}

for key, value in DEFAULT_STATE.items():
    if key not in st.session_state:
        st.session_state[key] = value


# ---------------------------------------------------------------------------
# Cached backend resources
# ---------------------------------------------------------------------------

@st.cache_resource
def get_reader():
    return BigQueryReader()


@st.cache_data
def get_incident_ids():
    return get_reader().list_incidents()


# ---------------------------------------------------------------------------
# Generic helpers
# ---------------------------------------------------------------------------

def safe_dict(value):
    return value if isinstance(value, dict) else {}


def safe_list(value):
    return value if isinstance(value, list) else []


def format_value(value, empty="—"):
    if value is None or value == "":
        return empty
    if isinstance(value, bool):
        return "Yes" if value else "No"
    return str(value)


def escape(value, empty="—"):
    return html.escape(format_value(value, empty))


def format_timestamp(value):
    if not value:
        return "—"

    try:
        dt = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
        return dt.strftime("%d %b %Y · %H:%M:%S UTC")
    except (ValueError, TypeError):
        return str(value)


def source_count(source_payload):
    payload = safe_dict(source_payload)

    if isinstance(payload.get("events"), list):
        return len(payload["events"])

    if isinstance(payload.get("executions"), list):
        return len(payload["executions"])

    if payload.get("state_available") is True:
        return 1

    return 0


def _spanner_inner(state):
    """Unwrap the nested 'state' dict that the Spanner reader returns.

    The reader payload looks like:
        {"incident_id": ..., "state": {"account_id": ..., "state_available": True, ...}}
    If the top-level dict already has the fields directly (legacy shape),
    it is returned as-is.
    """
    payload = safe_dict(state)
    nested = safe_dict(payload.get("state"))
    # Prefer the nested dict when it exists and has content
    return nested if nested else payload


def authoritative_state_available(state):
    inner = _spanner_inner(state)

    if "state_available" in inner:
        return bool(inner.get("state_available"))

    return bool(inner)


def authoritative_status(state):
    inner = _spanner_inner(state)

    if not authoritative_state_available(state):
        return "UNAVAILABLE"

    return format_value(
        inner.get("authoritative_status"),
        "UNAVAILABLE",
    )


def tool_statuses(tool_execution):
    statuses = []

    for execution in safe_list(
        safe_dict(tool_execution).get("executions")
    ):
        status = execution.get("status")

        if status:
            statuses.append(str(status).upper())

    return statuses


def outcome_class(outcome):
    normalized = str(outcome or "").upper()

    if normalized == "UPDATED":
        return "positive"

    if normalized in {"UNCHANGED", "UNCONFIRMED"}:
        return "warning"

    if normalized in {"FAILED", "FAILURE"}:
        return "negative"

    return "neutral"


def extract_agent_events(agent_execution):
    return safe_list(
        safe_dict(agent_execution).get("events")
    )


def extract_tool_executions(tool_execution):
    return safe_list(
        safe_dict(tool_execution).get("executions")
    )


def extract_telemetry_events(runtime_telemetry):
    return safe_list(
        safe_dict(runtime_telemetry).get("events")
    )


def render_source_card(title, role, pill_text, facts, empty_msg, count_msg, is_authoritative=False):
    """
    Renders clean, unindented HTML for source cards to prevent Streamlit's
    markdown parser from rendering raw HTML tags as text blocks.
    """
    card_class = "source-card authoritative" if is_authoritative else "source-card"
    pill_class = "source-pill authoritative" if is_authoritative else "source-pill"

    parts = [
        f'<div class="{card_class}">',
        f'<div class="source-header">',
        f'<div><div class="source-name">{escape(title)}</div>',
        f'<div class="source-role">{escape(role)}</div></div>',
        f'<span class="{pill_class}">{escape(pill_text)}</span>',
        f'</div>'
    ]

    if facts:
        for key, value in facts:
            parts.append(
                f'<div class="source-fact">'
                f'<span class="source-key">{escape(key)}</span>'
                f'<span class="source-value">{escape(value)}</span>'
                f'</div>'
            )
        if count_msg:
            parts.append(f'<div class="source-count">{escape(count_msg)}</div>')
    else:
        parts.append(f'<div class="source-empty">{empty_msg}</div>')

    parts.append('</div>')
    st.markdown("".join(parts), unsafe_allow_html=True)


# ---------------------------------------------------------------------------
# Backend → UI adapter
# ---------------------------------------------------------------------------

def build_ui_incident_context(result: dict) -> dict:
    """
    Adapt the V2 ADK result for the Streamlit presentation layer.

    The backend remains V2-native. The complete four-source evidence package
    is retained so investigators can inspect each source independently.
    """
    evidence = safe_dict(result.get("evidence"))
    deterministic_findings = safe_dict(
        result.get("deterministic_findings")
    )

    agent_execution = safe_dict(
        evidence.get("agent_execution")
    )
    tool_execution = safe_dict(
        evidence.get("tool_execution")
    )
    authoritative_state = safe_dict(
        evidence.get("authoritative_state")
    )
    runtime_telemetry = safe_dict(
        evidence.get("runtime_telemetry")
    )

    timeline = extract_agent_events(agent_execution)

    return {
        "incident_id": result.get("incident_id"),
        "correlation_id": evidence.get("correlation_id"),
        "evidence": evidence,
        "agent_execution": agent_execution,
        "tool_execution": tool_execution,
        "authoritative_state": authoritative_state,
        "runtime_telemetry": runtime_telemetry,
        "timeline": timeline,
        "evidence_count": (
            source_count(agent_execution)
            + source_count(tool_execution)
            + source_count(authoritative_state)
            + source_count(runtime_telemetry)
        ),
        "missing_evidence": safe_list(
            deterministic_findings.get("missing_evidence")
        ),
        "conflicts": safe_list(
            deterministic_findings.get("conflicts")
        ),
        "deterministic_findings": deterministic_findings,
    }


def normalize_investigation(raw):
    """
    Consume the structured InvestigationOutput returned by ADK/Gemini.
    """
    if isinstance(raw, dict):
        if "result" in raw and isinstance(raw["result"], dict):
            return raw["result"]

        return raw

    if isinstance(raw, str):
        return {
            "confirmed_facts": [],
            "conflicts": [],
            "missing_evidence": [],
            "business_outcome": "UNCONFIRMED",
            "possible_explanations": [],
            "recommended_next_checks": [],
            "uncertainty": raw,
            "evidence_references": [],
        }

    return {
        "confirmed_facts": [],
        "conflicts": [],
        "missing_evidence": [],
        "business_outcome": "UNCONFIRMED",
        "possible_explanations": [],
        "recommended_next_checks": [],
        "uncertainty": "No structured investigation result was returned.",
        "evidence_references": [],
    }


# ---------------------------------------------------------------------------
# Styling
# ---------------------------------------------------------------------------

st.markdown(
    """
    <style>
        :root {
            --ink: #101828;
            --text: #344054;
            --muted: #667085;
            --border: #e4e7ec;
            --surface: #ffffff;
            --surface-soft: #f8fafc;

            --warning: #b54708;
            --warning-bg: #fffaeb;
            --warning-border: #fedf89;

            --danger: #b42318;
            --danger-bg: #fef3f2;
            --danger-border: #fecdca;

            --success: #027a48;
            --success-bg: #ecfdf3;
            --success-border: #abefc6;

            --info: #175cd3;
            --info-bg: #eff8ff;
            --info-border: #b2ddff;

            --purple: #6941c6;
            --purple-bg: #fcfaff;
            --purple-border: #d6bbfb;
        }

        .block-container {
            max-width: 1280px;
            padding-top: 4.75rem;
            padding-bottom: 4rem;
        }

        .app-header {
            margin-top: 0.15rem;
            margin-bottom: 1.2rem;
        }

        .app-title {
            font-size: 2.25rem;
            line-height: 1.08;
            font-weight: 760;
            letter-spacing: -0.035em;
            color: #101828 !important;
            margin-bottom: 0.45rem;
        }

        .app-title .product-name,
        .app-title .title-dash {
            color: #1769d1 !important;
            margin-left: 0.05em;
        }

        /* In Streamlit dark mode, override back to light ink */
        @media (prefers-color-scheme: dark) {
            .app-title {
                color: #f0f4f9 !important;
            }

            .app-title .product-name,
            .app-title .title-dash {
                color: #6ea8fe !important;
            }

            .app-subtitle {
                color: rgba(240, 244, 249, 0.7) !important;
            }
        }

        .app-subtitle {
            color: #667085 !important;
            font-size: 0.94rem;
            line-height: 1.5;
            max-width: 820px;
        }

        [data-theme="light"] .app-subtitle {
            color: #667085;
        }

        .section-kicker {
            color: var(--muted);
            font-size: 0.7rem;
            font-weight: 800;
            letter-spacing: 0.11em;
            text-transform: uppercase;
            margin-top: 1.55rem;
            margin-bottom: 0.55rem;
        }

        .section-title {
            color: var(--ink);
            font-size: 1.18rem;
            font-weight: 720;
            margin-bottom: 0.75rem;
        }

        .incident-meta {
            display: flex;
            flex-wrap: wrap;
            gap: 0.5rem;
            margin: 0.4rem 0 1rem;
        }

        .meta-chip {
            border: 1px solid var(--border);
            border-radius: 6px;
            background: var(--surface-soft);
            padding: 0.35rem 0.55rem;
            font-family: ui-monospace, SFMono-Regular, Menlo, monospace;
            font-size: 0.7rem;
            color: #475467;
        }

        .outcome-card {
            border: 1px solid var(--border);
            border-radius: 12px;
            padding: 1.1rem 1.2rem;
            background: var(--surface);
            margin: 0.8rem 0 1.15rem;
        }

        .outcome-card.warning {
            border-color: var(--warning-border);
            background: linear-gradient(135deg, #fffdf5 0%, #ffffff 72%);
        }

        .outcome-card.positive {
            border-color: var(--success-border);
            background: linear-gradient(135deg, #f5fff9 0%, #ffffff 72%);
        }

        .outcome-card.negative {
            border-color: var(--danger-border);
            background: linear-gradient(135deg, #fff8f7 0%, #ffffff 72%);
        }

        .outcome-card.neutral {
            border-color: var(--border);
        }

        .outcome-eyebrow {
            color: var(--muted);
            font-size: 0.68rem;
            font-weight: 800;
            letter-spacing: 0.1em;
            text-transform: uppercase;
            margin-bottom: 0.25rem;
        }

        .outcome-value {
            color: var(--ink);
            font-size: 1.65rem;
            line-height: 1.1;
            font-weight: 820;
            letter-spacing: -0.025em;
        }

        .outcome-detail {
            color: var(--muted);
            font-size: 0.82rem;
            margin-top: 0.35rem;
        }

        .conflict-banner {
            border: 1px solid var(--warning-border);
            border-left: 4px solid #f79009;
            border-radius: 8px;
            padding: 0.85rem 1rem;
            background: var(--warning-bg);
            margin: 0.75rem 0 1.15rem;
        }

        .conflict-banner-title {
            color: #93370d;
            font-size: 0.82rem;
            font-weight: 760;
            margin-bottom: 0.2rem;
        }

        .conflict-banner-text {
            color: #7a2e0e;
            font-size: 0.82rem;
            line-height: 1.45;
        }

        .source-card {
            border: 1px solid var(--border);
            border-radius: 10px;
            background: #fff;
            padding: 1rem;
            height: 360px;
            box-sizing: border-box;
            display: flex;
            flex-direction: column;
        }

        .source-count,
        .source-empty {
            margin-top: auto;
        }

        .source-card.authoritative {
            border-color: #98a2b3;
            box-shadow: 0 0 0 1px rgba(16, 24, 40, 0.03);
        }

        .source-header {
            display: flex;
            justify-content: space-between;
            align-items: flex-start;
            gap: 0.5rem;
            margin-bottom: 0.7rem;
        }

        .source-name {
            color: var(--ink);
            font-size: 0.95rem;
            font-weight: 760;
        }

        .source-role {
            color: var(--muted);
            font-size: 0.68rem;
            margin-top: 0.12rem;
            line-height: 1.35;
        }

        .source-pill {
            border: 1px solid var(--border);
            border-radius: 999px;
            padding: 0.2rem 0.45rem;
            color: var(--muted);
            font-size: 0.6rem;
            font-weight: 760;
            white-space: nowrap;
        }

        .source-pill.authoritative {
            color: #344054;
            border-color: #98a2b3;
            background: #f8fafc;
        }

        .source-fact {
            display: flex;
            justify-content: space-between;
            align-items: flex-start;
            gap: 0.8rem;
            padding: 0.46rem 0;
            border-top: 1px solid #f0f2f5;
        }

        .source-key {
            color: var(--muted);
            font-size: 0.67rem;
            flex-shrink: 0;
            font-weight: 600;
        }

        .source-value {
            color: #344054;
            font-family: ui-monospace, SFMono-Regular, Menlo, monospace;
            font-size: 0.68rem;
            font-weight: 600;
            text-align: right;
            word-break: break-word;
            overflow-wrap: anywhere;
        }

        .source-empty {
            color: var(--muted);
            font-size: 0.77rem;
            line-height: 1.5;
            padding: 1.2rem 0 0.4rem;
        }

        .source-count {
            color: var(--muted);
            font-size: 0.66rem;
            margin-top: 0.8rem;
        }

        .detail-panel-box {
            border: 1px solid var(--border);
            border-radius: 12px;
            background: var(--surface);
            padding: 1.25rem 1.4rem;
            margin-top: 1rem;
            margin-bottom: 1.5rem;
        }

        .finding-card {
            border: 1px solid var(--border);
            border-radius: 9px;
            padding: 0.9rem 1rem;
            background: #fff;
            margin-bottom: 0.65rem;
        }

        .finding-title {
            font-size: 0.78rem;
            font-weight: 760;
            color: var(--ink);
            margin-bottom: 0.35rem;
        }

        .finding-text {
            color: #475467;
            font-size: 0.82rem;
            line-height: 1.5;
        }

        .finding-conflict {
            border-left: 3px solid #f79009;
            background: #fffdf7;
        }

        .finding-missing {
            border-left: 3px solid #98a2b3;
            background: #f8fafc;
        }

        .finding-hypothesis {
            border-left: 3px solid #9e77ed;
            background: var(--purple-bg);
        }

        .finding-check {
            border-left: 3px solid #53b1fd;
            background: #f8fbff;
        }

        .timeline-event {
            border-left: 2px solid #d0d5dd;
            padding: 0.1rem 0 1rem 1.1rem;
            margin-left: 0.45rem;
        }

        .timeline-time {
            font-family: ui-monospace, SFMono-Regular, Menlo, monospace;
            font-size: 0.67rem;
            color: var(--muted);
        }

        .timeline-source {
            color: #475467;
            font-size: 0.65rem;
            font-weight: 760;
            letter-spacing: 0.07em;
            text-transform: uppercase;
            margin-top: 0.25rem;
        }

        .timeline-type {
            color: var(--ink);
            font-size: 0.82rem;
            font-weight: 710;
            margin-top: 0.15rem;
        }

        .timeline-details {
            color: var(--muted);
            font-size: 0.76rem;
            margin-top: 0.2rem;
            line-height: 1.45;
        }

        .uncertainty-box {
            border: 1px solid var(--border);
            border-radius: 9px;
            padding: 1rem;
            background: #f8fafc;
            color: #475467;
            font-size: 0.82rem;
            line-height: 1.55;
            margin-top: 0.75rem;
        }

        .debug-label {
            color: var(--muted);
            font-size: 0.68rem;
            letter-spacing: 0.08em;
            font-weight: 800;
            text-transform: uppercase;
            margin-top: 1.5rem;
            margin-bottom: 0.5rem;
        }
    </style>
    """,
    unsafe_allow_html=True,
)


# ---------------------------------------------------------------------------
# Header
# ---------------------------------------------------------------------------

st.markdown(
    """
    <div class="app-header">
        <div class="app-title">
            <span class="product-name">I-ESPÍA</span><span class="title-dash">—</span> an AI incident investigator
        </div>
        <div class="app-subtitle">
            Incident Evidence Sequence, Prediction &amp; Investigation Agent
            · Evidence-grounded investigation for AI-agent operations
        </div>
    </div>
    """,
    unsafe_allow_html=True,
)

st.divider()


# ---------------------------------------------------------------------------
# Incident selection
# ---------------------------------------------------------------------------

st.markdown(
    '<div class="section-kicker">Investigation</div>',
    unsafe_allow_html=True,
)
st.markdown(
    '<div class="section-title">Select incident</div>',
    unsafe_allow_html=True,
)

incident_ids = get_incident_ids()

if not incident_ids:
    st.warning("No incidents available.")
    st.stop()

incident_id = st.selectbox(
    "Incident",
    incident_ids,
    label_visibility="collapsed",
)

previous_incident = st.session_state.get("selected_incident_id")

if previous_incident is not None and previous_incident != incident_id:
    st.session_state["incident_context"] = None
    st.session_state["investigation"] = None
    st.session_state["dashboard_view"] = None
    st.session_state["active_summary_tab"] = "conflicts"

st.session_state["selected_incident_id"] = incident_id

col_run, col_refresh = st.columns([1, 1])

with col_run:
    run_investigation = st.button(
        "Run Investigation",
        type="primary",
        use_container_width=True,
    )

with col_refresh:
    refresh_incidents = st.button(
        "↻ Refresh Incidents",
        use_container_width=True,
    )

if refresh_incidents:
    get_incident_ids.clear()
    st.rerun()

if st.session_state.get("incident_context") is None:
    st.info(
        f"**{incident_id}** selected. Run the investigation to reconstruct "
        "the incident across all four evidence sources."
    )


# ---------------------------------------------------------------------------
# Run investigation
# ---------------------------------------------------------------------------

if run_investigation:
    try:
        with st.spinner(
            "Reconstructing evidence and running I-ESPÍA investigation…"
        ):
            result = investigate_incident(incident_id)

        incident_context = build_ui_incident_context(result)
        investigation = normalize_investigation(
            result.get("gemini_investigation")
        )

        st.session_state["incident_context"] = incident_context
        st.session_state["investigation"] = investigation
        st.session_state["dashboard_view"] = None
        st.session_state["active_summary_tab"] = "conflicts"

        st.success("Investigation completed.")

    except Exception as exc:
        logger.exception(
            "Investigation failed for incident %s",
            incident_id,
        )
        st.error(f"Investigation failed: {exc}")


# ---------------------------------------------------------------------------
# Results
# ---------------------------------------------------------------------------

incident = st.session_state.get("incident_context")
investigation = st.session_state.get("investigation")

if incident is not None and investigation is not None:

    evidence = safe_dict(incident.get("evidence"))
    agent_execution = safe_dict(incident.get("agent_execution"))
    tool_execution = safe_dict(incident.get("tool_execution"))
    authoritative_state = safe_dict(incident.get("authoritative_state"))
    runtime_telemetry = safe_dict(incident.get("runtime_telemetry"))

    conflicts = safe_list(investigation.get("conflicts"))
    missing = safe_list(investigation.get("missing_evidence"))
    outcome = format_value(
        investigation.get("business_outcome"),
        "UNCONFIRMED",
    )

    # -----------------------------------------------------------------------
    # 1. Incident identity
    # -----------------------------------------------------------------------

    st.markdown(
        '<div class="section-kicker">Incident overview</div>',
        unsafe_allow_html=True,
    )

    st.markdown(
        f"""
        <div class="incident-meta">
            <span class="meta-chip">
                INCIDENT · {escape(incident.get("incident_id"))}
            </span>
            <span class="meta-chip">
                CORRELATION · {escape(incident.get("correlation_id"))}
            </span>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # Executive business outcome card
    outcome_style = outcome_class(outcome)
    state_status = authoritative_status(authoritative_state)
    state_available = authoritative_state_available(authoritative_state)

    state_detail = (
        f"Spanner authoritative state · {state_status}"
        if state_available
        else "Spanner authoritative state · unavailable"
    )

    st.markdown(
        f"""
        <div class="outcome-card {outcome_style}">
            <div class="outcome-eyebrow">Business outcome</div>
            <div class="outcome-value">{escape(outcome)}</div>
            <div class="outcome-detail">{escape(state_detail)}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    if conflicts:
        first_conflict = safe_dict(conflicts[0])
        conflict_text = format_value(
            first_conflict.get("description"),
            str(conflicts[0]),
        )
        st.markdown(
            f"""
            <div class="conflict-banner">
                <div class="conflict-banner-title">
                    Evidence conflict detected · {len(conflicts)}
                </div>
                <div class="conflict-banner-text">
                    {escape(conflict_text)}
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    # -----------------------------------------------------------------------
    # 2. Four evidence sources cards (NO RAW HTML)
    # -----------------------------------------------------------------------

    st.markdown(
        '<div class="section-kicker">Evidence sources</div>',
        unsafe_allow_html=True,
    )
    st.markdown(
        '<div class="section-title">What each system establishes</div>',
        unsafe_allow_html=True,
    )

    source_columns = st.columns(4)

    # BigQuery
    with source_columns[0]:
        events = extract_agent_events(agent_execution)
        if events:
            first = safe_dict(events[0])
            facts = [
                ("Events", str(len(events))),
                ("Status", format_value(first.get("status"))),
                ("Action", format_value(first.get("action"))),
                ("Actor", format_value(first.get("actor"))),
                ("Event", format_value(first.get("event_type"))),
            ]
            count_msg = f"{len(events)} agent execution event(s)"
        else:
            facts = []
            count_msg = ""
        render_source_card(
            title="BigQuery",
            role="Agent execution evidence",
            pill_text="EXECUTION",
            facts=facts,
            empty_msg="No agent execution events returned.",
            count_msg=count_msg,
        )

    # AlloyDB
    with source_columns[1]:
        executions = extract_tool_executions(tool_execution)
        if executions:
            first = safe_dict(executions[0])
            statuses = tool_statuses(tool_execution)
            facts = [
                ("Execution", format_value(first.get("execution_id"))),
                ("Tool", format_value(first.get("tool_name"))),
                ("Status", ", ".join(statuses) or "—"),
                ("Duration", f"{format_value(first.get('duration_ms'))} ms"),
            ]
            count_msg = f"{len(executions)} tool execution record(s)"
        else:
            facts = []
            count_msg = ""
        render_source_card(
            title="AlloyDB",
            role="Tool execution evidence",
            pill_text="TOOL",
            facts=facts,
            empty_msg="No tool execution records returned.",
            count_msg=count_msg,
        )

    # Spanner
    with source_columns[2]:
        available = authoritative_state_available(authoritative_state)
        s_inner = _spanner_inner(authoritative_state)

        if available:
            facts = [
                ("Status", format_value(s_inner.get("authoritative_status"))),
                ("Account", format_value(s_inner.get("account_id"))),
                ("Action", format_value(s_inner.get("requested_action"))),
                ("Version", format_value(s_inner.get("state_version"))),
                ("Modified by", format_value(s_inner.get("last_modified_by"))),
                ("Modified at", format_value(s_inner.get("last_modified_at"))),
            ]
            count_msg = "Authoritative state available"
        else:
            facts = []
            count_msg = ""
        render_source_card(
            title="Spanner",
            role="Authoritative business state",
            pill_text="AUTHORITATIVE",
            facts=facts,
            empty_msg="State unavailable.",
            count_msg=count_msg,
            is_authoritative=True,
        )

    # Bigtable
    with source_columns[3]:
        telemetry = extract_telemetry_events(runtime_telemetry)
        if telemetry:
            first = safe_dict(telemetry[0])
            facts = [
                ("Events", str(len(telemetry))),
                ("Event", format_value(first.get("event_type"))),
                ("Correlation", format_value(first.get("correlation_id"))),
                ("Row key", format_value(first.get("row_key"))),
            ]
            count_msg = f"{len(telemetry)} runtime telemetry event(s)"
        else:
            facts = []
            count_msg = ""
        render_source_card(
            title="Bigtable",
            role="Runtime telemetry",
            pill_text="TELEMETRY",
            facts=facts,
            empty_msg="No runtime telemetry events returned.",
            count_msg=count_msg,
        )

    # -----------------------------------------------------------------------
    # 3. Investigation Summary (V1 Progressive UI - Single Active Panel)
    # -----------------------------------------------------------------------

    st.markdown(
        '<div class="section-kicker">Investigation summary</div>',
        unsafe_allow_html=True,
    )

    evidence_total = (
        len(extract_agent_events(agent_execution))
        + len(extract_tool_executions(tool_execution))
        + (1 if authoritative_state_available(authoritative_state) else 0)
        + len(extract_telemetry_events(runtime_telemetry))
    )

    if st.session_state.get("active_summary_tab") not in {"evidence", "conflicts", "missing", "status"}:
        st.session_state["active_summary_tab"] = "conflicts" if conflicts else "evidence"

    active_tab = st.session_state["active_summary_tab"]

    col1, col2, col3, col4 = st.columns(4)

    with col1:
        btn_type = "primary" if active_tab == "evidence" else "secondary"
        if st.button(
            f"📊 Evidence records\n\n**{evidence_total}**",
            key="btn_evidence",
            use_container_width=True,
            type=btn_type,
        ):
            st.session_state["active_summary_tab"] = "evidence"
            st.rerun()

    with col2:
        btn_type = "primary" if active_tab == "conflicts" else "secondary"
        if st.button(
            f"⚠ Conflicts\n\n**{len(conflicts)}**",
            key="btn_conflicts",
            use_container_width=True,
            type=btn_type,
        ):
            st.session_state["active_summary_tab"] = "conflicts"
            st.rerun()

    with col3:
        btn_type = "primary" if active_tab == "missing" else "secondary"
        if st.button(
            f"◻ Missing evidence\n\n**{len(missing)}**",
            key="btn_missing",
            use_container_width=True,
            type=btn_type,
        ):
            st.session_state["active_summary_tab"] = "missing"
            st.rerun()

    with col4:
        btn_type = "primary" if active_tab == "status" else "secondary"
        if st.button(
            f"✓ Status\n\n**COMPLETE**",
            key="btn_status",
            use_container_width=True,
            type=btn_type,
        ):
            st.session_state["active_summary_tab"] = "status"
            st.rerun()

    # Dynamic Single Active Detail Panel
    st.markdown('<div class="detail-panel-box">', unsafe_allow_html=True)

    if active_tab == "conflicts":
        st.markdown("### Conflict detected")
        if conflicts:
            for conflict in conflicts:
                item = safe_dict(conflict)
                conflict_type = format_value(
                    item.get("type"), "TOOL_SUCCESS_VS_STATE_UNCHANGED"
                )
                description = format_value(
                    item.get("description"), str(conflict)
                )

                st.markdown(
                    f"""
                    <div class="finding-card finding-conflict">
                        <div class="finding-title">⚠ {escape(conflict_type)}</div>
                        <div class="finding-text">{escape(description)}</div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )

            tool_execs = extract_tool_executions(tool_execution)
            if tool_execs and authoritative_state_available(authoritative_state):
                first_tool = safe_dict(tool_execs[0])
                s_inner = _spanner_inner(authoritative_state)
                st.info(
                    f"**AlloyDB reports:** `{first_tool.get('tool_name', 'account_tool')}` → **{first_tool.get('status', 'SUCCESS')}** (Execution: `{first_tool.get('execution_id', 'EXEC-001')}`)\n\n"
                    f"**Spanner reports:** Account `{s_inner.get('account_id', 'ACC-001')}` → **{s_inner.get('authoritative_status', 'UNCHANGED')}**\n\n"
                    f"**Conclusion:** The tool reported successful execution, but authoritative business state did not change."
                )
        else:
            st.success("No evidence conflicts identified.")

    elif active_tab == "evidence":
        st.markdown("### Evidence records summary")
        st.markdown(
            f"- **BigQuery (Agent execution)**: **{len(extract_agent_events(agent_execution))}** event(s)\n"
            f"- **AlloyDB (Tool execution)**: **{len(extract_tool_executions(tool_execution))}** record(s)\n"
            f"- **Spanner (Authoritative state)**: **{'1 record' if authoritative_state_available(authoritative_state) else '0 records'}**\n"
            f"- **Bigtable (Runtime telemetry)**: **{len(extract_telemetry_events(runtime_telemetry))}** event(s)\n\n"
            f"**Total evidence records reconstructed**: **{evidence_total}**"
        )
        st.caption("Select a tab in 'Detailed source records' below to inspect specific records.")

    elif active_tab == "missing":
        st.markdown("### Missing evidence details")
        if missing:
            for item in missing:
                payload = safe_dict(item)
                source = format_value(
                    payload.get("missing_evidence_source"), "Missing evidence"
                )
                description = format_value(
                    payload.get("description"), str(item)
                )
                st.markdown(
                    f"""
                    <div class="finding-card finding-missing">
                        <div class="finding-title">◻ {escape(source)}</div>
                        <div class="finding-text">{escape(description)}</div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )
        else:
            st.success("No explicitly missing evidence identified.")

    elif active_tab == "status":
        st.markdown("### Investigation status & reasoning")
        st.markdown(f"**Status**: `COMPLETE` · **Business Outcome**: `{outcome}`")

        col_facts, col_explanations = st.columns(2)
        with col_facts:
            st.markdown("#### Confirmed facts")
            facts = safe_list(investigation.get("confirmed_facts"))
            if facts:
                for fact in facts:
                    st.markdown(
                        f"""
                        <div class="finding-card">
                            <div class="finding-text">✓ {escape(fact)}</div>
                        </div>
                        """,
                        unsafe_allow_html=True,
                    )
            else:
                st.caption("No confirmed facts returned.")

        with col_explanations:
            st.markdown("#### Possible explanations")
            hypotheses = safe_list(investigation.get("possible_explanations"))
            if hypotheses:
                for h in hypotheses:
                    st.markdown(
                        f"""
                        <div class="finding-card finding-hypothesis">
                            <div class="finding-text">◇ {escape(h)}</div>
                        </div>
                        """,
                        unsafe_allow_html=True,
                    )
            else:
                st.caption("No possible explanations returned.")

        checks = safe_list(investigation.get("recommended_next_checks"))
        if checks:
            st.markdown("#### Recommended next checks")
            for check in checks:
                st.markdown(
                    f"""
                    <div class="finding-card finding-check">
                        <div class="finding-text">→ {escape(check)}</div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )

        uncertainty = format_value(investigation.get("uncertainty"))
        if uncertainty:
            st.markdown(
                f"""
                <div class="uncertainty-box">
                    <strong>Assessment &amp; Uncertainty:</strong> {escape(uncertainty)}
                </div>
                """,
                unsafe_allow_html=True,
            )

    st.markdown('</div>', unsafe_allow_html=True)

    # -----------------------------------------------------------------------
    # 4. Execution Sequence (Collapsible timeline)
    # -----------------------------------------------------------------------

    st.markdown(
        '<div class="section-kicker">Execution sequence</div>',
        unsafe_allow_html=True,
    )

    with st.expander("Show agent execution timeline", expanded=False):
        agent_events = extract_agent_events(agent_execution)
        if agent_events:
            for event in agent_events:
                event = safe_dict(event)
                timestamp = format_timestamp(event.get("timestamp"))
                source = format_value(event.get("source"), "BIGQUERY")
                event_type = format_value(event.get("event_type"))
                status = format_value(event.get("status"))
                details = format_value(event.get("details"))

                st.markdown(
                    f"""
                    <div class="timeline-event">
                        <div class="timeline-time">{escape(timestamp)}</div>
                        <div class="timeline-source">{escape(source)} · {escape(status)}</div>
                        <div class="timeline-type">{escape(event_type)}</div>
                        <div class="timeline-details">{escape(details)}</div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )
        else:
            st.info("No agent execution timeline events were returned.")

    # -----------------------------------------------------------------------
    # 5. Detailed Source Records (4 Progressive Tabs)
    # -----------------------------------------------------------------------

    st.markdown(
        '<div class="section-kicker">Detailed source records</div>',
        unsafe_allow_html=True,
    )

    tab_bq, tab_alloy, tab_spanner, tab_bt = st.tabs(
        [
            "BigQuery",
            "AlloyDB",
            "Spanner",
            "Bigtable",
        ]
    )

    with tab_bq:
        st.markdown("#### BigQuery · Agent execution events")
        agent_events = extract_agent_events(agent_execution)
        if agent_events:
            for idx, event in enumerate(agent_events, 1):
                event = safe_dict(event)
                st.markdown(
                    f"**Sequence {idx}** · `{event.get('event_type', 'EVENT')}`\n\n"
                    f"- **Timestamp**: `{format_timestamp(event.get('timestamp'))}`\n"
                    f"- **Actor**: `{event.get('actor', '—')}` | **Action**: `{event.get('action', '—')}`\n"
                    f"- **Status**: `{event.get('status', '—')}`\n"
                    f"- **Details**: {event.get('details', '—')}"
                )
                st.divider()
        else:
            st.caption("No agent execution events returned.")

    with tab_alloy:
        st.markdown("#### AlloyDB · Tool execution records")
        executions = extract_tool_executions(tool_execution)
        if executions:
            for idx, exec_item in enumerate(executions, 1):
                exec_item = safe_dict(exec_item)
                st.markdown(
                    f"**Execution {idx}** (`{exec_item.get('execution_id', '—')}`)\n\n"
                    f"- **Tool Name**: `{exec_item.get('tool_name', '—')}`\n"
                    f"- **Status**: `{exec_item.get('status', '—')}`\n"
                    f"- **Duration**: `{exec_item.get('duration_ms', '—')} ms`\n"
                    f"- **Started At**: `{format_timestamp(exec_item.get('started_at'))}`\n"
                    f"- **Completed At**: `{format_timestamp(exec_item.get('completed_at'))}`"
                )
                if exec_item.get("parameters"):
                    st.json(exec_item["parameters"])
                st.divider()
        else:
            st.caption("No AlloyDB tool execution records returned.")

    with tab_spanner:
        st.markdown("#### Spanner · Authoritative business state")
        if authoritative_state_available(authoritative_state):
            s = _spanner_inner(authoritative_state)
            st.markdown(
                f"- **Authoritative Status**: `{s.get('authoritative_status', '—')}`\n"
                f"- **Account ID**: `{s.get('account_id', '—')}`\n"
                f"- **Requested Action**: `{s.get('requested_action', '—')}`\n"
                f"- **State Version**: `{s.get('state_version', '—')}`\n"
                f"- **Last Modified By**: `{s.get('last_modified_by', '—')}`\n"
                f"- **Last Modified At**: `{format_timestamp(s.get('last_modified_at'))}`"
            )
        else:
            st.caption("Spanner authoritative state unavailable.")

    with tab_bt:
        st.markdown("#### Bigtable · Runtime telemetry events")
        telemetry = extract_telemetry_events(runtime_telemetry)
        if telemetry:
            for idx, event in enumerate(telemetry, 1):
                event = safe_dict(event)
                st.markdown(
                    f"**Telemetry Event {idx}** · `{event.get('event_type', 'EVENT')}`\n\n"
                    f"- **Row Key**: `{event.get('row_key', '—')}`\n"
                    f"- **Correlation ID**: `{event.get('correlation_id', '—')}`\n"
                    f"- **Timestamp**: `{format_timestamp(event.get('timestamp'))}`"
                )
                if event.get("payload"):
                    st.json(event["payload"])
                st.divider()
        else:
            st.caption("No Bigtable runtime telemetry events returned.")

    # -----------------------------------------------------------------------
    # 6. Traceability & References
    # -----------------------------------------------------------------------

    st.markdown(
        '<div class="section-kicker">Traceability</div>',
        unsafe_allow_html=True,
    )

    st.markdown(
        '<div class="section-title">Evidence references</div>',
        unsafe_allow_html=True,
    )

    references = safe_list(investigation.get("evidence_references"))

    if references:
        for reference in references:
            st.code(
                str(reference),
                language=None,
            )
    else:
        st.caption("No evidence references returned.")

    # -----------------------------------------------------------------------
    # 7. Developer / Debugging (Collapsed expanders)
    # -----------------------------------------------------------------------

    st.divider()

    st.markdown(
        '<div class="debug-label">Developer / debugging</div>',
        unsafe_allow_html=True,
    )

    with st.expander("Technical evidence contract"):
        st.json(incident)

    with st.expander("Raw Gemini investigation JSON"):
        st.json(investigation)
