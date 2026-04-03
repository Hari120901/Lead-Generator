import streamlit as st
import requests
import pandas as pd
from io import BytesIO
import urllib.parse
import re

# ------------------------------
# CONFIG
# ------------------------------
st.set_page_config(page_title="Ad Intelligence Lead Generator", layout="wide")
st.title("📊 Business Leads with Real Ad Activity Status")

GOOGLE_API_KEY = st.secrets["GOOGLE_API_KEY"]
headers = {"User-Agent": "Mozilla/5.0"}

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

        if "sponsored" in html or "ad ·" in html:
            return True
        return False
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
# FINAL AD STATUS (CORRECT LOGIC)
# ------------------------------
def get_ad_activity_status(google_ads, platforms, website):

    # Active NOW (strong signal)
    if google_ads:
        return "🟢 Active Now"

    # Past advertiser (has tracking but no live ads)
    elif len(platforms) > 0:
        return "🟠 Past Advertiser (Last active unknown)"

    # Website only
    elif website:
        return "🟡 No Recent Ads (Website only)"

    # No signals
    else:
        return "🔴 No Ads Detected"

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

        # Ad Intelligence
        platforms = detect_ad_platforms(website)
        google_ads_flag = check_google_ads(name, location)

        ad_status = get_ad_activity_status(
            google_ads_flag,
            platforms,
            website
        )

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

    # CSV (always works)
    csv = df.to_csv(index=False).encode('utf-8')
    st.download_button(
        "⬇️ Download CSV",
        data=csv,
        file_name="ad_intelligence_leads.csv",
        mime="text/csv"
    )

    # Excel (safe fallback)
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
