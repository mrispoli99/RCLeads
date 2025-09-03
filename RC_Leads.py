# app.py (Final Version for CSV Download)

import streamlit as st
import pandas as pd
import random
from google_api_helpers import geocode_zip, search_places, get_place_details, get_place_photos, analyze_image_labels, get_photo_url
from scorer import calculate_score

# --- Page and API Key Configuration ---
st.set_page_config(page_title="Rough Country Lead Generator", page_icon="🤖")
API_KEY = st.secrets["GOOGLE_API_KEY"]

# --- Password Protection ---
def check_password():
    """Returns `True` if the user entered the correct password."""

    # Check if we've already authenticated.
    if st.session_state.get("password_correct", False):
        return True

    # Show a login form.
    with st.form("login_form"):
        password = st.text_input("Password", type="password")
        submitted = st.form_submit_button("Enter")

        if submitted:
            if password == st.secrets["APP_PASSWORD"]:
                st.session_state["password_correct"] = True
                # Rerun the app to show the main content.
                st.rerun()
            else:
                st.error("😕 Password incorrect")
    
    return False

# --- UI Setup ---
st.title("🤖 Rough Country Lead Generator")

# Run the password check. If it fails, stop the app.
if not check_password():
    st.stop()

# --- If login is successful, show the main app ---

API_KEY = st.secrets["GOOGLE_API_KEY"]

if not check_password():
    st.stop()  # Do not continue if check_password is not True.

with st.sidebar:
    st.header("Search Settings")
    max_locations = st.number_input(
        "Max number of locations to find:", 
        min_value=1, 
        max_value=100000, # Increased max value for larger searches
        value=50, 
        step=1,
        help="The bot will search until it finds this many unique locations."
    )

if "messages" not in st.session_state:
    st.session_state.messages = [{"role": "assistant", "content": "What kind of place are you looking for? I will generate a CSV file with the results."}]

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
            
            try:
                zip_df = pd.read_csv("zips.csv")
                zip_codes = zip_df['zipcode'].astype(str).tolist()
                random.shuffle(zip_codes)
            except FileNotFoundError:
                st.error("Error: `zips.csv` file not found.")
                st.stop()

            all_results = []
            found_place_ids = set()

            for zip_code in zip_codes:
                if len(all_results) >= max_locations:
                    break

                st.write(f"Searching in zip code: {zip_code}...")
                
                location = geocode_zip(API_KEY, zip_code)
                if not location:
                    continue

                places = search_places(API_KEY, prompt, location['lat'], location['lng'])
                
                for place in places:
                    place_id = place['place_id']
                    if place_id not in found_place_ids:
                        found_place_ids.add(place_id)
                        
                        details = get_place_details(API_KEY, place_id)
                        if not details:
                            continue
                        
                        all_image_labels = []
                        image_urls = []
                        photo_refs = [p['photo_reference'] for p in details.get('photos', [])[:3]]

                        for ref in photo_refs:
                            img_url = get_photo_url(API_KEY, ref)
                            image_urls.append(img_url)
                            if not all_image_labels: # Only analyze the first image
                                img_stream = get_place_photos(API_KEY, ref)
                                if img_stream:
                                   img_bytes = img_stream.getvalue()
                                   all_image_labels.extend(analyze_image_labels(img_bytes))
                        
                        score = calculate_score(details, all_image_labels, prompt)
                        
                        all_results.append({
                            "score": score,
                            "details": details,
                            "image_urls": image_urls,
                            "image_labels": list(set(all_image_labels))
                        })

                        if len(all_results) >= max_locations:
                            break
            
            # --- Prepare data and display download button ---
            if not all_results:
                st.warning("Sorry, no matching places were found.")
            else:
                sorted_results = sorted(all_results, key=lambda x: x['score'], reverse=True)
                
                st.success(f"Found {len(sorted_results)} locations! Your file is ready for download.")

                # Prepare the DataFrame with all requested columns
                data_for_df = []
                for result in sorted_results:
                    details = result['details']
                    # Google's editorial summary is nested, so we extract it carefully
                    description = details.get('editorial_summary', {}).get('overview', 'N/A')
                    
                    record = {
                        "Name": details.get('name'),
                        "Score": result['score'],
                        "Address": details.get('formatted_address'),
                        "Phone": details.get('formatted_phone_number'),
                        "Website": details.get('website'),
                        "PlaceID": details.get('place_id'),
                        "Description": description,
                        "Google_Types": ', '.join(details.get('types', [])),
                        "Detected_Image_Keywords": ', '.join(result['image_labels']),
                        "Image_URL_1": result['image_urls'][0] if len(result['image_urls']) > 0 else None,
                        "Image_URL_2": result['image_urls'][1] if len(result['image_urls']) > 1 else None,
                        "Image_URL_3": result['image_urls'][2] if len(result['image_urls']) > 2 else None,
                    }
                    data_for_df.append(record)
                
                df = pd.DataFrame(data_for_df)
                csv = df.to_csv(index=False).encode('utf-8')

                st.download_button(
                   label="Download Results as CSV",
                   data=csv,
                   file_name=f"{prompt.replace(' ', '_')}_results.csv",
                   mime="text/csv",
                )
                
                # REMOVED: The in-chat display loop is no longer here.


    st.session_state.messages.append({"role": "assistant", "content": f"I completed the search for '{prompt}'. The download link is available above."})




