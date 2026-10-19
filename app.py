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

CACHE_TTL_SECONDS = 300  # 5 minutes

# Initialize session state for query caching and pagination
if "last_response" not in st.session_state:
    st.session_state.last_response = None
if "last_meta" not in st.session_state:
    st.session_state.last_meta = None
if "page_number" not in st.session_state:
    st.session_state.page_number = 1
if "trigger_fetch" not in st.session_state:
    st.session_state.trigger_fetch = False
if "force_refresh" not in st.session_state:
    st.session_state.force_refresh = False
if "page_cache" not in st.session_state:
    st.session_state.page_cache = {}
if "selected_endpoint" not in st.session_state:
    st.session_state.selected_endpoint = "Organizations (List)"
if "org_id_input" not in st.session_state:
    st.session_state.org_id_input = "8509"
if "client_id_input" not in st.session_state:
    st.session_state.client_id_input = "6920"
if "lead_id_input" not in st.session_state:
    st.session_state.lead_id_input = "36"
if "nav_breadcrumbs" not in st.session_state:
    st.session_state.nav_breadcrumbs = []

def make_cache_key(endpoint: str, query_params: dict) -> str:
    sorted_items = sorted((str(k), str(v)) for k, v in (query_params or {}).items() if v is not None)
    return f"{endpoint.strip('/')}?{json.dumps(sorted_items)}"


def get_from_cache(endpoint: str, query_params: dict):
    key = make_cache_key(endpoint, query_params)
    entry = st.session_state.page_cache.get(key)
    if not entry:
        return None
    timestamp, meta, data = entry
    if time.time() - timestamp > CACHE_TTL_SECONDS:
        del st.session_state.page_cache[key]
        return None
    return meta, data


def save_to_cache(endpoint: str, query_params: dict, meta: dict, data):
    if len(st.session_state.page_cache) >= 100:
        oldest_key = min(st.session_state.page_cache.keys(), key=lambda k: st.session_state.page_cache[k][0])
        del st.session_state.page_cache[oldest_key]
    key = make_cache_key(endpoint, query_params)
    st.session_state.page_cache[key] = (time.time(), meta, data)


def navigate_page(target_page: int):
    st.session_state.page_number = target_page
    st.session_state.trigger_fetch = True


def on_endpoint_change():
    st.session_state.page_number = 1
    st.session_state.last_response = None
    st.session_state.last_meta = None
    st.session_state.nav_breadcrumbs = []


def drill_down_to(endpoint_label: str, target_id: str | int = None):
    current_entry = {
        "label": st.session_state.get("selected_endpoint", "Organizations (List)"),
        "page": st.session_state.get("page_number", 1),
        "org_id": st.session_state.get("org_id_input", "8509"),
        "client_id": st.session_state.get("client_id_input", "6920"),
        "lead_id": st.session_state.get("lead_id_input", "36"),
    }
    st.session_state.nav_breadcrumbs.append(current_entry)

    st.session_state.selected_endpoint = endpoint_label
    st.session_state.page_number = 1
    if target_id is not None:
        target_str = str(target_id)
        if "Organization" in endpoint_label:
            st.session_state.org_id_input = target_str
        elif "Client" in endpoint_label:
            st.session_state.client_id_input = target_str
        elif "Lead" in endpoint_label:
            st.session_state.lead_id_input = target_str

    st.session_state.trigger_fetch = True


def go_back_breadcrumb():
    if st.session_state.nav_breadcrumbs:
        prev = st.session_state.nav_breadcrumbs.pop()
        st.session_state.selected_endpoint = prev["label"]
        st.session_state.page_number = prev.get("page", 1)
        if "org_id" in prev and prev["org_id"]:
            st.session_state.org_id_input = prev["org_id"]
        if "client_id" in prev and prev["client_id"]:
            st.session_state.client_id_input = prev["client_id"]
        if "lead_id" in prev and prev["lead_id"]:
            st.session_state.lead_id_input = prev["lead_id"]
        st.session_state.trigger_fetch = True


def extract_record_relations(record: dict, endpoint_cat: str = "") -> dict:
    if not isinstance(record, dict):
        return {}

    relations = {}

    # Organization relation
    if "organization" in endpoint_cat and record.get("id"):
        relations["org"] = {
            "id": record.get("id"),
            "name": record.get("company_name", f"Org #{record.get('id')}"),
            "is_self": True,
        }
    elif isinstance(record.get("organization"), dict) and record["organization"].get("id"):
        relations["org"] = {
            "id": record["organization"].get("id"),
            "name": record["organization"].get("company_name", f"Org #{record['organization'].get('id')}"),
            "is_self": False,
        }
    elif record.get("organization_id"):
        relations["org"] = {
            "id": record.get("organization_id"),
            "name": f"Org #{record.get('organization_id')}",
            "is_self": False,
        }

    # Customer / Client relation
    if "client" in endpoint_cat and record.get("id"):
        relations["client"] = {
            "id": record.get("id"),
            "name": record.get("pic_name") or record.get("name") or f"Client #{record.get('id')}",
            "is_self": True,
        }
    elif isinstance(record.get("customer"), dict) and record["customer"].get("id"):
        relations["client"] = {
            "id": record["customer"].get("id"),
            "name": record["customer"].get("name") or record["customer"].get("pic_name") or f"Client #{record['customer'].get('id')}",
            "is_self": False,
        }
    elif isinstance(record.get("client"), dict) and record["client"].get("id"):
        relations["client"] = {
            "id": record["client"].get("id"),
            "name": record["client"].get("pic_name") or record["client"].get("name") or f"Client #{record['client'].get('id')}",
            "is_self": False,
        }
    elif record.get("client_id"):
        relations["client"] = {
            "id": record.get("client_id"),
            "name": f"Client #{record.get('client_id')}",
            "is_self": False,
        }

    # Lead / Deal pipeline relation
    if "lead" in endpoint_cat and record.get("id"):
        relations["lead"] = {"id": record.get("id"), "is_self": True}
    elif "deal" in endpoint_cat and record.get("id"):
        relations["lead"] = {"id": record.get("id"), "is_self": True}
    elif record.get("lead_id"):
        relations["lead"] = {"id": record.get("lead_id"), "is_self": False}

    return relations


def render_entity_inspector(data, table_records, endpoint_config, key_prefix="inspect"):
    if not table_records:
        st.info("No records available to inspect.")
        return

    st.markdown("#### 🔗 Related Entity Inspector & Drill-Down")
    st.caption("Select any record below (or click a table row above) to view linked organizations, clients, purchases, and lead histories:")

    selected_rec = None
    if len(table_records) > 1:
        def format_record(idx):
            r = table_records[idx]
            rid = r.get("id", idx + 1)
            name = (
                r.get("title")
                or r.get("company_name")
                or r.get("pic_name")
                or r.get("name")
                or r.get("product")
                or "Record"
            )
            extra = f" [{r.get('status')}]" if r.get("status") else ""
            return f"#{rid} - {name}{extra}"

        current_choice = st.session_state.get(f"{key_prefix}_record_selector", 0)
        if not isinstance(current_choice, int) or current_choice >= len(table_records):
            current_choice = 0

        chosen_idx = st.selectbox(
            "Select a record from this page to inspect linked entities:",
            range(len(table_records)),
            index=current_choice,
            format_func=format_record,
            key=f"{key_prefix}_record_selector",
        )
        selected_rec = table_records[chosen_idx]
    else:
        selected_rec = table_records[0]

    rels = extract_record_relations(selected_rec, endpoint_config.get("category", ""))
    is_detail_view = endpoint_config.get("type") == "detail"

    c1, c2, c3 = st.columns(3)
    with c1:
        st.markdown("##### 🏢 Organization")
        if "org" in rels:
            org_id = rels["org"]["id"]
            org_name = rels["org"]["name"]
            is_self = rels["org"].get("is_self", False)
            st.caption(f"**{org_name}** (`ID: {org_id}`)")
            if is_self and is_detail_view:
                st.info("Currently viewing this organization.")
            else:
                st.button(
                    f"🏢 View Org #{org_id} Details",
                    key=f"{key_prefix}_btn_org_{org_id}",
                    on_click=drill_down_to,
                    args=("Organization (Detail by ID)", org_id),
                    use_container_width=True,
                )
        else:
            st.caption("No linked Organization detected.")

    with c2:
        st.markdown("##### 👤 Client / Customer")
        if "client" in rels:
            cid = rels["client"]["id"]
            cname = rels["client"]["name"]
            is_self = rels["client"].get("is_self", False)
            st.caption(f"**{cname}** (`ID: {cid}`)")
            if not (is_self and is_detail_view):
                st.button(
                    f"👤 View Client #{cid}",
                    key=f"{key_prefix}_btn_cli_{cid}",
                    on_click=drill_down_to,
                    args=("Client (Detail by ID)", cid),
                    use_container_width=True,
                )
            st.button(
                f"🛍️ View Purchases (#{cid})",
                key=f"{key_prefix}_btn_pur_{cid}",
                on_click=drill_down_to,
                args=("Client Purchases", cid),
                use_container_width=True,
            )
        else:
            st.caption("No linked Client detected.")

    with c3:
        st.markdown("##### 📜 Lead / History")
        if "lead" in rels:
            lid = rels["lead"]["id"]
            st.caption(f"Lead ID: `{lid}`")
            if endpoint_config.get("type") == "history":
                st.info("Currently viewing this lead history.")
            else:
                st.button(
                    f"📜 View Lead #{lid} History",
                    key=f"{key_prefix}_btn_lead_{lid}",
                    on_click=drill_down_to,
                    args=("Lead History (by ID)", lid),
                    use_container_width=True,
                )
        else:
            st.caption("No linked Lead detected.")

    # Check for embedded clients list in organization detail
    org_clients = None
    if isinstance(data, dict):
        raw_data = data.get("data")
        if isinstance(raw_data, dict) and isinstance(raw_data.get("clients"), list):
            org_clients = raw_data.get("clients")
        elif isinstance(data.get("clients"), list):
            org_clients = data.get("clients")

    if org_clients:
        st.markdown("---")
        st.markdown(f"##### 👥 Associated Clients in this Organization ({len(org_clients)})")
        st.dataframe(pd.json_normalize(org_clients), use_container_width=True, height=200)

        cl_cols = st.columns([2, 1, 1])
        with cl_cols[0]:
            picked_c_idx = st.selectbox(
                "Select associated client to inspect:",
                range(len(org_clients)),
                format_func=lambda i: f"#{org_clients[i].get('id')}: {org_clients[i].get('pic_name', 'Client')}",
                key=f"{key_prefix}_org_client_choice",
            )
        picked_cid = org_clients[picked_c_idx].get("id")
        with cl_cols[1]:
            st.button(
                f"👤 View Client #{picked_cid}",
                key=f"{key_prefix}_btn_sub_client_{picked_cid}",
                on_click=drill_down_to,
                args=("Client (Detail by ID)", picked_cid),
                use_container_width=True,
            )
        with cl_cols[2]:
            st.button(
                f"🛍️ Purchases (#{picked_cid})",
                key=f"{key_prefix}_btn_sub_pur_{picked_cid}",
                on_click=drill_down_to,
                args=("Client Purchases", picked_cid),
                use_container_width=True,
            )
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

selected_label = st.sidebar.selectbox("Endpoint", list(ENDPOINT_OPTIONS.keys()), key="selected_endpoint", on_change=on_endpoint_change)
endpoint_config = ENDPOINT_OPTIONS[selected_label]

# Dynamic Inputs based on selected endpoint
params = {}
endpoint_path = ""
id_value = ""

if endpoint_config["type"] == "detail":
    if endpoint_config["category"] == "organizations":
        id_value = st.sidebar.text_input("Organization ID", key="org_id_input")
        endpoint_path = f"organizations/{id_value}"
        per_page = st.sidebar.number_input("Per Page", min_value=1, max_value=100, value=25)
        params["per_page"] = per_page
    elif endpoint_config["category"] == "clients":
        id_value = st.sidebar.text_input("Client ID", key="client_id_input")
        endpoint_path = f"clients/{id_value}"

elif endpoint_config["type"] == "purchases":
    id_value = st.sidebar.text_input("Client ID", key="client_id_input")
    per_page = st.sidebar.number_input("Per Page", min_value=1, max_value=100, value=25)
    page = st.sidebar.number_input("Page", min_value=1, step=1, key="page_number")
    endpoint_path = f"clients/{id_value}/purchases"
    params = {"per_page": per_page, "page": page}

elif endpoint_config["type"] == "history":
    id_value = st.sidebar.text_input("Lead ID", key="lead_id_input")
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

# Fetch and Refresh buttons in sidebar
col_f1, col_f2 = st.sidebar.columns([3, 1])
with col_f1:
    fetch_clicked = st.button("🚀 Fetch Data", type="primary", use_container_width=True)
with col_f2:
    refresh_clicked = st.button("🔄", help="Force live reload from API (bypass cache)", use_container_width=True)

is_force = refresh_clicked or st.session_state.get("force_refresh", False)
if is_force:
    st.session_state.force_refresh = False

should_run = fetch_clicked or refresh_clicked or st.session_state.get("trigger_fetch", False)

if should_run:
    st.session_state.trigger_fetch = False

    cached_entry = None if is_force else get_from_cache(endpoint_path, params)

    if cached_entry:
        cached_meta, cached_data = cached_entry
        st.session_state.last_meta = {
            **cached_meta,
            "duration_ms": 0.0,
            "from_cache": True,
        }
        st.session_state.last_response = cached_data
    else:
        with st.spinner(f"Querying `{endpoint_path}`..."):
            start_time = time.time()
            try:
                resp = client.request(endpoint_path, params=params)
                duration = round((time.time() - start_time) * 1000, 1)

                meta_dict = {
                    "url": resp.url,
                    "status_code": resp.status_code,
                    "reason": resp.reason,
                    "duration_ms": duration,
                    "endpoint_path": endpoint_path,
                    "params": dict(params),
                    "from_cache": False,
                }

                try:
                    resp_data = resp.json()
                except Exception:
                    resp_data = resp.text

                st.session_state.last_meta = meta_dict
                st.session_state.last_response = resp_data

                if resp.status_code == 200:
                    save_to_cache(endpoint_path, params, meta_dict, resp_data)

            except Exception as e:
                st.error(f"Request failed: {e}")

# Main Content Area
st.title("CRM API Explorer")

# Breadcrumbs navigation bar
if st.session_state.get("nav_breadcrumbs"):
    col_bc1, col_bc2 = st.columns([1.5, 6])
    with col_bc1:
        prev_crumb = st.session_state.nav_breadcrumbs[-1]
        st.button(
            f"⬅️ Back to {prev_crumb['label']}",
            key="btn_breadcrumb_back",
            on_click=go_back_breadcrumb,
            use_container_width=True,
        )
    with col_bc2:
        crumb_titles = [c["label"] for c in st.session_state.nav_breadcrumbs] + [st.session_state.selected_endpoint]
        st.info(f"📍 Navigation Path: {' ➔ '.join(crumb_titles)}")

if st.session_state.last_response is not None:
    meta = st.session_state.last_meta
    data = st.session_state.last_response

    # Normalize data into table_records list if possible
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

    # Telemetry metrics row
    col1, col2, col3, col4, col5 = st.columns([1, 1.2, 1, 1, 0.8])
    with col1:
        if 200 <= meta["status_code"] < 300:
            st.metric("Status", f"{meta['status_code']} {meta['reason']}")
        else:
            st.metric("Status", f"{meta['status_code']} {meta['reason']}", delta="-Error", delta_color="inverse")
    with col2:
        if meta.get("from_cache"):
            st.metric("Source", "⚡ In Cache (<1 ms)", help="Loaded instantly from 5-minute session cache without burning API quota.")
        else:
            st.metric("Response Time", f"{meta['duration_ms']} ms", help="Fetched live from CRM API.")
    with col3:
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
    with col5:
        st.markdown("<div style='padding-top: 10px;'>", unsafe_allow_html=True)
        if st.button("🔄 Refresh", key="telemetry_refresh_btn", help="Force live reload from CRM API (bypasses cache)", use_container_width=True):
            st.session_state.force_refresh = True
            st.session_state.trigger_fetch = True
            st.rerun()
        st.markdown("</div>", unsafe_allow_html=True)

    # Display Requested URL
    st.code(meta["url"], language="http")

    # Tabs for Dual View & Entity Inspection
    tab_table, tab_inspect, tab_json, tab_download = st.tabs([
        "📊 Table View",
        "🔗 Entity Inspector",
        "🔍 JSON Tree",
        "💾 Export Data",
    ])

    with tab_table:
        if table_records:
            clean_slug = meta["endpoint_path"].replace("/", "_")
            bulk_key = f"bulk_{meta['endpoint_path']}"
            cached_bulk_df = st.session_state.get(f"df_{bulk_key}")
            meta_info = data.get("meta") if isinstance(data, dict) else None
            last_page = int(meta_info.get("last_page", 1)) if meta_info else 1
            total_records = meta_info.get("total") if meta_info else len(table_records)

            # Filter & Search Panel
            with st.container(border=True):
                st.markdown("##### 🔎 Filter & Search")
                scope_choices = ["📄 Current Page"]
                if last_page > 1:
                    scope_choices.append("🌐 All Records (Global)")

                if len(scope_choices) > 1:
                    f_head1, f_head2 = st.columns([1.5, 3.5])
                    with f_head1:
                        chosen_scope = st.radio(
                            "Scope",
                            scope_choices,
                            horizontal=True,
                            key=f"scope_radio_{clean_slug}",
                        )
                    with f_head2:
                        if chosen_scope == "🌐 All Records (Global)":
                            if cached_bulk_df is None:
                                st.info(f"Global filter requires loading all {last_page} pages ({total_records:,} records).")
                                if st.button("⚡ Sync All Records to Memory", type="primary", key=f"btn_sync_{clean_slug}"):
                                    prog_bar = st.progress(0.0)
                                    stat_txt = st.empty()
                                    all_sync_recs = []
                                    try:
                                        for chunk, _, cur_p, tot_p in client.iter_pages(
                                            endpoint=meta["endpoint_path"],
                                            params=meta.get("params", {}),
                                            per_page=100,
                                        ):
                                            all_sync_recs.extend(chunk)
                                            prog_bar.progress(min(1.0, cur_p / max(1, tot_p)))
                                            stat_txt.text(f"Syncing page {cur_p}/{tot_p} ({len(all_sync_recs):,} records)...")

                                        synced_df = pd.json_normalize(all_sync_recs)
                                        st.session_state[f"df_{bulk_key}"] = synced_df
                                        st.session_state[bulk_key] = all_sync_recs
                                        cached_bulk_df = synced_df
                                        st.rerun()
                                    except Exception as ex:
                                        st.error(f"Sync error: {ex}")
                            else:
                                st.caption(f"⚡ **In Memory:** `{len(cached_bulk_df):,} total records` loaded. Ready for instant multi-filter.")
                else:
                    chosen_scope = "📄 Current Page"

                # Pick source dataframe
                if chosen_scope == "🌐 All Records (Global)" and cached_bulk_df is not None:
                    df_source = cached_bulk_df.copy()
                    source_label = f"all {len(df_source):,} global"
                else:
                    df_source = pd.json_normalize(table_records)
                    source_label = f"{len(df_source):,} current page"

                df_filtered = df_source.copy()
                active_filters = []

                if not df_source.empty:
                    f_col1, f_col2, f_col3 = st.columns(3)

                    # 1. Search Keyword
                    with f_col1:
                        kw = st.text_input(
                            "🔍 Search Keyword",
                            placeholder="Search any field...",
                            key=f"kw_{clean_slug}",
                        )
                        if kw.strip():
                            kw_clean = kw.strip()
                            active_filters.append(f"Keyword: '{kw_clean}'")
                            str_cols = df_filtered.select_dtypes(include=["object", "string"]).columns
                            if len(str_cols) > 0:
                                mask = False
                                for col in str_cols:
                                    mask = mask | df_filtered[col].astype(str).str.contains(kw_clean, case=False, na=False)
                                df_filtered = df_filtered[mask]

                    # 2. Industry or City filter
                    with f_col2:
                        if "industry" in df_source.columns:
                            avail_ind = sorted([str(x) for x in df_source["industry"].dropna().unique() if str(x).strip()])
                            if avail_ind:
                                picked_ind = st.multiselect(
                                    "🏢 Industry",
                                    options=avail_ind,
                                    placeholder="All Industries",
                                    key=f"ind_{clean_slug}",
                                )
                                if picked_ind:
                                    active_filters.append(f"Industry: {', '.join(picked_ind)}")
                                    df_filtered = df_filtered[df_filtered["industry"].isin(picked_ind)]
                        elif "city" in df_source.columns:
                            avail_city = sorted([str(x) for x in df_source["city"].dropna().unique() if str(x).strip() and str(x).lower() != "nan"])
                            if len(avail_city) > 1:
                                picked_city = st.multiselect(
                                    "📍 City",
                                    options=avail_city,
                                    placeholder="All Cities",
                                    key=f"city_{clean_slug}",
                                )
                                if picked_city:
                                    active_filters.append(f"City: {', '.join(picked_city)}")
                                    df_filtered = df_filtered[df_filtered["city"].isin(picked_city)]

                    # 3. Status filter
                    with f_col3:
                        if "status" in df_source.columns:
                            avail_stat = sorted([str(x) for x in df_source["status"].dropna().unique() if str(x).strip()])
                            if avail_stat:
                                picked_stat = st.multiselect(
                                    "📈 Status",
                                    options=avail_stat,
                                    placeholder="All Statuses",
                                    key=f"stat_{clean_slug}",
                                )
                                if picked_stat:
                                    active_filters.append(f"Status: {', '.join(picked_stat)}")
                                    df_filtered = df_filtered[df_filtered["status"].isin(picked_stat)]

                # Results Summary & Quick CSV Download Row
                sub_col1, sub_col2 = st.columns([3, 1])
                with sub_col1:
                    if active_filters:
                        st.caption(f"🎯 **Active Filters:** {' | '.join(active_filters)}")
                        st.markdown(f"**Found {len(df_filtered):,} matching records** (from {source_label} records)")
                    else:
                        st.caption(f"Showing all {len(df_filtered):,} {source_label} records. Use filters above to narrow results.")
                with sub_col2:
                    if not df_filtered.empty:
                        csv_data = df_filtered.to_csv(index=False).encode("utf-8")
                        st.download_button(
                            label=f"📥 Download Filtered CSV ({len(df_filtered):,})",
                            data=csv_data,
                            file_name=f"{clean_slug}_filtered_{int(time.time())}.csv",
                            mime="text/csv",
                            use_container_width=True,
                            key=f"btn_dl_filt_{clean_slug}",
                        )

            # Render Table View
            if not df_filtered.empty:
                df_event = st.dataframe(
                    df_filtered,
                    use_container_width=True,
                    height=450,
                    on_select="rerun",
                    selection_mode="single-row",
                    key=f"table_df_widget_{clean_slug}",
                )
                st.caption(f"Showing {len(df_filtered)} rows and {len(df_filtered.columns)} columns. Click any row to inspect relations below, or click headers to sort.")
                if hasattr(df_event, "selection") and df_event.selection and df_event.selection.rows:
                    sel_row_idx = df_event.selection.rows[0]
                    if 0 <= sel_row_idx < len(df_filtered):
                        st.session_state["table_panel_record_selector"] = sel_row_idx

                current_records_for_inspector = df_filtered.to_dict(orient="records")
            else:
                st.warning("No records matched your filter criteria.")
                current_records_for_inspector = []

            # Pagination Controls (only if viewing single page mode)
            if chosen_scope == "📄 Current Page" and meta_info and "current_page" in meta_info and "last_page" in meta_info:
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

            # Prominent Entity Inspector below Table
            if current_records_for_inspector:
                st.markdown("---")
                with st.container(border=True):
                    render_entity_inspector(data, current_records_for_inspector, endpoint_config, key_prefix="table_panel")
        else:
            st.info("Response is not tabular or is empty. View the JSON Tree tab.")
    with tab_inspect:
        render_entity_inspector(data, table_records, endpoint_config, key_prefix="tab_inspect")

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
