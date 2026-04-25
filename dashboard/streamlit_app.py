import json
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd
import streamlit as st

# ============================================================
# Paths
# ============================================================

BASE_DIR = Path(__file__).resolve().parent.parent
OUTPUT_DIR = BASE_DIR / "output"

RISK_METRICS_PATH = OUTPUT_DIR / "risk_metrics.json"
BACKTEST_PATH = OUTPUT_DIR / "backtest.json"
SCENARIOS_PATH = OUTPUT_DIR / "scenarios.csv"
BACKTEST_PNG_PATH = OUTPUT_DIR / "backtest.png"
CORR_PNG_PATH = OUTPUT_DIR / "correlation_heatmap.png"
SUMMARY_TXT_PATH = OUTPUT_DIR / "summary.txt"
RUN_COMPLETE_PATH = OUTPUT_DIR / "_RUN_COMPLETE"

REQUIRED_OUTPUTS = [
    RISK_METRICS_PATH,
    BACKTEST_PATH,
    SCENARIOS_PATH,
    RUN_COMPLETE_PATH,
]

OPTIONAL_OUTPUTS = [
    BACKTEST_PNG_PATH,
    CORR_PNG_PATH,
    SUMMARY_TXT_PATH,
]

MAX_WAIT_SECONDS = 10
POLL_INTERVAL_SECONDS = 2


# ============================================================
# Page config
# ============================================================

st.set_page_config(
    page_title="Investment Risk Dashboard",
    layout="wide",
    initial_sidebar_state="expanded",
)


# ============================================================
# Styling
# ============================================================

st.markdown(
    """
    <style>
        .stApp {
            background-color: #f5f7fb;
        }

        section[data-testid="stSidebar"] {
            background: linear-gradient(180deg, #081a33 0%, #0b2447 100%);
            color: white;
        }

        section[data-testid="stSidebar"] * {
            color: white !important;
        }

        .block-container {
            padding-top: 1.5rem;
            padding-bottom: 1.5rem;
        }

        .dashboard-title {
            font-size: 2.2rem;
            font-weight: 700;
            color: #111827;
            margin-bottom: 0.2rem;
        }

        .dashboard-subtitle {
            font-size: 1.05rem;
            color: #4b5563;
            margin-bottom: 1.25rem;
        }

        .status-pill {
            display: inline-block;
            padding: 0.25rem 0.7rem;
            border-radius: 999px;
            font-size: 0.82rem;
            font-weight: 600;
            background-color: #e8f5ee;
            color: #1f8f5f;
            border: 1px solid #c9ead7;
        }

        .panel {
            background: white;
            border: 1px solid #e5e7eb;
            border-radius: 14px;
            padding: 1rem 1rem 0.9rem 1rem;
            box-shadow: 0 1px 2px rgba(16, 24, 40, 0.04);
            margin-bottom: 1rem;
        }

        .panel-title {
            font-size: 1.1rem;
            font-weight: 700;
            color: #111827;
            margin-bottom: 0.75rem;
        }

        .kpi-card {
            background: white;
            border: 1px solid #e5e7eb;
            border-radius: 14px;
            padding: 1rem 1rem 0.95rem 1rem;
            box-shadow: 0 1px 2px rgba(16, 24, 40, 0.04);
            min-height: 130px;
        }

        .kpi-label {
            font-size: 0.95rem;
            color: #374151;
            font-weight: 600;
            margin-bottom: 0.55rem;
        }

        .kpi-value {
            font-size: 2rem;
            font-weight: 700;
            line-height: 1.05;
            margin-bottom: 0.45rem;
        }

        .kpi-sub {
            font-size: 0.9rem;
            color: #6b7280;
            white-space: pre-line;
        }

        .kpi-blue { color: #1668dc; }
        .kpi-purple { color: #6f42c1; }
        .kpi-green { color: #16a34a; }
        .kpi-orange { color: #d97706; }
        .kpi-red { color: #dc2626; }

        .small-muted {
            color: #6b7280;
            font-size: 0.88rem;
        }

        .table-note {
            color: #6b7280;
            font-size: 0.82rem;
            margin-top: 0.4rem;
        }

        .waiting-box {
            background: white;
            border: 1px solid #e5e7eb;
            border-radius: 14px;
            padding: 1.25rem;
            box-shadow: 0 1px 2px rgba(16, 24, 40, 0.04);
            margin-top: 1rem;
        }
    </style>
    """,
    unsafe_allow_html=True,
)

st.markdown(
    """
    <style>
    

    section[data-testid="stSidebar"] div.stButton > button {
    width: 100% !important;
    text-align: left !important;
    justify-content: flex-start !important;
    border-radius: 12px !important;
    padding: 0.70rem 0.90rem !important;
    margin: 0 0 0.45rem 0 !important;
    font-size: 16px !important;
    font-weight: 600 !important;
    background: rgba(255,255,255,0.06) !important;
    color: white !important;
    border: 1px solid rgba(255,255,255,0.12) !important;
    box-shadow: none !important;
}

section[data-testid="stSidebar"] div.stButton > button:hover {
    background: rgba(255,255,255,0.10) !important;
    color: white !important;
    border: 1px solid rgba(255,255,255,0.18) !important;
}

    /* force inner text visible */
    section[data-testid="stSidebar"] div.stButton > button p,
    section[data-testid="stSidebar"] div.stButton > button span,
    section[data-testid="stSidebar"] div.stButton > button div {
        color: white !important;
        text-align: left !important;
        justify-content: flex-start !important;
        margin: 0 !important;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

def set_section(section_name: str) -> None:
    st.session_state["selected_section"] = section_name


if "selected_section" not in st.session_state:
    st.session_state["selected_section"] = "Executive Summary"

# ============================================================
# Helpers
# ============================================================

@st.cache_data
def load_json(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


@st.cache_data
def load_csv(path: Path) -> pd.DataFrame:
    return pd.read_csv(path)


def safe_get(d: dict[str, Any], *keys: str, default: Any = None) -> Any:
    current: Any = d
    for key in keys:
        if not isinstance(current, dict) or key not in current:
            return default
        current = current[key]
    return current


def pct_fmt(x: Any, decimals: int = 2) -> str:
    if x is None or pd.isna(x):
        return "N/A"
    return f"{x:.{decimals}%}"


def chf_fmt(x: Any, decimals: int = 0) -> str:
    if x is None or pd.isna(x):
        return "N/A"
    return f"CHF {x:,.{decimals}f}"


def num_fmt(x: Any, decimals: int = 2) -> str:
    if x is None or pd.isna(x):
        return "N/A"
    return f"{x:,.{decimals}f}"


def dt_fmt(x: Any) -> str:
    if x is None:
        return "N/A"
    try:
        return pd.to_datetime(x).strftime("%Y-%m-%d %H:%M:%S")
    except Exception:
        return str(x)


def file_timestamp(path: Path) -> str:
    if not path.exists():
        return "N/A"
    ts = datetime.fromtimestamp(path.stat().st_mtime, tz=timezone.utc)
    return ts.strftime("%Y-%m-%d %H:%M:%S UTC")


def get_missing_required_files() -> list[Path]:
    return [p for p in REQUIRED_OUTPUTS if not p.exists()]


def render_kpi_card(label: str, value: str, sub: str = "", color_class: str = "kpi-blue") -> None:
    st.markdown(
        f"""
        <div class="kpi-card">
            <div class="kpi-label">{label}</div>
            <div class="kpi-value {color_class}">{value}</div>
            <div class="kpi-sub">{sub}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_panel_title(title: str) -> None:
    st.markdown(f'<div class="panel-title">{title}</div>', unsafe_allow_html=True)


# ============================================================
# Wait for risk engine outputs
# ============================================================

wait_placeholder = st.empty()

start_time = time.time()
missing_required = get_missing_required_files()

while missing_required and (time.time() - start_time < MAX_WAIT_SECONDS):
    elapsed = int(time.time() - start_time)

    with wait_placeholder.container():
        st.markdown('<div class="dashboard-title">Investment Risk Dashboard</div>', unsafe_allow_html=True)
        st.markdown(
            '<div class="dashboard-subtitle">Waiting for batch risk engine completion</div>',
            unsafe_allow_html=True,
        )
        st.markdown(
            """
            <div class="waiting-box">
                <p style="margin-top:0; font-weight:600; color:#111827;">
                    The dashboard will load automatically once the required output files are available.
                </p>
                <p style="color:#4b5563;">
                    This prevents incomplete or partially written results from being displayed.
                </p>
            </div>
            """,
            unsafe_allow_html=True,
        )

        st.write("**Pending files:**")
        for path in missing_required:
            st.write(f"- `{path.name}`")

        progress = min((time.time() - start_time) / MAX_WAIT_SECONDS, 1.0)
        st.progress(progress)
        st.caption(f"Elapsed wait time: {elapsed}s / {MAX_WAIT_SECONDS}s")

    time.sleep(POLL_INTERVAL_SECONDS)
    missing_required = get_missing_required_files()

wait_placeholder.empty()

if missing_required:
    st.markdown('<div class="dashboard-title">Investment Risk Dashboard</div>', unsafe_allow_html=True)
    st.markdown(
        '<div class="dashboard-subtitle">Outputs not available</div>',
        unsafe_allow_html=True,
    )
    st.error("Required output files were not created in time.")
    st.write("**Missing files:**")
    for path in missing_required:
        st.write(f"- `{path.name}`")
    st.code("python run_analysis.py", language="bash")
    st.stop()


# ============================================================
# Data loading
# ============================================================

risk_metrics = load_json(RISK_METRICS_PATH)
backtest = load_json(BACKTEST_PATH)
scenarios = load_csv(SCENARIOS_PATH)

component_var = pd.DataFrame(
    safe_get(risk_metrics, "component_var_by_sub_class", default=[])
)

if "portfolio_pnl_chf" not in scenarios.columns and "pnl_chf" in scenarios.columns:
    scenarios = scenarios.rename(columns={"pnl_chf": "portfolio_pnl_chf"})

if "portfolio_return" not in scenarios.columns and "scenario_return" in scenarios.columns:
    scenarios = scenarios.rename(columns={"scenario_return": "portfolio_return"})

if "portfolio_pnl_chf" in scenarios.columns:
    scenarios = scenarios.sort_values("portfolio_pnl_chf", ascending=True).reset_index(drop=True)

hist_var_95 = safe_get(risk_metrics, "historical", "var_95")
hist_var_99 = safe_get(risk_metrics, "historical", "var_99")
hist_es_95 = safe_get(risk_metrics, "historical", "cvar_95")
hist_es_99 = safe_get(risk_metrics, "historical", "cvar_99")

param_var_95 = safe_get(risk_metrics, "parametric", "var_95")
param_var_99 = safe_get(risk_metrics, "parametric", "var_99")
param_es_95 = safe_get(risk_metrics, "parametric", "cvar_95")
param_es_99 = safe_get(risk_metrics, "parametric", "cvar_99")

ewma_var_95 = safe_get(risk_metrics, "ewma", "var_95")
ewma_var_99 = safe_get(risk_metrics, "ewma", "var_99")

metadata = safe_get(risk_metrics, "metadata", default={})
run_timestamp = metadata.get("run_timestamp", file_timestamp(RISK_METRICS_PATH))
data_as_of = metadata.get("data_as_of", "N/A")
nav_chf = metadata.get("nav_chf", 500_000_000)

n_obs = safe_get(backtest, "n_obs")
n_breaches = safe_get(backtest, "n_breaches")
expected_breaches = safe_get(backtest, "expected_breaches")
kupiec = safe_get(backtest, "kupiec_test", default={})
kupiec_p_value = safe_get(kupiec, "p_value")
kupiec_reject = safe_get(kupiec, "reject_95pct")

worst_scenario_name = None
worst_scenario_pnl = None
worst_scenario_return = None
if not scenarios.empty:
    worst_row = scenarios.iloc[0]
    worst_scenario_name = worst_row.get("scenario_name", "N/A")
    worst_scenario_pnl = worst_row.get("portfolio_pnl_chf")
    worst_scenario_return = worst_row.get("portfolio_return")

if not component_var.empty and "component_var" in component_var.columns:
    component_var = component_var.sort_values("component_var", ascending=False).reset_index(drop=True)
    component_var["pct_of_total"] = component_var["component_var"] / component_var["component_var"].sum()


# ============================================================
# Sidebar
# ============================================================

with st.sidebar:
    st.markdown("## CRO Asset Management")
    st.markdown('<div class="small-muted">Confidential</div>', unsafe_allow_html=True)
    st.markdown("---")
    st.markdown("### NAVIGATION")

 
    nav_items = [
        ("Executive Summary", "🏠"),
        ("Risk Metrics", "📊"),
        ("Backtesting", "📈"),
        ("Stress Testing", "⚠️"),
        ("Risk Attribution", "🧩"),
        ("Correlation Heatmap", "🔗"),
    ]

    for label, icon in nav_items:
        is_active = st.session_state["selected_section"] == label

        if st.button(
            f"{icon}  {label}",
            key=f"nav_{label}",
            use_container_width=True,
            type="primary" if is_active else "secondary",
        ):
            st.session_state["selected_section"] = label

    section = st.session_state["selected_section"]

    st.markdown("---")
    st.markdown("### Run information")
    st.write(f"**Run Date (UTC)**  \n{dt_fmt(run_timestamp)}")
    st.write(f"**Data as of**  \n{data_as_of}")
    st.write(f"**Portfolio**  \nCHF 500M Multi-Asset Strategy")
    st.write(f"**Asset Class**  \nEquity / Bond")
    st.write(f"**NAV (CHF)**  \n{chf_fmt(nav_chf)}")

    st.markdown("---")
    st.caption("Risk Dashboard v1.0")


# ============================================================
# Header
# ============================================================

header_left, header_right = st.columns([6, 2])

with header_left:
    st.markdown('<div class="dashboard-title">Investment Risk Dashboard</div>', unsafe_allow_html=True)
    st.markdown(
        '<div class="dashboard-subtitle">CHF 500M Multi-Asset Portfolio | Internal Risk Oversight</div>',
        unsafe_allow_html=True,
    )

with header_right:
    st.markdown(
        """
        <div style="text-align:right; margin-top:0.55rem;">
            <span class="status-pill">● Latest run loaded successfully</span>
        </div>
        """,
        unsafe_allow_html=True,
    )


# ============================================================
# Executive Summary
# ============================================================

if section == "Executive Summary":
    row1 = st.columns(4)
    with row1[0]:
        render_kpi_card(
            "Historical VaR (95%)",
            pct_fmt(hist_var_95),
            f"1-Day Loss (CHF)\n{chf_fmt((hist_var_95 or 0) * nav_chf)}",
            "kpi-blue",
        )
    with row1[1]:
        render_kpi_card(
            "Historical VaR (99%)",
            pct_fmt(hist_var_99),
            f"1-Day Loss (CHF)\n{chf_fmt((hist_var_99 or 0) * nav_chf)}",
            "kpi-blue",
        )
    with row1[2]:
        render_kpi_card(
            "Parametric VaR (95%)",
            pct_fmt(param_var_95),
            f"1-Day Loss (CHF)\n{chf_fmt((param_var_95 or 0) * nav_chf)}",
            "kpi-purple",
        )
    with row1[3]:
        render_kpi_card(
            "Parametric VaR (99%)",
            pct_fmt(param_var_99),
            f"1-Day Loss (CHF)\n{chf_fmt((param_var_99 or 0) * nav_chf)}",
            "kpi-purple",
        )

    row2 = st.columns(4)
    with row2[0]:
        render_kpi_card(
            "Historical ES (95%)",
            pct_fmt(hist_es_95),
            f"1-Day Loss (CHF)\n{chf_fmt((hist_es_95 or 0) * nav_chf)}",
            "kpi-green",
        )
    with row2[1]:
        render_kpi_card(
            "Parametric ES (99%)",
            pct_fmt(hist_es_99),
            f"1-Day Loss (CHF)\n{chf_fmt((param_es_99 or 0) * nav_chf)}",
            "kpi-green",
        )
    with row2[2]:
        render_kpi_card(
            "Backtest Breaches (99%)",
            str(n_breaches) if n_breaches is not None else "N/A",
            f"Expected: {num_fmt(expected_breaches)}",
            "kpi-orange",
        )
    with row2[3]:
        render_kpi_card(
            "Worst Stress Scenario P&L",
            chf_fmt(worst_scenario_pnl, 1) if worst_scenario_pnl is not None else "N/A",
            worst_scenario_name or "N/A",
            "kpi-red",
        )

    row3 = st.columns(2)
    with row3[0]:
        render_kpi_card(
            "EWMA VaR (95%)",
            pct_fmt(ewma_var_95),
            f"1-Day Loss (CHF)\n{chf_fmt((ewma_var_95 or 0) * nav_chf)}",
            "kpi-purple",
        )
    with row3[1]:
        render_kpi_card(
            "EWMA VaR (99%)",
            pct_fmt(ewma_var_99),
            f"1-Day Loss (CHF)\n{chf_fmt((ewma_var_99 or 0) * nav_chf)}",
            "kpi-purple",
        )
    
    left, right = st.columns([1.25, 1.0])

    with left:
        with st.container():
            render_panel_title("Backtesting - EWMA VaR 99%")
            if BACKTEST_PNG_PATH.exists():
                st.image(str(BACKTEST_PNG_PATH), width="stretch")
            else:
                st.info("backtest.png not found in output.")

            if n_obs is not None:
                stats = pd.DataFrame(
                    {
                        "Observations": [n_obs],
                        "Breaches": [n_breaches],
                        "Expected Breaches": [expected_breaches],
                        "Kupiec p-value": [kupiec_p_value],
                        "Kupiec Test": [
                            "Not Rejected" if kupiec_reject is False
                            else "Rejected" if kupiec_reject is True
                            else "N/A"
                        ],
                    }
                )
                st.dataframe(stats, hide_index=True, use_container_width=True)
 
    with right:
        with st.container():
            render_panel_title("Stress Testing – Scenario P&L")

            if not scenarios.empty and "scenario_name" in scenarios.columns and "portfolio_pnl_chf" in scenarios.columns:
                st.bar_chart(scenarios.set_index("scenario_name")[["portfolio_pnl_chf"]])

                display_cols = [
                    c for c in ["scenario_name", "portfolio_return", "portfolio_pnl_chf"]
                    if c in scenarios.columns
                ]

                st.dataframe(
                    scenarios[display_cols].style.format(
                        {
                            "portfolio_return": "{:.2%}",
                            "portfolio_pnl_chf": "CHF {:,.1f}",
                        }
                    ),
                    hide_index=True,
                    use_container_width=True,
                )
            else:
                st.info("Scenario data not available.")
        

    bottom_left, bottom_right = st.columns([1.1, 0.9])

    with bottom_left:
        with st.container():
            render_panel_title("Risk Attribution – Component VaR (95%)")
            if not component_var.empty and "sub_class" in component_var.columns and "component_var" in component_var.columns:
                plot_df = component_var.set_index("sub_class")[["component_var"]]
                st.bar_chart(plot_df)
                display_df = component_var.copy()
                if "pct_of_total" in display_df.columns:
                    st.dataframe(
                        display_df.style.format(
                            {
                                "component_var": "{:.4%}",
                                "pct_of_total": "{:.1%}",
                            }
                        ),
                        hide_index=True,
                        use_container_width=True,
                    )
            else:
                st.info("Component VaR data not available.")
        

    with bottom_right:
        with st.container():
            render_panel_title("Correlation Heatmap (Returns)")
            if CORR_PNG_PATH.exists():
                st.image(str(CORR_PNG_PATH), width="stretch")
            else:
                st.info("correlation_heatmap.png not found in output.")
        


# ============================================================
# Risk Metrics
# ============================================================

elif section == "Risk Metrics":
    
    render_panel_title("Risk Metrics")

    st.write("Comparison of historical (non-parametric) and parametric risk measures.")

    var_df = pd.DataFrame(
        {
            "Metric": ["VaR (95%)", "VaR (99%)"],
            "Historical": [hist_var_95, hist_var_99],
            "Parametric": [param_var_95, param_var_99],
            "EWMA": [ewma_var_95, ewma_var_99],
        }
    )

    es_df = pd.DataFrame(
        {
            "Metric": ["ES (95%)", "ES (99%)"],
            "Historical": [hist_es_95, hist_es_99],
            "Parametric": [param_es_95, param_es_99],
        }
    )

    upper_left, upper_right = st.columns([1.05, 1.15])

    with upper_left:
        st.markdown("#### VaR Comparison")
        st.dataframe(
            var_df.style.format(
                {
                    "Historical": "{:.2%}",
                    "Parametric": "{:.2%}",
                    "EWMA": "{:.2%}",
                }
            ),
            hide_index=True,
            use_container_width=True,
        )

        st.markdown("#### ES Comparison")
        st.dataframe(
            es_df.style.format(
                {
                    "Historical": "{:.2%}",
                    "Parametric": "{:.2%}",
                }
            ),
            hide_index=True,
            use_container_width=True,
        )

        st.markdown(
            '<div class="table-note">All metrics are 1-day ahead. VaR = Value at Risk, ES = Expected Shortfall.</div>',
            unsafe_allow_html=True,
        )

    with upper_right:
        st.markdown("#### VaR Comparison Chart")
        st.bar_chart(var_df.set_index("Metric")[["Historical", "Parametric", "EWMA"]])

        st.markdown("#### ES Comparison Chart")
        st.bar_chart(es_df.set_index("Metric")[["Historical", "Parametric"]])


    lower_left, lower_right = st.columns(2)

    with lower_left:
        
        render_panel_title("Methodology – Historical (Non-Parametric)")
        st.markdown(
            """
            - Empirical distribution of daily portfolio returns  
            - VaR: empirical quantile  
            - ES: average of returns worse than VaR threshold  
            - No distributional assumptions  
            """
        )
        

    with lower_right:
        
        render_panel_title("Methodology – Parametric (Normal Assumption)")
        st.markdown(
            """
            - Assumes returns are normally distributed  
            - VaR based on mean and volatility  
            - ES derived from normal tail expectation  
            - Sensitive to non-normality and outliers  
            """
        )
        
# ============================================================
# Backtesting
# ============================================================

elif section == "Backtesting":
    model_name = backtest.get("model", "N/A")
    st.markdown(
        f"<div class='small-muted'>Model used: <b>{str(model_name).upper()}</b></div>",
        unsafe_allow_html=True,
    )
    top = st.columns(4)
    with top[0]:
        render_kpi_card("Observations", str(n_obs) if n_obs is not None else "N/A", "", "kpi-blue")
    with top[1]:
        render_kpi_card("Breaches", str(n_breaches) if n_breaches is not None else "N/A", "", "kpi-orange")
    with top[2]:
        render_kpi_card("Expected Breaches", num_fmt(expected_breaches), "", "kpi-blue")
    with top[3]:
        render_kpi_card("Kupiec p-value", num_fmt(kupiec_p_value, 4), "", "kpi-green")

    
    render_panel_title("Rolling 99 EWMA VaR Backtest")
    if BACKTEST_PNG_PATH.exists():
        st.image(str(BACKTEST_PNG_PATH), width="stretch")
    else:
        st.info("backtest.png not found in output.")
    

    lower_left, lower_right = st.columns([1, 1])

    with lower_left:
        
        render_panel_title("Kupiec Test")
        if kupiec:
            st.dataframe(pd.DataFrame([kupiec]), hide_index=True, use_container_width=True)
        else:
            st.info("Kupiec test details unavailable.")
        

    with lower_right:
        
        render_panel_title("Breach Dates")
        breach_dates = backtest.get("breach_dates", [])
        if breach_dates:
            st.dataframe(pd.DataFrame({"breach_date": breach_dates}), hide_index=True, use_container_width=True)
        else:
            st.write("No breaches recorded.")
        


# ============================================================
# Stress Testing
# ============================================================

elif section == "Stress Testing":
    
    render_panel_title("Scenario P&L")
    if not scenarios.empty:
        if "scenario_name" in scenarios.columns and "portfolio_pnl_chf" in scenarios.columns:
            st.bar_chart(scenarios.set_index("scenario_name")[["portfolio_pnl_chf"]])

        display_cols = [c for c in ["scenario_name", "portfolio_return", "portfolio_pnl_chf", "description"] if c in scenarios.columns]
        st.dataframe(
            scenarios[display_cols].style.format(
                {
                    "portfolio_return": "{:.2%}",
                    "portfolio_pnl_chf": "CHF {:,.1f}",
                }
            ),
            hide_index=True,
            use_container_width=True,
        )
    else:
        st.warning("No scenario results available.")
    

# ============================================================
# Risk Attribution
# ============================================================

elif section == "Risk Attribution":
    
    render_panel_title("Component VaR by Sub-Asset Class")
    if not component_var.empty and "sub_class" in component_var.columns and "component_var" in component_var.columns:
        st.bar_chart(component_var.set_index("sub_class")[["component_var"]])
        show_df = component_var.copy()
        st.dataframe(
            show_df.style.format(
                {
                    "component_var": "{:.4%}",
                    "pct_of_total": "{:.1%}",
                }
            ),
            hide_index=True,
            use_container_width=True,
        )
    else:
        st.warning("No component VaR data available.")
    


# ============================================================
# Correlations
# ============================================================

elif section == "Correlation Heatmap":
    
    render_panel_title("Correlation Heatmap (Returns)")
    if CORR_PNG_PATH.exists():
        st.image(str(CORR_PNG_PATH), width="stretch")
    else:
        st.info("correlation_heatmap.png not found in output.")
    st.markdown(
        '<div class="table-note">The correlation structure provides context on diversification quality '
        'and cross-asset dependency.</div>',
        unsafe_allow_html=True,
    )
    