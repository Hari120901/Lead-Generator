import streamlit as st
import requests
import pandas as pd
from io import BytesIO
import urllib.parse
import re

# ------------------------------
# CONFIG
# ------------------------------
st.set_page_config(page_title="Ad Intelligence Lead Gen Pro", layout="wide")
st.title("📊 Lead Generator: Google + Meta Ad Insights")

with st.sidebar:
    st.header("API Configuration")
    google_key = st.text_input("Google Places API Key", value=st.secrets.get("GOOGLE_API_KEY", ""), type="password")
    meta_token = st.text_input("Meta Ad Library Access Token", type="password", help="Required for live ad dates and counts.")

headers = {"User-Agent": "Mozilla/5.0"}

# ------------------------------
# API & SCRAPING LOGIC
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

def check_meta_ads_detailed(business_name, token):
    """Queries Meta API for count and earliest 'Started Running' date"""
    if not token:
        return 0, "Token Missing"
    
    url = "https://graph.facebook.com/v19.0/ads_archive"
    params = {
        'access_token': token,
        'search_terms': business_name,
        'ad_active_status': 'ACTIVE',
        'ad_reached_countries': "['IN']",
        'fields': 'id,ad_delivery_start_time',
        'limit': 500 # Adjust based on expected volume
    }
    try:
        response = requests.get(url, params=params, timeout=10).json()
        ads = response.get('data', [])
        if not ads:
            return 0, "No Active Ads"
        
        # Sort to find the oldest running ad (the 'Active Since' date)
        start_dates = [a.get('ad_delivery_start_time') for a in ads if a.get('ad_delivery_start_time')]
        if start_dates:
            oldest_ad = min(start_dates).split('T')[0]
            return len(ads), oldest_ad
        return len(ads), "Date Unknown"
    except Exception:
        return 0, "API Error"

def check_google_ads(name, location):
    try:
        query = f"{name} {location}"
        url = f"https://www.google.com/search?q={urllib.parse.quote(query)}"
        html = requests.get(url, headers=headers, timeout=5).text.lower()
        ad_signals = ["sponsored", "ad ·", "ads by google", "googleadservices"]
        return any(signal in html for signal in ad_signals)
    except:
        return False

def extract_emails(website):
    if not website or website == "N/A": return "N/A"
    try:
        html = requests.get(website, headers=headers, timeout=5).text
        emails = re.findall(r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}", html)
        return ", ".join(set(emails)) if emails else "Not Found"
    except:
        return "Error"

# ------------------------------
# MAIN INTERFACE
# ------------------------------

location = st.text_input("📍 Search Location", value="Mumbai")
category = st.text_input("🏢 Business Category", value="Jewellery Store")
max_results = st.slider("Number of Leads", 5, 50, 10)

if st.button("🔍 Generate High-Intent Leads"):
    if not google_key:
        st.error("Please enter a Google API Key in the sidebar.")
        st.stop()

    query = f"{category} in {location}, India"
    
    with st.spinner(f"Scouting {category} in {location}..."):
        places = get_places(query, google_key, max_results)
        lead_data = []

        for p in places:
            name = p.get("name")
            addr = p.get("formatted_address")
            phone, web, rate, revs = get_details(p.get("place_id"), google_key)
            
            # Fetch Live Ad Signals
            google_active = "Yes" if check_google_ads(name, location) else "No"
            meta_count, meta_date = check_meta_ads_detailed(name, meta_token)
            
            # Email Discovery
            emails = extract_emails(web)

            lead_data.append({
                "Business Name": name,
                "Ad Status": f"🟢 {meta_count} Meta Ads" if meta_count > 0 else "⚪ Inactive",
                "Active Since": meta_date,
                "Google Ads": google_active,
                "Phone": phone,
                "Email": emails,
                "Website": web,
                "Rating": f"{rate} ({revs})",
                "Address": addr
            })

        df = pd.DataFrame(lead_data)
        st.success(f"Found {len(df)} leads!")
        st.dataframe(df, use_container_width=True)

        # Excel Export
        buffer = BytesIO()
        with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
            df.to_excel(writer, index=False, sheet_name='Leads')
        
        st.download_button(
            label="⬇️ Download Excel Report",
            data=buffer.getvalue(),
            file_name=f"Leads_{location}_{category}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
