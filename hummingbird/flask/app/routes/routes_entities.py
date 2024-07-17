from flask import Blueprint, request, jsonify
from flask_restful import reqparse, Resource

from datetime import datetime

from ..components import data_parser

def initializeEntityRoutes(api, db):
    class CreateEntity(Resource):
        def post(self, user_id):
            parser = reqparse.RequestParser()
            
            parser.add_argument('entity_type', required = True, type = str, help = 'Entity type cannot be blank')
            parser.add_argument('entity_name', required = True, type = str, help = 'Entity name cannot be blank')
            parser.add_argument('template_id', required = False, type = str)
            parser.add_argument('folder_id', required = False, type = str)
            parser.add_argument('entity_description', required = False, type = str)
            parser.add_argument('entity_content', required = False, type = data_parser.parse_json, help = 'Content must be a valid JSON structure')
            
            args = parser.parse_args()

            entity_type = args['entity_type']
            entity_name = args['entity_name']
            template_id = args['template_id']
            folder_id = args['folder_id']
            entity_description = args['entity_description']
            entity_content = args['entity_content']

            try:
                # Add created_at timestamp
                created_at = datetime.now()

                # Check if the entity_relations document exists, create it if it doesn't
                entity_relations_ref = db.collection('users').document(user_id).collection('entity_relations').document('default')
                entity_relations_doc = entity_relations_ref.get()

                if not entity_relations_doc.exists:
                    entity_relations_ref.set({})  # Create the document if it doesn't exist


                entity_ref = entity_relations_ref.collection('entities').add({
                    'entity_type': entity_type,
                    'entity_name': entity_name,
                    'template_id': template_id,
                    'folder_id': folder_id,
                    'entity_description': entity_description,
                    'entity_content': entity_content,
                    'created_at': created_at
                })

                return {'message': 'Entity data added successfully', 'id': entity_ref[1].id}, 201
            
            except Exception as e:
                return {'message': f'An error occurred: {str(e)}'}, 500
            
    class UpdateEntity(Resource):
        def put(self, user_id, entity_id):
            parser = reqparse.RequestParser()

            parser.add_argument('entity_type', required = False, type = str, help = 'Entity type cannot be blank')
            parser.add_argument('entity_name', required = False, type = str, help = 'Entity name cannot be blank')
            parser.add_argument('template_id', required = False, type = str)
            parser.add_argument('folder_id', required = False, type = str)
            parser.add_argument('entity_description', required = False, type = str)
            parser.add_argument('entity_content', required = False, type = data_parser.parse_json, help = 'Content must be a valid JSON structure')
            
            args = parser.parse_args()

            update_data = {}

            if args['entity_type']:
                update_data['entity_type'] = args['entity_type']
            if args['entity_name']:
                update_data['entity_name'] = args['entity_name']
            if args['template_id']:
                update_data['template_id'] = args['template_id']
            if args['folder_id']:
                update_data['folder_id'] = args['folder_id']
            if args['entity_description']:
                update_data['entity_description'] = args['entity_description']
            if args['entity_content']:
                update_data['entity_content'] = args['entity_content']

            try:
                # Add updated_at timestamp
                update_data['updated_at'] = datetime.now()
                
                entity_ref = db.collection('users').document(user_id).collection('entity_relations').document('default').collection('entities').document(entity_id)
                entity_doc = entity_ref.get()

                if not entity_doc.exists:
                    return {'message': 'Entity not found'}, 404

                entity_ref.update(update_data)

                return {'message': 'Entity data updated successfully'}, 200
            
            except Exception as e:
                 return {'message': f'An error occurred: {str(e)}'}, 500
            
    class GetEntityByID(Resource):
        def get(self, user_id, entity_id):

            try:
                entity_ref = db.collection('users').document(user_id).collection('entity_relations').document('default').collection('entities').document(entity_id)
                entity_doc = entity_ref.get()

                if entity_doc.exists:
                    entity_data = entity_doc.to_dict()
                    entity_data['id'] = user_id
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
                entity_ref = db.collection('users').document(user_id).collection('entity_relations').document('default').collection('entities')
                query = entity_ref.where(attribute, '==', value).stream()
                
                entity_data = None
                for entity in query:
                    entity_data = entity.to_dict()
                    entity_data['id'] = entity.id
                    break
                
                if entity_data:
                    return entity_data, 200
                else:
                    return {'message': 'Entity not found'}, 404

            except Exception as e:
                return {'message': f'An error occurred: {str(e)}'}, 500
            
    class DeleteEntity(Resource):
        def delete(self, user_id, entity_id):
            try:
                entity_ref = db.collection('users').document(user_id).collection('entity_relations').document('default').collection('entities').document(entity_id)
                entity_doc = entity_ref.get()

                if not entity_doc.exists:
                    return {'message': 'Entity not found'}, 404

                entity_ref.delete()
                return {'message': 'Entity deleted successfully'}, 200
            except Exception as e:
                return {'message': f'An error occurred: {str(e)}'}, 500
            
    api.add_resource(CreateEntity, '/create_entity/<string:user_id>')
    api.add_resource(UpdateEntity, '/update_entity/<string:user_id>/entities/<string:entity_id>')
    api.add_resource(GetEntityByID, '/get_entity/<string:user_id>/entities/<string:entity_id>')
    api.add_resource(GetEntityByAttribute, '/get_entity/<string:user_id>')
    api.add_resource(DeleteEntity, '/delete_entity/<string:user_id>/entities/<string:entity_id>')