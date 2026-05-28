import streamlit as st
import requests
import pandas as pd
import urllib.parse
import re
import time

# =====================================================
# PAGE CONFIG
# =====================================================

st.set_page_config(
    page_title="CORPOS Lead Generator",
    layout="wide"
)

st.title("📊 CORPOS: Lead Generator")

# =====================================================
# SIDEBAR
# =====================================================

with st.sidebar:
    st.header("🔑 API Configuration")

    google_key = st.text_input(
        "Google Places API Key",
        type="password"
    )

    meta_token = st.text_input(
        "Meta Ad Library Token",
        type="password"
    )

# =====================================================
# HELPERS
# =====================================================

def extract_brand_name(full_name):
    """
    Cleans business names:
    'Joyalukkas - Kondapur' -> 'Joyalukkas'
    """

    if not full_name:
        return ""

    name = re.split(r'[-–—|:,()]', full_name)[0]

    noise_words = {
        'hyderabad',
        'kondapur',
        'india',
        'jewellery',
        'jewelry',
        'store',
        'showroom',
        'pvt',
        'ltd',
        'private',
        'limited'
    }

    cleaned = [
        word for word in name.split()
        if word.lower() not in noise_words
    ]

    return " ".join(cleaned).strip()


def fetch_google_places(query, api_key, max_results=60):
    """
    Fetch businesses from Google Places API
    with pagination support.
    """

    results = []

    url = (
        "https://maps.googleapis.com/maps/api/place/textsearch/json"
        f"?query={urllib.parse.quote(query)}"
        f"&key={api_key}"
    )

    while url and len(results) < max_results:

        response = requests.get(url)
        data = response.json()

        places = data.get("results", [])
        results.extend(places)

        next_page_token = data.get("next_page_token")

        if next_page_token:
            time.sleep(2)

            url = (
                "https://maps.googleapis.com/maps/api/place/textsearch/json"
                f"?pagetoken={next_page_token}"
                f"&key={api_key}"
            )
        else:
            break

    return results[:max_results]


def check_meta_ads(brand_name, token):
    """
    Check if a business is actively running Meta ads.
    """

    if not token:
        return 0, "No Token"

    url = "https://graph.facebook.com/v19.0/ads_archive"

    params = {
        "access_token": token,
        "search_terms": brand_name,
        "ad_active_status": "ACTIVE",
        "ad_reached_countries": "['IN']",
        "fields": "ad_delivery_start_time,page_name",
        "limit": 100
    }

    try:
        response = requests.get(url, params=params)
        data = response.json()

        # API error handling
        if "error" in data:
            msg = data["error"].get("message", "Unknown Error")

            if "permission" in msg.lower():
                return 0, "🔒 FB ID Verification Needed"

            return 0, f"❌ {msg[:80]}"

        ads = data.get("data", [])

        if not ads:
            return 0, "⚪ No Active Ads"

        first_date = ads[0].get(
            "ad_delivery_start_time",
            ""
        )[:10]

        return len(ads), f"🟢 Active Since {first_date}"

    except Exception:
        return 0, "⚠️ API Error"


# =====================================================
# INPUTS
# =====================================================

col1, col2 = st.columns(2)

with col1:
    location = st.text_input(
        "📍 Location",
        "Kondapur"
    )

with col2:
    category = st.text_input(
        "🏢 Category",
        "Jewellery Store"
    )

# =====================================================
# MAIN SEARCH
# =====================================================

if st.button("🚀 Generate Leads"):

    if not google_key:
        st.error("Please enter Google Places API Key")
        st.stop()

    search_query = f"{category} in {location}, India"

    with st.spinner("Fetching businesses and checking Meta ads..."):

        places = fetch_google_places(
            search_query,
            google_key
        )

        if not places:
            st.warning("No businesses found.")
            st.stop()

        leads = []

        progress = st.progress(0)

        for index, place in enumerate(places):

            business_name = place.get("name", "")
            address = place.get("formatted_address", "")

            brand = extract_brand_name(
                business_name
            )

            ads_count, ad_status = check_meta_ads(
                brand,
                meta_token
            )

            # ONLY ACTIVE ADVERTISERS
            if ads_count > 0:

                leads.append({
                    "Business Name": business_name,
                    "Brand": brand,
                    "Ads Found": ads_count,
                    "Ad Status": ad_status,
                    "Address": address,
                    "Google Rating": place.get("rating"),
                    "User Ratings": place.get(
                        "user_ratings_total"
                    )
                })

            progress.progress(
                (index + 1) / len(places)
            )

        progress.empty()

    # =================================================
    # RESULTS
    # =================================================

    if not leads:
        st.warning(
            "No active advertisers found."
        )

    else:

        df = pd.DataFrame(leads)

        # Sort by ads count
        df = df.sort_values(
            by="Ads Found",
            ascending=False
        )

        st.success(
            f"✅ Found {len(df)} active advertisers"
        )

        st.dataframe(
            df,
            use_container_width=True
        )

        # CSV DOWNLOAD
        csv = df.to_csv(index=False)

        st.download_button(
            label="⬇ Download CSV",
            data=csv,
            file_name="active_leads.csv",
            mime="text/csv"
        )
