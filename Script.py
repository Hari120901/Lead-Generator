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
# LOGIC WITH STRICT FILTERING
# ------------------------------

def get_places(query, api_key, max_res, target_location, target_category):
    url = f"https://maps.googleapis.com/maps/api/place/textsearch/json?query={urllib.parse.quote(query)}&key={api_key}"
    response = requests.get(url).json()
    raw_results = response.get("results", [])
    
    filtered_results = []
    for place in raw_results:
        address = place.get("formatted_address", "").lower()
        name = place.get("name", "").lower()
        
        # STRICT LOCATION CHECK: Ensure the searched location is in the address
        # STRICT CATEGORY CHECK: Ensure keywords match (e.g., 'jewellery' or 'realty')
        is_in_location = target_location.lower() in address
        is_correct_category = any(word in name or word in address for word in target_category.lower().split())
        
        if is_in_location and is_correct_category:
            filtered_results.append(place)
            
    return filtered_results[:max_res]

def check_meta_ads_detailed(business_name, token):
    if not token: return 0, "Token Missing"
    url = "https://graph.facebook.com/v19.0/ads_archive"
    params = {
        'access_token': token,
        'search_terms': f'"{business_name}"', # Using quotes for exact match
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

# ... (Keeping get_details, check_google_ads, and extract_emails from previous version)

# ------------------------------
# MAIN INTERFACE
# ------------------------------

search_loc = st.text_input("📍 Exact Location", value="Nanakramguda")
search_cat = st.text_input("🏢 Exact Category", value="Real Estate")
max_results = st.slider("Number of Leads", 5, 50, 10)

if st.button("🔍 Generate Filtered Leads"):
    if not google_key:
        st.error("Please enter a Google API Key.")
        st.stop()

    # Refined search string
    full_query = f"{search_cat} in {search_loc}, Hyderabad"
    
    with st.spinner(f"Filtering results strictly for {search_cat} in {search_loc}..."):
        # Pass search terms into the function for filtering
        places = get_places(full_query, google_key, max_results, search_loc, search_cat)
        
        if not places:
            st.warning("No results matched your strict location/category criteria. Try a broader search term.")
            st.stop()

        lead_data = []
        for p in places:
            name = p.get("name")
            addr = p.get("formatted_address")
            # Only process details for businesses that passed the filter
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
                "Website": web
            })

        df = pd.DataFrame(lead_data)
        st.success(f"Found {len(df)} verified leads in {search_loc}")
        st.dataframe(df, use_container_width=True)

        # Excel Export logic remains the same...
