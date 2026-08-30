import streamlit as st
import json
from processor.bigquery_reader import BigQueryReader
from processor.incident_processor import IncidentProcessor
from processor.gemini_investigator import GeminiInvestigator

import logging

# ---------------------------------------------------------------------------
# Session state initialization
# ---------------------------------------------------------------------------

if "selected_incident_id" not in st.session_state:
    st.session_state["selected_incident_id"] = None

if "incident_context" not in st.session_state:
    st.session_state["incident_context"] = None

if "investigation" not in st.session_state:
    st.session_state["investigation"] = None

if "dashboard_view" not in st.session_state:
    st.session_state["dashboard_view"] = None

st.set_page_config(
    page_title="Patchamomma | AI Incident Investigator",
    layout="wide",
)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
)
# ---------------------------------------------------------------------------
# Cached backend resources and operations
# ---------------------------------------------------------------------------

@st.cache_resource
def get_reader():
    return BigQueryReader()


@st.cache_resource
def get_investigator():
    return GeminiInvestigator()


@st.cache_data
def get_incident_ids():
    reader = get_reader()
    return reader.list_incidents()


@st.cache_data(ttl=60)
def get_incident(incident_id: str):
    reader = get_reader()
    return reader.get_incident(incident_id)


@st.cache_data(ttl=60)
def process_incident(incident_id: str):
    raw_incident = get_incident(incident_id)

    processor = IncidentProcessor()

    return processor.process(raw_incident)


@st.cache_data
def run_gemini_investigation(context_json: str):
    incident_context = json.loads(context_json)

    investigator = get_investigator()

    return investigator.investigate(incident_context)

# ---------------------------------------------------------------------------
# Styling
# ---------------------------------------------------------------------------

st.markdown(
    """
    <style>
        .block-container {
            max-width: 1200px;
            padding-top: 2rem;
            padding-bottom: 3rem;
        }

        .app-header {
            margin-bottom: 1.5rem;
        }

        .app-title {
            font-size: 2rem;
            font-weight: 650;
            letter-spacing: -0.02em;
            margin-bottom: 0.2rem;
        }

        .app-subtitle {
            color: #6b7280;
            font-size: 0.95rem;
        }

        .section-label {
            font-size: 0.78rem;
            font-weight: 650;
            letter-spacing: 0.08em;
            text-transform: uppercase;
            color: #6b7280;
            margin-top: 1.5rem;
            margin-bottom: 0.7rem;
        }

        .timeline-event {
            border-left: 2px solid #d1d5db;
            padding: 0.15rem 0 1.15rem 1.2rem;
            margin-left: 0.5rem;
        }

        .timeline-time {
            font-family: monospace;
            font-size: 0.82rem;
            color: #6b7280;
        }

        .timeline-source {
            font-size: 0.78rem;
            font-weight: 650;
            letter-spacing: 0.05em;
            color: #374151;
            text-transform: uppercase;
        }

        .timeline-type {
            font-weight: 650;
            font-size: 0.95rem;
            margin-top: 0.15rem;
        }

        .timeline-details {
            color: #4b5563;
            font-size: 0.9rem;
            margin-top: 0.2rem;
        }

        .investigation-card {
            border: 1px solid #e5e7eb;
            border-radius: 8px;
            padding: 1rem 1.1rem;
            margin-bottom: 0.8rem;
            background: #ffffff;
        }

        .investigation-label {
            font-size: 0.76rem;
            font-weight: 650;
            letter-spacing: 0.06em;
            text-transform: uppercase;
            color: #6b7280;
            margin-bottom: 0.45rem;
        }

        .status-conflict {
            border-left: 3px solid #d97706;
            padding-left: 0.9rem;
        }

        .status-missing {
            border-left: 3px solid #6b7280;
            padding-left: 0.9rem;
        }

        .hypothesis {
            border-left: 3px solid #7c3aed;
            padding-left: 0.9rem;
            margin-bottom: 0.8rem;
        }

        .uncertainty-box {
            border: 1px solid #e5e7eb;
            border-radius: 8px;
            padding: 1rem;
            background: #f9fafb;
        }

        .metric-label {
            font-size: 0.75rem;
            color: #6b7280;
        }

        .metric-value {
            font-size: 1.15rem;
            font-weight: 650;
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
        <div class="app-title">Patchamomma AI Incidents Investigator</div>
        <div class="app-subtitle">
            Incident Investigation Console · Evidence-grounded AI agent analysis
        </div>
    </div>
    """,
    unsafe_allow_html=True,
)

st.divider()


# ---------------------------------------------------------------------------
# Incident selection
# ---------------------------------------------------------------------------

st.subheader("Select Incident")

incident_ids = get_incident_ids()

if not incident_ids:
    st.warning("No incidents available.")
    st.stop()

incident_id = st.selectbox(
    "Select an incident",
    incident_ids,
    label_visibility="collapsed",
)

# Detect incident change and clear stale investigation results.
previous_incident = st.session_state.get("selected_incident_id")

if (
    previous_incident is not None
    and previous_incident != incident_id
):
    st.session_state["incident_context"] = None
    st.session_state["investigation"] = None
    st.session_state["dashboard_view"] = None


st.session_state["selected_incident_id"] = incident_id

col_run, col_refresh = st.columns([1, 1])

with col_run:
    run_investigation = st.button(
        "Run Investigation",
        type="primary",
    )

if st.session_state.get("incident_context") is None:
    st.info(
        f"**{incident_id}** selected. "
        "Click **Run Investigation** to analyze this incident."
    )
with col_refresh:
    refresh_incidents = st.button(
        "↻ Refresh Incidents",
    )

if refresh_incidents:
    get_incident_ids.clear()
    st.rerun()

# ---------------------------------------------------------------------------
# Backend pipeline
# ---------------------------------------------------------------------------

if run_investigation:

    try:
        with st.spinner("Preparing incident evidence..."):

            incident_context = process_incident(incident_id)

        context_json = json.dumps(
            incident_context,
            sort_keys=True,
            ensure_ascii=False,
            default=str,
        )

        with st.spinner("Running Gemini investigation..."):

            investigation = run_gemini_investigation(
                context_json
            )

        st.session_state["incident_context"] = incident_context
        st.session_state["investigation"] = investigation

        st.success("Investigation completed.")

    except Exception as exc:
        st.error(f"Investigation failed: {exc}")

# ---------------------------------------------------------------------------
# Display results
# ---------------------------------------------------------------------------
incident = st.session_state.get("incident_context")
investigation = st.session_state.get("investigation")

if incident is not None and investigation is not None:
    st.divider()

    # -----------------------------------------------------------------------
    # Investigation Dashboard
    # -----------------------------------------------------------------------

    st.subheader("Investigation Dashboard")

    conflict_count = len(
        investigation.get("conflicts", [])
    )

    missing_count = len(
        investigation.get("missing_evidence", [])
    )

    evidence_count = incident["evidence_count"]

    status = "Complete"

    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.metric(
            "Evidence Events",
            evidence_count,
            help="Evidence events reconstructed by Workstream A.",
        )
        if st.button(
            "View evidence timeline →",
            key="view_evidence",
            use_container_width=True,
        ):
            st.session_state["dashboard_view"] = "evidence"
            st.rerun()

    with col2:
        st.metric(
            "Conflicts",
            conflict_count,
            help="Conflicts identified during the evidence-grounded investigation.",
        )
        if st.button(
            "Review conflicts →",
            key="view_conflicts",
            use_container_width=True,
        ):
            st.session_state["dashboard_view"] = "conflicts"
            st.rerun()

    with col3:
        st.metric(
            "Missing Evidence",
            missing_count,
            help="Explicitly identified missing evidence carried through the A → B contract.",
        )
        if st.button(
            "Review missing evidence →",
            key="view_missing",
            use_container_width=True,
        ):
            st.session_state["dashboard_view"] = "missing"
            st.rerun()

    with col4:
        st.metric(
            "Investigation",
            status,
            help="Gemini investigation status.",
        )
        if st.button(
            "View investigation →",
            key="view_investigation",
            use_container_width=True,
        ):
            st.session_state["dashboard_view"] = "investigation"
            st.rerun()

    st.caption(
            f"Incident {incident['incident_id']} · "
            f"Correlation ID {incident['corelation_id']}"
        )

    # -----------------------------------------------------------------------
    # Dashboard detail panel
    # -----------------------------------------------------------------------

    dashboard_view = st.session_state.get("dashboard_view")

    if dashboard_view:

        st.divider()

        if st.button("← Back to Dashboard", key="dashboard_back"):
            st.session_state["dashboard_view"] = None
            st.rerun()

        # Evidence detail
        if dashboard_view == "evidence":

            st.markdown("### Evidence Timeline")

            for event in incident["timeline"]:

                timestamp = event.get("timestamp", "")
                source = event.get("source", "")
                event_type = event.get("event_type", "")
                status = event.get("status", "")
                details = event.get("details", "")

                with st.container(border=True):

                    col1, col2, col3 = st.columns([1.5, 1, 4])

                    with col1:
                        st.write(timestamp)

                    with col2:
                        st.write(f"**{source}**")
                        st.caption(status)

                    with col3:
                        st.write(f"**{event_type}**")
                        st.write(details)

        # Conflict detail
        elif dashboard_view == "conflicts":

            st.markdown("### Conflicts")

            conflicts = investigation.get("conflicts", [])

            if conflicts:
                for conflict in conflicts:

                    if isinstance(conflict, dict):
                        description = conflict.get(
                            "description",
                            str(conflict),
                        )
                    else:
                        description = str(conflict)

                    st.warning(description)

            else:
                st.success("No conflicts identified.")

        # Missing evidence detail
        elif dashboard_view == "missing":

            st.markdown("### Missing Evidence")

            missing = investigation.get(
                "missing_evidence",
                [],
            )

            if missing:
                for item in missing:

                    if isinstance(item, dict):
                        source = item.get(
                            "missing_evidence_source",
                            str(item),
                        )
                        st.info(source)
                    else:
                        st.info(str(item))

            else:
                st.success(
                    "No explicitly missing evidence identified."
                )

        # Investigation detail
        elif dashboard_view == "investigation":

            st.markdown("### Gemini Investigation")

            facts = investigation.get(
                "confirmed_facts",
                [],
            )

            st.markdown("#### Confirmed Facts")

            if facts:
                for fact in facts:
                    st.write(f"• {fact}")
            else:
                st.caption("No confirmed facts returned.")

            hypotheses = investigation.get(
                "possible_explanations",
                [],
            )

            st.markdown("#### Possible Explanations")

            if hypotheses:
                for hypothesis in hypotheses:
                    st.write(f"• {hypothesis}")
            else:
                st.caption("No possible explanations returned.")

            st.markdown("#### Recommended Next Checks")

            checks = investigation.get(
                "recommended_next_checks",
                [],
            )

            if checks:
                for check in checks:
                    st.write(f"• {check}")
            else:
                st.caption("No additional checks recommended.")

            uncertainty = investigation.get(
                "uncertainty",
                "",
            )

            st.markdown("#### Uncertainty")

            if uncertainty:
                st.info(uncertainty)
            else:
                st.caption(
                    "No uncertainty statement returned."
                )

            references = investigation.get(
                "evidence_references",
                [],
            )

            st.markdown("#### Evidence References")

            if references:
                for reference in references:
                    st.write(f"• {reference}")
            else:
                st.caption(
                    "No evidence references returned."
                )
    # -----------------------------------------------------------------------
    # Developer / contract views
    # -----------------------------------------------------------------------

    st.divider()

    with st.expander("Technical evidence contract"):
        st.json(incident)

    with st.expander("Raw Gemini investigation JSON"):
        st.json(investigation)