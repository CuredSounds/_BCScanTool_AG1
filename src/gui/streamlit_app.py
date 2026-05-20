import streamlit as st
import uvicorn
import pandas as pd
import requests
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime
import sys
import socket
import time
from pathlib import Path
from src import config
from src.utils.pdf_generator import generate_health_report

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
HEADERS = {config.API_KEY_NAME: config.API_KEY}

@st.cache_data(ttl=60)
def fetch_vehicles():
    try:
        response = requests.get(f"{API_BASE_URL}/vehicles", headers=HEADERS)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        st.error(f"Failed to connect to API. Is the FastAPI server running? Error: {e}")
        return []

@st.cache_data(ttl=60)
def fetch_diagnostics(vin: str):
    try:
        response = requests.get(f"{API_BASE_URL}/vehicles/{vin}/diagnostics", headers=HEADERS)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        st.error(f"Failed to fetch diagnostics for {vin}")
        return None

@st.cache_data(ttl=60)
def fetch_topology(vin: str):
    try:
        response = requests.get(f"{API_BASE_URL}/vehicles/{vin}/topology", headers=HEADERS)
        response.raise_for_status()
        return response.json()
    except Exception:
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
                    res = requests.post(f"{API_BASE_URL}/upload", files=files, headers=HEADERS)
                    if res.status_code == 200:
                        st.success("File processed! ML pipelines are retraining in the background.")
                        st.cache_data.clear()
                    else:
                        st.error(f"Upload failed: {res.text}")
                except Exception as e:
                    st.error(f"Connection error: {e}")

    st.markdown("---")
    st.subheader("Vehicle Maintenance")
    repair_desc = st.text_input("Repair Description", placeholder="e.g., Replaced Cylinder 1 Spark Plug")
    if st.button("Log Repair & Reset Baseline", use_container_width=True):
        if repair_desc:
            with st.spinner("Logging repair..."):
                try:
                    res = requests.post(f"{API_BASE_URL}/repairs", json={
                        "vin": selected_vin,
                        "description": repair_desc
                    }, headers=HEADERS)
                    if res.status_code == 200:
                        st.success("Repair logged! Baseline reset.")
                        st.cache_data.clear()
                        st.rerun()
                    else:
                        st.error(f"Failed to log repair: {res.text}")
                except Exception as e:
                    st.error(f"Connection error: {e}")
        else:
            st.warning("Please enter a repair description.")

    if st.button("✅ Confirm Current State as Healthy Baseline", use_container_width=True):
        with st.spinner("Confirming baseline..."):
            try:
                res = requests.post(f"{API_BASE_URL}/vehicles/baseline", json={
                    "vin": selected_vin
                }, headers=HEADERS)
                if res.status_code == 200:
                    st.success("Baseline confirmed! Predictive models will use this as a reference.")
                    st.cache_data.clear()
                else:
                    st.error(f"Failed to confirm baseline: {res.text}")
            except Exception as e:
                st.error(f"Connection error: {e}")

    st.markdown("---")
    st.subheader("☁️ Cloud Backup")
    st.markdown("Sync diagnostic DB to Google Drive.")
    if st.button("Force Cloud Sync", use_container_width=True):
        with st.spinner("Compressing and uploading..."):
            try:
                res = requests.post(f"{API_BASE_URL}/cloud_sync", headers=HEADERS)
                if res.status_code == 200:
                    st.success("Backup successfully synced to Google Drive!")
                else:
                    st.error(f"Sync failed: {res.json().get('detail', res.text)}")
            except Exception as e:
                st.error(f"Connection error: {e}")

# Main Content
diag_data = fetch_diagnostics(selected_vin)

if diag_data:
    # Add Export PDF button right above the tabs
    col_title, col_btn = st.columns([3, 1])
    with col_btn:
        with st.spinner("Generating PDF..."):
            pdf_bytes = generate_health_report(diag_data)
            st.download_button(
                label="🖨️ Export PDF Report",
                data=pdf_bytes,
                file_name=f"HealthReport_{selected_vin}_{datetime.now().strftime('%Y%m%d')}.pdf",
                mime="application/pdf",
                use_container_width=True
            )
            
    tab1, tab_live, tab2, tab3 = st.tabs(["📊 Overview & Analytics", "🔌 Live Cab Mode", "🌐 Vehicle Topology", "🤖 AI Diagnostic Assistant"])
    
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

    with tab_live:
        st.markdown("## 🔌 Live Telemetry & Cab Mode Diagnostics")
        st.markdown("*Optimized for high-contrast viewing on laptop screens inside the truck cab. Connects directly to local ELM327 Wi-Fi streams.*")
        
        # Settings in a clean row
        set_col1, set_col2, set_col3 = st.columns([2, 1, 1])
        with set_col1:
            stream_ip = st.text_input("OBD2 Dongle / Server IP", "127.0.0.1")
        with set_col2:
            stream_port = st.number_input("TCP Port", value=35000)
        with set_col3:
            st.markdown("<br>", unsafe_allow_html=True)
            stream_active = st.toggle("🔌 Connect Live Stream", value=False)
            
        status_container = st.empty()
        
        if stream_active:
            status_container.info("Establishing connection to OBD2 stream dongle...")
            
            try:
                # Open Socket
                s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                s.settimeout(2.0)
                s.connect((stream_ip, int(stream_port)))
                status_container.success(f"✅ CONNECTED! Streaming live 2Hz Tacoma telemetry from {stream_ip}:{stream_port}")
                
                # Setup placeholders for massive high-contrast metrics
                st.markdown("### 🏎️ Core Physics & Mechanical Drag Indicators")
                metric_cols = st.columns(3)
                with metric_cols[0]:
                    load_placeholder = st.empty()
                with metric_cols[1]:
                    stft_placeholder = st.empty()
                with metric_cols[2]:
                    ltft_placeholder = st.empty()
                    
                st.markdown("### 📈 Transient Rate-of-Change Physics (Derived Deltas)")
                delta_cols = st.columns(3)
                with delta_cols[0]:
                    d_maf_placeholder = st.empty()
                with delta_cols[1]:
                    d_rpm_placeholder = st.empty()
                with delta_cols[2]:
                    d_load_placeholder = st.empty()
                    
                st.markdown("### 📊 Time-Series Diagnostics Waveform")
                chart_placeholder = st.empty()
                
                # Stream buffer & lists
                buffer = ""
                headers = []
                data_points = []
                
                while stream_active:
                    try:
                        data = s.recv(4096).decode("utf-8")
                        if not data:
                            status_container.error("🔌 Stream connection closed by the dongle/server.")
                            break
                        buffer += data
                        
                        while "\n" in buffer:
                            line, buffer = buffer.split("\n", 1)
                            line = line.strip()
                            if not line:
                                continue
                            
                            # Parse CSV columns
                            parts = line.split(",")
                            if not headers:
                                headers = [h.strip() for h in parts]
                                continue
                            
                            # Handle potential column mismatches
                            if len(parts) != len(headers):
                                continue
                                
                            row_dict = dict(zip(headers, parts))
                            
                            # Helper to extract value safely by matching column name keywords
                            def get_sensor_val(d, kw, default=0.0):
                                for k, v in d.items():
                                    if kw.lower() in k.lower():
                                        try:
                                            return float(v)
                                        except:
                                            pass
                                return default
                                
                            load_val = get_sensor_val(row_dict, "Calculate Load")
                            stft_val = get_sensor_val(row_dict, "Short FT (Bank1")
                            ltft_val = get_sensor_val(row_dict, "Long FT (Bank1")
                            
                            # Deltas from derived columns (from Task 1)
                            d_maf = get_sensor_val(row_dict, "Delta_MAF", 0.0)
                            d_rpm = get_sensor_val(row_dict, "Delta_RPM", 0.0)
                            d_load = get_sensor_val(row_dict, "Delta_Calculate_Load", 0.0)
                            
                            # Fallback delta logic if not streamed
                            if len(data_points) > 0:
                                prev = data_points[-1]
                                if d_maf == 0.0:
                                    maf_now = get_sensor_val(row_dict, "MAF")
                                    maf_prev = get_sensor_val(prev, "MAF")
                                    d_maf = maf_now - maf_prev
                                if d_rpm == 0.0:
                                    rpm_now = get_sensor_val(row_dict, "Engine Speed")
                                    rpm_prev = get_sensor_val(prev, "Engine Speed")
                                    d_rpm = rpm_now - rpm_prev
                                if d_load == 0.0:
                                    d_load = load_val - prev.get("Calculate Load [%]", load_val)
                            
                            # Save data point for streaming chart
                            point = {
                                "Timestamp": datetime.now(),
                                "Calculate Load [%]": load_val,
                                "Short FT (Bank1) [%]": stft_val,
                                "Long FT (Bank1) [%]": ltft_val,
                                "Delta_MAF": d_maf,
                                "Delta_RPM": d_rpm,
                                "Delta_Calculate_Load": d_load,
                                "MAF": get_sensor_val(row_dict, "MAF"),
                                "Engine Speed": get_sensor_val(row_dict, "Engine Speed")
                            }
                            data_points.append(point)
                            if len(data_points) > 60:
                                data_points.pop(0)
                                
                            # 1. High-Contrast Premium Gauges (optimized for cab viewing)
                            load_color = "#ef4444" if load_val > 80.0 else "#eab308" if load_val > 50.0 else "#22c55e"
                            stft_color = "#ef4444" if abs(stft_val) > 15.0 else "#eab308" if abs(stft_val) > 8.0 else "#22c55e"
                            ltft_color = "#ef4444" if abs(ltft_val) > 10.0 else "#eab308" if abs(ltft_val) > 5.0 else "#22c55e"
                            
                            load_placeholder.markdown(f"""
                            <div style="background-color:#1E293B; border-top: 10px solid {load_color}; padding:30px 10px; border-radius:15px; text-align:center; box-shadow: 0 10px 15px -3px rgba(0, 0, 0, 0.3);">
                                <span style="font-size:20px; font-weight:800; color:#94A3B8; text-transform:uppercase; letter-spacing:1px;">Engine Load</span>
                                <h1 style="font-size:84px; margin:15px 0; color:#F8FAFC; font-weight:900; line-height:1;">{load_val:.1f}%</h1>
                            </div>
                            """, unsafe_allow_html=True)
                            
                            stft_placeholder.markdown(f"""
                            <div style="background-color:#1E293B; border-top: 10px solid {stft_color}; padding:30px 10px; border-radius:15px; text-align:center; box-shadow: 0 10px 15px -3px rgba(0, 0, 0, 0.3);">
                                <span style="font-size:20px; font-weight:800; color:#94A3B8; text-transform:uppercase; letter-spacing:1px;">Short FT B1</span>
                                <h1 style="font-size:84px; margin:15px 0; color:#F8FAFC; font-weight:900; line-height:1;">{stft_val:+.1f}%</h1>
                            </div>
                            """, unsafe_allow_html=True)
                            
                            ltft_placeholder.markdown(f"""
                            <div style="background-color:#1E293B; border-top: 10px solid {ltft_color}; padding:30px 10px; border-radius:15px; text-align:center; box-shadow: 0 10px 15px -3px rgba(0, 0, 0, 0.3);">
                                <span style="font-size:20px; font-weight:800; color:#94A3B8; text-transform:uppercase; letter-spacing:1px;">Long FT B1</span>
                                <h1 style="font-size:84px; margin:15px 0; color:#F8FAFC; font-weight:900; line-height:1;">{ltft_val:+.1f}%</h1>
                            </div>
                            """, unsafe_allow_html=True)
                            
                            # 2. Update rate-of-change physics indicators
                            d_maf_placeholder.metric(label="Δ MAF (gm/s/s)", value=f"{d_maf:+.2f}")
                            d_rpm_placeholder.metric(label="Δ RPM (rpm/s)", value=f"{d_rpm:+.1f}")
                            d_load_placeholder.metric(label="Δ Load (%/s)", value=f"{d_load:+.2f}")
                            
                            # 3. Update Chart
                            chart_df = pd.DataFrame(data_points)
                            fig = px.line(
                                chart_df, 
                                x="Timestamp", 
                                y=["Calculate Load [%]", "Short FT (Bank1) [%]", "Long FT (Bank1) [%]"],
                                title="Real-Time Telemetry Trend Tracker",
                                labels={"value": "Value (%)", "variable": "Sensor Parameter"}
                            )
                            fig.update_layout(
                                paper_bgcolor="rgba(0,0,0,0)", 
                                plot_bgcolor="#0F172A", 
                                font={'color': "#F1F5F9", 'size': 14},
                                height=450,
                                margin=dict(l=40, r=40, t=50, b=40),
                                legend=dict(orientation="h", y=1.1, x=0.5, xanchor="center")
                            )
                            fig.update_xaxes(showgrid=True, gridcolor="#334155")
                            fig.update_yaxes(showgrid=True, gridcolor="#334155")
                            chart_placeholder.plotly_chart(fig, use_container_width=True)
                            
                    except socket.timeout:
                        continue
                    except Exception as e:
                        status_container.error(f"Stream error: {e}")
                        break
            except Exception as e:
                status_container.error(f"❌ Connection failed: {e}. Please ensure the Mock ELM327 server is running on port {stream_port} or check your network settings.")
                st.info("💡 **To launch the Mock Server:** Open a new terminal and run: `python3 scripts/mock_elm327.py` or launch the master control panel.")
        else:
            status_container.warning("🔌 Live stream is currently offline. Toggle 'Connect Live Stream' to begin.")
            
            # Display helpful instructions on how to use live stream mode
            st.markdown("""
            ### 📖 How to use Live Cab Mode
            1. **Launch the Mock Server** in a separate terminal:
               ```bash
               python3 scripts/mock_elm327.py
               ```
               *This reads a Toyota Tacoma baseline CSV and streams it sequentially at a 2Hz frequency, seamlessly looping.*
            2. Toggle **Connect Live Stream** above.
            3. Sit back and watch the metrics update in real-time with large, high-contrast, high-visibility styling suitable for live in-truck diagnostics.
            """)

    with tab2:
        st.subheader("Vehicle Module Network Topology")
        st.markdown("Visual representation of communication status and health for all onboard modules.")
        
        topology_data = fetch_topology(selected_vin)
        if topology_data:
            if not topology_data.get('has_full_scan'):
                st.info("⚠️ Full System Scan (AllSystemDTC) not found for this vehicle. Showing estimated module status based on available Engine/Transmission data.")
            else:
                st.success("✅ Full System Scan Detected! Displaying all mapped modules.")
            
            # Draw a grid of modules
            modules = topology_data.get('modules', [])
            cols = st.columns(3)
            for i, mod in enumerate(modules):
                with cols[i % 3]:
                    status = mod.get('status', 'UNKNOWN')
                    color = "#22c55e" if status == "OK" else "#ef4444" if status == "FAULT" else "#eab308" if status == "WARNING" else "#64748b"
                    icon = "✅" if status == "OK" else "❌" if status == "FAULT" else "⚠️" if status == "WARNING" else "❓"
                    
                    st.markdown(f"""
                    <div style="background-color: #1E293B; padding: 20px; border-radius: 10px; border-top: 5px solid {color}; margin-bottom: 20px; text-align: center; box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);">
                        <h2 style="margin:0; color: #E2E8F0; font-size: 28px;">{mod.get('id')}</h2>
                        <p style="color: #94A3B8; font-size: 12px; margin-bottom: 10px;">{mod.get('name')}</p>
                        <div style="font-size: 32px; margin: 10px 0;">{icon}</div>
                        <p style="margin-top: 5px; font-weight: 800; color: {color}; letter-spacing: 1px;">{status}</p>
                        <p style="font-size: 12px; color: #94A3B8; margin: 0;">Active Codes: {mod.get('codes', 0)}</p>
                    </div>
                    """, unsafe_allow_html=True)
        else:
            st.error("Failed to load topology data. Check API connection.")

    with tab3:
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
                        }, headers=HEADERS)
                        res.raise_for_status()
                        response = res.json().get("response", "I'm sorry, I couldn't generate a response.")
                    except Exception as e:
                        response = f"Communication Error: {e}"
                    
                    st.markdown(response)
            
            # Add assistant response to chat history
            st.session_state.messages.append({"role": "assistant", "content": response})


