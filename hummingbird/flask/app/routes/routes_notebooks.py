from flask import request

from flask_restful import reqparse, Resource

from google.cloud.firestore_v1.base_query import FieldFilter

from datetime import datetime

from ..components import data_parser, progress_calculator, data_validator, storage_access

def initializeNotebookRoutes(api, firestore_client):
    class CreateNotebook(Resource):
        def post(self, user_id):
            data = request.get_json()

            notebook_name = data.get('notebook_name')
            parent_notebook_id = data.get('parent_notebook_id')  # ID of the parent notebook, if any
            
            if not notebook_name:
                return {'message': 'Notebook name is required'}, 400

            try:
                created_at = datetime.now()

                if parent_notebook_id:
                    # Check if the parent notebook exists
                    parent_notebook_ref = firestore_client.collection('users').document(user_id).collection('notebooks').document(parent_notebook_id)
                    parent_notebook_doc = parent_notebook_ref.get()
                    if not parent_notebook_doc.exists:
                        return {'message': 'Parent notebook not found'}, 404

                existing_notebook_query = firestore_client.collection('users').document(user_id).collection('notebooks').where(filter = FieldFilter('notebook_name', '==', notebook_name)).stream()
                existing_notebooks = [notebook for notebook in existing_notebook_query]
                if existing_notebooks:
                    return {'message': 'A notebook with this name already exists'}, 400
                

                notebook_data = {
                    "notebook_name": notebook_name,
                    "parent_notebook_id": parent_notebook_id,
                    "created_at": created_at,
                    "updated_at": created_at
                }

                notebook_ref = firestore_client.collection('users').document(user_id).collection('notebooks').document()
                notebook_id = notebook_ref.id

                notebook_ref.set(notebook_data)

                return {'message': 'Notebook created successfully', 'notebook_id': notebook_id}, 201

            except Exception as e:
                return {'message': f'An error occurred: {str(e)}'}, 500
    
    class UpdateNotebook(Resource):
        def put(self, user_id, notebook_id):
            data = request.get_json()

            update_data = {}
            if 'notebook_name' in data:
                update_data['notebook_name'] = data['notebook_name']
            if 'parent_notebook_id' in data:
                update_data['parent_notebook_id'] = data['parent_notebook_id']

            if not update_data:
                return {'message': 'No fields to update'}, 400

            try:
                notebook_ref = firestore_client.collection('users').document(user_id).collection('notebooks').document(notebook_id)
                notebook_doc = notebook_ref.get()

                if not notebook_doc.exists:
                    return {'message': 'Notebook not found'}, 404
                
                if update_data['notebook_name']:
                    existing_notebook_query = firestore_client.collection('users').document(user_id).collection('notebooks').where(filter = FieldFilter('notebook_name', '==', update_data['notebook_name'])).stream()
                    existing_notebooks = [notebook for notebook in existing_notebook_query]
                    if existing_notebooks:
                        return {'message': 'A notebook with this name already exists'}, 400
                    

                update_data['updated_at'] = datetime.now()
                notebook_ref.update(update_data)

                return {'message': 'Notebook updated successfully'}, 200

            except Exception as e:
                return {'message': f'An error occurred: {str(e)}'}, 500

    class MoveItem(Resource):
        def put(self, user_id, item_type, item_id):
            data = request.get_json()

            new_notebook_id = data.get('new_notebook_id')
            if not new_notebook_id:
                return {'message': 'New notebook ID is required'}, 400

            try:
                new_notebook_ref = firestore_client.collection('users').document(user_id).collection('notebooks').document(new_notebook_id)
                new_notebook_doc = new_notebook_ref.get()

                if not new_notebook_doc.exists:
                    return {'message': 'New notebook not found'}, 404

                item_ref = None
                if item_type == 'notebook':
                    item_ref = firestore_client.collection('users').document(user_id).collection('notebooks').document(item_id)
                elif item_type == 'content':
                    item_ref = firestore_client.collection('users').document(user_id).collection('contents').document(item_id)
                elif item_type == 'entity':
                    item_ref = firestore_client.collection('users').document(user_id).collection('entity_relations').document('default').collection('entities').document(item_id)

                if item_ref is None:
                    return {'message': 'Invalid item type'}, 400

                item_doc = item_ref.get()
                if not item_doc.exists:
                    return {'message': f'{item_type.capitalize()} not found'}, 404

                # Update notebook_id for content or entity
                if item_type in ['content', 'entity']:
                    item_ref.update({'notebook_id': new_notebook_id, 'updated_at': datetime.now()})

                # Update parent_notebook_id for notebook
                if item_type == 'notebook':
                    item_ref.update({'parent_notebook_id': new_notebook_id, 'updated_at': datetime.now()})

                return {'message': f'{item_type.capitalize()} moved successfully'}, 200

            except Exception as e:
                return {'message': f'An error occurred: {str(e)}'}, 500

    class UpdateNotebookContents(Resource):
        def put(self, user_id, notebook_id):
            data = request.get_json()

            new_content_ids = data.get('content_ids', [])
            new_entity_ids = data.get('entity_ids', [])

            if not new_content_ids and not new_entity_ids:
                return {'message': 'No content or entity IDs provided'}, 400

            try:
                notebook_ref = firestore_client.collection('users').document(user_id).collection('notebooks').document(notebook_id)
                notebook_doc = notebook_ref.get()

                if not notebook_doc.exists:
                    return {'message': 'Notebook not found'}, 404

                batch = firestore_client.batch()

                # Update contents
                for content_id in new_content_ids:
                    content_ref = firestore_client.collection('users').document(user_id).collection('content').document(content_id)
                    batch.update(content_ref, {'notebook_id': notebook_id, 'updated_at': datetime.now()})

                # Update entities
                for entity_id in new_entity_ids:
                    entity_ref = firestore_client.collection('users').document(user_id).collection('entity_relations').document('default').collection('entities').document(entity_id)
                    batch.update(entity_ref, {'notebook_id': notebook_id, 'updated_at': datetime.now()})

                batch.commit()

                return {'message': 'Notebook contents updated successfully'}, 200

            except Exception as e:
                return {'message': f'An error occurred: {str(e)}'}, 500
            
    class GetNotebookByID(Resource):
        def get(self, user_id, notebook_id):
            try:
                notebook_ref = firestore_client.collection('users').document(user_id).collection('notebooks').document(notebook_id)
                notebook_doc = notebook_ref.get()

                if not notebook_doc.exists:
                    return {'message': 'Notebook not found'}, 404

                notebook_data = notebook_doc.to_dict()
                notebook_data = data_parser.parse_timestamps(notebook_data)
                notebook_data['notebook_id'] = notebook_doc.id
                return notebook_data, 200

            except Exception as e:
                return {'message': f'An error occurred: {str(e)}'}, 500
            
    class GetNotebookByAttribute(Resource):
        def get(self, user_id):
            attribute = request.args.get('attribute')
            value = request.args.get('value')

            if not attribute or value is None:
                return {'message': 'Attribute and value query parameters are required'}, 400

            try:
                notebooks_ref = firestore_client.collection('users').document(user_id).collection('notebooks')
                notebook_docs = notebooks_ref.where(attribute, '==', value).stream()

                notebooks = []
                for notebook_doc in notebook_docs:
                    notebook_data = notebook_doc.to_dict()
                    notebook_data = data_parser.parse_timestamps(notebook_data)
                    notebook_data['notebook_id'] = notebook_doc.id
                    notebooks.append(notebook_data)

                if notebooks:
                    return notebooks, 200
                else:
                    return {'message': 'No notebooks found with the specified attribute and value'}, 404

            except Exception as e:
                return {'message': f'An error occurred: {str(e)}'}, 500
            
    class GetAllNotebooks(Resource):
        def get(self, user_id):
            try:
                notebooks_ref = firestore_client.collection('users').document(user_id).collection('notebooks')
                notebook_docs = notebooks_ref.stream()

                notebooks = []
                for notebook_doc in notebook_docs:
                    notebook_data = notebook_doc.to_dict()
                    notebook_data = data_parser.parse_timestamps(notebook_data)
                    notebook_data['notebook_id'] = notebook_doc.id
                    notebooks.append(notebook_data)

                if notebooks:
                    return notebooks, 200
                else:
                    return {'message': 'No notebooks found'}, 404

            except Exception as e:
                return {'message': f'An error occurred: {str(e)}'}, 500
            
    class GetNotebookContent(Resource):
        def get(self, user_id, notebook_id):
            try:
                notebook_ref = firestore_client.collection('users').document(user_id).collection('notebooks').document(notebook_id)
                notebook_doc = notebook_ref.get()

                if not notebook_doc.exists:
                    return {'message': 'Notebook not found'}, 404
                
                notebook_data = notebook_doc.to_dict()
                notebook_data = data_parser.parse_timestamps(notebook_data)

                # Retrieve sub-notebooks
                sub_notebooks_ref = firestore_client.collection('users').document(user_id).collection('notebooks')
                sub_notebook_docs = sub_notebooks_ref.where('parent_notebook_id', '==', notebook_id).stream()
                
                sub_notebooks = []
                for sub_notebook_doc in sub_notebook_docs:
                    sub_notebook_data = sub_notebook_doc.to_dict()
                    sub_notebook_data = data_parser.parse_timestamps(sub_notebook_data)
                    sub_notebook_data['notebook_id'] = sub_notebook_doc.id
                    
                    sub_notebooks.append(sub_notebook_data)

                # Retrieve contents
                contents_ref = firestore_client.collection('users').document(user_id).collection('contents')
                content_docs = contents_ref.where('notebook_id', '==', notebook_id).stream()
                contents = []
                for content_doc in content_docs:
                    content_data = content_doc.to_dict()
                    content_data['content_id'] = content_doc.id
                    content_data = data_parser.parse_timestamps(content_data)
                    contents.append(content_data)

                # Retrieve entities
                entities_ref = firestore_client.collection('users').document(user_id).collection('entity_relations').document('default').collection('entities')
                entity_docs = entities_ref.where('notebook_id', '==', notebook_id).stream()
                entities = []
                for entity_doc in entity_docs:
                    entity_data = entity_doc.to_dict()
                    entity_data = data_parser.parse_timestamps(entity_data)
                    entity_data['entity_id'] = entity_doc.id
                    entities.append(entity_data)

                notebook_data['sub_notebooks'] = sub_notebooks
                notebook_data['contents'] = contents
                notebook_data['entities'] = entities

                return notebook_data, 200

            except Exception as e:
                return {'message': f'An error occurred: {str(e)}'}, 500
            
    class DeleteNotebookAndContents(Resource):
        def delete(self, user_id, notebook_id):
            try:
                def delete_notebook_contents(user_id, notebook_id):
                    notebook_ref = firestore_client.collection('users').document(user_id).collection('notebooks').document(notebook_id)
                    notebook_doc = notebook_ref.get()

                    if not notebook_doc.exists:
                        return False
                
                    # Get sub-notebooks
                    sub_notebooks_ref = firestore_client.collection('users').document(user_id).collection('notebooks')
                    sub_notebook_docs = sub_notebooks_ref.where(filter = FieldFilter('parent_notebook_id', '==', notebook_id)).stream()

                    for sub_notebook_doc in sub_notebook_docs:
                        sub_notebook_id = sub_notebook_doc.id
                        delete_notebook_contents(user_id, sub_notebook_id)

                    # Delete contents
                    contents_ref = firestore_client.collection('users').document(user_id).collection('contents')
                    content_docs = contents_ref.where(filter = FieldFilter('notebook_id', '==', notebook_id)).stream()
                    for content_doc in content_docs:
                        content_doc.reference.delete()

                    # Delete entities
                    entities_ref = firestore_client.collection('users').document(user_id).collection('entity_relations').document('default').collection('entities')
                    entity_docs = entities_ref.where(filter = FieldFilter('notebook_id', '==', notebook_id)).stream()
                    for entity_doc in entity_docs:
                        entity_doc.reference.delete()

                    # Delete the notebook itself
                    notebook_ref.delete()

                delete_notebook_contents(user_id, notebook_id)

                return {'message': 'Notebook and all its contents deleted successfully'}, 200

            except Exception as e:
                return {'message': f'An error occurred: {str(e)}'}, 500
    
    class DeleteNotebookOnly(Resource):
        def delete(self, user_id, notebook_id):
            try:
                notebook_ref = firestore_client.collection('users').document(user_id).collection('notebooks').document(notebook_id)
                notebook_doc = notebook_ref.get()

                if not notebook_doc.exists:
                    return {'message': 'Notebook not found'}, 404

                # Set notebook_id to null for all contents and entities within this notebook
                batch = firestore_client.batch()

                # Update contents
                contents_ref = firestore_client.collection('users').document(user_id).collection('contents')
                content_docs = contents_ref.where(filter = FieldFilter('notebook_id', '==', notebook_id)).stream()
                for content_doc in content_docs:
                    batch.update(content_doc.reference, {'notebook_id': None, 'updated_at': datetime.now()})

                # Update entities
                entities_ref = firestore_client.collection('users').document(user_id).collection('entity_relations').document('default').collection('entities')
                entity_docs = entities_ref.where(filter = FieldFilter('notebook_id', '==', notebook_id)).stream()
                for entity_doc in entity_docs:
                    batch.update(entity_doc.reference, {'notebook_id': None, 'updated_at': datetime.now()})

                # Update parent_notebook_id to null for sub-notebooks
                sub_notebooks_ref = firestore_client.collection('users').document(user_id).collection('notebooks')
                sub_notebook_docs = sub_notebooks_ref.where(filter = FieldFilter('notebook_id', '==', notebook_id)).stream()
                for sub_notebook_doc in sub_notebook_docs:
                    batch.update(sub_notebook_doc.reference, {'parent_notebook_id': None, 'updated_at': datetime.now()})

                # Delete the notebook itself
                batch.delete(notebook_ref)

                batch.commit()

                return {'message': 'Notebook deleted successfully, contents and entities reassigned'}, 200

            except Exception as e:
                return {'message': f'An error occurred: {str(e)}'}, 500

    api.add_resource(CreateNotebook, '/create_notebook/<string:user_id>')
    api.add_resource(MoveItem, '/move_item/<string:user_id>/type/<string:item_type>/item/<string:item_id>')
    api.add_resource(UpdateNotebook, '/update_notebook/<string:user_id>/notebook/<string:notebook_id>')
    api.add_resource(UpdateNotebookContents, '/update_notebook_contents/<string:user_id>/notebook/<string:notebook_id>')
    api.add_resource(GetNotebookByID, '/get_notebook/<string:user_id>/notebook/<string:notebook_id>')
    api.add_resource(GetNotebookByAttribute, '/get_notebook/<string:user_id>')
    api.add_resource(GetAllNotebooks, '/get_notebook/all/<string:user_id>')
    api.add_resource(GetNotebookContent, '/get_notebook/<string:user_id>/notebook/<string:notebook_id>/contents')
    api.add_resource(DeleteNotebookAndContents, '/delete_notebook_complete/<string:user_id>/notebook/<string:notebook_id>')
    api.add_resource(DeleteNotebookOnly, '/delete_notebook/<string:user_id>/notebook/<string:notebook_id>')