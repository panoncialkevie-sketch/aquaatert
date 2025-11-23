import streamlit as st
import pandas as pd
import numpy as np
from datetime import datetime
import os
from geopy.distance import geodesic
import folium
from streamlit_folium import st_folium

# -------------------------
# Optional external integrations
# -------------------------
TWILIO_SID = os.getenv("TWILIO_SID")
TWILIO_TOKEN = os.getenv("TWILIO_TOKEN")
TWILIO_FROM = os.getenv("TWILIO_FROM")
DEFAULT_ALERT_PHONE = os.getenv("DEFAULT_ALERT_PHONE")
FCM_SERVER_KEY = os.getenv("FCM_SERVER_KEY")
OPENWEATHER_API_KEY = os.getenv("OPENWEATHER_API_KEY")

# -------------------------
# Page Configuration
# -------------------------
st.set_page_config(page_title="🌊 AquaAlert", layout="wide")

# -------------------------
# Page Design / Styling with Background Image
# -------------------------
st.markdown(
    """
    <style>
    [data-testid="stAppViewContainer"] {
        background-image: url("https://images.unsplash.com/photo-1507525428034-b723cf961d3e");
        background-size: cover;
        background-position: center;
        background-repeat: no-repeat;
    }
    [data-testid="stSidebar"] {
        background-image: url("https://images.unsplash.com/photo-1506744038136-46273834b3fb");
        background-size: cover;
        background-position: center;
        background-repeat: no-repeat;
        background-color: rgba(255, 255, 255, 0.85);
        backdrop-filter: blur(6px);
    }
    [data-testid="stAppViewContainer"] > div:first-child {
        background-color: rgba(255, 255, 255, 0.85);
        border-radius: 12px;
        padding: 1rem;
        margin: 1rem;
        box-shadow: 0 4px 15px rgba(0, 0, 0, 0.1);
    }
    .stButton>button {
        background-color: #0073e6;
        color: white;
        border-radius: 10px;
        font-weight: 600;
        transition: 0.3s;
    }
    .stButton>button:hover {
        background-color: #005bb5;
        transform: scale(1.02);
    }
    div[data-testid="stSidebar"] .stButton>button {
        background-color: #cc0000;
        color: white;
        border-radius: 10px;
        font-weight: 600;
        transition: 0.3s;
    }
    div[data-testid="stSidebar"] .stButton>button:hover {
        background-color: #990000;
        transform: scale(1.03);
    }
    .sidebar-footer {
        position: fixed;
        bottom: 20px;
        left: 10px;
        width: 90%;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

# -------------------------
# File Paths
# -------------------------
REPORTS_FILE = "reports.csv"
ALERTS_FILE = "alerts.csv"
SENSORS_FILE = "sensors.csv"
SHELTERS_FILE = "shelters.csv"
USERS_FILE = "users.csv"

# -------------------------
# Ensure CSV files exist
# -------------------------
def ensure_files():
    if not os.path.exists(REPORTS_FILE):
        pd.DataFrame(columns=["timestamp", "name", "lat", "lon", "level", "notes", "report_id", "contact"]).to_csv(REPORTS_FILE, index=False)
    if not os.path.exists(ALERTS_FILE):
        pd.DataFrame(columns=["timestamp", "type", "severity", "message", "lat", "lon"]).to_csv(ALERTS_FILE, index=False)
    if not os.path.exists(SENSORS_FILE):
        sensors = [
            {"id": "S-01", "lat": 9.6113, "lon": 125.6345, "water_level": 10},
            {"id": "S-02", "lat": 9.6150, "lon": 125.6300, "water_level": 8},
            {"id": "S-03", "lat": 9.6060, "lon": 125.6400, "water_level": 5},
        ]
        pd.DataFrame(sensors).to_csv(SENSORS_FILE, index=False)
    if not os.path.exists(SHELTERS_FILE):
        shelters = [
            {"name": "Bacuag Municipal Gym", "lat": 9.6107, "lon": 125.6351, "capacity": 500},
            {"name": "Bacuag National High School", "lat": 9.6095, "lon": 125.6370, "capacity": 300},
            {"name": "Bacuag Barangay Hall", "lat": 9.6130, "lon": 125.6335, "capacity": 200},
            {"name": "Bacuag Evacuation Center", "lat": 9.6142, "lon": 125.6322, "capacity": 400},
            {"name": "Poblacion Covered Court", "lat": 9.6125, "lon": 125.6368, "capacity": 250},
        ]
        pd.DataFrame(shelters).to_csv(SHELTERS_FILE, index=False)
    if not os.path.exists(USERS_FILE):
        pd.DataFrame(columns=["username", "password", "role"]).to_csv(USERS_FILE, index=False)

ensure_files()

# -------------------------
# Authentication
# -------------------------
def load_users():
    return pd.read_csv(USERS_FILE)

def save_user(username, password, role):
    users = load_users()
    if username in users["username"].values:
        return False
    new_user = pd.DataFrame([[username, password, role]], columns=["username", "password", "role"])
    users = pd.concat([users, new_user], ignore_index=True)
    users.to_csv(USERS_FILE, index=False)
    return True

def authenticate(username, password):
    users = load_users()
    match = users[(users["username"] == username) & (users["password"] == password)]
    if not match.empty:
        return match.iloc[0]["role"]
    return None

# -------------------------
# Sidebar (Always Visible)
# -------------------------
st.sidebar.title("🌊 AquaAlert")
st.sidebar.markdown("**Bacuag Flood Awareness System**")
st.sidebar.markdown("---")

# Initialize session state
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
    st.session_state.role = None

# Sidebar User Info & Logout
if st.session_state.logged_in:
    st.sidebar.markdown(f"👤 **User:** {st.session_state.role}")
    st.sidebar.markdown('<div class="sidebar-footer">', unsafe_allow_html=True)
    if st.sidebar.button("🚪 Logout", key="logout_btn"):
        st.session_state.logged_in = False
        st.session_state.role = None
        st.success("You have been logged out.")
        st.rerun()
    st.sidebar.markdown("</div>", unsafe_allow_html=True)
else:
    st.sidebar.info("🔑 Please log in to access the dashboard.")

# -------------------------
# Login / Register UI
# -------------------------
if not st.session_state.logged_in:
    st.title("🔑 Login or 📝 Register")

    tab1, tab2 = st.tabs(["Login", "Register"])

    with tab1:
        username = st.text_input("Username", key="login_user")
        password = st.text_input("Password", type="password", key="login_pass")
        if st.button("Login"):
            role = authenticate(username, password)
            if role:
                st.session_state.logged_in = True
                st.session_state.role = role
                st.success(f"Welcome back, {username}! You are logged in as **{role}**.")
                st.rerun()
            else:
                st.error("Invalid username or password.")

    with tab2:
        new_username = st.text_input("Create Username", key="reg_user")
        new_password = st.text_input("Create Password", type="password", key="reg_pass")
        role = st.selectbox("Register as", ["Local Resident", "LGU Official"])
        if st.button("Register"):
            if save_user(new_username, new_password, role):
                st.success("✅ Account created successfully! You can now log in.")
            else:
                st.warning("⚠️ Username already exists. Please choose another.")
    st.stop()

# -------------------------
# After Login — Main Dashboard
# -------------------------
st.title(f"🌊 AquaAlert Dashboard — {st.session_state.role}")

simulate = st.sidebar.checkbox("Simulate IoT updates", value=True)
rain_manual = st.sidebar.slider("Simulated rainfall (mm last 6h)", 0, 300, 20)
risk_threshold = st.sidebar.slider("Alert threshold (risk score)", 0.0, 1.0, 0.6, step=0.05)

# -------------------------
# Load Data
# -------------------------
def load_reports(): return pd.read_csv(REPORTS_FILE)
def load_sensors(): return pd.read_csv(SENSORS_FILE)
def load_shelters(): return pd.read_csv(SHELTERS_FILE)
def load_alerts(): return pd.read_csv(ALERTS_FILE)
def append_report(r):
    df = load_reports()
    df = pd.concat([df, pd.DataFrame([r])], ignore_index=True)
    df.to_csv(REPORTS_FILE, index=False)
def append_alert(a):
    df = load_alerts()
    df = pd.concat([df, pd.DataFrame([a])], ignore_index=True)
    df.to_csv(ALERTS_FILE, index=False)
def save_sensors(df): df.to_csv(SENSORS_FILE, index=False)

# -------------------------
# Flood Risk Logic
# -------------------------
def sensor_trend_score(sensors_df):
    if "sensor_ewma" not in st.session_state:
        st.session_state.sensor_ewma = sensors_df["water_level"].mean()
    alpha = 0.3
    st.session_state.sensor_ewma = alpha * sensors_df["water_level"].mean() + (1 - alpha) * st.session_state.sensor_ewma
    current = sensors_df["water_level"].mean()
    trend = max(0.0, (current - st.session_state.sensor_ewma))
    return min(trend / 20.0, 1.0)

def predict_flood_risk(rain_mm_last_6h, avg_sensor_level, sensors_df):
    r = min(rain_mm_last_6h / 200.0, 1.0)
    s = min(avg_sensor_level / 100.0, 1.0)
    t = sensor_trend_score(sensors_df)
    score = 0.5 * r + 0.3 * s + 0.2 * t + 0.05 * r * s
    return min(score, 1.0)

# -------------------------
# Simulate Sensor Data
# -------------------------
sensors = load_sensors()
shelters = load_shelters()

if simulate:
    np.random.seed(42)
    noise = np.random.randint(-2, 4, size=len(sensors))
    sensors["water_level"] = sensors["water_level"].astype(float) + (rain_manual / 50.0) + noise
    sensors["water_level"] = sensors["water_level"].clip(0, 200)
    save_sensors(sensors)

avg_level = sensors["water_level"].mean()
risk_score = predict_flood_risk(rain_manual, avg_level, sensors)

# -------------------------
# Alerts
# -------------------------
if risk_score >= risk_threshold or (sensors["water_level"] >= 120).any():
    severity = "HIGH" if (sensors["water_level"] >= 150).any() or risk_score >= 0.9 else ("MEDIUM" if risk_score >= 0.75 else "LOW")
    msg = f"Flood risk: score {risk_score:.2f}. Avg sensor {avg_level:.1f} cm."
    append_alert({"timestamp": datetime.now().isoformat(), "type": "FloodRisk", "severity": severity, "message": msg, "lat": np.nan, "lon": np.nan})
    if severity == "HIGH":
        st.error(f"🚨 HIGH RISK: {msg}")
    elif severity == "MEDIUM":
        st.warning(f"⚠️ MEDIUM RISK: {msg}")
    else:
        st.info(f"ℹ️ LOW RISK: {msg}")
else:
    st.success(f"✅ No immediate flood alert (risk {risk_score:.2f})")

# -------------------------
# Map: Shelters, Sensors & Routes
# -------------------------
st.markdown("---")
st.subheader("🗺 Bacuag Safe Zones & Evacuation Routes")

m = folium.Map(location=[9.6113, 125.6345], zoom_start=14)

shelter_icon = folium.CustomIcon(
    icon_image="https://cdn-icons-png.flaticon.com/512/619/619034.png",
    icon_size=(35, 35)
)

for _, row in shelters.iterrows():
    folium.Marker(
        [row["lat"], row["lon"]],
        popup=f"<b>{row['name']}</b><br>Capacity: {row['capacity']}",
        tooltip=row["name"],
        icon=shelter_icon
    ).add_to(m)

for _, s in sensors.iterrows():
    folium.CircleMarker(
        location=[s["lat"], s["lon"]],
        radius=6,
        popup=f"Sensor {s['id']}<br>Water Level: {s['water_level']} cm",
        color="blue" if s["water_level"] < 50 else "orange" if s["water_level"] < 100 else "red",
        fill=True,
        fill_opacity=0.7
    ).add_to(m)

st_folium(m, width=900, height=500)

# -------------------------
# Community Reports
# -------------------------
st.markdown("---")
st.subheader("📝 Community Report")

with st.form("report_form", clear_on_submit=True):
    name = st.text_input("Your name (optional)")
    lat = st.number_input("Latitude", value=9.6113, format="%.6f")
    lon = st.number_input("Longitude", value=125.6345, format="%.6f")
    level = st.slider("Observed water level", 0, 200, 10)
    notes = st.text_area("Additional notes")
    submitted = st.form_submit_button("Submit Report")

    if submitted:
        report_id = f"R-{int(datetime.utcnow().timestamp())}"
        append_report({
            "timestamp": datetime.now().isoformat(),
            "name": name,
            "lat": lat,
            "lon": lon,
            "level": level,
            "notes": notes,
            "report_id": report_id,
            "contact": ""
        })
        st.success("✅ Report submitted successfully!")

# -------------------------
# Data Tables
# -------------------------
with st.expander("📊 Sensor Data"):
    st.dataframe(sensors)
with st.expander("📋 Community Reports"):
    st.dataframe(load_reports())
with st.expander("🚨 Alerts Log"):
    st.dataframe(load_alerts().sort_values("timestamp", ascending=False))

# -------------------------
# 👥 USER INFORMATION FORM
# -------------------------
USER_INFO_FILE = "user_info.csv"

if not os.path.exists(USER_INFO_FILE):
    pd.DataFrame(columns=["name","address","contact_number","barangay","family_members","timestamp"]).to_csv(USER_INFO_FILE, index=False)

def load_user_info(): return pd.read_csv(USER_INFO_FILE)
def save_user_info(data):
    df = load_user_info()
    df = pd.concat([df, pd.DataFrame([data])], ignore_index=True)
    df.to_csv(USER_INFO_FILE, index=False)

st.markdown("---")
st.subheader("👥 User Information Form")

with st.form("user_info_form", clear_on_submit=True):
    col1, col2 = st.columns(2)
    with col1:
        name = st.text_input("Full Name")
        address = st.text_input("Address")
        contact = st.text_input("Contact Number")
    with col2:
        barangay = st.text_input("Barangay")
        family_members = st.number_input("Number of Family Members", min_value=1, max_value=20, value=1)
    submitted = st.form_submit_button("Save Information")

    if submitted:
        save_user_info({
            "name": name,
            "address": address,
            "contact_number": contact,
            "barangay": barangay,
            "family_members": family_members,
            "timestamp": datetime.now().isoformat()
        })
        st.success("✅ Information saved successfully!")

with st.expander("📋 View All Registered User Information"):
    st.dataframe(load_user_info())

# -------------------------
# Barangay Images Gallery (Upload + Delete)
# -------------------------
st.markdown("---")
st.subheader("🏞️ Barangay Images")

# Folder and CSV setup
UPLOAD_FOLDER = "barangay_images"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

BARANGAY_IMG_FILE = "barangay_images.csv"
if not os.path.exists(BARANGAY_IMG_FILE):
    pd.DataFrame(columns=["barangay", "filename"]).to_csv(BARANGAY_IMG_FILE, index=False)

def load_barangay_images():
    return pd.read_csv(BARANGAY_IMG_FILE)

def save_barangay_image(barangay, file_name):
    df = load_barangay_images()
    existing = df[df["barangay"] == barangay]
    if not existing.empty:
        df.loc[df["barangay"] == barangay, "filename"] = file_name
    else:
        df = pd.concat([df, pd.DataFrame([[barangay, file_name]], columns=["barangay", "filename"])], ignore_index=True)
    df.to_csv(BARANGAY_IMG_FILE, index=False)

def delete_barangay_image(barangay):
    df = load_barangay_images()
    row = df[df["barangay"] == barangay]
    if not row.empty:
        file_path = row.iloc[0]["filename"]
        if os.path.exists(file_path):
            os.remove(file_path)
        df = df[df["barangay"] != barangay]
        df.to_csv(BARANGAY_IMG_FILE, index=False)
        st.success(f"🗑️ Deleted image for {barangay} successfully!")
    else:
        st.warning("⚠️ No image found for that barangay.")

# Barangay list
barangay_list = ["Poblacion", "Cabugao", "Cambuayon", "Campo", "Dugsangon", "Pautao", "Payapag", "Sto. Rosario", "Pongtud"]

# Upload form
st.markdown("### 📤 Upload Barangay Image")
with st.form("upload_barangay_form"):
    barangay = st.selectbox("Select Barangay", barangay_list)
    uploaded_file = st.file_uploader("Choose an image", type=["jpg", "jpeg", "png"])
    upload_submit = st.form_submit_button("Upload Image")

    if upload_submit and uploaded_file:
        file_path = os.path.join(UPLOAD_FOLDER, f"{barangay}_{uploaded_file.name}")
        with open(file_path, "wb") as f:
            f.write(uploaded_file.getbuffer())
        save_barangay_image(barangay, file_path)
        st.success(f"✅ Image for {barangay} uploaded successfully!")

# Display gallery
st.markdown("### 🖼️ Barangay Image Gallery")

barangay_df = load_barangay_images()
if barangay_df.empty:
    st.info("No images uploaded yet. Upload barangay images above.")
else:
    cols = st.columns(3)
    for i, row in barangay_df.iterrows():
        barangay = row["barangay"]
        file_path = row["filename"]

        with cols[i % 3]:
            if os.path.exists(file_path):
                st.image(file_path, caption=barangay, use_container_width=True)
                delete_btn = st.button(f"🗑️ Delete {barangay}", key=f"delete_{barangay}")
                if delete_btn:
                    delete_barangay_image(barangay)
                    st.rerun()
            else:
                st.warning(f"⚠️ Missing file for {barangay}")

# -------------------------
# Flood Preparedness Guide
# -------------------------
st.markdown("---")
st.subheader("📖 Flood Preparedness & Response Guide")
st.markdown(
    """
    **Before Floods**
    - Prepare emergency kits and documents.
    - Know your nearest evacuation center.
    - Monitor AquaAlert for flood warnings.

    **During Floods**
    - Move to higher ground.
    - Avoid floodwaters.
    - Follow LGU instructions.

    **After Floods**
    - Report damages.
    - Avoid contaminated water.
    - Seek medical help if needed.
    """
)
st.caption("🧠 Powered by AquaAlert — Bacuag Flood Awareness Platform")