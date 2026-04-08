import streamlit as st
import requests
import pandas as pd
from io import BytesIO
import urllib.parse
import re

# ------------------------------
# CONFIG & UI
# ------------------------------
st.set_page_config(page_title="Lead Gen Pro", layout="wide")
st.title("📊 Lead Generator: Discovery Mode")

with st.sidebar:
    st.header("API Configuration")
    google_key = st.text_input("Google Places API Key", type="password")
    meta_token = st.text_input("Meta Ad Library Token", type="password")
    mode = st.radio("Search Mode", ["Google First (Local)", "Meta First (Discovery)"])

headers = {"User-Agent": "Mozilla/5.0"}

# ------------------------------
# DISCOVERY LOGIC
# ------------------------------

def discover_meta_brands(keyword, token, limit=20):
    """Finds brands currently advertising on Meta for a specific keyword"""
    url = "https://graph.facebook.com/v19.0/ads_archive"
    params = {
        'access_token': token,
        'search_terms': keyword,
        'ad_active_status': 'ACTIVE',
        'ad_reached_countries': "['IN']",
        'fields': 'page_name,page_id,ad_delivery_start_time',
        'limit': limit
    }
    try:
        res = requests.get(url, params=params).json()
        ads = res.get('data', [])
        unique_brands = {}
        for ad in ads:
            name = ad.get('page_name')
            if name not in unique_brands:
                unique_brands[name] = ad.get('ad_delivery_start_time', '').split('T')[0]
        return unique_brands
    except:
        return {}

def get_local_info(brand_name, location, api_key):
    """Finds Google contact info for a brand discovered on Meta"""
    query = f"{brand_name} in {location}"
    url = f"https://maps.googleapis.com/maps/api/place/textsearch/json?query={urllib.parse.quote(query)}&key={api_key}"
    res = requests.get(url).json().get("results", [])
    if res:
        p = res[0]
        details_url = f"https://maps.googleapis.com/maps/api/place/details/json?place_id={p['place_id']}&fields=formatted_phone_number,website&key={api_key}"
        det = requests.get(details_url).json().get("result", {})
        return det.get("formatted_phone_number", "N/A"), det.get("website", "N/A"), p.get("formatted_address")
    return "N/A", "N/A", "No Local Office Found"

# ------------------------------
# MAIN INTERFACE
# ------------------------------
loc = st.text_input("📍 Target Location", "Kondapur")
cat = st.text_input("🏢 Industry Keyword", "Jewellery")

if st.button("🔍 Discover Competitors"):
    if not meta_token or not google_key:
        st.error("Please provide both API keys.")
        st.stop()

    with st.spinner("Extracting brands from Meta Ad Library..."):
        # 1. DISCOVER
        found_brands = discover_meta_brands(cat, meta_token)
        
        rows = []
        for brand, start_date in found_brands.items():
            # 2. ENRICH
            phone, site, addr = get_local_info(brand, loc, google_key)
            
            rows.append({
                "Brand Name": brand,
                "Ad Status": "🟢 Active on Meta",
                "Ads Started": start_date,
                "Local Address": addr,
                "Phone": phone,
                "Website": site
            })

        df = pd.DataFrame(rows)
        st.dataframe(df, use_container_width=True)
        
        # 3. EXPORT
        csv = df.to_csv(index=False).encode('utf-8')
        st.download_button("⬇️ Download Discovery Report", csv, "meta_discovery.csv", "text/csv")
