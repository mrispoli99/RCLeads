# scorer.py (New 10-Point System)

def calculate_score(place_details, image_labels, user_query):
    """
    Calculates a relevance score for a place based on a custom 10-point system.
    Note: The 'user_query' is no longer used in this specific scoring model
    but is kept for compatibility with the main app.
    """
    score = 0
    
    # --- 1. Name Analysis (Max 5 points) ---
    name_keywords = ['truck', 'atv', 'install', 'installation']
    place_name = place_details.get('name', '').lower()

    if any(keyword in place_name for keyword in name_keywords):
        score += 5

    # --- 2. Image Analysis (Max 5 points) ---
    if image_labels:
        # Define the visual keywords we're looking for based on Vision API labels
        garage_bay_labels = ['garage door', 'automotive repair shop', 'auto part', 'vehicle repair', 'service bay']
        truck_labels = ['truck', 'pickup truck', 'commercial vehicle', 'monster truck']
        showroom_labels = ['retail', 'showroom', 'display case', 'store', 'shelf', 'merchandise']

        # Check for garage bays (+2 points)
        if any(label in image_labels for label in garage_bay_labels):
            score += 2
        
        # Check for trucks (+2 points)
        if any(label in image_labels for label in truck_labels):
            score += 2

        # Check for a showroom/retail area (+1 point)
        if any(label in image_labels for label in showroom_labels):
            score += 1
            
    # The final score is returned (max possible is 10, though some combinations might exceed it)
    # To cap it at 10, you could use: return min(score, 10)
    return score