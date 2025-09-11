# app.py (Final Version with Metro Area Search Override)

import streamlit as st
import pandas as pd
import random
from google_api_helpers import geocode_zip, search_places, get_place_details, get_place_photos, analyze_image_labels, get_photo_url
from scorer import calculate_score

# --- Data for Metro Area Dropdown ---
# Sourced from US Census Bureau data
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
col1, col2 = st.columns([0.1, 0.9]) 
with col1:
    st.image("RC.jpg", width=60)  
with col2:
    st.markdown("## Rough Country Lead Generator")  




API_KEY = st.secrets["GOOGLE_API_KEY"]

# --- UI Setup ---
with st.sidebar:
    st.header("Search Settings")
    max_locations = st.number_input(
        "Max number of locations to find:", 
        min_value=1, max_value=100000, value=50, step=50
    )
    st.markdown("---")
    # NEW: Metro area override controls
    use_metro_search = st.checkbox("Pick Metro Areas (If not selected, I will do a national search using a 30 mile radius of a central zip code in each metro)")
    selected_metros = []
    if use_metro_search:
        selected_metros = st.multiselect("Select Metro Areas:", options=TOP_100_METROS)

# ... Chat history setup ...
if "messages" not in st.session_state:
    st.session_state.messages = [{"role": "assistant", "content": "What kind of place are you looking for? I will generate a CSV file with the results based on a random national search or you can select metro areas on the left."}]
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# --- Main Application Logic ---
if prompt := st.chat_input("e.g., 'truck and atv accessories and installation'"):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    with st.chat_message("assistant"):
        with st.spinner(f"Scouting for up to {max_locations} places... This may take a while for large requests."):
            
            # --- NEW: Conditional Search Logic ---
            search_areas = []
            search_radius = 0
            search_type = ""

            if use_metro_search and selected_metros:
                search_areas = selected_metros
                search_radius = 40000  # 40km or ~25 miles for large metro areas
                search_type = "Metro Area"
            else:
                try:
                    zip_df = pd.read_csv("zips.csv")
                    search_areas = zip_df['zipcode'].astype(str).tolist()
                    random.shuffle(search_areas)
                    search_radius = 40000  # 5km or ~3 miles for zip codes
                    search_type = "Zip Code"
                except FileNotFoundError:
                    st.error("Error: `zips.csv` file not found. Please upload one or select a metro area to search.")
                    st.stop()
            
            # --- Universal Search Loop ---
            all_results = []
            found_place_ids = set()

            for area in search_areas:
                if len(all_results) >= max_locations:
                    break

                st.write(f"Searching in {search_type}: {area}...")
                
                # The geocode function works for both zips and metro names
                location = geocode_zip(API_KEY, area)
                if not location:
                    st.warning(f"Could not find coordinates for {area}. Skipping.")
                    continue

                places = search_places(API_KEY, prompt, location['lat'], location['lng'], search_radius)
                
                # ... (The rest of the result processing loop remains exactly the same) ...
                for place in places:
                    place_id = place['place_id']
                    if place_id not in found_place_ids:
                        found_place_ids.add(place_id)
                        details = get_place_details(API_KEY, place_id)
                        if not details: continue
                        
                        all_image_labels, image_urls = [], []
                        photo_refs = [p['photo_reference'] for p in details.get('photos', [])[:3]]

                        for ref in photo_refs:
                            img_url = get_photo_url(API_KEY, ref)
                            image_urls.append(img_url)
                            if not all_image_labels:
                                img_stream = get_place_photos(API_KEY, ref)
                                if img_stream:
                                   img_bytes = img_stream.getvalue()
                                   all_image_labels.extend(analyze_image_labels(img_bytes))
                        
                        score = calculate_score(details, all_image_labels, prompt)
                        all_results.append({
                            "score": score, "details": details, "image_urls": image_urls, "image_labels": list(set(all_image_labels))
                        })

                        if len(all_results) >= max_locations: break
            
            # ... (The rest of the CSV generation and download logic remains exactly the same) ...
            if not all_results:
                st.warning("Sorry, no matching places were found.")
            else:
                sorted_results = sorted(all_results, key=lambda x: x['score'], reverse=False)
                st.success(f"Found {len(sorted_results)} locations! Your file is ready for download.")
                
                data_for_df = []
                for result in sorted_results:
                    details, description = result['details'], details.get('editorial_summary', {}).get('overview', 'N/A')
                    record = {
                        "Name": details.get('name'), "Score": result['score'], "Address": details.get('formatted_address'),
                        "Phone": details.get('formatted_phone_number'), "Website": details.get('website'), "PlaceID": details.get('place_id'),
                        "Description": description, "Google_Types": ', '.join(details.get('types', [])),
                        "Detected_Image_Keywords": ', '.join(result['image_labels']),
                        "Image_URL_1": result['image_urls'][0] if len(result['image_urls']) > 0 else None,
                        "Image_URL_2": result['image_urls'][1] if len(result['image_urls']) > 1 else None,
                        "Image_URL_3": result['image_urls'][2] if len(result['image_urls']) > 2 else None,
                    }
                    data_for_df.append(record)
                
                df = pd.DataFrame(data_for_df)
                csv = df.to_csv(index=False).encode('utf-8')
                st.download_button(
                   label="Download Results as CSV", data=csv, file_name=f"{prompt.replace(' ', '_')}_results.csv", mime="text/csv"
                )

    st.session_state.messages.append({"role": "assistant", "content": f"I completed the search for '{prompt}'. The download link is available above."})





