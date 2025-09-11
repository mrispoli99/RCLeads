# scorer.py

def calculate_score(place_details, image_labels, user_query):
    """
    Calculates a raw score based on a custom 10-point system,
    then converts it to a tiered score (1=Top, 2=Mid, 3=Low).
    """
    raw_score = 0
    
    # --- 1. Name Analysis (Max 5 points) ---
    name_keywords = ['truck', 'atv', 'install', 'installation']
    place_name = place_details.get('name', '').lower()

    if any(keyword in place_name for keyword in name_keywords):
        raw_score += 5

    # --- 2. Image Analysis (Max 5 points) ---
    if image_labels:
        garage_bay_labels = ['garage door', 'automotive repair shop', 'auto part', 'vehicle repair', 'service bay']
        truck_labels = ['truck', 'pickup truck', 'commercial vehicle', 'monster truck']
        showroom_labels = ['retail', 'showroom', 'display case', 'store', 'shelf', 'merchandise']

        if any(label in image_labels for label in garage_bay_labels):
            raw_score += 2
        
        if any(label in image_labels for label in truck_labels):
            raw_score += 2

        if any(label in image_labels for label in showroom_labels):
            raw_score += 1
            
    # --- 3. Convert Raw Score to Final Tier ---
    if raw_score >= 7:
        return 1  # Top Tier
    elif raw_score >= 4:
        return 2  # Mid Tier
    else:
        return 3  # Low Tier

