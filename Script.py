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
    # Using secrets for Google Key is safer, but manual input works too
    google_key = st.text_input("Google Places API Key", value=st.secrets.get("GOOGLE_API_KEY", ""), type="password")
    meta_token = st.text_input("Meta Ad Library Access Token", type="password")

headers = {"User-Agent": "Mozilla/5.0"}

# ------------------------------
# CORE LOGIC
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
        data.get("website", "N/A"),
        data.get("rating", "N/A"),
        data.get("user_ratings_total", "N/A")
    )

def check_meta_ads_detailed(business_name, token):
    """Smart Search: Strips location names to find brand-level ads"""
    if not token: return 0, "Token Missing"
    
    # 1. CLEANING: Remove branch info (e.g., 'CaratLane - Kondapur' -> 'CaratLane')
    # This ensures we find the ~200 results you see in the Ad Library
    clean_name = re.split(r'[-–—,]', business_name)[0].strip()
    
    url = "https://graph.facebook.com/v19.0/ads_archive"
    params = {
        'access_token': token,
        'search_terms': clean_name, # Keywords, not exact phrase
        'ad_active_status': 'ACTIVE',
        'ad_reached_countries': "['IN']",
        'fields': 'id,ad_delivery_start_time',
        'limit': 500
    }
    try:
        response = requests.get(url, params=params, timeout=10).json()
        ads = response.get('data', [])
        if not ads: return 0, "No Active Ads"
        
        # 2. DATE EXTRACTION: Find the oldest 'Started running on' date
        start_dates = [a.get('ad_delivery_start_time') for a in ads if a.get('ad_delivery_start_time')]
        oldest_ad = min(start_dates).split('T')[0] if start_dates else "Date Unknown"
        return len(ads), oldest_ad
    except: return 0, "API Error"

def check_google_ads(name, location):
    try:
        query = f"{name} {location}"
        url = f"https://www.google.com/search?q={urllib.parse.quote(query)}"
        html = requests.get(url, headers=headers, timeout=5).text.lower()
        return any(s in html for s in ["sponsored", "ad ·", "ads by google"])
    except: return False

def extract_emails(website):
    if not website or website == "N/A": return "N/A"
    try:
        html = requests.get(website, headers=headers, timeout=5).text
        emails = re.findall(r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}", html)
        return ", ".join(set(emails)) if emails else "Not Found"
    except: return "Error"

# ------------------------------
# INTERFACE
# ------------------------------

loc_input = st.text_input("📍 Location", value="Kondapur")
cat_input = st.text_input("🏢 Category", value="Jewellery Store")
max_res = st.slider("Max Leads", 5, 50, 10)

if st.button("🔍 Run Intelligence Search"):
    if not google_key:
        st.error("Enter Google API Key in sidebar.")
        st.stop()

    query = f"{cat_input} in {loc_input}, India"
    with st.spinner("Scouting leads and checking Meta Ad Library..."):
        places = get_places(query, google_key, max_res)
        results = []
        for p in places:
            name = p.get("name")
            phone, web, rate, revs = get_details(p.get("place_id"), google_key)
            
            # Use the cleaning logic to check Meta
            meta_count, meta_date = check_meta_ads_detailed(name, meta_token)
            google_ad = "Yes" if check_google_ads(name, loc_input) else "No"
            
            results.append({
                "Business Name": name,
                "Ad Status": f"🟢 {meta_count} Ads" if meta_count > 0 else "⚪ Inactive",
                "Active Since": meta_date,
                "Google Ads": google_ad,
                "Email": extract_emails(web),
                "Phone": phone,
                "Website": web
            })

        df = pd.DataFrame(results)
        st.dataframe(df, use_container_width=True)

        # Excel Export logic - Fixed with Buffer and Openpyxl
        buffer = BytesIO()
        try:
            with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
                df.to_excel(writer, index=False)
            st.download_button("⬇️ Download Excel Report", data=buffer.getvalue(), file_name=f"Leads_{loc_input}.xlsx")
        except ModuleNotFoundError:
            st.warning("Excel export is initializing. Please 'Reboot' the app in Streamlit settings.")
