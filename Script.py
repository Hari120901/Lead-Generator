import streamlit as st
import requests
import pandas as pd
from io import BytesIO
import urllib.parse
import re
from urllib.parse import urlparse

# ------------------------------
# CONFIG
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
# FUNCTIONS
# ------------------------------

def get_places(query, api_key, max_res):
    url = f"https://maps.googleapis.com/maps/api/place/textsearch/json?query={urllib.parse.quote(query)}&key={api_key}"
    res = requests.get(url).json()
    return res.get("results", [])[:max_res]

def get_details(place_id, api_key):
    url = f"https://maps.googleapis.com/maps/api/place/details/json?place_id={place_id}&fields=formatted_phone_number,website&key={api_key}"
    data = requests.get(url).json().get("result", {})
    return data.get("formatted_phone_number", "N/A"), data.get("website", "N/A")

def extract_brand_name(full_name):
    name = re.split(r'[-–—|:,]', full_name)[0]
    noise = ['jewellery','jewelry','store','showroom','pvt','ltd','india','private','limited']
    words = [w for w in name.split() if w.lower() not in noise]
    return " ".join(words[:2]).strip() if words else name.strip()

def extract_domain_name(website):
    if not website or website=="N/A":
        return None
    domain = urlparse(website).netloc.lower().replace("www.", "")
    return domain.split('.')[0]

def generate_search_terms(brand, domain):
    terms = [brand]
    if domain:
        terms.append(domain)
    base = domain if domain else brand
    terms += [f"{base} india", f"{base} official", f"{base} store"]
    return list(set(terms))

def is_match(name1, name2):
    # simple match check, avoids fuzzywuzzy
    return name1.lower() in name2.lower() or name2.lower() in name1.lower()

def check_meta_ads(brand, website, token):
    if not token: return 0, "No Token"
    
    # We use the clean brand name directly
    url = "https://graph.facebook.com/v19.0/ads_archive"
    params = {
        "access_token": token,
        "search_terms": f'"{brand}"', # Using quotes for exact brand match
        "ad_active_status": "ACTIVE",
        "ad_reached_countries": "['IN']",
        "fields": "ad_delivery_start_time",
        "limit": 50
    }
    
    try:
        res = requests.get(url, params=params, timeout=8).json()
        ads = res.get("data", [])
        
        if not ads:
            return 0, "No Ads Found"
            
        total_ads = len(ads)
        # Get the oldest date from the results
        dates = [ad.get("ad_delivery_start_time") for ad in ads if ad.get("ad_delivery_start_time")]
        earliest_date = min(dates).split("T")[0] if dates else "Date Unknown"
        
        return total_ads, earliest_date
    except:
        return 0, "API Error"

def check_google_ads(name, location):
    try:
        query = f"{name} {location}"
        url = f"https://www.google.com/search?q={urllib.parse.quote(query)}"
        html = requests.get(url, headers=headers, timeout=5).text.lower()
        return any(x in html for x in ["sponsored", "ads by google", "ad ·"])
    except:
        return False

def extract_emails(site):
    if not site or site == "N/A":
        return "N/A"
    try:
        html = requests.get(site, headers=headers, timeout=5).text
        emails = re.findall(r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}", html)
        return ", ".join(set(emails)) if emails else "Not Found"
    except:
        return "Error"

# ------------------------------
# INPUTS
# ------------------------------
loc = st.text_input("📍 Location", "Kondapur")
cat = st.text_input("🏢 Category", "Jewellery Store")
limit = st.slider("Max Leads", 5, 50, 10)

# ------------------------------
# MAIN EXECUTION
# ------------------------------
if st.button("🔍 Run Search"):

    if not google_key:
        st.error("Enter Google API Key")
        st.stop()

    query = f"{cat} in {loc}, Hyderabad"

    with st.spinner("🔎 Analyzing businesses..."):
        places = get_places(query, google_key, limit)
        rows = []

        for p in places:
            full_name = p.get("name")
            brand = extract_brand_name(full_name)
            phone, site = get_details(p.get("place_id"), google_key)

            # Meta Ads detection
            meta_ads, meta_date = check_meta_ads(brand, site, meta_token)

            # Google Ads fallback
            google_ads = check_google_ads(brand, loc)

            # Final status
            if meta_ads > 0:
                status = "🟢 Active (Meta Ads)"
            elif google_ads:
                status = "🟡 Likely Running Ads (Google)"
            else:
                status = "⚪ No Ads Detected"

            rows.append({
                "Brand": brand,
                "Ad Status": status,
                "Meta Ads Count": meta_ads,
                "Active Since": meta_date,
                "Google Ads": "Yes" if google_ads else "No",
                "Email": extract_emails(site),
                "Phone": phone,
                "Website": site
            })

        df = pd.DataFrame(rows)

        if only_ads:
            df = df[df["Ad Status"] != "⚪ No Ads Detected"]

        st.dataframe(df, use_container_width=True)

        # CSV download
        csv = df.to_csv(index=False).encode("utf-8")
        st.download_button(
            "⬇️ Download CSV",
            csv,
            file_name=f"leads_{loc}.csv",
            mime="text/csv"
        )
