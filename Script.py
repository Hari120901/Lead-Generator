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
st.title("📊 Business Leads with Real-Time Ad Insights")

# Sidebar for API Keys
with st.sidebar:
    st.header("API Configuration")
    google_key = st.text_input("Google Places API Key", value=st.secrets.get("GOOGLE_API_KEY", ""), type="password")
    meta_token = st.text_input("Meta Ad Library Access Token", type="password", help="Get this from developers.facebook.com")

headers = {"User-Agent": "Mozilla/5.0"}

# ------------------------------
# GOOGLE PLACES SEARCH
# ------------------------------
def get_places(query, api_key, max_res):
    url = f"https://maps.googleapis.com/maps/api/place/textsearch/json?query={urllib.parse.quote(query)}&key={api_key}"
    response = requests.get(url).json()
    return response.get("results", [])[:max_res]

def get_details(place_id, api_key):
    url = f"https://maps.googleapis.com/maps/api/place/details/json?place_id={place_id}&fields=formatted_phone_number,website,rating,user_ratings_total&key={api_key}"
    data = requests.get(url).json().get("result", {})
    return (
        data.get("formatted_phone_number", "N/A"),
        data.get("website"),
        data.get("rating", "N/A"),
        data.get("user_ratings_total", "N/A")
    )

# ------------------------------
# META AD LIBRARY INTEGRATION (NEW)
# ------------------------------
def check_meta_ads(business_name, token):
    """Queries Meta Ad Library API for active ads in India"""
    if not token:
        return "Token Missing"
    
    url = "https://graph.facebook.com/v19.0/ads_archive"
    params = {
        'access_token': token,
        'search_terms': business_name,
        'ad_active_status': 'ACTIVE',
        'ad_reached_countries': "['IN']",
        'fields': 'id'
    }
    try:
        response = requests.get(url, params=params, timeout=5).json()
        count = len(response.get('data', []))
        return count if count > 0 else 0
    except:
        return 0

# ------------------------------
# EXISTING SCRAPING FUNCTIONS
# ------------------------------
def extract_emails(website):
    if not website: return "N/A"
    try:
        html = requests.get(website, headers=headers, timeout=5).text
        emails = re.findall(r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}", html)
        return ", ".join(set(emails)) if emails else "Not Found"
    except: return "Error"

def check_google_ads(name, location):
    try:
        query = f"{name} {location}"
        url = f"https://www.google.com/search?q={urllib.parse.quote(query)}"
        html = requests.get(url, headers=headers, timeout=5).text.lower()
        ad_signals = ["sponsored", "ad ·", "ads by google", "googleadservices"]
        return any(signal in html for signal in ad_signals)
    except: return False

# ------------------------------
# REWRITTEN MULTI-SIGNAL LOGIC
# ------------------------------
def get_ad_activity_status(google_ads, meta_ads_count):
    if isinstance(meta_ads_count, int) and meta_ads_count > 0:
        return f"🟢 Active on Meta ({meta_ads_count} Ads)"
    elif google_ads:
        return "🔵 Active on Google"
    elif meta_ads_count == 0:
        return "⚪ No Live Ads (Checked Meta/Google)"
    else:
        return "🟡 Verification Pending"

# ------------------------------
# MAIN INTERFACE
# ------------------------------
location = st.text_input("📍 Location", placeholder="e.g. Mumbai")
category = st.text_input("🏢 Category", placeholder="e.g. Jewellery Store")
max_results = st.selectbox("Max Results", [10, 20, 50])

if st.button("Generate Leads with Meta & Google Insights"):
    if not google_key:
        st.error("Please provide a Google API Key in the sidebar.")
        st.stop()

    query = f"{category} in {location}, India"
    with st.spinner("Analyzing Market Activity..."):
        businesses = get_places(query, google_key, max_results)
        results = []
        
        for biz in businesses:
            name = biz.get("name")
            address = biz.get("formatted_address")
            phone, website, rating, reviews = get_details(biz.get("place_id"), google_key)
            
            # Multi-Platform Check
            google_ads_flag = check_google_ads(name, location)
            meta_ads_count = check_meta_ads(name, meta_token)
            
            status = get_ad_activity_status(google_ads_flag, meta_ads_count)
            emails = extract_emails(website)

            results.append([name, address, phone, website, emails, status, rating, reviews])

        df = pd.DataFrame(results, columns=["Business Name", "Address", "Phone", "Website", "Emails", "Ad Status", "Rating", "Reviews"])
        st.success("Intelligence Report Ready")
        st.dataframe(df)

        # Download
        output = BytesIO()
        df.to_excel(output, index=False, engine="openpyxl")
        st.download_button("⬇️ Export to Excel", data=output.getvalue(), file_name="meta_google_leads.xlsx")
