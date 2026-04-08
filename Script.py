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
    google_key = st.text_input("Google Places API Key", type="password")
    meta_token = st.text_input("Meta Ad Library Access Token", type="password")
    only_ads = st.checkbox("Show Only Businesses Running Ads", value=False)

headers = {"User-Agent": "Mozilla/5.0"}

# ------------------------------
# FUNCTIONS
# ------------------------------

def get_places(query, api_key, max_res):
    url = f"https://maps.googleapis.com/maps/api/place/textsearch/json?query={urllib.parse.quote(query)}&key={api_key}"
    response = requests.get(url).json()
    return response.get("results", [])[:max_res]


def get_details(place_id, api_key):
    url = f"https://maps.googleapis.com/maps/api/place/details/json?place_id={place_id}&fields=formatted_phone_number,website&key={api_key}"
    data = requests.get(url).json().get("result", {})

    return (
        data.get("formatted_phone_number", "N/A"),
        data.get("website", "N/A")
    )


def extract_brand_name(full_name):
    """
    Example:
    'CaratLane Jewellery, Kondapur, Hyderabad' → 'CaratLane'
    """
    name = re.split(r'[-–—|:,]', full_name)[0]

    remove_words = [
        'jewellery', 'jewelry', 'store', 'showroom',
        'pvt', 'ltd', 'india', 'private', 'limited'
    ]

    words = name.split()
    clean_words = [w for w in words if w.lower() not in remove_words]

    return clean_words[0] if clean_words else name.strip()


def check_meta_ads(brand_name, token):
    if not token:
        return 0, "Token Missing"

    url = "https://graph.facebook.com/v19.0/ads_archive"

    # 🔥 Multiple search attempts (fix inactive issue)
    search_terms_list = [
        brand_name,
        f"{brand_name} India",
        f"{brand_name} Official",
        f"{brand_name} Store"
    ]

    for term in search_terms_list:
        params = {
            'access_token': token,
            'search_terms': term,
            'ad_active_status': 'ACTIVE',
            'ad_reached_countries': "['IN']",
            'fields': 'id,ad_delivery_start_time',
            'limit': 100
        }

        try:
            response = requests.get(url, params=params, timeout=10).json()
            ads = response.get('data', [])

            if ads:
                dates = [a.get('ad_delivery_start_time') for a in ads if a.get('ad_delivery_start_time')]
                oldest = min(dates).split("T")[0] if dates else "Unknown"

                return len(ads), oldest

        except:
            continue

    return 0, "No Active Ads"


def check_google_ads(name, location):
    try:
        query = f"{name} {location}"
        url = f"https://www.google.com/search?q={urllib.parse.quote(query)}"
        html = requests.get(url, headers=headers, timeout=5).text.lower()

        return any(x in html for x in ["sponsored", "ads by google", "ad ·"])

    except:
        return False


def extract_emails(website):
    if not website or website == "N/A":
        return "N/A"

    try:
        html = requests.get(website, headers=headers, timeout=5).text
        emails = re.findall(r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}", html)

        return ", ".join(set(emails)) if emails else "Not Found"

    except:
        return "Error"


# ------------------------------
# INPUT
# ------------------------------

loc_input = st.text_input("📍 Location", value="Kondapur")
cat_input = st.text_input("🏢 Category", value="Jewellery Store")
max_res = st.slider("Max Leads", 5, 50, 10)

# ------------------------------
# MAIN
# ------------------------------

if st.button("🔍 Run Intelligence Search"):

    if not google_key:
        st.error("Please enter Google API Key")
        st.stop()

    query = f"{cat_input} in {loc_input}, Hyderabad"

    with st.spinner("🔎 Finding businesses and analyzing ads..."):

        places = get_places(query, google_key, max_res)
        results = []

        for p in places:
            full_name = p.get("name")

            # ✅ Clean brand
            brand_name = extract_brand_name(full_name)

            phone, website = get_details(p.get("place_id"), google_key)

            # ✅ Meta Ads (improved detection)
            meta_count, meta_date = check_meta_ads(brand_name, meta_token)

            # ✅ Google Ads
            google_ads = "Yes" if check_google_ads(brand_name, loc_input) else "No"

            results.append({
                "Brand Name": brand_name,
                "Meta Ads Running": meta_count,
                "Active Since": meta_date,
                "Google Ads": google_ads,
                "Email": extract_emails(website),
                "Phone": phone,
                "Website": website
            })

        df = pd.DataFrame(results)

        # ✅ Filter only active advertisers
        if only_ads:
            df = df[df["Meta Ads Running"] > 0]

        st.dataframe(df, use_container_width=True)

        # ------------------------------
        # EXCEL EXPORT (FIXED)
        # ------------------------------
        buffer = BytesIO()

        with pd.ExcelWriter(buffer, engine='xlsxwriter') as writer:
            df.to_excel(writer, index=False, sheet_name="Leads")

        st.download_button(
            label="⬇️ Download Excel",
            data=buffer.getvalue(),
            file_name=f"Leads_{loc_input}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
