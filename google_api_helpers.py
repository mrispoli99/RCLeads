# google_api_helpers.py (Updated Version)

import requests
import streamlit as st
from io import BytesIO

# Import the Vision client library and credentials helper
from google.cloud import vision
from google.oauth2 import service_account

# --- Functions using API Key (No changes here) ---
@st.cache_data
def geocode_zip(_api_key, zip_code):
    # ... same as before ...
    endpoint_url = "https://maps.googleapis.com/maps/api/geocode/json"
    params = {'address': zip_code, 'key': _api_key}
    response = requests.get(endpoint_url, params=params)
    if response.status_code == 200:
        results = response.json().get('results', [])
        if results:
            location = results[0]['geometry']['location']
            return {'lat': location['lat'], 'lng': location['lng']}
    return None

def search_places(api_key, query, location_lat, location_lng):
    # ... same as before ...
    endpoint_url = "https://maps.googleapis.com/maps/api/place/textsearch/json"
    search_radius_meters = 30000
    params = {
        'query': query,
        'location': f'{location_lat},{location_lng}',
        'radius': search_radius_meters,
        'key': api_key
    }
    response = requests.get(endpoint_url, params=params)
    if response.status_code == 200:
        return response.json().get('results', [])
    return []

def get_place_details(api_key, place_id):
    """Gets detailed information for a specific place."""
    endpoint_url = "https://maps.googleapis.com/maps/api/place/details/json"
    
    # NEW: Added 'editorial_summary' and 'types' to the fields we request
    fields = "name,formatted_address,formatted_phone_number,website,place_id,photo,editorial_summary,types"
    
    params = {
        'place_id': place_id,
        'fields': fields,
        'key': api_key
    }
    response = requests.get(endpoint_url, params=params)
    if response.status_code == 200:
        return response.json().get('result', {})
    return {}

def get_place_photos(api_key, photo_reference, max_width=800):
    # ... same as before ...
    endpoint_url = "https://maps.googleapis.com/maps/api/place/photo"
    params = { 'photoreference': photo_reference, 'maxwidth': max_width, 'key': api_key }
    response = requests.get(endpoint_url, params=params)
    if response.status_code == 200:
        return BytesIO(response.content)
    return None
    
# NEW function to construct a photo URL
def get_photo_url(api_key, photo_reference, max_width=800):
    """Constructs the URL for a Google Place photo."""
    # This URL includes your API key and is suitable for temporary use or embedding.
    return f"https://maps.googleapis.com/maps/api/place/photo?maxwidth={max_width}&photoreference={photo_reference}&key={api_key}"


# --- UPDATED FUNCTION using JSON Credentials ---
@st.cache_data
def analyze_image_labels(image_content):
    """Analyzes an image using the Google Cloud Vision client library and service account credentials."""
    try:
        # Load credentials from Streamlit's secrets
        creds = service_account.Credentials.from_service_account_info(st.secrets["gcp_service_account"])
        client = vision.ImageAnnotatorClient(credentials=creds)

        # Prepare the image for the API
        image = vision.Image(content=image_content)

        # Perform label detection
        response = client.label_detection(image=image)
        labels = response.label_annotations
        
        # Return a list of label descriptions
        return [label.description.lower() for label in labels]
        
    except Exception as e:
        st.error(f"Error with Vision API: {e}")

        return []
