
import streamlit as st
import pandas as pd
import random
import re
from google_api_helpers import geocode_zip, search_places, get_place_details, get_place_photos, analyze_image_labels, get_photo_url
from scorer import calculate_score

# --- MODIFIED: Helper function to load accounts for advanced matching ---
@st.cache_data
def load_existing_accounts(filename="accounts.csv"):
    """Loads account data and creates two lookup dictionaries for matching."""
    place_id_map = {}
    address_zip_map = {}
    try:
        df = pd.read_csv(filename, dtype={'zipcode': str}) # Read zipcode as string
        # Create a map for place_id -> sap_account_type
        if "place_id" in df.columns and "sap_account_type" in df.columns:
            id_df = df.dropna(subset=['place_id', 'sap_account_type'])
            place_id_map = dict(zip(id_df['place_id'], id_df['sap_account_type']))

        # Create a map for (first 6 of address, zipcode) -> sap_account_type
        if "addr" in df.columns and "zipcode" in df.columns and "sap_account_type" in df.columns:
            addr_df = df.dropna(subset=['addr', 'zipcode', 'sap_account_type'])
            for index, row in addr_df.iterrows():
                # Standardize the address key: lowercase, first 6 chars
                addr_key = str(row['addr']).lower().strip()[:6]
                zip_key = str(row['zipcode']).strip()
                address_zip_map[(addr_key, zip_key)] = row['sap_account_type']
                
    except FileNotFoundError:
        pass # It's okay if the file doesn't exist
    except Exception as e:
        st.error(f"Error loading {filename}: {e}")

    return place_id_map, address_zip_map
    
# --- NEW: Helper function for the new matching logic ---
def get_account_status(details, place_id_map, address_zip_map):
    """Checks for a match by place_id first, then by address + zip."""
    place_id = details.get('place_id')

    # Method 1: Check for a direct place_id match
    if place_id and place_id in place_id_map:
        return place_id_map[place_id]

    # Method 2: Check by address and zip code
    address = details.get('formatted_address', '')
    if address:
        # Standardize the address from Google for lookup
        addr_lower = address.lower()
        addr_key = addr_lower.strip()[:6]
        
        # Extract 5-digit zip code from the formatted address
        zip_match = re.search(r'\b\d{5}\b', address)
        if zip_match:
            zip_key = zip_match.group(0)
            if (addr_key, zip_key) in address_zip_map:
                return address_zip_map[(addr_key, zip_key)]

    # If no match is found by either method
    return "New"
        
        
 # Helper function to load zip codes for the dropdown
@st.cache_data
def load_zip_list(filename="zips.csv"):
    try:
        df = pd.read_csv(filename)
        return sorted(df['zipcode'].astype(str).tolist())
    except FileNotFoundError:
        return []


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
    
    
existing_accounts = load_existing_accounts()
# --- THIS IS THE CORRECTED LINE THAT DEFINES THE MISSING VARIABLES ---
place_id_accounts, address_accounts = load_existing_accounts()
ALL_ZIPS = load_zip_list()

# --- NEW: Load existing accounts at the start ---
existing_accounts = load_existing_accounts()

# Display logo and title
col1, col2 = st.columns([0.1, 0.9])
with col1:
    st.image("RC_Leads.png", width=60)
with col2:
    st.markdown("Rough Country Lead Generator")

API_KEY = st.secrets["GOOGLE_API_KEY"]

# --- MODIFIED: UI Setup with new filter controls ---
with st.sidebar:
    st.header("Search Settings")
    max_locations = st.number_input("Max number of locations to find:", min_value=1, max_value=10000, value=50, step=1)
    st.markdown("---")
    
    search_mode = st.radio("Choose Search Method:", ("Search All Zips", "Search by Metro Area", "Search by Specific Zip Code(s)"))
    
    selected_metros, selected_zips = [], []
    if search_mode == "Search by Metro Area":
        selected_metros = st.multiselect("Select Metro Areas:", options=TOP_100_METROS)
    elif search_mode == "Search by Specific Zip Code(s)":
        if ALL_ZIPS: selected_zips = st.multiselect("Select Zip Codes:", options=ALL_ZIPS)
        else: st.warning("`zips.csv` not found or is empty.")
    
    st.markdown("---")
    # --- NEW: Filter to exclude account types ---
    st.header("Filter Results")
    exclude_types = st.multiselect("Exclude Account Types:", options=["Customer", "Lead", "Prospect"])

# ... (Chat & State Initialization are unchanged) ...
if "messages" not in st.session_state: st.session_state.messages = [{"role": "assistant", "content": "What kind of place are you looking for?"}]
if "search_results" not in st.session_state: st.session_state.search_results = []
for message in st.session_state.messages:
    with st.chat_message(message["role"]): st.markdown(message["content"])

# --- Main Application Logic ---
if prompt := st.chat_input("e.g., 'truck installation and accessories'"):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"): st.markdown(prompt)

    with st.chat_message("assistant"):
        with st.spinner(f"Scouting for up to {max_locations} places..."):
            # ... (Search area selection logic is unchanged) ...
            search_areas, search_radius, search_type = [], 0, ""
            if search_mode == "Search by Metro Area":
                if selected_metros: search_areas, search_radius, search_type = selected_metros, 40000, "Metro Area"
                else: st.warning("Please select at least one metro area."); st.stop()
            elif search_mode == "Search by Specific Zip Code(s)":
                if selected_zips: search_areas, search_radius, search_type = selected_zips, 11265, "Zip Code"
                else: st.warning("Please select at least one zip code."); st.stop()
            else:
                if ALL_ZIPS:
                    search_areas = list(ALL_ZIPS)
                    random.shuffle(search_areas)
                    search_radius, search_type = 5000, "Zip Code"
                else: st.error("`zips.csv` not found or is empty."); st.stop()
            
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
                        details = get_place_details(API_KEY, place_id)
                        if not details: continue
                        
                        # --- MODIFIED: Determine status and apply filter early ---
                        account_type = get_account_status(details, place_id_accounts, address_accounts)
                        
                        if account_type in exclude_types:
                            found_place_ids.add(place_id) # Add to found set to avoid re-processing
                            continue # Skip this location

                        found_place_ids.add(place_id)
                        
                        # ... (Image processing and scoring are unchanged) ...
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
                            "image_labels": list(set(image_labels)), "images": image_streams,
                            "account_type": account_type # --- NEW: Store account type with result
                        })
            
            # ... (Result handling is unchanged) ...
            if not all_results:
                st.warning("Sorry, no matching places were found after filtering.")
                st.session_state.search_results = []
            else:
                st.session_state.search_results = sorted(all_results, key=lambda x: x['score'], reverse=False)
                st.success(f"Found {len(st.session_state.search_results)} locations! Review and select them below.")
                st.rerun()

# --- MODIFIED: Display and CSV Download ---
if st.session_state.search_results:
    for result in st.session_state.search_results:
        details = result['details']
        place_id = details['place_id']
        
        with st.expander(f"**{details.get('name', 'N/A')}** (Tier: {result['score']})", expanded=True):
            col1, col2 = st.columns([0.7, 0.3])
            with col1:
                # --- MODIFIED: Display the new account type ---
                st.markdown(f"**Account Type:** {result['account_type']}")
                st.markdown(f"**Address:** {details.get('formatted_address', 'N/A')}")
                st.markdown(f"**Phone:** {details.get('formatted_phone_number', 'N/A')}")
                st.markdown(f"**Website:** {details.get('website', 'N/A')}")
            with col2:
                st.checkbox("Good for research", key=f"good_{place_id}")
            if result['images']:
                st.image(result['images'], width=150)

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
            
            record = {
                "Name": details.get('name'),
                "Account_Type": res['account_type'], # --- MODIFIED: Use new account type
                "Score": res['score'],
                "Address": details.get('formatted_address'), "Phone": details.get('formatted_phone_number'),
                "Website": details.get('website'), "PlaceID": place_id, "Description": description,
                "Google_Types": ', '.join(details.get('types', [])), "Detected_Image_Keywords": ', '.join(res['image_labels']),
                "Image_URL_1": res['image_urls'][0] if len(res['image_urls']) > 0 else None,
                "Image_URL_2": res['image_urls'][1] if len(res['image_urls']) > 1 else None,
                "Image_URL_3": res['image_urls'][2] if len(res['image_urls']) > 2 else None,
            }
            data_for_df.append(record)
        df = pd.DataFrame(data_for_df)
        csv = df.to_csv(index=False).encode('utf-8')
        st.sidebar.download_button(
           label=f"Download {len(good_results)} Selected Locations", data=csv,
           file_name=f"selected_locations.csv", mime="text/csv",
        )



