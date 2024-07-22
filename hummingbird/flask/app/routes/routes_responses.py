from flask import Blueprint, request, jsonify
from flask_restful import reqparse, Resource

from google.cloud.firestore_v1.base_query import FieldFilter

from datetime import datetime

from ..components import data_parser

def initializeResponsesRoutes(api, firestore_client):
    class CreateResponse(Resource):
        def post(self, user_id, content_id, feedback_id):
            data = request.get_json()

            responder_id = data.get('responder_id')
            response_content = data.get('response_content')

            if not responder_id or not response_content:
                return {'message': 'Missing required fields'}, 400
            
            try:
                created_at = datetime.now()

                response_data = {
                    "responder_id": responder_id,
                    "response_content": response_content,
                    "created_at": created_at
                }

                response_ref = firestore_client.collection('users').document(user_id).collection('content').document(content_id).collection('feedback').document(feedback_id).collection('responses').document()
                response_id = response_ref.id
                response_data['response_id'] = response_id

                response_ref.set(response_data)

                return {'message': 'Response created successfully', 'response_id': response_id}, 201

            except Exception as e:
                return {'message': f'An error occurred: {str(e)}'}, 500
            
    class GetAllResponses(Resource):
        def get(self, user_id, content_id, feedback_id):
            try:
                response_ref = firestore_client.collection('users').document(user_id).collection('content').document(content_id).collection('feedback').document(feedback_id).collection('responses')
                query = response_ref.stream()

                response_list = []
                for response_doc in query:
                    response_data = response_doc.to_dict()
                    response_data = data_parser.parse_timestamps(response_data)

                    response_data['response_id'] = response_doc.id  # Add feedback_id to the returned data
                    response_list.append(response_data)

                if response_list:
                    return response_list, 200
                else:
                    return {'message': 'No responses found.'}, 404

            except Exception as e:
                return {'message': f'An error occurred: {str(e)}'}, 500
            
    class GetResponseByID(Resource):
        def get(self, user_id, content_id, feedback_id, response_id):
            try:
                response_ref = firestore_client.collection('users').document(user_id).collection('content').document(content_id).collection('feedback').document(feedback_id).collection('responses').document(response_id)
                response_doc = response_ref.get()

                if not response_doc.exists:
                    return {'message': 'Response not found.'}, 404

                response_data = response_doc.to_dict()
                response_data = data_parser.parse_timestamps(response_data)

                response_data['response_id'] = response_doc.id  # Add response_id to the returned data
                return response_data, 200

            except Exception as e:
                return {'message': f'An error occurred: {str(e)}'}, 500  

    class DeleteResponse(Resource):
        def delete(self, user_id, content_id, feedback_id, response_id):
            try:
                # Initialize Firestore document reference
                response_ref = firestore_client.collection('users').document(user_id).collection('content').document(content_id).collection('feedback').document(feedback_id).collection('responses').document(response_id)
                response_doc = response_ref.get()

                if not response_doc.exists:
                    return {'message': 'Response not found'}, 404

                # Mark response as deleted
                response_ref.update({'deleted': True})

                return {'message': 'Response deleted successfully'}, 200

            except Exception as e:
                return {'message': f'An error occurred: {str(e)}'}, 500

    api.add_resource(CreateResponse, '/create_response/<string:user_id>/content/<string:content_id>/feedback/<string:feedback_id>')
    api.add_resource(GetResponseByID, '/get_response/<string:user_id>/content/<string:content_id>/feedback/<string:feedback_id>/response/<string:response_id>')
    api.add_resource(GetAllResponses, '/get_response/all/<string:user_id>/content/<string:content_id>/feedback/<string:feedback_id>')
    api.add_resource(DeleteResponse, '/delete_response/<string:user_id>/content/<string:content_id>/feedback/<string:feedback_id>/response/<string:response_id>')