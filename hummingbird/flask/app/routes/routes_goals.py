from flask import request

from flask_restful import reqparse, Resource

from google.cloud.firestore_v1.base_query import FieldFilter

from datetime import datetime

from ..components import data_parser, progress_calculator, data_validator, storage_access

def initializeGoalsRoutes(api, firestore_client):
    class CreateGoal(Resource):
        def post (self, user_id):
            data = request.get_json()

            goal_name = data.get('goal_name')
            goal_type = data.get('goal_type')
            goal_content = data.get('content_id')
            target = data.get('target')
            notes = data.get('notes')
            tasks = data.get('tasks', [])

            if not goal_name or not goal_type or not target:
                return {'message': 'Missing required fields.'}, 400

            try:
                data_validator.validate_goal_type(goal_type)

                # Check for existing goal with the same goal_name
                goals_ref = firestore_client.collection('users').document(user_id).collection('goals')
                existing_goals = goals_ref.where(filter = FieldFilter('goal_name', '==', goal_name)).stream()

                if any(existing_goals):
                    return {'message': 'A goal with this name already exists'}, 400

                created_at = datetime.now()

                goal_data = {
                    "goal_name": goal_name,
                    "goal_type": goal_type,
                    "target": target,
                    "notes": notes,
                    "created_at": created_at,
                    "progress": 0
                }

                if goal_type == "number_of_words" and goal_content:
                    goal_data["content_id"] = goal_content

                goal_ref = goals_ref.document()
                goal_id = goal_ref.id
                goal_data['goal_id'] = goal_id

                goal_ref.set(goal_data)

                if goal_type == 'user_defined':
                    for task in tasks:
                        task_name = task.get('task_name')
                        task_notes = task.get('task_notes')
                        task_data = {
                            "task_name": task_name,
                            "task_notes": task_notes,
                            "completed": False,
                            "created_at": created_at
                        }

                        task_ref = goal_ref.collection('tasks').document()
                        task_ref.set(task_data)

                return {'message': 'Goal created successfully', 'goal_id': goal_id}, 201
            
            except Exception as e:
                return {'message': f'An error occurred: {str(e)}'}, 500
            
    class UpdateGoal(Resource):
        def put(self, user_id, goal_id):
            data  = request.get_json()

            update_data = {}
            if 'goal_name' in data:
                update_data['goal_name'] = data['goal_name']

            if 'goal_type' in data:
                try:
                    data_validator.validate_goal_type(data['goal_type'])
                    update_data['goal_type'] = data['goal_type']
                except ValueError as e:
                    return {'message': str(e)}, 400
                
            if 'target' in data:
                update_data['target'] = data['target']
            if 'content_id' in data:
                update_data['content_id'] = data['content_id']
                
            if not update_data:
                return {'message': 'No fields to update.'}, 400
            
            try:
                goal_ref = firestore_client.collection('users').document(user_id).collection('goals').document(goal_id)
                goal_doc = goal_ref.get()

                if not goal_doc.exists:
                    return {'message': 'Goal not found'}, 404

                # Update the goal data
                goal_ref.update(update_data)

                # Fetch the updated goal data
                goal_doc = goal_ref.get()
                goal_data = goal_doc.to_dict()

                # Recalculate the progress
                progress = progress_calculator.recalculate_progress(goal_ref, goal_data, user_id)

                # Update the progress in the goal document
                goal_ref.update({'progress': progress})

                return {'message': 'Goal updated successfully', 'progress': progress}, 200

            except Exception as e:
                return {'message': f'An error occurred: {str(e)}'}, 500
            
    class GetGoalByID(Resource):
        def get(self, user_id, goal_id):
            try:
                goal_ref = firestore_client.collection('users').document(user_id).collection('goals').document(goal_id)
                goal_doc = goal_ref.get()

                if not goal_doc.exists:
                    return {'message': 'Goal not found'}, 404

                goal_data = goal_doc.to_dict()
                goal_data = data_parser.parse_timestamps(goal_data)

                goal_data['goal_id'] = goal_doc.id
                return goal_data, 200

            except Exception as e:
                return {'message': f'An error occurred: {str(e)}'}, 500
            
    class GetGoalByAttribute(Resource):
        def get(self, user_id):
            attribute = request.args.get('attribute')
            value = request.args.get('value')

            if not attribute or not value:
                return {'message': 'Attribute and value query parameters are required'}, 400

            try:
                goals_ref = firestore_client.collection('users').document(user_id).collection('goals')
                goals_query = goals_ref.where(attribute, '==', value)
                goal_docs = goals_query.stream()

                goals = []
                for goal_doc in goal_docs:
                    goal_data = goal_doc.to_dict()
                    goal_data = data_parser.parse_timestamps(goal_data)

                    goal_data['goal_id'] = goal_doc.id
                    goals.append(goal_data)

                if goals:
                    return goals, 200
                else:
                    return {'message': 'No goals found with the specified attribute'}, 404

            except Exception as e:
                return {'message': f'An error occurred: {str(e)}'}, 500
            
    class GetAllGoals(Resource):
        def get(self, user_id):
            try:
                goals_ref = firestore_client.collection('users').document(user_id).collection('goals')
                goal_docs = goals_ref.stream()

                goals = []
                for goal_doc in goal_docs:
                    goal_data = goal_doc.to_dict()
                    goal_data = data_parser.parse_timestamps(goal_data)

                    goal_data['goal_id'] = goal_doc.id
                    goals.append(goal_data)

                if goals:
                    return goals, 200
                else:
                    return{'message': 'No goals found.'}, 400
                
            except Exception as e:
                return {'message': f'an error occurred: {str(e)}'}, 500
            
    class DeleteGoal(Resource):
        def delete(self, user_id, goal_id):
            try:
                goal_ref = firestore_client.collection('users').document(user_id).collection('goals').document(goal_id)
                goal_doc = goal_ref.get()

                if not goal_doc.exists:
                    return {'message': 'Goal not found'}, 404

                # Delete progress and tasks subcollections
                progress_ref = goal_ref.collection('progress')
                for progress_doc in progress_ref.stream():
                    progress_doc.reference.delete()

                tasks_ref = goal_ref.collection('tasks')
                for task_doc in tasks_ref.stream():
                    task_doc.reference.delete()

                # Delete the goal document
                goal_ref.delete()
                return {'message': 'Goal deleted successfully'}, 200

            except Exception as e:
                return {'message': f'An error occurred: {str(e)}'}, 500
            
    api.add_resource(CreateGoal, '/create_goal/<string:user_id>')
    api.add_resource(UpdateGoal, '/update_goal/<string:user_id>/<string:goal_id>')
    api.add_resource(GetGoalByID, '/get_goal/<string:user_id>/goal/<string:goal_id>')
    api.add_resource(GetGoalByAttribute, '/get_goal/<string:user_id>')
    api.add_resource(GetAllGoals, '/get_goal/all/<string:user_id>')
    api.add_resource(DeleteGoal, '/delete_goal/<string:user_id>/goal/<string:goal_id>')