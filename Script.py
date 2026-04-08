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
st.title("📊 Lead Generator: Google + Meta Ads Intelligence")

with st.sidebar:
    st.header("API Configuration")
    google_key = st.text_input("Google Places API Key", type="password")
    meta_token = st.text_input("Meta Ad Library Token", type="password")
    only_ads = st.checkbox("Show Only Ad-Active Businesses", value=False)

headers = {"User-Agent": "Mozilla/5.0"}

# ------------------------------
# LOGIC FUNCTIONS
# ------------------------------

def extract_brand_name(full_name):
    """Strips location and noise to get a clean brand name for Meta search"""
    # Split by common separators
    name = re.split(r'[-–—|:,]', full_name)[0]
    # Remove common area/business noise
    noise = ['kondapur', 'hyderabad', 'jewellery', 'jewelry', 'store', 'showroom', 'pvt', 'ltd', 'india']
    words = [w for w in name.split() if w.lower() not in noise]
    return " ".join(words[:2]).strip() if words else name.strip()

def check_meta_ads(brand, token):
    """Queries Meta API without strict quotes for higher discovery rate"""
    if not token: return 0, "No Token"
    
    url = "https://graph.facebook.com/v19.0/ads_archive"
    params = {
        "access_token": token,
        "search_terms": brand, # FIX: Removed double quotes for broader matching
        "ad_active_status": "ACTIVE",
        "ad_reached_countries": "['IN']",
        "fields": "ad_delivery_start_time",
        "limit": 50
    }
    
    try:
        res = requests.get(url, params=params, timeout=10).json()
        if "error" in res:
            return 0, f"Error: {res['error'].get('message')[:20]}..."
            
        ads = res.get("data", [])
        if not ads:
            return 0, "No Ads Found"
            
        # Extract the oldest ad date
        dates = [ad.get("ad_delivery_start_time") for ad in ads if ad.get("ad_delivery_start_time")]
        earliest_date = min(dates).split("T")[0] if dates else "Date Unknown"
        
        return len(ads), earliest_date
    except:
        return 0, "API Error"

def get_places(query, api_key, max_res):
    url = f"https://maps.googleapis.com/maps/api/place/textsearch/json?query={urllib.parse.quote(query)}&key={api_key}"
    res = requests.get(url).json()
    return res.get("results", [])[:max_res]

def get_details(place_id, api_key):
    url = f"https://maps.googleapis.com/maps/api/place/details/json?place_id={place_id}&fields=formatted_phone_number,website&key={api_key}"
    data = requests.get(url).json().get("result", {})
    return data.get("formatted_phone_number", "N/A"), data.get("website", "N/A")

# ------------------------------
# MAIN EXECUTION
# ------------------------------
loc = st.text_input("📍 Location", "Kondapur")
cat = st.text_input("🏢 Category", "Jewellery Store")
limit = st.slider("Max Leads", 5, 50, 10)

if st.button("🔍 Run Search"):
    if not google_key or not meta_token:
        st.error("Enter both API Keys in the sidebar.")
        st.stop()

    query = f"{cat} in {loc}, Hyderabad"
    with st.spinner("🔎 Analyzing local businesses and Meta Ad Library..."):
        places = get_places(query, google_key, limit)
        rows = []
        
        for p in places:
            full_name = p.get("name")
            brand = extract_brand_name(full_name) # Get 'Joyalukkas' from 'Joyalukkas - Kondapur'
            phone, site = get_details(p.get("place_id"), google_key)
            
            # Meta Ads Detection
            meta_count, meta_date = check_meta_ads(brand, meta_token)
            
            # Ad Status Logic
            if meta_count > 0:
                status = "🟢 Active (Meta Ads)"
            else:
                status = "⚪ No Ads Detected"

            rows.append({
                "Brand": brand,
                "Ad Status": status,
                "Meta Ads Count": meta_count,
                "Active Since": meta_date,
                "Phone": phone,
                "Website": site,
                "Full Name": full_name
            })

        df = pd.DataFrame(rows)
        if only_ads:
            df = df[df["Meta Ads Count"] > 0]
        
        st.dataframe(df, use_container_width=True)
        
        # CSV Export
        csv = df.to_csv(index=False).encode("utf-8")
        st.download_button("⬇️ Download CSV", csv, file_name=f"leads_{loc}.csv", mime="text/csv")
