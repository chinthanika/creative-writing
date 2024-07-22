from flask import Blueprint, request, jsonify, make_response
from flask_restful import reqparse, Resource

from google.cloud.firestore_v1.base_query import FieldFilter

from datetime import datetime, timedelta

import requests

from ..components import data_parser, storage_access

def initializeEntityRoutes(api, firestore_client, storage_bucket):
    class CreateEntity(Resource):
        def post(self, user_id):
            data = request.get_json()

            entity_type = data.get('entity_type')
            entity_name = data.get('entity_name')
            template_id = data.get('template_id')
            folder_id = data.get('folder_id')
            entity_description = data.get('entity_description')
            entity_content = data.get('entity_content')
            is_public = data_parser.parse_bool(data.get('is_public', 'false'))

            if not entity_name or not entity_type:
                return{'message': 'Entity Name and Entity Type are required.'}, 400

            try:
                # Add created_at timestamp
                created_at = datetime.now()

                # Check if the entity_relations document exists, create it if it doesn't
                entities_ref = firestore_client.collection('users').document(user_id).collection('entity_relations').document('default').collection('entities')


                existing_entity_query = entities_ref.where(filter = FieldFilter('entity_name', '==', entity_name)).stream()
                existing_entities = [entity for entity in existing_entity_query]
                if existing_entities:
                    return {'message': 'An entity with this name already exists'}, 400
                
                new_entity_ref = entities_ref.document()
                entity_id = new_entity_ref.id

                # Handle entity content and image uploads
                image_urls = data.get('image_urls', {})
                if 'images' in request.files:
                    image_files = request.files.getlist('images')
                    for image_file in image_files:
                        blob = storage_bucket.blob(f'entities/{user_id}/{entity_id}/images/{image_file.filename}')
                        blob.upload_from_file(image_file, content_type=image_file.content_type)
                        image_urls[image_file.filename] = blob.public_url

                # Upload entity to Firebase Storage
                file_url = None

                # Upload entity_content to storage
                if entity_content:
                    entity_content = data_parser.json_md_parser(entity_content)

                    # Replace image placeholders with URLs in the content
                    for filename, url in image_urls.items():
                        entity_content = entity_content.replace(f'{{{{ {filename} }}}}', url)

                    blob = storage_bucket.blob(f'entities/{user_id}/{entity_id}.md')
                    blob.upload_from_string(entity_content, content_type='text/markdown')
                    file_url = blob.public_url

                entity_data = {
                    'entity_type': entity_type,
                    'entity_name': entity_name,
                    'template_id': template_id,
                    'folder_id': folder_id,
                    'entity_description': entity_description,
                    'file_url': file_url,
                    'is_public': is_public,
                    'created_at': created_at,
                    'updated_at': created_at
                }

                new_entity_ref.set(entity_data)

                return {'message': 'Entity saved successfully', 'file_url': file_url, 'entity_id': entity_id}, 201
            
            except Exception as e:
                return {'message': f'An error occurred: {str(e)}'}, 500
            
    class UploadEntityImages(Resource):
        def post(self, user_id, entity_id):
            image_files = request.files.getlist('images')
            image_urls = {}

            for image_file in image_files:
                try:
                    blob = storage_bucket.blob(f'entities/{user_id}/{entity_id}/images/{image_file.filename}')
                    blob.upload_from_file(image_file, content_type=image_file.content_type)
                    image_urls[image_file.filename] = blob.public_url

                except Exception as e:
                    return {'message': f'An error occurred while uploading images: {str(e)}'}, 500

            return {'image_urls': image_urls}, 201
            
    class UpdateEntity(Resource):
        def put(self, user_id, entity_id):
            data = request.get_json()

            entity_type = data.get('entity_type')
            entity_name = data.get('entity_name')
            template_id = data.get('template_id')
            folder_id = data.get('folder_id')
            entity_description = data.get('entity_description')
            entity_content = data.get('entity_content')
            is_public = data.get('is_public')

            try:
                updated_at = datetime.now()

                # Initialize Firestore document reference
                entity_ref = firestore_client.collection('users').document(user_id).collection('entity_relations').document('default').collection('entities').document(entity_id)

                entity_doc = entity_ref.get()
                if not entity_doc.exists:
                    return {'message': 'Entity not found.'}, 404
                
                file_url = entity_doc.get('file_url')

                # Retrieve existing image URLs from the content file
                existing_content_blob = storage_bucket.blob(f'entities/{user_id}/{entity_id}.md')
                existing_content = existing_content_blob.download_as_string().decode('utf-8')

                # Extract existing image URLs
                existing_image_urls = {}
                for line in existing_content.split('\n'):
                    if line.startswith('!['):  # Markdown image syntax
                        start_idx = line.find('(') + 1
                        end_idx = line.find(')')
                        url = line[start_idx:end_idx]
                        filename = url.split('/')[-1]
                        existing_image_urls[filename] = url

                # Handle new image uploads
                new_image_urls = data.get('image_urls', {})
                if 'images' in request.files:
                    image_files = request.files.getlist('images')
                    for image_file in image_files:
                        blob = storage_bucket.blob(f'entities/{user_id}/{entity_id}/images/{image_file.filename}')
                        blob.upload_from_file(image_file, content_type=image_file.content_type)
                        new_image_urls[image_file.filename] = blob.public_url

                # Combine existing and new image URLs
                combined_image_urls = {**existing_image_urls, **new_image_urls}

                if entity_content:
                    entity_content = data_parser.json_md_parser(entity_content)

                    # Replace image placeholders with URLs in the content
                    for filename, url in combined_image_urls.items():
                        entity_content = entity_content.replace(f'{{{{ {filename} }}}}', url)

                    blob = storage_bucket.blob(f'entities/{user_id}/{entity_id}.md')
                    blob.upload_from_string(entity_content, content_type='text/markdown')
                    file_url = blob.public_url

                # Remove old images that are no longer referenced in the content
                for filename in existing_image_urls:
                    if filename not in new_image_urls:
                        blob = storage_bucket.blob(f'entities/{user_id}/{entity_id}/images/{filename}')
                        blob.delete()

                update_data = {
                    'entity_type': entity_type,
                    'entity_name': entity_name,
                    'template_id': template_id,
                    'folder_id': folder_id,
                    'entity_description': entity_description,
                    'file_url': file_url,
                    'updated_at': updated_at
                }

                if is_public is not None:
                    update_data['is_public'] = data.__annotations__.parse_bool(is_public)

                entity_ref.update({k: v for k, v in update_data.items() if v is not None})
                
                return {'message': 'Entity updated successfully', 'file_url': file_url, 'entity__id': entity_id}, 200

            except Exception as e:
                return {'message': f'An error occurred: {str(e)}'}, 500
            
    class GetEntityByID(Resource):
        def get(self, user_id, entity_id):
            try:
                entity_ref = firestore_client.collection('users').document(user_id).collection('entity_relations').document('default').collection('entities').document(entity_id)
                entity_doc = entity_ref.get()

                if entity_doc.exists:
                    entity_data = entity_doc.to_dict()
                    entity_data = data_parser.parse_timestamps(entity_data)
                    
                    entity_data['id'] = entity_id
                    return entity_data, 200
                
                else:
                    return {'message': 'Entity not found'}, 404

            except Exception as e:
                return {'message': f'An error occurred: {str(e)}'}, 500
            
    class GetEntityByAttribute(Resource):
        def get(self, user_id):
            # Get query parameters
            args = request.args
            attribute = args.get('attribute')
            value = args.get('value')

            if not attribute or not value:
                return {'message': 'Attribute and value query parameters are required'}, 400

            try:
                entity_ref = firestore_client.collection('users').document(user_id).collection('entity_relations').document('default').collection('entities')
                query = entity_ref.where(filter = FieldFilter(attribute, '==', value)).stream()
                
                entity_data = None
                for entity in query:
                    entity_data = entity.to_dict()
                    entity_data = data_parser.parse_timestamps(entity_data)

                    entity_data['id'] = entity.id
                    break
                
                if entity_data:
                    return entity_data, 200
                else:
                    return {'message': 'Entity not found'}, 404

            except Exception as e:
                return {'message': f'An error occurred: {str(e)}'}, 500


    class GetAllEntities(Resource):
        def get(self, user_id):
            try:
                # Check if the entity_relations document exists
                entity_relations_ref = firestore_client.collection('users').document(user_id).collection('entity_relations').document('default')
                entity_relations_doc = entity_relations_ref.get()

                if not entity_relations_doc.exists:
                    return {'message': 'Entity relations document not found'}, 404

                # Query all relations
                entities_ref = entity_relations_ref.collection('entities')
                query = entities_ref.stream()

                entities_data = []
                for entity in query:
                    entity_data = entity.to_dict()
                    entity_data = data_parser.parse_timestamps(entity_data)
                    
                    entity_data['id'] = entity.id
                    entities_data.append(entity_data)

                if entities_data:
                    return entities_data, 200
                else:
                    return {'message': 'No entities found'}, 404

            except Exception as e:
                return {'message': f'An error occurred: {str(e)}'}, 500
            

    class DownloadEntity(Resource):
        def get(self, user_id, entity_id):
            try:
                entity_ref = firestore_client.collection('users').document(user_id).collection('entity_relations').document('default').collection('entities').document(entity_id)
                entity_doc = entity_ref.get()
                if not entity_doc.exists:
                    return {'message': 'Entity not found.'}, 404

                file_url = entity_doc.get('file_url')
                if not file_url:
                    return {'message': 'File URL not found in document'}, 404

                # Retrieve content from Firebase Storage
                content_blob = storage_bucket.blob(f'entities/{user_id}/{entity_id}.md')
                signed_url = content_blob.generate_signed_url(expiration=timedelta(minutes=15))

                response = requests.get(signed_url)
                if response.status_code == 200:
                    content = response.text

                    signed_content = signed_url(content, storage_bucket, user_id, entity_id)

                    return make_response(signed_content, 200, {'Content-Type': 'text/markdown'})
                else:
                    return {'message': f'Failed to download content: {response.status_code}'}, 400

            except Exception as e:
                return {'message': f'An error occurred: {str(e)}'}, 500  
            
    class DeleteEntity(Resource):
        def delete(self, user_id, entity_id):
            try:
                entity_ref = firestore_client.collection('users').document(user_id).collection('entity_relations').document('default').collection('entities').document(entity_id)
                entity_doc = entity_ref.get()

                if not entity_doc.exists:
                    return {'message': 'Entity not found'}, 404

                # Delete associated content from Firebase Storage
                content_blob = storage_bucket.blob(f'entities/{user_id}/{entity_id}.md')
                content_blob.delete()

                # Delete associated images from Firebase Storage
                image_prefix = f'entities/{user_id}/{entity_id}/images/'
                
                # There seems to be some issue here with using storage_client rather than storage_bucket
                # However, storage.Client doesn't seem to exist?
                # If something isn't working here check this
                blobs = storage_bucket.list_blobs(prefix=image_prefix)
                for blob in blobs:
                    blob.delete()

                entity_ref.delete()
                return {'message': 'Entity deleted successfully'}, 200
            except Exception as e:
                return {'message': f'An error occurred: {str(e)}'}, 500
            
    api.add_resource(CreateEntity, '/create_entity/<string:user_id>')
    api.add_resource(UpdateEntity, '/update_entity/<string:user_id>/entities/<string:entity_id>')
    api.add_resource(UploadEntityImages, '/upload_entity_image/<string:user_id>/entities/<string:entity_id>')
    api.add_resource(GetEntityByID, '/get_entity/<string:user_id>/entities/<string:entity_id>')
    api.add_resource(GetEntityByAttribute, '/get_entity/<string:user_id>')
    api.add_resource(GetAllEntities, '/get_entity/all/<string:user_id>')
    api.add_resource(DownloadEntity, '/download_entity/<string:user_id>/entities/<string:entity_id>')
    api.add_resource(DeleteEntity, '/delete_entity/<string:user_id>/entities/<string:entity_id>')