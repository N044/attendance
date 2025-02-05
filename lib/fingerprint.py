import os
import pandas as pd

FINGERPRINT_DB = 'data/fingerprint_db.csv'

# Function to register fingerprint (called once for each user)
def register_fingerprint(username):
    # Simulate fingerprint capture (you would replace this with actual fingerprint capture logic)
    # For the sake of this example, we're using a mock "fingerprint ID"
    fingerprint_id = f"{username}_fingerprint_id"
    
    # Save the fingerprint data to a CSV (if not already registered)
    if os.path.exists(FINGERPRINT_DB):
        df = pd.read_csv(FINGERPRINT_DB)
        if username in df['Username'].values:
            return False  # Fingerprint already registered
    else:
        df = pd.DataFrame(columns=['Username', 'FingerprintID'])
    
    # Append new fingerprint data
    new_entry = pd.DataFrame({'Username': [username], 'FingerprintID': [fingerprint_id]})
    df = pd.concat([df, new_entry], ignore_index=True)
    df.to_csv(FINGERPRINT_DB, index=False)
    return True

# Function to verify fingerprint (during each login attempt)
def verify_fingerprint(username):
    if os.path.exists(FINGERPRINT_DB):
        df = pd.read_csv(FINGERPRINT_DB)
        if username in df['Username'].values:
            # For this simulation, we just check if the username exists
            # In real scenarios, you'd compare captured fingerprint data with the stored one
            return True
    return False
