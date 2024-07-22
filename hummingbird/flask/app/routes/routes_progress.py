from flask import request

from flask_restful import reqparse, Resource

from google.cloud.firestore_v1.base_query import FieldFilter

from datetime import datetime

from ..components import data_parser, data_validator, progress_calculator

def initializeProgressRoutes(api, firestore_client, storage_bucket):
    class UpdateProgress(Resource):
        def post(self, user_id, goal_id):
            try:
                timestamp = datetime.now()

                goal_ref = firestore_client.collection('users').document(user_id).collection('goals').document(goal_id)
                goal_doc = goal_ref.get()

                if not goal_doc.exists:
                    return {'message': 'Goal not found'}, 404

                goal_data = goal_doc.to_dict()
                goal_data = data_parser.parse_timestamps(goal_data)

                try:
                    data_validator.validate_goal_type(goal_data.get('goal_type'))
                except ValueError as e:
                    return {'message': str(e)}, 400

                progress = progress_calculator.recalculate_progress(goal_ref, goal_data, user_id)

                goal_ref.update({'progress': progress})

                #Log progress update
                progress_ref = goal_ref.collection('progress').document()
                progress_data = {
                    "progress": progress,
                    "timestamp": timestamp
                }
                progress_ref.set(progress_data)

                return{'message': 'Progress updated successfully', 'progress': progress},
            except Exception as e:
                return {'message': f'An error occurred: {str(e)}'}, 500

    api.add_resource(UpdateProgress, '/update_progress/<string:user_id>/<string:goal_id>')
                    
