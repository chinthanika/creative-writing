from datetime import timedelta
from urllib.parse import unquote
import requests

def img_access(content, storage_bucket, user_id, entity_id):
    # This function is optional and only needed if images are not publicly accessible.
    lines = content.split('\n')
    new_lines = []
    for line in lines:
        if line.startswith('!['):  # Markdown image syntax
            start_idx = line.find('(') + 1
            end_idx = line.find(')')
            url = line[start_idx:end_idx]
            filename = url.split('/')[-1]
            blob = storage_bucket.blob(f'entities/{user_id}/{entity_id}/images/{filename}')
            signed_url = blob.generate_signed_url(expiration=timedelta(minutes=15))
            new_line = line.replace(url, signed_url)
            new_lines.append(new_line)
        else:
            new_lines.append(line)
    return '\n'.join(new_lines)

def content_download(user_id, content_id, firestore_client, storage_bucket):
    # Retrieve the file URL from Firestore
    content_ref = firestore_client.collection('users').document(user_id).collection('content').document(content_id)
    content_doc = content_ref.get()
    if not content_doc.exists:
        raise RuntimeError('Content not found')

    file_url = content_doc.get('file_url')
    if not file_url:
        raise RuntimeError('File URL not found in document')

    # Extract the relative file path from the URL
    file_path = file_url.replace(f'https://storage.googleapis.com/{storage_bucket.name}/', '')

    # URL-decode the file path to ensure it's correct
    decoded_file_path = unquote(file_path)

    # Generate a signed URL for the file
    blob = storage_bucket.blob(decoded_file_path)
    signed_url = blob.generate_signed_url(expiration=timedelta(minutes=15))

    # Send a GET request to the signed URL
    response = requests.get(signed_url)
    if response.status_code == 200:
        return response.content
    else:
        raise RuntimeError(f'Failed to download content: {response.status_code}')