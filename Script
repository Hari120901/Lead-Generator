import streamlit as st
import requests
import pandas as pd
from io import BytesIO
import urllib.parse
import re

st.set_page_config(page_title="Business Lead Generator", layout="wide")
st.title("📈 Business Leads with Contact & Advertising Activity")

# ------------------------------
# USER INPUT
# ------------------------------
location = st.text_input("📍 Location (e.g., Andheri West, Mumbai)")
category = st.text_input("🏢 Category (e.g., jewellery store)")
max_results = st.selectbox("Max Results", [10, 20, 30, 50, 60])

GOOGLE_API_KEY = st.secrets["GOOGLE_API_KEY"]
headers = {"User-Agent": "Mozilla/5.0"}

# ------------------------------
# GOOGLE PLACES SEARCH
# ------------------------------
def get_places(query):
    encoded_query = urllib.parse.quote(query)
    url = f"https://maps.googleapis.com/maps/api/place/textsearch/json?query={encoded_query}&key={GOOGLE_API_KEY}"
    response = requests.get(url).json()
    return response.get("results", [])[:max_results]

# ------------------------------
# GET PLACE DETAILS
# ------------------------------
def get_details(place_id):
    details_url = f"https://maps.googleapis.com/maps/api/place/details/json?place_id={place_id}&fields=formatted_phone_number,website,rating,user_ratings_total&key={GOOGLE_API_KEY}"
    details = requests.get(details_url).json().get("result", {})
    phone = details.get("formatted_phone_number", "N/A")
    website = details.get("website", None)
    rating = details.get("rating", "N/A")
    reviews = details.get("user_ratings_total", "N/A")
    return phone, website, rating, reviews

# ------------------------------
# EXTRACT EMAILS & WHATSAPP
# ------------------------------
def extract_contacts(website):
    if not website:
        return "N/A", "N/A"

    emails = set()
    whatsapp = set()
    urls_to_check = [website, urllib.parse.urljoin(website, "contact")]

    for url in urls_to_check:
        try:
            r = requests.get(url, headers=headers, timeout=5)
            html = r.text

            # Extract emails
            found_emails = re.findall(r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}", html)
            for e in found_emails:
                emails.add(e)

            # Extract WhatsApp numbers (India format)
            found_wa = re.findall(r"(\+91[6-9]\d{9})", html)
            for w in found_wa:
                whatsapp.add(w)

        except:
            continue

    return ", ".join(emails) if emails else "Not Found", ", ".join(whatsapp) if whatsapp else "Not Found"

# ------------------------------
# GOOGLE ADS DETECTION
# ------------------------------
def check_google_ads(name, location):
    try:
        query = f"{name} {location}"
        url = f"https://www.google.com/search?q={urllib.parse.quote(query)}"
        response = requests.get(url, headers=headers, timeout=5).text
        if "Sponsored" in response or "Ad ·" in response:
            return "Yes"
        return "No"
    except:
        return "Unknown"

# ------------------------------
# MAIN PROCESS
# ------------------------------
if st.button("Generate Leads"):

    if not location or not category:
        st.warning("Please enter both Location and Category")
        st.stop()

    query = f"{category} in {location}, India"
    with st.spinner("Searching businesses..."):
        businesses = get_places(query)

    results = []

    for biz in businesses:

        name = biz.get("name")
        address = biz.get("formatted_address")
        place_id = biz.get("place_id")

        # Get phone, website, rating
        phone, website, rating, reviews = get_details(place_id)

        # Extract emails & WhatsApp
        emails, whatsapp = extract_contacts(website)

        # Detect Google Ads
        google_ads = check_google_ads(name, location)

        # Compute advertising activity score
        score = 0
        if google_ads == "Yes": score += 1
        if website and website != "N/A": score += 1
        if emails != "Not Found": score += 1
        if whatsapp != "Not Found": score += 1

        if score == 0:
            status = "Low Activity"
        elif score <= 2:
            status = "Medium Activity"
        else:
            status = "High Activity"

        results.append([
            name,
            address,
            phone,
            website if website else "N/A",
            emails,
            whatsapp,
            rating,
            reviews,
            google_ads,
            score,
            status
        ])

    df = pd.DataFrame(results, columns=[
        "Business Name",
        "Address",
        "Phone",
        "Website",
        "Emails",
        "WhatsApp",
        "Google Rating",
        "Review Count",
        "Google Ads Detected",
        "Lead Score (0-4)",
        "Lead Level"
    ])

    st.success("Lead Generation Complete ✅")
    st.dataframe(df)

    output = BytesIO()
    df.to_excel(output, index=False, engine="openpyxl")
    output.seek(0)

    st.download_button(
        "Download Excel",
        data=output,
        file_name="business_leads_with_adv_activity.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
