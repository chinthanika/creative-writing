from datetime import timedelta

def sign_img_urls(content, storage_bucket, user_id, entity_id):
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