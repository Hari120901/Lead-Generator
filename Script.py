import streamlit as st
import requests
import pandas as pd
from io import BytesIO
import urllib.parse
import re
import os
import json
from datetime import datetime, timedelta

# ------------------------------
# CONFIG
# ------------------------------
st.set_page_config(page_title="Business Leads with Ad Activity", layout="wide")
st.title("📊 Business Leads with Ad Status (Free Version)")

GOOGLE_API_KEY = st.secrets["GOOGLE_API_KEY"]
headers = {"User-Agent": "Mozilla/5.0"}

# File to store last seen active dates
LAST_ACTIVE_FILE = "last_active.json"
if os.path.exists(LAST_ACTIVE_FILE):
    with open(LAST_ACTIVE_FILE, "r") as f:
        last_active_data = json.load(f)
else:
    last_active_data = {}

# ------------------------------
# USER INPUT
# ------------------------------
location = st.text_input("📍 Location (e.g., Andheri West, Mumbai)")
category = st.text_input("🏢 Category (e.g., jewellery store)")
max_results = st.selectbox("Max Results", [10, 20, 30, 50])

# ------------------------------
# GOOGLE PLACES SEARCH
# ------------------------------
def get_places(query):
    url = f"https://maps.googleapis.com/maps/api/place/textsearch/json?query={urllib.parse.quote(query)}&key={GOOGLE_API_KEY}"
    response = requests.get(url).json()
    return response.get("results", [])[:max_results]

# ------------------------------
# PLACE DETAILS
# ------------------------------
def get_details(place_id):
    url = f"https://maps.googleapis.com/maps/api/place/details/json?place_id={place_id}&fields=formatted_phone_number,website,rating,user_ratings_total&key={GOOGLE_API_KEY}"
    data = requests.get(url).json().get("result", {})
    return (
        data.get("formatted_phone_number", "N/A"),
        data.get("website"),
        data.get("rating", "N/A"),
        data.get("user_ratings_total", "N/A")
    )

# ------------------------------
# EMAIL EXTRACTION
# ------------------------------
def extract_emails(website):
    if not website:
        return "N/A"
    try:
        html = requests.get(website, headers=headers, timeout=5).text
        emails = re.findall(r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}", html)
        return ", ".join(set(emails)) if emails else "Not Found"
    except:
        return "Error"

# ------------------------------
# GOOGLE ADS DETECTION (LIVE SIGNAL)
# ------------------------------
def check_google_ads(name, location):
    try:
        query = f"{name} {location}"
        url = f"https://www.google.com/search?q={urllib.parse.quote(query)}"
        html = requests.get(url, headers=headers, timeout=5).text.lower()
        ad_signals = ["sponsored", "ad ·", "ads by google", "googleadservices", "/aclk?"]
        return any(signal in html for signal in ad_signals)
    except:
        return False

# ------------------------------
# DETECT AD PLATFORMS (PAST SIGNAL)
# ------------------------------
def detect_ad_platforms(website):
    if not website:
        return []
    try:
        html = requests.get(website, headers=headers, timeout=5).text.lower()
        platforms = []
        if "fbq(" in html or "facebook.com" in html:
            platforms.append("Meta")
        if "googletagmanager" in html or "googleads" in html:
            platforms.append("Google")
        if "linkedin" in html:
            platforms.append("LinkedIn")
        if "tiktok" in html:
            platforms.append("TikTok")
        return platforms
    except:
        return []

# ------------------------------
# BRAND PRESENCE (SUPPORT SIGNAL)
# ------------------------------
def check_brand_presence(name, location):
    try:
        query = f"{name} {location}"
        url = f"https://www.google.com/search?q={urllib.parse.quote(query)}"
        html = requests.get(url, headers=headers, timeout=5).text.lower()
        return name.lower() in html
    except:
        return False

# ------------------------------
# DETERMINE AD STATUS WITH DURATION
# ------------------------------
def get_ad_activity_status(name, google_ads, platforms, website, brand_presence):
    today = datetime.today()
    last_seen_str = last_active_data.get(name)
    last_seen_date = datetime.strptime(last_seen_str, "%Y-%m-%d") if last_seen_str else None

    # Update last active if Google Ads detected now
    if google_ads:
        last_active_data[name] = today.strftime("%Y-%m-%d")
        return "🟢 Active Now"

    # Check last seen active
    if last_seen_date:
        days_since_active = (today - last_seen_date).days
        if days_since_active <= 7:
            return "🟢 Active Now"
        else:
            return f"🟠 Past Advertiser (Last active: {last_seen_date.strftime('%b %Y')})"

    # Likely Active based on signals
    if brand_presence and len(platforms) > 0:
        return "🟡 Likely Active"

    # Website only
    if website:
        return "⚪ No Signals (Website only)"

    return "🔴 No Ads"

# ------------------------------
# MAIN PROCESS
# ------------------------------
if st.button("Generate Leads with Ad Insights"):

    if not location or not category:
        st.warning("Please enter both Location and Category")
        st.stop()

    query = f"{category} in {location}, India"
    with st.spinner("Fetching businesses..."):
        businesses = get_places(query)

    results = []

    for biz in businesses:
        name = biz.get("name")
        address = biz.get("formatted_address")
        place_id = biz.get("place_id")

        phone, website, rating, reviews = get_details(place_id)
        emails = extract_emails(website)
        platforms = detect_ad_platforms(website)
        google_ads_flag = check_google_ads(name, location)
        brand_presence = check_brand_presence(name, location)
        ad_status = get_ad_activity_status(name, google_ads_flag, platforms, website, brand_presence)

        results.append([
            name,
            address,
            phone,
            website if website else "N/A",
            emails,
            rating,
            reviews,
            ", ".join(platforms) if platforms else "None",
            "Yes" if google_ads_flag else "No",
            ad_status
        ])

    # Save last active data to file
    with open(LAST_ACTIVE_FILE, "w") as f:
        json.dump(last_active_data, f)

    # ------------------------------
    # DATAFRAME
    # ------------------------------
    df = pd.DataFrame(results, columns=[
        "Business Name",
        "Address",
        "Phone",
        "Website",
        "Emails",
        "Rating",
        "Reviews",
        "Ad Platforms Detected",
        "Google Ads Running",
        "Ad Activity Status"
    ])

    st.success("Ad Intelligence Generated ✅")
    st.dataframe(df)

    # ------------------------------
    # DOWNLOAD OPTIONS
    # ------------------------------
    csv = df.to_csv(index=False).encode('utf-8')
    st.download_button(
        "⬇️ Download CSV",
        data=csv,
        file_name="ad_intelligence_leads.csv",
        mime="text/csv"
    )

    try:
        output = BytesIO()
        df.to_excel(output, index=False, engine="openpyxl")
        output.seek(0)
        st.download_button(
            "⬇️ Download Excel",
            data=output,
            file_name="ad_intelligence_leads.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
    except:
        st.warning("Excel export requires openpyxl. CSV is available.")
