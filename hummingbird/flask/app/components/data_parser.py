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
    
# JSON to Markdown parser
def json_md_parser(json_value):
    markdown = ""
    for key, value in json_value.items():
        markdown += f"**{key.capitalize()}**: {value}\n\n"
    return markdown

# String to Boolean parser 
def parse_bool(value):
    if isinstance(value, bool):
        return value
    
    if isinstance(value, str):
        return value.lower() in ('true', '1', 't', 'y', 'yes')
    
    return False

# Firestore timestamps to ISO 8601 string format parser
def parse_timestamps(doc):

    for key, value in doc.items():
        if isinstance(value, datetime):
            doc[key] = value.isoformat()
    return doc