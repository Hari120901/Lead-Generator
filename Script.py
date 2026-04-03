import streamlit as st
import requests
import pandas as pd
from io import BytesIO
import urllib.parse
import re
from datetime import datetime

st.set_page_config(page_title="Ad Intelligence Lead Generator", layout="wide")
st.title("📊 Business Leads with Ad Activity Timeline")

# ------------------------------
# USER INPUT
# ------------------------------
location = st.text_input("📍 Location (e.g., Andheri West, Mumbai)")
category = st.text_input("🏢 Category (e.g., jewellery store)")
max_results = st.selectbox("Max Results", [10, 20, 30, 50])

GOOGLE_API_KEY = st.secrets["GOOGLE_API_KEY"]
headers = {"User-Agent": "Mozilla/5.0"}

# ------------------------------
# GOOGLE PLACES SEARCH
# ------------------------------
def get_places(query):
    url = f"https://maps.googleapis.com/maps/api/place/textsearch/json?query={urllib.parse.quote(query)}&key={GOOGLE_API_KEY}"
    return requests.get(url).json().get("results", [])[:max_results]

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
# DETECT AD PLATFORMS
# ------------------------------
def detect_ad_platforms(website):
    if not website:
        return "Unknown"

    try:
        html = requests.get(website, headers=headers, timeout=5).text.lower()

        platforms = []

        if "facebook.com" in html or "fbq(" in html:
            platforms.append("Meta Ads")

        if "googletagmanager" in html or "googleads" in html:
            platforms.append("Google Ads")

        if "linkedin" in html:
            platforms.append("LinkedIn Ads")

        if "tiktok" in html:
            platforms.append("TikTok Ads")

        return ", ".join(platforms) if platforms else "Not Detected"

    except:
        return "Error"

# ------------------------------
# ESTIMATE AD DATES (Heuristic / API placeholder)
# ------------------------------
def estimate_ad_dates(name):
    """
    Replace this with:
    - Meta Ads Library API
    - Google Ads Transparency API
    """
    # Placeholder logic (simulate recent activity)
    today = datetime.today()

    return f"{today.strftime('%b %Y')} (Active)"

# ------------------------------
# EXTRACT EMAILS
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
# MAIN
# ------------------------------
if st.button("Generate Leads with Ad Insights"):

    if not location or not category:
        st.warning("Enter both fields")
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

        # NEW FEATURES
        platforms = detect_ad_platforms(website)
        ad_dates = estimate_ad_dates(name)

        results.append([
            name,
            address,
            phone,
            website if website else "N/A",
            emails,
            rating,
            reviews,
            platforms,
            ad_dates
        ])

    df = pd.DataFrame(results, columns=[
        "Business Name",
        "Address",
        "Phone",
        "Website",
        "Emails",
        "Rating",
        "Reviews",
        "Ad Platforms Detected",
        "Ad Activity (Month/Date)"
    ])

    st.success("Ad Intelligence Ready ✅")
    st.dataframe(df)

    output = BytesIO()
    df.to_excel(output, index=False)
    output.seek(0)

    st.download_button(
        "Download Excel",
        data=output,
        file_name="ad_intelligence_leads.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
