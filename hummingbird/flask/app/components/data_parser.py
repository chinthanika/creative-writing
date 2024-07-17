import json

from firebase_admin import firestore
from datetime import datetime

# JSON to Python object parser
def parse_json(value):
    if isinstance (value, dict):
        return(value)
    
    try:
        print(value)
        return json.loads(value)
    
    except json.JSONDecodeError:
        raise ValueError('Invalid JSON structure')

# String to Boolean parser 
def parse_bool(value):
    if isinstance(value, bool):
        return value
    
    if value.lower() in ['true', '1', 't', 'y', 'yes']:
        return True
    
    elif value.lower() in ['false', '0', 'f', 'n', 'no']:
        return False
    
    else:
        raise ValueError('Boolean value expected.')

# Firestore timestamps to ISO 8601 string format parser
def parse_timestamps(doc):

    for key, value in doc.items():
        if isinstance(value, datetime):
            doc[key] = value.isoformat()
    return doc