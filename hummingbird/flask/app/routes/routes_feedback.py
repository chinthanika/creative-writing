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
            
    class GetAllFeedback(Resource):
        def get(self, user_id, content_id):
            try:
                feedback_ref = firestore_client.collection('users').document(user_id).collection('content').document(content_id).collection('feedback')
                query = feedback_ref.stream()

                feedback_list = []
                for feedback_doc in query:
                    feedback_data = feedback_doc.to_dict()
                    feedback_data = data_parser.parse_timestamps(feedback_data)

                    feedback_data['feedback_id'] = feedback_doc.id  # Add feedback_id to the returned data
                    feedback_list.append(feedback_data)

                if feedback_list:
                    return feedback_list, 200
                else:
                    return {'message': 'No feedback found.'}, 404

            except Exception as e:
                return {'message': f'An error occurred: {str(e)}'}, 500

    class GetAllFeedbackByID(Resource):
            def get(self, feedback_user_id):
                try:
                    feedback_ref = firestore_client.collection_group('feedback').where(filter = FieldFilter('feedback_user_id', '==', feedback_user_id))
                    feedback_docs = feedback_ref.stream()

                    feedback_list = []
                    for feedback_doc in feedback_docs:
                        feedback_data = feedback_doc.to_dict()
                        feedback_data = data_parser.parse_timestamps(feedback_data)

                        feedback_data['feedback_id'] = feedback_doc.id  # Add feedback_id to the returned data

                        # Extract user_id and content_id from the document path
                        path_parts = feedback_doc.reference.path.split('/')
                        user_id = path_parts[1]
                        content_id = path_parts[3]

                        # Fetch the content document to check is_public attribute
                        content_ref = firestore_client.collection('users').document(user_id).collection('content').document(content_id)
                        content_doc = content_ref.get()

                        if content_doc.exists:
                            content_data = content_doc.to_dict()
                            if content_data.get('is_public'):
                                feedback_data['content_id'] = content_id
                                feedback_data['user_id'] = user_id
                            else:
                                feedback_data['content_id'] = 'private'
                                feedback_data['user_id'] = 'private'
                        else:
                            feedback_data['content_id'] = 'unknown'  # In case content document is not found

                        feedback_list.append(feedback_data)

                    if feedback_list:
                        return feedback_list, 200
                    else:
                        return {'message': 'No feedback found for this user.'}, 404

                except Exception as e:
                    return {'message': f'An error occurred: {str(e)}'}, 500
    
    class GetFeedbackByID(Resource):
        def get(self, user_id, content_id, feedback_id):
            try:
                feedback_ref = firestore_client.collection('users').document(user_id).collection('content').document(content_id).collection('feedback').document(feedback_id)
                feedback_doc = feedback_ref.get()

                if not feedback_doc.exists:
                    return {'message': 'Feedback not found.'}, 404

                feedback_data = feedback_doc.to_dict()
                feedback_data = data_parser.parse_timestamps(feedback_data)

                feedback_data['feedback_id'] = feedback_doc.id  # Add response_id to the returned data
                return feedback_data, 200

            except Exception as e:
                return {'message': f'An error occurred: {str(e)}'}, 500 

    # To maintain records and data retention, feedback will be flagged as deleted
    class DeleteFeedback(Resource):
        def delete(self, user_id, content_id, feedback_id):
            try:
                # Initialize Firestore document reference
                feedback_ref = firestore_client.collection('users').document(user_id).collection('content').document(content_id).collection('feedback').document(feedback_id)
                feedback_doc = feedback_ref.get()

                if not feedback_doc.exists:
                    return {'message': 'Feedback not found'}, 404

                # Mark feedback as deleted
                feedback_ref.update({'deleted': True})
                
                # Optionally, mark all responses as deleted
                responses_ref = feedback_ref.collection('responses')
                responses_docs = responses_ref.stream()
                for response_doc in responses_docs:
                    response_doc.reference.update({'deleted': True})

                return {'message': 'Feedback deleted successfully'}, 200

            except Exception as e:
                return {'message': f'An error occurred: {str(e)}'}, 500

    api.add_resource(CreateFeedback, '/create_feedback/<string:user_id>/content/<string:content_id>')
    api.add_resource(GetFeedbackByID, '/get_feedback/<string:user_id>/content/<string:content_id>/feedback/<string:feedback_id>')
    api.add_resource(GetAllFeedback, '/get_feedback/all/<string:user_id>/content/<string:content_id>')
    api.add_resource(GetAllFeedbackByID, '/get_feedback/all/<string:feedback_user_id>')
    api.add_resource(DeleteFeedback, '/delete_feedback/<string:user_id>/content/<string:content_id>/feedback/<string:feedback_id>')