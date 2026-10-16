import json
import time
import pandas as pd
import streamlit as st
from crm_client import CRMClient

# Page configuration
st.set_page_config(
    page_title="CRM API Explorer",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Custom styling for clean, compact modern layout
st.markdown(
    """
    <style>
        .block-container { padding-top: 1.5rem; padding-bottom: 2rem; }
        .stMetric { background-color: rgba(255, 255, 255, 0.03); border-radius: 8px; padding: 10px; }
        div[data-testid="stExpander"] { border-radius: 8px; }
    </style>
    """,
    unsafe_allow_html=True,
)

# Initialize API Client
client = CRMClient()

# Initialize session state for query caching
if "last_response" not in st.session_state:
    st.session_state.last_response = None
if "last_meta" not in st.session_state:
    st.session_state.last_meta = None

# Sidebar - Settings & Query Builder
st.sidebar.title("⚡ CRM Explorer")
st.sidebar.caption(f"Base URL: `{client.base_url}`")

# Auth Status Check
if client.is_configured():
    st.sidebar.success("Auth: Keys loaded from `.env`", icon="✅")
else:
    st.sidebar.warning("Auth: Placeholder/missing keys in `.env`", icon="⚠️")

st.sidebar.markdown("---")
st.sidebar.subheader("Select Query")

ENDPOINT_OPTIONS = {
    "Organizations (List)": {"category": "organizations", "type": "list"},
    "Organization (Detail by ID)": {"category": "organizations", "type": "detail"},
    "Clients (List)": {"category": "clients", "type": "list"},
    "Client (Detail by ID)": {"category": "clients", "type": "detail"},
    "Client Purchases": {"category": "clients", "type": "purchases"},
    "Sales (List)": {"category": "sales", "type": "list"},
    "Products (List)": {"category": "products", "type": "list"},
    "Leads (List)": {"category": "leads", "type": "list"},
    "Deals (List)": {"category": "deals", "type": "list"},
    "Lead History (by ID)": {"category": "leads", "type": "history"},
    "Custom Endpoint": {"category": "custom", "type": "custom"},
}

selected_label = st.sidebar.selectbox("Endpoint", list(ENDPOINT_OPTIONS.keys()))
endpoint_config = ENDPOINT_OPTIONS[selected_label]

# Dynamic Inputs based on selected endpoint
params = {}
endpoint_path = ""
id_value = ""

if endpoint_config["type"] == "detail":
    if endpoint_config["category"] == "organizations":
        id_value = st.sidebar.text_input("Organization ID", value="8509")
        endpoint_path = f"organizations/{id_value}"
        per_page = st.sidebar.number_input("Per Page", min_value=1, max_value=250, value=25)
        params["per_page"] = per_page
    elif endpoint_config["category"] == "clients":
        id_value = st.sidebar.text_input("Client ID", value="6920")
        endpoint_path = f"clients/{id_value}"

elif endpoint_config["type"] == "purchases":
    id_value = st.sidebar.text_input("Client ID", value="6920")
    per_page = st.sidebar.number_input("Per Page", min_value=1, max_value=250, value=25)
    page = st.sidebar.number_input("Page", min_value=1, value=1)
    endpoint_path = f"clients/{id_value}/purchases"
    params = {"per_page": per_page, "page": page}

elif endpoint_config["type"] == "history":
    id_value = st.sidebar.text_input("Lead ID", value="36")
    endpoint_path = f"leads/{id_value}/history"

elif endpoint_config["type"] == "list":
    per_page = st.sidebar.number_input("Per Page", min_value=1, max_value=250, value=25)
    page = st.sidebar.number_input("Page", min_value=1, value=1)
    params = {"per_page": per_page, "page": page}
    endpoint_path = endpoint_config["category"]

elif endpoint_config["type"] == "custom":
    endpoint_path = st.sidebar.text_input("Endpoint Path", value="organizations")
    per_page = st.sidebar.number_input("Per Page", min_value=1, max_value=250, value=25)
    page = st.sidebar.number_input("Page", min_value=1, value=1)
    params = {"per_page": per_page, "page": page}

# Fetch button
fetch_clicked = st.sidebar.button("🚀 Fetch Data", type="primary", use_container_width=True)

if fetch_clicked:
    with st.spinner(f"Querying `{endpoint_path}`..."):
        start_time = time.time()
        try:
            resp = client.request(endpoint_path, params=params)
            duration = round((time.time() - start_time) * 1000, 1)

            st.session_state.last_meta = {
                "url": resp.url,
                "status_code": resp.status_code,
                "reason": resp.reason,
                "duration_ms": duration,
                "endpoint_path": endpoint_path,
            }

            try:
                st.session_state.last_response = resp.json()
            except Exception:
                st.session_state.last_response = resp.text

        except Exception as e:
            st.error(f"Request failed: {e}")

# Main Content Area
st.title("CRM API Explorer")

if st.session_state.last_response is not None:
    meta = st.session_state.last_meta
    data = st.session_state.last_response

    # Telemetry metrics row
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        if 200 <= meta["status_code"] < 300:
            st.metric("Status", f"{meta['status_code']} {meta['reason']}")
        else:
            st.metric("Status", f"{meta['status_code']} {meta['reason']}", delta="-Error", delta_color="inverse")
    with col2:
        st.metric("Response Time", f"{meta['duration_ms']} ms")
    with col3:
        # Check if list count exists
        count = None
        if isinstance(data, list):
            count = len(data)
        elif isinstance(data, dict):
            if isinstance(data.get("data"), list):
                count = len(data["data"])
            elif "total" in data:
                count = data.get("total")
        st.metric("Records Found", str(count) if count is not None else "1 (Object)")
    with col4:
        st.metric("Endpoint", f"/{meta['endpoint_path']}")

    # Display Requested URL
    st.code(meta["url"], language="http")

    # Tabs for Dual View
    tab_table, tab_json, tab_download = st.tabs(["📊 Table View", "🔍 JSON Tree", "💾 Export Data"])

    with tab_table:
        table_records = None
        if isinstance(data, list):
            table_records = data
        elif isinstance(data, dict):
            if isinstance(data.get("data"), list):
                table_records = data["data"]
            elif all(isinstance(v, (str, int, float, bool, type(None))) for v in data.values()):
                # Single flat object -> key/value table
                table_records = [{"Field": k, "Value": str(v)} for k, v in data.items()]
            else:
                # Wrap single complex object
                table_records = [data]

        if table_records:
            try:
                df = pd.json_normalize(table_records)
                st.dataframe(df, use_container_width=True, height=500)
                st.caption(f"Showing {len(df)} rows and {len(df.columns)} columns. Click column headers to sort or use search icon.")
            except Exception as e:
                st.warning(f"Could not convert response to table automatically: {e}")
                st.info("Please inspect the raw payload in the JSON Tree tab.")
        else:
            st.info("Response is not tabular or is empty. View the JSON Tree tab.")

    with tab_json:
        if isinstance(data, (dict, list)):
            st.json(data, expanded=True)
        else:
            st.code(str(data))

    with tab_download:
        st.subheader("Export Options")
        col_dl1, col_dl2 = st.columns(2)

        clean_slug = meta["endpoint_path"].replace("/", "_")
        json_str = json.dumps(data, indent=2, ensure_ascii=False) if isinstance(data, (dict, list)) else str(data)

        with col_dl1:
            st.download_button(
                label="📥 Download JSON",
                data=json_str,
                file_name=f"{clean_slug}_{int(time.time())}.json",
                mime="application/json",
                use_container_width=True,
            )

        with col_dl2:
            if table_records:
                try:
                    df = pd.json_normalize(table_records)
                    csv_data = df.to_csv(index=False).encode("utf-8")
                    st.download_button(
                        label="📥 Download CSV",
                        data=csv_data,
                        file_name=f"{clean_slug}_{int(time.time())}.csv",
                        mime="text/csv",
                        use_container_width=True,
                    )
                except Exception:
                    st.button("CSV Download Unavailable", disabled=True, use_container_width=True)
            else:
                st.button("CSV Download Unavailable (Not tabular)", disabled=True, use_container_width=True)

else:
    st.info("👈 Select an endpoint and parameters in the sidebar, then click **Fetch Data** to query the API.")

    st.markdown("### Quick Tips")
    st.markdown(
        """
        - **Custom per_page**: Adjust the `Per Page` input in the sidebar to fetch 10, 25, 50, or 100 items.
        - **Interactive Tables**: In the Table tab, click any column header to sort, drag columns to resize, or download directly.
        - **Direct JSON Inspection**: In the JSON Tree tab, click keys to expand/collapse nested structures.
        - **Export**: Instantly download responses as formatted `.json` or `.csv`.
        """
    )
