from flask import request, make_response
from flask_restful import Resource

from google.cloud import storage
from google.cloud.firestore_v1.base_query import FieldFilter

from datetime import datetime, timedelta
from urllib.parse import unquote

import requests

from ..components import data_parser

def initializeContentRoutes(api, firestore_client, storage_bucket):
    class CreateContent(Resource):
        def post(self, user_id):
            data = request.get_json()

            content_name = data.get('content_name')
            content_summary = data.get('content_summary')
            content = data.get('content')
            is_public = data_parser.parse_bool(data.get('is_public', 'false'))
            
            if not content_name:
                return {'message': 'Content name is required'}, 400

            try:
                content_ref = firestore_client.collection('users').document(user_id).collection('content')
                
                # Check if content with the same name already exists
                existing_content_query = content_ref.where(filter = FieldFilter('content_name', '==', content_name)).get()
                if existing_content_query:
                    return {'message': 'Content with this name already exists'}, 400

                new_content_ref = content_ref.document()
                content_id = new_content_ref.id

                # Upload content to Firebase Storage
                file_url = None
                if content:
                    blob = storage_bucket.blob(f'content/{user_id}/{content_id}.md')
                    blob.upload_from_string(content, content_type='text/markdown')
                    file_url = blob.public_url

                # Store metadata in Firestore
                created_at = datetime.now()

                content_data = {
                    'content_name': content_name,
                    'content_summary': content_summary,
                    'file_url': file_url,
                    'created_at': created_at,
                    'is_public': is_public,
                    'updated_at': created_at
                }

                new_content_ref.set(content_data)

                return {'message': 'Content saved successfully', 'file_url': file_url, 'content_id': content_id}, 201
            
            except Exception as e:
                return {'message': f'An error occurred: {str(e)}'}, 500
            
    class UpdateContent(Resource):
        def put(self, user_id, content_id):
            data = request.get_json()

            content_name = data.get('content_name')
            content_summary = data.get('content_summary')
            content = data.get('content')
            is_public = data.get('is_public')

            try:
                updated_at = datetime.now()
                
                # Initialize Firestore document reference
                content_ref = firestore_client.collection('users').document(user_id).collection('content').document(content_id)

                # Check if the content exists
                content_doc = content_ref.get()
                if not content_doc.exists:
                    return {'message': 'Content not found'}, 404

                # Upload updated content to Firebase Storage if content is provided
                file_url = content_doc.get('file_url')
                if content:
                    blob = storage_bucket.blob(f'content/{user_id}/{content_id}.md')
                    blob.upload_from_string(content, content_type='text/markdown')
                    file_url = blob.public_url

                update_data = {
                    'content_name': content_name,
                    'content_summary': content_summary,
                    'file_url': file_url,
                    'updated_at': updated_at
                }
                if is_public is not None:
                    update_data['is_public'] = data.__annotations__.parse_bool(is_public)


                content_ref.update({k: v for k, v in update_data.items() if v is not None})

                return {'message': 'Content updated successfully', 'file_url': file_url, 'content_id': content_id}, 200

            except Exception as e:
                return {'message': f'An error occurred: {str(e)}'}, 500
            
    class GetContentByID(Resource):
        def get(self, user_id, content_id):
            try:
                # Retrieve the document reference
                content_ref = firestore_client.collection('users').document(user_id).collection('content').document(content_id)
                
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
            
    class GetContentByName(Resource):
        def get(self, user_id):
            args = request.args
            attribute = args.get('attribute')
            value = args.get('value')

            if not attribute or not value:
                return {'message': 'Attribute and value query parameters are required'}, 400
            
            try:
                # Retrieve the document reference
                content_ref = firestore_client.collection('users').document(user_id).collection('content')
                query = content_ref.where(filter = FieldFilter(attribute, '==', value)).stream()

                content_data = None
                for content in query:
                    content_data = content.to_dict()
                    content_data = data_parser.parse_timestamps(content_data)

                    content_data['id'] = content.id
                    break
                
                if content_data:
                    return content_data, 200
                else:
                    return {'message': 'Content not found'}, 404

            except Exception as e:
                return {'message': f'An error occurred: {str(e)}'}, 500
            
    class GetAllContent(Resource):
        def get(self, user_id):
            try:
                # Check if the content_feedback document exists
                content_feedback_ref = firestore_client.collection('users').document(user_id)
                # content_feedback_doc = content_feedback_ref.get()

                # if not content_feedback_doc.exists:
                #     return {'message': 'Content-Feedback document not found'}, 404

                # Query all relations
                content_ref = content_feedback_ref.collection('content')
                query = content_ref.stream()

                content_data = []
                for content in query:
                    data = content.to_dict()
                    data = data_parser.parse_timestamps(data)
                    
                    data['id'] = content.id
                    content_data.append(data)

                if content_data:
                    return content_data, 200
                else:
                    return {'message': 'No content found'}, 404

            except Exception as e:
                return {'message': f'An error occurred: {str(e)}'}, 500
            
    class DownloadContent(Resource):
        def get(self, user_id, content_id):
            try:
                # Retrieve the file URL
                content_ref = firestore_client.collection('users').document(user_id).collection('content').document(content_id)
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
                    return make_response(response.content, 200, {'Content-Type': 'text/markdown'})
                else:
                    return {'message': f'Failed to download content: {response.status_code}'}, 400
            except Exception as e:
                return {'message': f'An error occurred: {str(e)}'}, 500
            
    class DeleteContent(Resource):
        def delete(self, user_id, content_id):
            try:
                # Initialize Firestore document reference
                content_ref = firestore_client.collection('users').document(user_id).collection('content').document(content_id)

                # Check if the content exists
                content_doc = content_ref.get()
                if not content_doc.exists:
                    return {'message': 'Content not found'}, 404

                # Retrieve the file URL from the document
                file_url = content_doc.get('file_url')
                if file_url:
                    # Extract the relative file path from the URL
                    file_path = file_url.replace(f'https://storage.googleapis.com/{storage_bucket.name}/', '')

                    # Delete the file from Firebase Storage
                    blob = storage_bucket.blob(file_path)
                    blob.delete()

                # Delete the document from Firestore
                content_ref.delete()

                return {'message': 'Content deleted successfully'}, 200

            except Exception as e:
                return {'message': f'An error occurred: {str(e)}'}, 500

    api.add_resource(CreateContent, '/create_content/<string:user_id>')
    api.add_resource(UpdateContent, '/update_content/<string:user_id>/content/<string:content_id>')
    api.add_resource(GetContentByID, '/get_content/<string:user_id>/content/<string:content_id>')
    api.add_resource(GetContentByName, '/get_content/<string:user_id>/')
    api.add_resource(GetAllContent, '/get_content/all/<string:user_id>')
    api.add_resource(DownloadContent, '/download_content/<string:user_id>/content/<string:content_id>')
    api.add_resource(DeleteContent, '/delete_content/<string:user_id>/content/<string:content_id>')  