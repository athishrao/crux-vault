import os
import streamlit as st
import pandas as pd
import json
import tempfile
from pathlib import Path
from datetime import datetime, timedelta

import cruxvault as crux

st.set_page_config(
    page_title="CruxVault Dashboard",
    page_icon="",
    layout="wide"
)

st.markdown("""
<style>
    .metric-card {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        padding: 20px;
        border-radius: 10px;
        color: white;
    }
    .secret-card {
        background: #f8f9fa;
        padding: 15px;
        border-radius: 8px;
        border-left: 4px solid #667eea;
        margin: 10px 0;
    }
</style>
""", unsafe_allow_html=True)

# Initialize session state
if 'show_values' not in st.session_state:
    st.session_state.show_values = False

# Sidebar
with st.sidebar:
    st.image("https://dummyimage.com/600x400/26272f/fff&text=CruxVault", width='stretch')
    st.markdown("---")
    
    page = st.radio("Navigation", [
        "📊 Dashboard",
        "🔑 Secrets",
        "📝 Audit Log",
        "📈 Analytics",
        "⚙️ Settings"
    ])
    
    st.markdown("---")
    st.caption(f"Last updated: {datetime.now().strftime('%H:%M:%S')}")

def load_secrets():
    try:
        return crux.list() or []
    except:
        return []

def load_audit_log():
    try:
        log_path = crux.get_audit_path()
        if log_path.exists():
            logs = []
            with open(log_path, 'r') as f:
                for line in f:
                    logs.append(json.loads(line))
            return logs[-100:]  # Last 100 entries
        return []
    except:
        return []

def get_metrics():
    secrets = load_secrets()
    audit = load_audit_log()
    
    types = {}
    tags = {}
    for s in secrets:
        t = s.get('type', 'secret')
        types[t] = types.get(t, 0) + 1
        for tag in s.get('tags', []):
            tags[tag] = tags.get(tag, 0) + 1
    
    return {
        'total': len(secrets),
        'types': types,
        'tags': tags,
        'recent_ops': len([a for a in audit if datetime.fromisoformat(a['timestamp']) > datetime.now() - timedelta(hours=24)])
    }

if page == "📊 Dashboard":
    st.title("CruxVault Dashboard")
    
    metrics = get_metrics()
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("Total Secrets", metrics['total'], delta=None)
    
    with col2:
        st.metric("Secrets", metrics['types'].get('secret', 0))
    
    with col3:
        st.metric("Configs", metrics['types'].get('config', 0))
    
    with col4:
        st.metric("24h Operations", metrics['recent_ops'])
    
    st.markdown("---")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("Secrets by Type")
        if metrics['types']:
            st.bar_chart(metrics['types'])
        else:
            st.info("No secrets yet")
    
    with col2:
        st.subheader("Tags Distribution")
        if metrics['tags']:
            tag_df = pd.DataFrame(list(metrics['tags'].items()), columns=['Tag', 'Count'])
            st.dataframe(tag_df, width='stretch', hide_index=True)
        else:
            st.info("No tags yet")
    
    st.subheader("Recent Activity")
    audit = load_audit_log()
    if audit:
        recent = audit[-5:][::-1]
        for log in recent:
            status = "✅" if log['success'] else "❌"
            st.text(f"{status} {log['timestamp']} - {log['action'].upper()} {log['path']} by {log['user']}")
    else:
        st.info("No activity yet")

elif page == "🔑 Secrets":
    st.title("🔑 Secrets Management")
    
    tab1, tab2, tab3, tab4 = st.tabs(["📋 List", "➕ Add New", "Import/Export", "🔍 Search"])
    
    with tab1:
        col1, col2 = st.columns([3, 1])
        with col1:
            st.session_state.show_values = st.checkbox("Show Values", value=st.session_state.show_values)
        with col2:
            if st.button("🔄 Refresh", width='stretch'):
                st.rerun()
        
        secrets = load_secrets()
        
        if secrets:
            filter_col1, filter_col2 = st.columns(2)
            with filter_col1:
                type_filter = st.multiselect("Filter by Type", 
                    options=list(set([s.get('type', 'secret') for s in secrets])))
            with filter_col2:
                all_tags = set()
                for s in secrets:
                    all_tags.update(s.get('tags', []))
                tag_filter = st.multiselect("Filter by Tags", options=list(all_tags))
            
            filtered = secrets
            if type_filter:
                filtered = [s for s in filtered if s.get('type', 'secret') in type_filter]
            if tag_filter:
                filtered = [s for s in filtered if any(t in s.get('tags', []) for t in tag_filter)]
            
            st.write(f"Showing {len(filtered)} of {len(secrets)} secrets")
            
            for secret in filtered:
                with st.expander(f"🔑 {secret['path']}"):
                    col1, col2 = st.columns([3, 1])
                    
                    with col1:
                        st.text(f"Type: {secret.get('type', 'secret')}")
                        st.text(f"Version: {secret.get('version', 1)}")
                        st.text(f"Modified: {secret.get('modified', 'N/A')}")
                        if secret.get('tags'):
                            st.text(f"Tags: {', '.join(secret['tags'])}")
                        
                        if st.session_state.show_values:
                            try:
                                value = crux.get(secret['path'])
                                st.code(value, language=None)
                            except Exception as e:
                                st.error(f"Error: {e}")
                        else:
                            if st.button("👁️ Reveal", key=f"reveal_{secret['path']}"):
                                try:
                                    value = crux.get(secret['path'])
                                    st.code(value, language=None)
                                except Exception as e:
                                    st.error(f"Error: {e}")
                    
                    with col2:
                        if st.button("📜 History", key=f"hist_{secret['path']}", width='stretch'):
                            try:
                                history = crux.history(secret['path'])
                                st.json(history)
                            except Exception as e:
                                st.error(f"Error: {e}")
                        
                        if st.button("🗑️ Delete", key=f"del_{secret['path']}", width='stretch', type="secondary"):
                            st.session_state[f"confirm_{secret['path']}"] = True

                        if st.session_state.get(f"confirm_{secret['path']}", False):
                            if st.button("⚠️ Confirm Delete", key=f"confirm_del_{secret['path']}", type="primary"):
                                try:
                                    crux.delete(secret['path'])
                                    st.success("Deleted!")
                                    st.rerun()
                                except Exception as e:
                                    st.error(f"Error: {e}")
        else:
            st.info("No secrets stored yet. Add your first secret!")
    
    with tab2:
        with st.form("add_secret_form"):
            st.subheader("Add New Secret")
            
            path = st.text_input("Path *", placeholder="api/key or database/password")
            value = st.text_area("Value *", placeholder="Enter secret value")
            
            col1, col2 = st.columns(2)
            with col1:
                secret_type = st.selectbox("Type", ["secret", "config", "flag"])
            with col2:
                tags_input = st.text_input("Tags (comma-separated)", placeholder="production, api")
            
            submitted = st.form_submit_button("💾 Save Secret", width='stretch')
            
            if submitted:
                if not path or not value:
                    st.error("Path and Value are required!")
                else:
                    try:
                        tags = [t.strip() for t in tags_input.split(',')] if tags_input else []
                        crux.set(path, value, tags=tags)
                        st.success(f"✅ Secret '{path}' saved successfully!")
                        st.balloons()
                    except Exception as e:
                        st.error(f"Error: {e}")
    
    with tab3:
        st.subheader("Import from .env")
        uploaded_file = st.file_uploader("Choose a .env file", type=['env', 'txt'])
        if uploaded_file:
            prefix = st.text_input("Import with prefix (optional)", placeholder="staging/")
            if st.button("Import"):
                # Recreate file in /tmp
                with tempfile.TemporaryDirectory() as tmpdir:
                    file_path = os.path.join(tmpdir, uploaded_file.name)

                    with open(file_path, "wb") as f:
                        f.write(uploaded_file.getbuffer())

                    num_imported = crux.import_env(file_path, prefix)

                st.success(f"Imported {num_imported} keys from uploaded file!")
        
        st.markdown("---")
        
        st.subheader("Export to .env")
        st.download_button(
            label="Download All Secrets(as txt)",
            data=crux.export_env(),
            file_name="secrets.env",
            mime="text/plain"
        )
            # st.info("Export feature requires CLI command: crux dev export")

    with tab4:
        st.subheader("Search Secrets")
        search_term = st.text_input("Search by path", placeholder="Enter search term...")
        
        if search_term:
            secrets = load_secrets()
            results = [s for s in secrets if search_term.lower() in s['path'].lower()]
            
            if results:
                st.write(f"Found {len(results)} results")
                for secret in results:
                    st.text(f"🔑 {secret['path']}")
            else:
                st.info("No results found")

elif page == "📝 Audit Log":
    st.title("📝 Audit Log")
    
    audit = load_audit_log()
    
    if audit:
        col1, col2, col3 = st.columns(3)
        with col1:
            action_filter = st.multiselect("Filter by Action", 
                options=list(set([a['action'] for a in audit])))
        with col2:
            user_filter = st.multiselect("Filter by User",
                options=list(set([a['user'] for a in audit])))
        with col3:
            time_range = st.selectbox("Time Range", ["Last Hour", "Last 24 Hours", "Last Week", "All"])
        
        filtered = audit
        if action_filter:
            filtered = [a for a in filtered if a['action'] in action_filter]
        if user_filter:
            filtered = [a for a in filtered if a['user'] in user_filter]
        
        now = datetime.now()
        if time_range == "Last Hour":
            cutoff = now - timedelta(hours=1)
            filtered = [a for a in filtered if datetime.fromisoformat(a['timestamp']) > cutoff]
        elif time_range == "Last 24 Hours":
            cutoff = now - timedelta(days=1)
            filtered = [a for a in filtered if datetime.fromisoformat(a['timestamp']) > cutoff]
        elif time_range == "Last Week":
            cutoff = now - timedelta(weeks=1)
            filtered = [a for a in filtered if datetime.fromisoformat(a['timestamp']) > cutoff]
        
        st.write(f"Showing {len(filtered)} of {len(audit)} events")
        
        df = pd.DataFrame(filtered)
        if not df.empty:
            df['timestamp'] = pd.to_datetime(df['timestamp'])
            df = df.sort_values('timestamp', ascending=False)
            st.dataframe(df, width='stretch', hide_index=True)
        else:
            st.info("No events match the filters")
    else:
        st.info("No audit log entries yet")

elif page == "📈 Analytics":
    st.title("📈 Analytics")
    
    secrets = load_secrets()
    audit = load_audit_log()
    
    if audit:
        df = pd.DataFrame(audit)
        df['timestamp'] = pd.to_datetime(df['timestamp'])
        df['date'] = df['timestamp'].dt.date
        
        st.subheader("Activity Timeline")
        daily_activity = df.groupby('date').size()
        st.line_chart(daily_activity)
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.subheader("Actions Distribution")
            action_counts = df['action'].value_counts()
            st.bar_chart(action_counts)
        
        with col2:
            st.subheader("User Activity")
            user_counts = df['user'].value_counts()
            st.bar_chart(user_counts)
        
        st.subheader("Most Accessed Secrets")
        get_operations = df[df['action'] == 'get']
        if not get_operations.empty:
            top_secrets = get_operations['path'].value_counts().head(10)
            st.bar_chart(top_secrets)
        else:
            st.info("No get operations yet")
    else:
        st.info("Not enough data for analytics yet")

elif page == "⚙️ Settings":
    st.title("⚙️ Settings")
    
    tab1, tab2 = st.tabs(["Security", "Collaberation Settings"])
    
    with tab1:
        st.subheader("Security Information")
        
        st.info("🔐 Encryption: AES-256-GCM")
        st.info("🔑 Key Storage: System Keychain")
        
        st.subheader("Master Key")
        st.text("Master key is stored securely in system keychain")

    with tab2:
        st.info("Coming Soon...")

        
st.markdown("---")
st.caption("CruxVault Dashboard • Built with ❤️  in the Bay Area!")
