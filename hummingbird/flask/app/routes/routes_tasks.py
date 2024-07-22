from flask import request

from flask_restful import reqparse, Resource

from google.cloud.firestore_v1.base_query import FieldFilter

from datetime import datetime

from ..components import data_parser, progress_calculator, data_validator, storage_access

def intitializeTaskRoutes(api, firestore_client):
    class CreateTask(Resource):
        def post(self, user_id, goal_id):
            data = request.get_json()

            task_name = data.get('task_name')
            task_notes = data.get('task_notes')

            if not task_name:
                return {'message': 'Task name is required'}, 400
            
            try:
                # Check for existing goal with the same goal_name
                tasks_ref = firestore_client.collection('users').document(user_id).collection('goals').document(goal_id).collection('tasks')
                existing_tasks = tasks_ref.where(filter = FieldFilter('task_name', '==', task_name)).stream()

                if any(existing_tasks):
                    return {'message': 'A task with this name already exists'}, 400
                
                created_at = datetime.now()

                task_data = {
                    "task_name": task_name,
                    "task_notes": task_notes,
                    "completed": False,
                    "created_at": created_at
                }

                task_ref = tasks_ref.document()
                task_id = task_ref.id
                task_data['task_id'] = task_id

                task_ref.set(task_data)

                return {'message': 'Task created successfully', 'task_id': task_ref.id}, 201
            
            except Exception as e:
                return {'message': f'An error occurred: {(e)}'}, 500
            
    class UpdateTask(Resource):
        def put(self, user_id, goal_id, task_id):
            data = request.get_json()

            update_data = {}
            if 'task_name' in data:
                update_data['task_name'] = data['task_name']
            if 'task_notes' in data:
                update_data['task_notes'] = data['task_notes']
            if 'completed' in data:
                update_data['completed'] = data_parser.parse_bool(data['completed'])

            if not update_data:
                return {'message': 'No fields to update'}, 400

            try:
                task_ref = firestore_client.collection('users').document(user_id).collection('goals').document(goal_id).collection('tasks').document(task_id)
                task_doc = task_ref.get()

                if not task_doc.exists:
                    return {'message': 'Task not found'}, 404

                task_ref.update(update_data)

                # Update goal progress if the completion status was updated
                if 'completed' in update_data:
                    goal_ref = firestore_client.collection('users').document(user_id).collection('goals').document(goal_id)
                    goal_doc = goal_ref.get()
                    goal_data = goal_doc.to_dict()

                    # Recalculate the progress
                    # progress = progress_calculator.recalculate_progress(goal_ref, goal_data, user_id)

                    # # Update the progress in the goal document
                    # goal_ref.update({'progress': progress})

                return {'message': 'Task updated successfully', 'updated_data': update_data}, 200

            except Exception as e:
                return {'message': f'An error occurred: {str(e)}'}, 500
            
    class GetTaskByID(Resource):
        def get(self, user_id, goal_id, task_id):
            try:
                task_ref = firestore_client.collection('users').document(user_id).collection('goals').document(goal_id).collection('tasks').document(task_id)
                task_doc = task_ref.get()

                if not task_doc.exists:
                    return {'message': 'Task not found'}, 404

                task_data = task_doc.to_dict()
                task_data = data_parser.parse_timestamps(task_data)

                task_data['task_id'] = task_doc.id
                return task_data, 200

            except Exception as e:
                return {'message': f'An error occurred: {str(e)}'}, 500
            
    class GetTasksByAttribute(Resource):
        def get(self, user_id, goal_id):
            attribute = request.args.get('attribute')
            value = request.args.get('value')

            if not attribute or value is None:
                return {'message': 'Attribute and value query parameters are required'}, 400

            try:
                # Convert the value to the appropriate type if needed
                if attribute == 'completed':
                    value = data_parser.parse_bool(value)
                    if value is None:
                        return {'message': 'Invalid boolean value for completed attribute'}, 400

                # Reference to the tasks collection for the specific goal and user
                tasks_ref = firestore_client.collection('users').document(user_id).collection('goals').document(goal_id).collection('tasks')
                
                # Filter tasks based on the attribute and value
                task_docs = tasks_ref.where(attribute, '==', value).stream()

                tasks = []
                for task_doc in task_docs:
                    task_data = task_doc.to_dict()
                    task_data = data_parser.parse_timestamps(task_data)
                    task_data['task_id'] = task_doc.id
                    tasks.append(task_data)

                if tasks:
                    return tasks, 200
                else:
                    return {'message': 'No tasks found with the specified attribute and value'}, 404

            except Exception as e:
                return {'message': f'An error occurred: {str(e)}'}, 500
            
    class GetAllTasksForGoal(Resource):
        def get(self, user_id, goal_id):
            try:
                tasks_ref = firestore_client.collection('users').document(user_id).collection('goals').document(goal_id).collection('tasks')
                task_docs = tasks_ref.stream()

                tasks = []
                for task_doc in task_docs:
                    task_data = task_doc.to_dict()
                    task_data = data_parser.parse_timestamps(task_data)

                    task_data['task_id'] = task_doc.id
                    tasks.append(task_data)

                if tasks:
                    return tasks, 200
                else:
                    return {'message': 'No tasks found'}, 404

            except Exception as e:
                return {'message': f'An error occurred: {str(e)}'}, 500
                
    class DeleteTask(Resource):
        def delete(self, user_id, goal_id, task_id):
            try:
                task_ref = firestore_client.collection('users').document(user_id).collection('goals').document(goal_id).collection('tasks').document(task_id)
                task_doc = task_ref.get()

                if not task_doc.exists:
                    return {'message': 'Task not found'}, 404

                task_ref.delete()

                # # Update goal progress
                # goal_ref = firestore_client.collection('users').document(user_id).collection('goals').document(goal_id)
                # goal_doc = goal_ref.get()
                # goal_data = goal_doc.to_dict()

                # # Recalculate the progress
                # progress = progress_calculator.recalculate_progress(goal_ref, goal_data, user_id)

                # # Update the progress in the goal document
                # goal_ref.update({'progress': progress})

                return {'message': 'Task deleted successfully'}, 200

            except Exception as e:
                return {'message': f'An error occurred: {str(e)}'}, 500
                    
    api.add_resource(CreateTask, '/create_task/<string:user_id>/goal/<string:goal_id>')
    api.add_resource(UpdateTask, '/update_task/<string:user_id>/goal/<string:goal_id>/task/<string:task_id>')
    api.add_resource(GetTaskByID, '/get_task/<string:user_id>/goal/<string:goal_id>/task/<string:task_id>')
    api.add_resource(GetTasksByAttribute, '/get_task/<string:user_id>/goal/<string:goal_id>')
    api.add_resource(GetAllTasksForGoal, '/get_task/all/<string:user_id>/goal/<string:goal_id>')
    api.add_resource(DeleteTask, '/delete_task/<string:user_id>/goal/<string:goal_id>/task/<string:task_id>')