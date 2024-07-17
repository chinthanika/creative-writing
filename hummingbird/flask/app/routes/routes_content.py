from flask import request, make_response
from flask_restful import Resource

from google.cloud import storage
from google.cloud.firestore_v1.base_query import FieldFilter

from datetime import datetime, timedelta
from urllib.parse import unquote

import requests

def initializeContentRoutes(api, firestore_client, storage_bucket):
    class CreateContent(Resource):
        def post(self, user_id):
            data = request.get_json()

            content_name = data.get('content_name')
            content_summary = data.get('content_summary')
            content = data.get('content')
            
            if not content_name:
                return {'message': 'Content name is required'}, 400
            
            try:
                content_ref = firestore_client.collection('users').document(user_id).collection('content_feedback').document('default').collection('content')
                
                # Check if content with the same name already exists
                existing_content_query = content_ref.where(filter = FieldFilter('content_name', '==', content_name)).get()
                if existing_content_query:
                    return {'message': 'Content with this name already exists'}, 400

                # Upload content to Firebase Storage
                file_url = None
                if content:
                    blob = storage_bucket.blob(f'content/{user_id}/{content_name}.txt')
                    blob.upload_from_string(content, content_type='text/plain')
                    file_url = blob.public_url

                # Store metadata in Firestore
                created_at = datetime.now()

                content_data = {
                    'content_name': content_name,
                    'content_summary': content_summary,
                    'file_url': file_url,
                    'created_at': created_at,
                    'updated_at': created_at
                }

                content_ref.document().set(content_data)

                return {'message': 'Content saved successfully', 'file_url': file_url}, 201
            
            except Exception as e:
                return {'message': f'An error occurred: {str(e)}'}, 500
            
    class UpdateContent(Resource):
        def put(self, user_id, content_id):
            data = request.get_json()

            content_name = data.get('content_name')
            content_summary = data.get('content_summary')
            content = data.get('content')

            try:
                # Initialize Firestore document reference
                content_ref = firestore_client.collection('users').document(user_id).collection('content_feedback').document('default').collection('content').document(content_id)

                # Check if the content exists
                content_doc = content_ref.get()
                if not content_doc.exists:
                    return {'message': 'Content not found'}, 404

                # Upload updated content to Firebase Storage if content is provided
                file_url = content_doc.get('file_url')
                if content:
                    blob = storage_bucket.blob(f'content/{user_id}/{content_doc.get("content_name")}.txt')
                    blob.upload_from_string(content, content_type='text/plain')
                    file_url = blob.public_url

                updated_at = datetime.utcnow()
                update_data = {
                    'content_summary': content_summary,
                    'file_url': file_url,
                    'updated_at': updated_at
                }
                content_ref.update({k: v for k, v in update_data.items() if v is not None})

                return {'message': 'Content updated successfully', 'file_url': file_url}, 200

            except Exception as e:
                return {'message': f'An error occurred: {str(e)}'}, 500
            
    class GetContentByID(Resource):
        def get(self, user_id, content_id):
            try:
                # Retrieve the document reference
                content_ref = firestore_client.collection('users').document(user_id).collection('content_feedback').document('default').collection('content').document(content_id)
                
                # Get the document
                content_doc = content_ref.get()
                if not content_doc.exists:
                    return {'message': 'Content not found'}, 404
                
                # Retrieve the file URL from the document
                file_url = content_doc.get('file_url')
                if not file_url:
                    return {'message': 'File URL not found in document'}, 404

                return {'file_url': file_url}, 200
        
            except Exception as e:
                return {'message': f'An error occurred: {str(e)}'}, 500
            
    class DownloadContent(Resource):
        def get(self, user_id, content_id):
            try:
                # Retrieve the file URL
                content_ref = firestore_client.collection('users').document(user_id).collection('content_feedback').document('default').collection('content').document(content_id)
                content_doc = content_ref.get()
                if not content_doc.exists:
                    return {'message': 'Content not found'}, 404
                
                file_url = content_doc.get('file_url')
                if not file_url:
                    return {'message': 'File URL not found in document'}, 404
                
                # Extract the relative file path from the URL
                file_path = file_url.replace(f'https://storage.googleapis.com/{storage_bucket.name}/', '')
                
                # URL-decode the file path to ensure it's correct
                decoded_file_path = unquote(file_path)

                # Debugging: Print the file path to verify correctness
                print(f'Decoded file path: {decoded_file_path}')

                # Generate a signed URL for the file
                blob = storage_bucket.blob(decoded_file_path)
                signed_url = blob.generate_signed_url(expiration=timedelta(minutes=15))

                # Debugging: Print the signed URL to verify correctness
                print(f'Signed URL: {signed_url}')

                # Send a GET request to the signed URL
                response = requests.get(signed_url)
                print(response)
                if response.status_code == 200:
                    # Serve the content directly in the response
                    return make_response(response.content, 200, {'Content-Type': 'text/plain'})
                else:
                    return {'message': f'Failed to download content: {response.status_code}'}, 400
            except Exception as e:
                return {'message': f'An error occurred: {str(e)}'}, 500

    api.add_resource(CreateContent, '/create_content/<string:user_id>')
    api.add_resource(UpdateContent, '/update_content/<string:user_id>/content/<string:content_id>')
    api.add_resource(GetContentByID, '/get_content/<string:user_id>/content/<string:content_id>')
    api.add_resource(DownloadContent, '/download_content/<string:user_id>/content/<string:content_id>')   