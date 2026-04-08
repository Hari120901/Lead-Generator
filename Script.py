import streamlit as st
import requests
import pandas as pd
import urllib.parse
import re

st.set_page_config(page_title="Lead Gen Pro", layout="wide")
st.title("📊 Lead Generator: Google + Meta Ads Intelligence")

with st.sidebar:
    st.header("API Configuration")
    google_key = st.text_input("Google Places API Key", type="password")
    meta_token = st.text_input("Meta Ad Library Token", type="password")

def extract_brand_name(full_name):
    name = re.split(r'[-–—|:,]', full_name)[0]
    noise = ['kondapur', 'hyderabad', 'jewellery', 'jewelry', 'store', 'showroom', 'pvt', 'ltd', 'india']
    words = [w for w in name.split() if w.lower() not in noise]
    return " ".join(words).strip()

def check_meta_ads(brand_name, token):
    if not token: return 0, "No Token"
    url = "https://graph.facebook.com/v19.0/ads_archive"
    params = {
        "access_token": token,
        "search_terms": brand_name, 
        "ad_active_status": "ACTIVE",
        "ad_reached_countries": "['IN']",
        "fields": "ad_delivery_start_time",
        "limit": 5
    }
    try:
        res = requests.get(url, params=params).json()
        if "error" in res:
            # This captures the 'Permission' error you are seeing
            return 0, f"🔒 {res['error'].get('message')[:25]}..."
            
        ads = res.get("data", [])
        if not ads: return 0, "⚪ Inactive"
            
        return len(ads), f"🟢 Active (Since {ads[0].get('ad_delivery_start_time')[:10]})"
    except:
        return 0, "⚠️ Connection Error"

# MAIN SEARCH
loc = st.text_input("📍 Location", "Kondapur")
cat = st.text_input("🏢 Category", "Jewellery Store")

if st.button("🔍 Run Search"):
    query = f"{cat} in {loc}, Hyderabad"
    with st.spinner("Searching..."):
        g_url = f"https://maps.googleapis.com/maps/api/place/textsearch/json?query={urllib.parse.quote(query)}&key={google_key}"
        places = requests.get(g_url).json().get("results", [])[:10]
        
        results = []
        for p in places:
            brand = extract_brand_name(p.get("name"))
            count, status = check_meta_ads(brand, meta_token)
            
            results.append({
                "Brand": brand,
                "Ad Status": status,
                "Ads Found": count,
                "Address": p.get("formatted_address")
            })
        
        st.dataframe(pd.DataFrame(results), use_container_width=True)
