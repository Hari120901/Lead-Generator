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
    st.info("Note: Ensure your Meta Token is fresh from the Graph API Explorer.")

headers = {"User-Agent": "Mozilla/5.0"}

# ------------------------------
# LOGIC FUNCTIONS
# ------------------------------

def extract_brand_name(full_name):
    """Cleans names like 'Joyalukkas - Kondapur' into 'Joyalukkas'"""
    name = re.split(r'[-–—|:,]', full_name)[0]
    noise = ['kondapur', 'hyderabad', 'jewellery', 'jewelry', 'store', 'showroom', 'pvt', 'ltd', 'india']
    words = [w for w in name.split() if w.lower() not in noise]
    return " ".join(words).strip()

def check_meta_ads(brand_name, token):
    """Directly queries Meta for active ads without restrictive quoting"""
    if not token: return 0, "No Token"
    
    url = "https://graph.facebook.com/v19.0/ads_archive"
    params = {
        "access_token": token,
        "search_terms": brand_name, 
        "ad_active_status": "ACTIVE",
        "ad_reached_countries": "['IN']",
        "fields": "ad_delivery_start_time",
        "limit": 50
    }
    
    try:
        res = requests.get(url, params=params, timeout=10).json()
        if "error" in res:
            return 0, f"Error: {res['error'].get('message')[:30]}..."
            
        ads = res.get("data", [])
        if not ads:
            return 0, "No Ads Found"
            
        dates = [ad.get("ad_delivery_start_time") for ad in ads if ad.get("ad_delivery_start_time")]
        earliest_date = min(dates).split("T")[0] if dates else "Date Unknown"
        
        return len(ads), earliest_date
    except:
        return 0, "Connection Error"

# ------------------------------
# MAIN EXECUTION
# ------------------------------
loc = st.text_input("📍 Location", "Kondapur")
cat = st.text_input("🏢 Category", "Jewellery Store")

if st.button("🔍 Run Search"):
    if not google_key or not meta_token:
        st.error("Missing API Keys.")
        st.stop()

    query = f"{cat} in {loc}, Hyderabad"
    with st.spinner("Analyzing Market..."):
        # Google Places Discovery
        g_url = f"https://maps.googleapis.com/maps/api/place/textsearch/json?query={urllib.parse.quote(query)}&key={google_key}"
        places = requests.get(g_url).json().get("results", [])[:10]
        
        rows = []
        for p in places:
            full_name = p.get("name")
            brand = extract_brand_name(full_name)
            
            # Meta Ads Check
            count, start_date = check_meta_ads(brand, meta_token)
            
            rows.append({
                "Brand": brand,
                "Ad Status": "🟢 Active" if count > 0 else "⚪ Inactive",
                "Ads Count": count,
                "Active Since": start_date,
                "Address": p.get("formatted_address")
            })

        df = pd.DataFrame(rows)
        st.dataframe(df, use_container_width=True)
