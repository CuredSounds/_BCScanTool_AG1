import streamlit as st
import uvicorn
import pandas as pd
import requests
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime

# Configure page
st.set_page_config(
    page_title="BCScanTool Dashboard",
    page_icon="🏎️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for premium look
st.markdown("""
<style>
    .stMetric {
        background-color: #1E293B;
        border-radius: 10px;
        padding: 15px;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -1px rgba(0, 0, 0, 0.06);
    }
    .main-header {
        background: linear-gradient(90deg, #4facfe 0%, #00f2fe 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        font-weight: 800;
        font-size: 3rem;
        margin-bottom: 0px;
    }
    div[data-testid="stSidebar"] {
        border-right: 1px solid #334155;
    }
    .critical-alert {
        background-color: rgba(239, 68, 68, 0.1);
        border-left: 4px solid #ef4444;
        padding: 15px;
        border-radius: 4px;
        margin-bottom: 10px;
    }
    .warning-alert {
        background-color: rgba(245, 158, 11, 0.1);
        border-left: 4px solid #f59e0b;
        padding: 15px;
        border-radius: 4px;
        margin-bottom: 10px;
    }
</style>
""", unsafe_allow_html=True)

API_BASE_URL = "http://localhost:8080/api"

@st.cache_data(ttl=60)
def fetch_vehicles():
    try:
        response = requests.get(f"{API_BASE_URL}/vehicles")
        response.raise_for_status()
        return response.json()
    except Exception as e:
        st.error(f"Failed to connect to API. Is the FastAPI server running? Error: {e}")
        return []

@st.cache_data(ttl=60)
def fetch_diagnostics(vin: str):
    try:
        response = requests.get(f"{API_BASE_URL}/vehicles/{vin}/diagnostics")
        response.raise_for_status()
        return response.json()
    except Exception as e:
        st.error(f"Failed to fetch diagnostics for {vin}")
        return None

def draw_health_gauge(score: float, grade: str):
    color = "#22c55e" if score >= 80 else "#eab308" if score >= 60 else "#ef4444"
    
    fig = go.Figure(go.Indicator(
        mode = "gauge+number+delta",
        value = score,
        domain = {'x': [0, 1], 'y': [0, 1]},
        title = {'text': "Vehicle Health Score", 'font': {'size': 24, 'color': '#E2E8F0'}},
        number = {'font': {'size': 48, 'color': color}, 'suffix': f" ({grade})"},
        gauge = {
            'axis': {'range': [0, 100], 'tickwidth': 1, 'tickcolor': "#334155"},
            'bar': {'color': color},
            'bgcolor': "#1E293B",
            'borderwidth': 2,
            'bordercolor': "#334155",
            'steps': [
                {'range': [0, 60], 'color': 'rgba(239, 68, 68, 0.2)'},
                {'range': [60, 80], 'color': 'rgba(234, 179, 8, 0.2)'},
                {'range': [80, 100], 'color': 'rgba(34, 197, 94, 0.2)'}],
        }
    ))
    fig.update_layout(paper_bgcolor="rgba(0,0,0,0)", font={'color': "#E2E8F0"}, height=300)
    return fig

# --- App Layout ---

st.markdown('<h1 class="main-header">BCScanTool Dashboard</h1>', unsafe_allow_html=True)
st.markdown("Phase 3: Real-Time Diagnostic Analytics")

# Sidebar
with st.sidebar:
    st.image("https://cdn-icons-png.flaticon.com/512/2857/2857850.png", width=100) # Placeholder icon
    st.title("Fleet Overview")
    
    vehicles = fetch_vehicles()
    if not vehicles:
        st.warning("No vehicles found in database.")
        st.stop()
        
    vehicle_options = {f"{v['year']} {v['make']} {v['model']} ({v['vin'][-6:]})": v['vin'] for v in vehicles}
    selected_vehicle_label = st.selectbox("Select Vehicle", list(vehicle_options.keys()))
    selected_vin = vehicle_options[selected_vehicle_label]
    
    if st.button("🔄 Refresh Data", use_container_width=True):
        st.cache_data.clear()
        st.rerun()

    st.markdown("---")
    st.subheader("Ingest New Scan")
    uploaded_file = st.file_uploader("Upload .x431 or .csv", type=['x431', 'csv'])
    if uploaded_file is not None:
        if st.button("Process & Upload", use_container_width=True):
            with st.spinner("Uploading and analyzing..."):
                try:
                    files = {"file": (uploaded_file.name, uploaded_file.getvalue(), uploaded_file.type)}
                    res = requests.post(f"{API_BASE_URL}/upload", files=files)
                    if res.status_code == 200:
                        st.success("File processed! ML pipelines are retraining in the background.")
                        st.cache_data.clear()
                    else:
                        st.error(f"Upload failed: {res.text}")
                except Exception as e:
                    st.error(f"Connection error: {e}")

# Main Content
diag_data = fetch_diagnostics(selected_vin)

if diag_data:
    tab1, tab2 = st.tabs(["📊 Overview & Analytics", "🤖 AI Diagnostic Assistant"])
    
    with tab1:
        # Top Metrics Row
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric(label="Active Issues", value=len(diag_data.get('issues', [])))
        with col2:
            st.metric(label="Predictive Alerts", value=len(diag_data.get('predictions', [])))
        with col3:
            st.metric(label="Total Scans", value=diag_data.get('scans_count', 0))
        with col4:
            st.metric(label="Status", value=diag_data.get('health_status', 'Unknown'))
            
        st.markdown("---")
        
        # Health Gauge & Quick Info
        lcol, rcol = st.columns([1, 2])
        with lcol:
            st.plotly_chart(draw_health_gauge(diag_data.get('health_score', 0), diag_data.get('health_grade', 'N/A')), use_container_width=True)
            
        with rcol:
            st.subheader("Predictive Maintenance Alerts")
            predictions = diag_data.get('predictions', [])
            if not predictions:
                st.success("No predictive alerts detected. Vehicle is operating normally.")
            else:
                for pred in predictions:
                    severity = pred.get('severity', 'INFO')
                    icon = "🔴" if severity == 'CRITICAL' else "⚠️" if severity == 'WARNING' else "ℹ️"
                    css_class = "critical-alert" if severity == 'CRITICAL' else "warning-alert" if severity == 'WARNING' else ""
                    
                    st.markdown(f"""
                    <div class="{css_class}">
                        <h4>{icon} {pred.get('issue')}</h4>
                        <p><b>Details:</b> {pred.get('details')}</p>
                        <p><b>Prediction:</b> {pred.get('prediction')} (Confidence: {pred.get('confidence')})</p>
                    </div>
                    """, unsafe_allow_html=True)
                    
        st.markdown("---")
        
        # Diagnostics Table
        st.subheader("Current Diagnostic Issues")
        issues = diag_data.get('issues', [])
        if issues:
            issues_df = pd.DataFrame(issues)
            if 'vin' in issues_df.columns:
                issues_df = issues_df.drop(columns=['vin'])
            
            # Style the dataframe
            def color_severity(val):
                color = '#ef4444' if val == 'CRITICAL' else '#f59e0b' if val == 'WARNING' else '#3b82f6'
                return f'color: {color}; font-weight: bold'
                
            st.dataframe(
                issues_df.style.map(color_severity, subset=['severity']),
                use_container_width=True,
                hide_index=True
            )
        else:
            st.success("No active diagnostic issues detected.")

    with tab2:
        st.subheader("Chat with your AI Mechanic")
        st.markdown("Ask questions about your vehicle's health, misfires, or recommended maintenance.")
        
        # Initialize chat history
        if "messages" not in st.session_state:
            st.session_state.messages = []
            # Add initial welcome message
            st.session_state.messages.append({"role": "assistant", "content": "Hello! I am your AI mechanic. I've reviewed your vehicle's diagnostic data. How can I help you today?"})

        # Display chat messages from history on app rerun
        for message in st.session_state.messages:
            with st.chat_message(message["role"]):
                st.markdown(message["content"])

        # React to user input
        if prompt := st.chat_input("Ask about P0300, repair costs, or misfires..."):
            # Display user message in chat message container
            st.chat_message("user").markdown(prompt)
            # Add user message to chat history
            st.session_state.messages.append({"role": "user", "content": prompt})

            with st.chat_message("assistant"):
                with st.spinner("Analyzing vehicle data..."):
                    try:
                        res = requests.post(f"{API_BASE_URL}/chat", json={
                            "message": prompt,
                            "vin": selected_vin,
                            "context_data": diag_data
                        })
                        res.raise_for_status()
                        response = res.json().get("response", "I'm sorry, I couldn't generate a response.")
                    except Exception as e:
                        response = f"Communication Error: {e}"
                    
                    st.markdown(response)
            
            # Add assistant response to chat history
            st.session_state.messages.append({"role": "assistant", "content": response})


