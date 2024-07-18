from flask import Blueprint, request, jsonify
from flask_restful import reqparse, Resource
from google.cloud.firestore_v1.base_query import FieldFilter

from datetime import datetime

from ..components import data_parser

def initializeRelationRoutes(api, firestore_client):
    class CreateRelation(Resource):
        def post(self, user_id):
            parser = reqparse.RequestParser()
            
            parser.add_argument('relation_type', required = True, type = str, help = 'Relation type cannot be blank')
            parser.add_argument('entity1_name', required = True, type = str, help = 'Entity 1 cannot be blank')
            parser.add_argument('entity2_name', required = True, type = str, help = 'Entity 2 cannot be blank')
            
            args = parser.parse_args()

            relation_type = args['relation_type']
            entity1_name = args['entity1_name']
            entity2_name = args['entity2_name']

            try:
                # Add created_at timestamp
                created_at = datetime.now()
                
                # Check if the entity_relations document exists, create it if it doesn't
                entity_relations_ref = firestore_client.collection('users').document(user_id).collection('entity_relations').document('default')
                entity_relations_doc = entity_relations_ref.get()

                if not entity_relations_doc.exists:
                    entity_relations_ref.set({})  # Create the document if it doesn't exist

                # Lookup entity1 ID
                entity1_ref = entity_relations_ref.collection('entities').where(filter = FieldFilter('entity_name', '==', entity1_name)).get()

                entity1 = list(entity1_ref)
                if len(entity1) != 1:
                    return {'message': 'Entity 1 not found or duplicate entities found'}, 400
                
                entity1_id = entity1[0].id

                # Lookup entity2 ID
                entity2_ref = entity_relations_ref.collection('entities').where(filter = FieldFilter('entity_name', '==', entity2_name)).get()

                entity2 = list(entity2_ref)
                if len(entity2) != 1:
                    return {'message': 'Entity 2 not found or duplicate entities found'}, 400
                
                entity2_id = entity2[0].id

                relation_ref = entity_relations_ref.collection('relations').add({
                    'relation_type': relation_type,
                    'entity1_id': entity1_id,
                    'entity2_id': entity2_id,
                    'created_at': created_at
                })

                return {'message': 'Relation data added successfully', 'id': relation_ref[1].id}, 201
            
            except Exception as e:
                return {'message': f'An error occurred: {str(e)}'}, 500
            
    class UpdateRelation(Resource):
        def put(self, user_id, relation_id):
            parser = reqparse.RequestParser()
            
            parser.add_argument('relation_type', required = False, type = str)
            parser.add_argument('entity1_name', required = False, type = str)
            parser.add_argument('entity2_name', required = False, type = str)
            
            args = parser.parse_args()

            print(args)

            update_data = {}

            try:
                if args['relation_type']:
                    update_data['relation_type'] = args['relation_type']

                # Add updated_at timestamp
                update_data['updated_at'] = datetime.now()

                # Check if the entity_relations document exists, create it if it doesn't
                entity_relations_ref = firestore_client.collection('users').document(user_id).collection('entity_relations').document('default')
                entity_relations_doc = entity_relations_ref.get()

                if not entity_relations_doc.exists:
                    entity_relations_ref.set({})  # Create the document if it doesn't exist

                if args['entity1_name']:
                    # Lookup entity1 ID
                    entity1_name = args['entity1_name']
                    entity1_ref = entity_relations_ref.collection('entities').where(filter = FieldFilter('entity_name', '==', entity1_name)).get()

                    entity1 = list(entity1_ref)
                    if len(entity1) != 1:
                        return {'message': 'Entity 1 not found or duplicate entities found'}, 400
                    
                    update_data['entity1_id'] = entity1[0].id

                if args['entity2_name']:
                    # Lookup entity2 ID
                    entity2_name = args['entity2_name']
                    entity2_ref = entity_relations_ref.collection('entities').where(filter = FieldFilter('entity_name', '==', entity2_name)).get()

                    entity2 = list(entity2_ref)
                    if len(entity2) != 1:
                        return {'message': 'Entity 2 not found or duplicate entities found'}, 400
                    
                    update_data['entity2_id'] = entity2[0].id

                print(update_data)

                relation_ref = entity_relations_ref.collection('relations').document(relation_id)
                relation_ref.update(update_data)

                return {'message': 'Relation data updated successfully'}, 200
            
            except Exception as e:
                return {'message': f'An error occurred: {str(e)}'}, 500
            
    class GetRelationByID(Resource):
        def get(self, user_id, relation_id):
            try:
                relation_ref = firestore_client.collection('users').document(user_id).collection('entity_relations').document('default').collection('relations').document(relation_id)
                relation_doc = relation_ref.get()

                if relation_doc.exists:
                    relation_data = relation_doc.to_dict()
                    relation_data = data_parser.parse_timestamps(relation_data)

                    relation_data['id'] = relation_id
                    return relation_data, 200
                
                else:
                    return {'message': 'Entity not found'}, 404

            except Exception as e:
                return {'message': f'An error occurred: {str(e)}'}, 500
            
    class GetRelationByAttribute(Resource):
        def get(self, user_id):
            args = request.args
            attribute = args.get('attribute')
            value = args.get('value')

            if not attribute or not value:
                return {'message': 'Attribute and value query parameters are required'}, 400
            
            # Check if the entity_relations document exists, create it if it doesn't
            entity_relations_ref = firestore_client.collection('users').document(user_id).collection('entity_relations').document('default')
            entity_relations_doc = entity_relations_ref.get()

            
            try:
                # If the attribute is entity1_name or entity2_name, convert the name to ID
                if attribute in ['entity1_name', 'entity2_name']:
                    entity_ref = entity_relations_ref.collection('entities').where(filter = FieldFilter('entity_name', '==', value)).get()
                    entity_list = list(entity_ref)

                    if len(entity_list) != 1:
                        return {'message': f'{attribute.capitalize().replace("_", " ")} not found or duplicate entities found'}, 400
                    
                    attribute = 'entity1_id' if attribute == 'entity1_name' else 'entity2_id'
                    value = entity_list[0].id

                relations_ref = entity_relations_ref.collection('relations')
                query = relations_ref.where(filter = FieldFilter(attribute, '==', value)).stream()
                
                relations_data = None
                for relations in query:
                    relations_data = relations.to_dict()
                    relations_data = data_parser.parse_timestamps(relations_data)

                    relations_data['id'] = relations.id
                    break
                
                if relations_data:
                    return relations_data, 200
                else:
                    return {'message': 'Relation not found'}, 404

            except Exception as e:
                return {'message': f'An error occurred: {str(e)}'}, 500
            
    class GetAllRelations(Resource):
        def get(self, user_id):
            try:
                # Check if the entity_relations document exists
                entity_relations_ref = firestore_client.collection('users').document(user_id).collection('entity_relations').document('default')
                entity_relations_doc = entity_relations_ref.get()

                if not entity_relations_doc.exists:
                    return {'message': 'Entity relations document not found'}, 404

                # Query all relations
                relations_ref = entity_relations_ref.collection('relations')
                query = relations_ref.stream()

                relations_data = []
                for relation in query:
                    relation_data = relation.to_dict()
                    relation_data = data_parser.parse_timestamps(relation_data)
                    
                    relation_data['id'] = relation.id
                    relations_data.append(relation_data)

                if relations_data:
                    return relations_data, 200
                else:
                    return {'message': 'No relations found'}, 404

            except Exception as e:
                return {'message': f'An error occurred: {str(e)}'}, 500
            
    class DeleteRelation(Resource):
        def delete(self, user_id, relation_id):
            try:
                relation_ref = firestore_client.collection('users').document(user_id).collection('entity_relations').document('default').collection('relations').document(relation_id)
                relation_doc = relation_ref.get()

                if not relation_doc.exists:
                    return {'message': 'Entity not found'}, 404

                relation_ref.delete()
                return {'message': 'Relation deleted successfully'}, 200
            except Exception as e:
                return {'message': f'An error occurred: {str(e)}'}, 500

    api.add_resource(CreateRelation, '/create_relation/<string:user_id>')
    api.add_resource(UpdateRelation, '/update_relation/<string:user_id>/relations/<string:relation_id>')
    api.add_resource(GetRelationByID, '/get_relation/<string:user_id>/relations/<string:relation_id>')
    api.add_resource(GetRelationByAttribute, '/get_relation/<string:user_id>')
    api.add_resource(GetAllRelations, '/get_relation/all/<string:user_id>')
    api.add_resource(DeleteRelation, '/delete_relation/<string:user_id>/relations/<string:relation_id>') 