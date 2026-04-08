import streamlit as st
import requests
import pandas as pd
from io import BytesIO
import urllib.parse
import re

# ------------------------------
# CONFIG & UI
# ------------------------------
st.set_page_config(page_title="Ad Intelligence Lead Gen Pro", layout="wide")
st.title("📊 Lead Generator: Google + Meta Ad Insights")

with st.sidebar:
    st.header("API Configuration")
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

def extract_brand_name(full_name):
    """
    Strips location data and suffixes to get a clean brand name.
    Example: 'CaratLane - Kondapur, Hyderabad' -> 'CaratLane'
    """
    # 1. Split by common delimiters
    name = re.split(r'[-–—|:,]', full_name)[0]
    
    # 2. Remove common city/area noise words
    noise = ['kondapur', 'hyderabad', 'telangana', 'gachibowli', 'pvt', 'ltd', 'india', 'store', 'showroom']
    words = name.split()
    clean_words = [w for w in words if w.lower() not in noise]
    
    return " ".join(clean_words).strip()

def check_meta_ads_detailed(business_name, token):
    if not token: return 0, "Token Missing"
    
    # GET THE CLEAN BRAND NAME
    brand_query = extract_brand_name(business_name)
    
    url = "https://graph.facebook.com/v19.0/ads_archive"
    params = {
        'access_token': token,
        'search_terms': brand_query, 
        'ad_active_status': 'ACTIVE',
        'ad_reached_countries': "['IN']",
        'fields': 'id,ad_delivery_start_time',
        'limit': 500
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
# UI / MAIN
# ------------------------------

loc_input = st.text_input("📍 Location", value="Kondapur")
cat_input = st.text_input("🏢 Category", value="Jewellery Store")
max_res = st.slider("Max Leads", 5, 50, 10)

if st.button("🔍 Run Intelligence Search"):
    if not google_key:
        st.error("Enter Google API Key.")
        st.stop()

    query = f"{cat_input} in {loc_input}, Hyderabad"
    with st.spinner("Filtering for Brand Ads..."):
        places = get_places(query, google_key, max_res)
        results = []
        for p in places:
            name = p.get("name")
            phone, web, rate, revs = get_details(p.get("place_id"), google_key)
            
            # This now uses the extract_brand_name logic inside
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

        buffer = BytesIO()
        try:
            with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
                df.to_excel(writer, index=False)
            st.download_button("⬇️ Download Excel", data=buffer.getvalue(), file_name=f"Leads_{loc_input}.xlsx")
        except:
            st.info("Export ready. If error occurs, please reboot Streamlit app to install openpyxl.")
