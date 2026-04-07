import streamlit as st
import requests
import pandas as pd
from io import BytesIO
import urllib.parse
import re

# ------------------------------
# CONFIG
# ------------------------------
st.set_page_config(page_title="Strict Ad Intelligence Lead Gen", layout="wide")
st.title("📊 Strict Lead Generator: Filtered by Location & Category")

with st.sidebar:
    st.header("API Configuration")
    google_key = st.text_input("Google Places API Key", value=st.secrets.get("GOOGLE_API_KEY", ""), type="password")
    meta_token = st.text_input("Meta Ad Library Access Token", type="password")

headers = {"User-Agent": "Mozilla/5.0"}

# ------------------------------
# CORE LOGIC FUNCTIONS
# ------------------------------

def get_places(query, api_key, max_res, target_location, target_category):
    """Fetches places and strictly filters by location and category keywords"""
    url = f"https://maps.googleapis.com/maps/api/place/textsearch/json?query={urllib.parse.quote(query)}&key={api_key}"
    response = requests.get(url).json()
    raw_results = response.get("results", [])
    
    filtered_results = []
    for place in raw_results:
        address = place.get("formatted_address", "").lower()
        name = place.get("name", "").lower()
        
        # Check if searched location is actually in the address string
        is_in_location = target_location.lower() in address
        # Check if category keywords match name or address
        is_correct_category = any(word in name or word in address for word in target_category.lower().split())
        
        if is_in_location and is_correct_category:
            filtered_results.append(place)
            
    return filtered_results[:max_res]

def get_details(place_id, api_key):
    """Fetches specific contact details from Google Places API"""
    url = f"https://maps.googleapis.com/maps/api/place/details/json?place_id={place_id}&fields=formatted_phone_number,website,rating,user_ratings_total&key={api_key}"
    data = requests.get(url).json().get("result", {})
    return (
        data.get("formatted_phone_number", "N/A"),
        data.get("website", "N/A"),
        data.get("rating", "N/A"),
        data.get("user_ratings_total", "N/A")
    )

def check_meta_ads_detailed(business_name, token):
    """Queries Meta API for exact business name ads and start dates"""
    if not token: return 0, "Token Missing"
    url = "https://graph.facebook.com/v19.0/ads_archive"
    params = {
        'access_token': token,
        'search_terms': f'"{business_name}"',
        'ad_active_status': 'ACTIVE',
        'ad_reached_countries': "['IN']",
        'fields': 'id,ad_delivery_start_time'
    }
    try:
        response = requests.get(url, params=params, timeout=10).json()
        ads = response.get('data', [])
        if not ads: return 0, "No Active Ads"
        
        start_dates = [a.get('ad_delivery_start_time') for a in ads if a.get('ad_delivery_start_time')]
        oldest_ad = min(start_dates).split('T')[0] if start_dates else "Date Unknown"
        return len(ads), oldest_ad
    except: return 0, "API Error"

def check_google_ads(name, location):
    """Scrapes Google Search for 'Sponsored' signals"""
    try:
        query = f"{name} {location}"
        url = f"https://www.google.com/search?q={urllib.parse.quote(query)}"
        html = requests.get(url, headers=headers, timeout=5).text.lower()
        ad_signals = ["sponsored", "ad ·", "ads by google", "googleadservices"]
        return any(signal in html for signal in ad_signals)
    except: return False

def extract_emails(website):
    """Crawl website for email patterns"""
    if not website or website == "N/A": return "N/A"
    try:
        html = requests.get(website, headers=headers, timeout=5).text
        emails = re.findall(r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}", html)
        return ", ".join(set(emails)) if emails else "Not Found"
    except: return "Error"

# ------------------------------
# MAIN INTERFACE
# ------------------------------

search_loc = st.text_input("📍 Exact Location", value="Nanakramguda")
search_cat = st.text_input("🏢 Exact Category", value="Real Estate")
max_results = st.slider("Number of Leads", 5, 50, 10)

if st.button("🔍 Generate Filtered Leads"):
    if not google_key:
        st.error("Please enter a Google API Key in the sidebar.")
        st.stop()

    full_query = f"{search_cat} in {search_loc}, Hyderabad"
    
    with st.spinner(f"Processing {search_cat} leads for {search_loc}..."):
        places = get_places(full_query, google_key, max_results, search_loc, search_cat)
        
        if not places:
            st.warning("No businesses found in that exact location/category. Try broadening your terms.")
            st.stop()

        lead_data = []
        for p in places:
            name = p.get("name")
            addr = p.get("formatted_address")
            
            # These functions were missing in the last version, causing the NameError
            phone, web, rate, revs = get_details(p.get("place_id"), google_key)
            meta_count, meta_date = check_meta_ads_detailed(name, meta_token)
            google_active = "Yes" if check_google_ads(name, search_loc) else "No"
            emails = extract_emails(web)

            lead_data.append({
                "Business Name": name,
                "Ad Status": f"🟢 {meta_count} Meta Ads" if meta_count > 0 else "⚪ Inactive",
                "Active Since": meta_date,
                "Google Ads": google_active,
                "Address": addr,
                "Email": emails,
                "Website": web,
                "Phone": phone
            })

        df = pd.DataFrame(lead_data)
        st.success(f"Successfully generated {len(df)} verified leads.")
        st.dataframe(df, use_container_width=True)

        # Export to Excel
        output = BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df.to_excel(writer, index=False, sheet_name='Leads')
        
        st.download_button(
            label="⬇️ Download Excel Report",
            data=output.getvalue(),
            file_name=f"Leads_{search_loc}_{search_cat}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
