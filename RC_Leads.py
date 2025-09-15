# app.py (Final Version with Existing Account Check)

import streamlit as st
import pandas as pd
import random
from google_api_helpers import geocode_zip, search_places, get_place_details, get_place_photos, analyze_image_labels, get_photo_url
from scorer import calculate_score

# --- NEW: Helper function to load your existing accounts from accounts.csv ---
@st.cache_data
def load_existing_accounts(filename="accounts.csv"):
    try:
        df = pd.read_csv(filename)
        if "place_id" in df.columns:
            return set(df["place_id"].dropna().astype(str))
        else:
            st.warning(f"Warning: '{filename}' found, but it does not contain a 'place_id' column.")
            return set()
    except FileNotFoundError:
        return set()

# --- Data for Metro Area Dropdown ---
TOP_100_METROS = [
    "New York-Newark-Jersey City, NY-NJ-PA", "Los Angeles-Long Beach-Anaheim, CA", "Chicago-Naperville-Elgin, IL-IN-WI",
    "Dallas-Fort Worth-Arlington, TX", "Houston-The Woodlands-Sugar Land, TX", "Washington-Arlington-Alexandria, DC-VA-MD-WV",
    "Miami-Fort Lauderdale-Pompano Beach, FL", "Philadelphia-Camden-Wilmington, PA-NJ-DE-MD", "Atlanta-Sandy Springs-Alpharetta, GA",
    "Boston-Cambridge-Newton, MA-NH", "Phoenix-Mesa-Chandler, AZ", "San Francisco-Oakland-Berkeley, CA",
    "Riverside-San Bernardino-Ontario, CA", "Detroit-Warren-Dearborn, MI", "Seattle-Tacoma-Bellevue, WA",
    "Minneapolis-St. Paul-Bloomington, MN-WI", "San Diego-Chula Vista-Carlsbad, CA", "Tampa-St. Petersburg-Clearwater, FL",
    "Denver-Aurora-Lakewood, CO", "St. Louis, MO-IL", "Baltimore-Columbia-Towson, MD", "Charlotte-Concord-Gastonia, NC-SC",
    "Orlando-Kissimmee-Sanford, FL", "San Antonio-New Braunfels, TX", "Portland-Vancouver-Hillsboro, OR-WA",
    "Sacramento-Roseville-Folsom, CA", "Pittsburgh, PA", "Las Vegas-Henderson-Paradise, NV", "Austin-Round Rock-Georgetown, TX",
    "Cincinnati, OH-KY-IN", "Kansas City, MO-KS", "Cleveland-Elyria, OH", "Columbus, OH", "Indianapolis-Carmel-Anderson, IN",
    "San Jose-Sunnyvale-Santa Clara, CA", "Nashville-Davidson–Murfreesboro–Franklin, TN", "Virginia Beach-Norfolk-Newport News, VA-NC",
    "Providence-Warwick, RI-MA", "Milwaukee-Waukesha, WI", "Jacksonville, FL", "Oklahoma City, OK", "Raleigh-Cary, NC",

    "Memphis, TN-MS-AR", "Richmond, VA", "New Orleans-Metairie, LA", "Louisville/Jefferson County, KY-IN", "Salt Lake City, UT",
    "Hartford-East Hartford-Middletown, CT", "Buffalo-Cheektowaga, NY", "Birmingham-Hoover, AL", "Grand Rapids-Kentwood, MI",
    "Rochester, NY", "Tucson, AZ", "Urban Honolulu, HI", "Tulsa, OK", "Fresno, CA", "Worcester, MA-CT", "Omaha-Council Bluffs, NE-IA",
    "Bridgeport-Stamford-Norwalk, CT", "Albuquerque, NM", "Albany-Schenectady-Troy, NY", "Greenville-Anderson, SC", "Bakersfield, CA",
    "New Haven-Milford, CT", "McAllen-Edinburg-Mission, TX", "Allentown-Bethlehem-Easton, PA-NJ", "Baton Rouge, LA", "Dayton-Kettering, OH",
    "Columbia, SC", "Charleston-North Charleston, SC", "El Paso, TX", "Des Moines-West Des Moines, IA", "Little Rock-North Little Rock-Conway, AR",
    "Akron, OH", "Syracuse, NY", "Oxnard-Thousand Oaks-Ventura, CA", "Augusta-Richmond County, GA-SC", "Springfield, MA", "Boise City, ID",
    "Knoxville, TN", "Madison, WI", "Winston-Salem, NC", "Stockton, CA", "Scranton–Wilkes-Barre, PA", "Colorado Springs, CO",
    "Poughkeepsie-Newburgh-Middletown, NY", "Harrisburg-Carlisle, PA", "Toledo, OH", "Ogden-Clearfield, UT", "Chattanooga, TN-GA",
    "Provo-Orem, UT", "Lansing-East Lansing, MI", "Cape Coral-Fort Myers, FL", "Jackson, MS", "Wichita, KS", "Palm Bay-Melbourne-Titusville, FL",
    "Lakeland-Winter Haven, FL", "Greensboro-High Point, NC", "Concord, NC"
]
TOP_100_METROS.sort()

# --- Password Protection ---
def check_password():
    if st.session_state.get("password_correct", False):
        return True
    with st.form("login_form"):
        password = st.text_input("Password", type="password")
        submitted = st.form_submit_button("Enter")
        if submitted:
            if password == st.secrets["APP_PASSWORD"]:
                st.session_state["password_correct"] = True
                st.rerun()
            else:
                st.error("😕 Password incorrect")
    return False

# --- Main App ---
st.set_page_config(page_title="Rough Country Lead Generator", page_icon="🤖")
if not check_password():
    st.stop()

# --- NEW: Load existing accounts at the start ---
existing_accounts = load_existing_accounts()

# Display logo and title
col1, col2 = st.columns([0.1, 0.9])
with col1:
    st.image("RC_Leads.png", width=60)
with col2:
    st.markdown("Rough Country Lead Generator")

API_KEY = st.secrets["GOOGLE_API_KEY"]

# UI Setup
with st.sidebar:
    st.header("Search Settings")
    max_locations = st.number_input("Max number of locations to find:", min_value=10, max_value=10000, value=50, step=1)
    st.markdown("---")
    use_metro_search = st.checkbox("Pick Metro Areas (If not selected, I will do a national search using a 30 mile radius of a central zip code in each metro")
    selected_metros = []
    if use_metro_search:
        selected_metros = st.multiselect("Select Metro Areas:", options=TOP_100_METROS)

# Chat & State Initialization
if "messages" not in st.session_state:
    st.session_state.messages = [{"role": "assistant", "content": "What kind of place are you looking for? I will generate a CSV file with the results based on a random national search or you can select metro areas on the left"}]
if "search_results" not in st.session_state:
    st.session_state.search_results = []

for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# Main Application Logic
if prompt := st.chat_input("e.g., 'truck accessories and installation'"):
    # ...(Search logic remains the same)...
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    with st.chat_message("assistant"):
        with st.spinner(f"Scouting for up to {max_locations} places..."):
            # ...(The entire search block is the same)...
            search_areas, search_radius, search_type = [], 0, ""
            if use_metro_search and selected_metros:
                search_areas, search_radius, search_type = selected_metros, 40000, "Metro Area"
            else:
                try:
                    search_areas = pd.read_csv("zips.csv")['zipcode'].astype(str).tolist()
                    random.shuffle(search_areas)
                    search_radius, search_type = 5000, "Zip Code"
                except FileNotFoundError:
                    st.error("`zips.csv` not found. Please select a metro area.")
                    st.stop()
            
            all_results, found_place_ids = [], set()
            for area in search_areas:
                if len(all_results) >= max_locations: break
                st.write(f"Searching in {search_type}: {area}...")
                location = geocode_zip(API_KEY, area)
                if not location: continue

                places = search_places(API_KEY, prompt, location['lat'], location['lng'], search_radius)
                for place in places:
                    if len(all_results) >= max_locations: break
                    place_id = place['place_id']
                    if place_id not in found_place_ids:
                        found_place_ids.add(place_id)
                        details = get_place_details(API_KEY, place_id)
                        if not details: continue
                        
                        image_labels, image_urls, image_streams = [], [], []
                        photo_refs = [p['photo_reference'] for p in details.get('photos', [])[:3]]
                        for ref in photo_refs:
                            image_urls.append(get_photo_url(API_KEY, ref))
                            img_stream = get_place_photos(API_KEY, ref)
                            if img_stream:
                                image_streams.append(img_stream)
                                if not image_labels:
                                   image_labels.extend(analyze_image_labels(img_stream.getvalue()))
                        
                        score = calculate_score(details, image_labels, prompt)
                        all_results.append({
                            "score": score, "details": details, "image_urls": image_urls, 
                            "image_labels": list(set(image_labels)), "images": image_streams
                        })
            
            if not all_results:
                st.warning("Sorry, no matching places were found.")
                st.session_state.search_results = []
            else:
                st.session_state.search_results = sorted(all_results, key=lambda x: x['score'], reverse=False)
                st.success(f"Found {len(st.session_state.search_results)} locations! Review and select them below.")
                st.rerun()

# Display Results and Selection
if st.session_state.search_results:
    for result in st.session_state.search_results:
        details = result['details']
        place_id = details['place_id']
        
        # --- CHANGE 1: Added expanded=True to auto-expand the results ---
        with st.expander(f"**{details.get('name', 'N/A')}** (Tier: {result['score']})", expanded=True):
            col1, col2 = st.columns([0.7, 0.3])
            with col1:
                # --- CHANGE 2: Display "Yes" or "No" for existing accounts ---
                is_existing = place_id in existing_accounts
                status_text = "Yes" if is_existing else "No"
                st.markdown(f"**Existing Account:** {status_text}")
                
                st.markdown(f"**Address:** {details.get('formatted_address', 'N/A')}")
                st.markdown(f"**Phone:** {details.get('formatted_phone_number', 'N/A')}")
                st.markdown(f"**Website:** {details.get('website', 'N/A')}")
            
            with col2:
                st.checkbox("Good for research", key=f"good_{place_id}")
            
            if result['images']:
                st.image(result['images'], width=150)

    # Filtered CSV Download
    good_results = []
    for result in st.session_state.search_results:
        place_id = result['details']['place_id']
        if st.session_state.get(f"good_{place_id}", False):
            good_results.append(result)

    if good_results:
        st.sidebar.markdown("---")
        st.sidebar.header("Download Selections")
        
        data_for_df = []
        for res in good_results:
            details = res['details']
            place_id = details.get('place_id')
            description = details.get('editorial_summary', {}).get('overview', 'N/A')
            
            # --- CHANGE 3: Set status to "Yes" or "No" for the CSV ---
            is_existing = place_id in existing_accounts
            status = "Yes" if is_existing else "No"
            
            record = {
                "Name": details.get('name'),
                "Existing_Account": status,  # Changed column header
                "Score": res['score'],
                "Address": details.get('formatted_address'),
                "Phone": details.get('formatted_phone_number'),
                "Website": details.get('website'),
                "PlaceID": place_id,
                "Description": description,
                "Google_Types": ', '.join(details.get('types', [])),
                "Detected_Image_Keywords": ', '.join(res['image_labels']),
                "Image_URL_1": res['image_urls'][0] if len(res['image_urls']) > 0 else None,
                "Image_URL_2": res['image_urls'][1] if len(res['image_urls']) > 1 else None,
                "Image_URL_3": res['image_urls'][2] if len(res['image_urls']) > 2 else None,
            }
            data_for_df.append(record)
        
        df = pd.DataFrame(data_for_df)
        csv = df.to_csv(index=False).encode('utf-8')

        st.sidebar.download_button(
           label=f"Download {len(good_results)} Selected Locations",
           data=csv,
           file_name=f"selected_locations.csv",
           mime="text/csv",
        )
