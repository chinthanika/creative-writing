from flask import Blueprint, request, jsonify
from flask_restful import reqparse, Resource

from google.cloud.firestore_v1.base_query import FieldFilter

from datetime import datetime

from ..components import data_parser

def initializeFeedbackRoutes(api, firestore_client):
    class CreateFeedback(Resource):
        def post(self, user_id, content_id):
            parser = reqparse.RequestParser()

            parser.add_argument('feedback_content', type=str, required=True, help='Feedback body is required')
            parser.add_argument('highlight_start', type=int, required=True, help='Highlight start is required')
            parser.add_argument('highlight_end', type=int, required=True, help='Highlight end is required')
            parser.add_argument('feedback_user_id', type=str, required=True)
            args = parser.parse_args()

            feedback_content = args['feedback_content']
            feedback_user_id = args['feedback_user_id']
            highlight_start = args['highlight_start']
            highlight_end = args['highlight_end']

            if not feedback_content or not feedback_user_id or highlight_start is None or highlight_end is None:
                return {'message': 'Missing required fields'}, 400
        
            try:
                created_at = datetime.now()
                highlight_length = (highlight_end - highlight_start)

                feedback_data = {
                    "feedback_content": feedback_content,
                    "feedback_user_id": feedback_user_id,
                    "highlight_start": highlight_start,
                    "highlight_end": highlight_end,
                    "highlight_length": highlight_length,
                    "created_at": created_at
                }

                feedback_ref = firestore_client.collection('users').document(user_id).collection('content').document(content_id).collection('feedback').document()
                feedback_id = feedback_ref.id
                feedback_data['feedback_id'] = feedback_id

                feedback_ref.set(feedback_data)

                return {'message': 'Feedback created successfully', 'feedback_id': feedback_id}, 201

            except Exception as e:
                return {'message': f'An error occurred: {str(e)}'}, 500
            

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
            
    class GetResponses(Resource):
        def get(self, user_id, content_id, feedback_id):
            try:
                responses_ref = firestore_client.collection('users').document(user_id).collection('content').document(content_id).collection('feedback').document(feedback_id).collection('responses')
                response_docs = responses_ref.stream()

                responses = []
                for response_doc in response_docs:
                    response_data = response_doc.to_dict()
                    response_data = data_parser.parse_timestamps(response_data)

                    responses.append(response_data)

                if responses:
                    return responses, 200
                else:
                    return {'message': 'No responses found.'}, 404

            except Exception as e:
                return {'message': f'An error occurred: {str(e)}'}, 500
            
    class GetAllFeedback(Resource):
        def get(self, user_id, content_id):
            try:
                feedback_ref = firestore_client.collection('users').document(user_id).collection('content').document(content_id).collection('feedback')
                query = feedback_ref.stream()

                feedback_list = []
                for feedback_doc in query:
                    feedback_data = feedback_doc.to_dict()
                    feedback_data['feedback_id'] = feedback_doc.id  # Add feedback_id to the returned data
                    feedback_list.append(feedback_data)

                if feedback_list:
                    return feedback_list, 200
                else:
                    return {'message': 'No feedback found.'}, 404

            except Exception as e:
                return {'message': f'An error occurred: {str(e)}'}, 500

    api.add_resource(CreateFeedback, '/create_feedback/<string:user_id>/content/<string:content_id>')
    api.add_resource(CreateResponse, '/create_response/<string:user_id>/content/<string:content_id>/feedback/<string:feedback_id>')
    api.add_resource(GetAllFeedback, '/get_feedback/all/<string:user_id>/content/<string:content_id>')