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

# Initialize session state for query caching and pagination
if "last_response" not in st.session_state:
    st.session_state.last_response = None
if "last_meta" not in st.session_state:
    st.session_state.last_meta = None
if "page_number" not in st.session_state:
    st.session_state.page_number = 1
if "trigger_fetch" not in st.session_state:
    st.session_state.trigger_fetch = False


def navigate_page(target_page: int):
    st.session_state.page_number = target_page
    st.session_state.trigger_fetch = True


def on_endpoint_change():
    st.session_state.page_number = 1
    st.session_state.last_response = None
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

selected_label = st.sidebar.selectbox("Endpoint", list(ENDPOINT_OPTIONS.keys()), on_change=on_endpoint_change)
endpoint_config = ENDPOINT_OPTIONS[selected_label]

# Dynamic Inputs based on selected endpoint
params = {}
endpoint_path = ""
id_value = ""

if endpoint_config["type"] == "detail":
    if endpoint_config["category"] == "organizations":
        id_value = st.sidebar.text_input("Organization ID", value="8509")
        endpoint_path = f"organizations/{id_value}"
        per_page = st.sidebar.number_input("Per Page", min_value=1, max_value=100, value=25)
        params["per_page"] = per_page
    elif endpoint_config["category"] == "clients":
        id_value = st.sidebar.text_input("Client ID", value="6920")
        endpoint_path = f"clients/{id_value}"

elif endpoint_config["type"] == "purchases":
    id_value = st.sidebar.text_input("Client ID", value="6920")
    per_page = st.sidebar.number_input("Per Page", min_value=1, max_value=100, value=25)
    page = st.sidebar.number_input("Page", min_value=1, step=1, key="page_number")
    endpoint_path = f"clients/{id_value}/purchases"
    params = {"per_page": per_page, "page": page}

elif endpoint_config["type"] == "history":
    id_value = st.sidebar.text_input("Lead ID", value="36")
    endpoint_path = f"leads/{id_value}/history"

elif endpoint_config["type"] == "list":
    per_page = st.sidebar.number_input("Per Page", min_value=1, max_value=100, value=25)
    page = st.sidebar.number_input("Page", min_value=1, step=1, key="page_number")
    params = {"per_page": per_page, "page": page}
    endpoint_path = endpoint_config["category"]

elif endpoint_config["type"] == "custom":
    endpoint_path = st.sidebar.text_input("Endpoint Path", value="organizations")
    per_page = st.sidebar.number_input("Per Page", min_value=1, max_value=100, value=25)
    page = st.sidebar.number_input("Page", min_value=1, step=1, key="page_number")
    params = {"per_page": per_page, "page": page}

# Fetch button
fetch_clicked = st.sidebar.button("🚀 Fetch Data", type="primary", use_container_width=True)

if fetch_clicked or st.session_state.get("trigger_fetch"):
    st.session_state.trigger_fetch = False
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
                "params": dict(params),
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

        # Pagination Controls below table
        meta_info = data.get("meta") if isinstance(data, dict) else None
        if meta_info and "current_page" in meta_info and "last_page" in meta_info:
            cur_p = max(1, int(meta_info.get("current_page", 1)))
            last_p = max(1, int(meta_info.get("last_page", 1)))
            total_recs = meta_info.get("total")

            st.markdown("---")
            nav_col1, nav_col2, nav_col3, nav_col4, nav_col5 = st.columns([1, 1.2, 2.5, 1.2, 1])

            with nav_col1:
                st.button(
                    "⏮️ First",
                    key="btn_first_page",
                    disabled=(cur_p <= 1),
                    use_container_width=True,
                    on_click=navigate_page,
                    args=(1,),
                )

            with nav_col2:
                st.button(
                    "⬅️ Previous",
                    key="btn_prev_page",
                    disabled=(cur_p <= 1),
                    use_container_width=True,
                    on_click=navigate_page,
                    args=(cur_p - 1,),
                )

            with nav_col3:
                total_text = f" ({total_recs:,} records total)" if total_recs is not None else ""
                st.markdown(
                    f"<div style='text-align: center; line-height: 2.2; font-weight: 500; font-size: 14px;'>"
                    f"Page <b style='color: #00d26a;'>{cur_p}</b> of <b>{last_p}</b>{total_text}"
                    f"</div>",
                    unsafe_allow_html=True,
                )

            with nav_col4:
                st.button(
                    "Next ➡️",
                    key="btn_next_page",
                    disabled=(cur_p >= last_p),
                    use_container_width=True,
                    on_click=navigate_page,
                    args=(cur_p + 1,),
                )

            with nav_col5:
                st.button(
                    "Last ⏭️",
                    key="btn_last_page",
                    disabled=(cur_p >= last_p),
                    use_container_width=True,
                    on_click=navigate_page,
                    args=(last_p,),
                )

    with tab_json:
        if isinstance(data, (dict, list)):
            st.json(data, expanded=True)
        else:
            st.code(str(data))

    with tab_download:
        st.subheader("Current Page Export")
        col_dl1, col_dl2 = st.columns(2)

        clean_slug = meta["endpoint_path"].replace("/", "_")
        json_str = json.dumps(data, indent=2, ensure_ascii=False) if isinstance(data, (dict, list)) else str(data)

        with col_dl1:
            st.download_button(
                label="📥 Download Current Page (JSON)",
                data=json_str,
                file_name=f"{clean_slug}_page_{st.session_state.page_number}_{int(time.time())}.json",
                mime="application/json",
                use_container_width=True,
            )

        with col_dl2:
            if table_records:
                try:
                    df = pd.json_normalize(table_records)
                    csv_data = df.to_csv(index=False).encode("utf-8")
                    st.download_button(
                        label="📥 Download Current Page (CSV)",
                        data=csv_data,
                        file_name=f"{clean_slug}_page_{st.session_state.page_number}_{int(time.time())}.csv",
                        mime="text/csv",
                        use_container_width=True,
                    )
                except Exception:
                    st.button("CSV Download Unavailable", disabled=True, use_container_width=True)
            else:
                st.button("CSV Download Unavailable (Not tabular)", disabled=True, use_container_width=True)

        # Bulk Export (All Pages)
        meta_info = data.get("meta") if isinstance(data, dict) else None
        last_page = int(meta_info.get("last_page", 1)) if meta_info else 1
        total_records = meta_info.get("total") if meta_info else None

        if meta_info and last_page > 1:
            st.markdown("---")
            st.subheader("Bulk Export (All Pages)")
            total_label = f" ({total_records:,} total records)" if total_records is not None else ""
            st.caption(f"Fetch all pages across **{last_page} pages**{total_label} using connection pooling and safe rate-limit pacing.")

            bulk_key = f"bulk_{meta['endpoint_path']}"
            if bulk_key not in st.session_state:
                st.session_state[bulk_key] = None

            col_b1, col_b2 = st.columns([2, 1])
            with col_b1:
                start_bulk = st.button("⚡ Fetch All Pages for Download", type="primary", use_container_width=True, key="btn_start_bulk")
            with col_b2:
                max_p = st.number_input("Max Pages to Fetch (0 for all)", min_value=0, max_value=last_page, value=0, key="bulk_max_pages")

            if start_bulk:
                prog_bar = st.progress(0.0)
                status_txt = st.empty()
                all_bulk_records = []
                target_pages = max_p if max_p > 0 else last_page

                try:
                    for chunk, chunk_meta, cur_p, total_p in client.iter_pages(
                        endpoint=meta["endpoint_path"],
                        params=meta.get("params", {}),
                        per_page=100,
                        max_pages=target_pages,
                    ):
                        all_bulk_records.extend(chunk)
                        pct = min(1.0, cur_p / target_pages)
                        prog_bar.progress(pct)
                        status_txt.text(f"Fetched page {cur_p} of {target_pages} ({len(all_bulk_records):,} records collected)...")

                    prog_bar.progress(1.0)
                    status_txt.success(f"Successfully collected {len(all_bulk_records):,} total records from {target_pages} pages!")
                    st.session_state[bulk_key] = all_bulk_records
                except Exception as ex:
                    st.error(f"Bulk fetch interrupted: {ex}")

            if st.session_state.get(bulk_key):
                bulk_records = st.session_state[bulk_key]
                st.markdown(f"**Ready for Download: {len(bulk_records):,} records**")
                col_b_dl1, col_b_dl2 = st.columns(2)
                with col_b_dl1:
                    b_json = json.dumps(bulk_records, indent=2, ensure_ascii=False)
                    st.download_button(
                        label=f"📥 Download All JSON ({len(bulk_records):,} items)",
                        data=b_json,
                        file_name=f"all_{clean_slug}_{int(time.time())}.json",
                        mime="application/json",
                        use_container_width=True,
                        key="btn_dl_all_json",
                    )
                with col_b_dl2:
                    try:
                        b_df = pd.json_normalize(bulk_records)
                        b_csv = b_df.to_csv(index=False).encode("utf-8")
                        st.download_button(
                            label=f"📥 Download All CSV ({len(bulk_records):,} rows)",
                            data=b_csv,
                            file_name=f"all_{clean_slug}_{int(time.time())}.csv",
                            mime="text/csv",
                            use_container_width=True,
                            key="btn_dl_all_csv",
                        )
                    except Exception:
                        st.button("CSV Download Unavailable", disabled=True, use_container_width=True)
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
