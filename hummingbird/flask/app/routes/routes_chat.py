from flask import request
from flask_restful import Resource

import logging

from datetime import datetime

import threading
import time

from ..components import data_parser

def initializeChatRoutes(api, firestore_client):

    # In-memory cache for messages
    message_cache = {}

    # Lock for thread-safe operations on the cache
    cache_lock = threading.Lock()

    # Function to flush the cache to Firestore
    def flush_cache():
        while True:
            time.sleep(60)  # Adjust the interval as needed
            with cache_lock:
                for (user_id, chat_id), messages in message_cache.items():
                    if messages:
                        try:
                            chat_ref = firestore_client.collection('users').document(user_id).collection('conversations').document(chat_id)
                            batch = firestore_client.batch()

                            for message in messages:
                                message_ref = chat_ref.collection('messages').document()
                                batch.set(message_ref, message)

                            # Update the updated_at timestamp of the conversation
                            batch.update(chat_ref, {'updated_at': datetime.now()})


                            batch.commit()
                            message_cache[(user_id, chat_id)] = []  # Clear the cache after committing
                        except Exception as e:
                            print(f"Error flushing cache: {e}")

    # Start the background thread
    threading.Thread(target=flush_cache, daemon=True).start()

    class CreateChat(Resource):
        def post(self, user_id):
            try:
                created_at = datetime.now()
                chat_data = {
                    "created_at": created_at,
                    "updated_at": created_at
                }

                chat_ref = firestore_client.collection('users').document(user_id).collection('conversations').document()
                chat_ref.set(chat_data)

                return {'message': 'Chat started successfully', 'chat_id': chat_ref.id}, 201

            except Exception as e:
                return {'message': f'An error occurred: {str(e)}'}, 500

    class StoreMessage(Resource):
        def post(self, user_id, chat_id):
            data = request.get_json()
            message_text = data.get('message_text')
            timestamp = datetime.now()

            if not message_text:
                return {'message': 'Message text is required'}, 400

            try:
                with cache_lock:
                    if (user_id, chat_id) not in message_cache:
                        message_cache[(user_id, chat_id)] = []
                    message_cache[(user_id, chat_id)].append({
                        'message_text': message_text,
                        'timestamp': timestamp,
                        'sender': 'user'
                    })

                return {'message': 'Message stored in cache'}, 201

            except Exception as e:
                logging.error(f"Error storing message for {user_id}-{chat_id}: {e}")
                return {'message': f'An error occurred: {str(e)}'}, 500
        
    class StoreBotMessage(Resource):
        def post(self, user_id, chat_id):
            data = request.get_json()
            message_text = data.get('message_text')
            timestamp = datetime.now()

            if not message_text:
                return {'message': 'Message text is required'}, 400
            
            try:
                with cache_lock:
                    if (user_id, chat_id) not in message_cache:
                        message_cache[(user_id, chat_id)] = []
                    message_cache[(user_id, chat_id)].append({
                        'message_text': message_text,
                        'timestamp': timestamp,
                        'sender': 'bot'
                    })

                return {'message': 'Message stored in cache'}, 201

            except Exception as e:
                logging.error(f"Error storing bot message for {user_id}-{chat_id}: {e}")
                return {'message': f'An error occurred: {str(e)}'}, 500
        
    class GetConversationHistory(Resource):
        def get(self, user_id, chat_id):
            try:
                chat_ref = firestore_client.collection('users').document(user_id).collection('conversations').document(chat_id)
                messages_ref = chat_ref.collection('messages').order_by('timestamp')

                message_docs = messages_ref.stream()
                messages = []
                for message_doc in message_docs:
                    message_data = message_doc.to_dict()
                    message_data['message_id'] = message_doc.id
                    message_data = data_parser.parse_timestamps(message_data)

                    messages.append(message_data)

                return messages, 200

            except Exception as e:
                return {'message': f'An error occurred: {str(e)}'}, 500

    class GetCacheMessages(Resource):
        def get(self, user_id, chat_id):
            with cache_lock:
                messages = message_cache.get((user_id, chat_id), [])
                parsed_messages = [data_parser.parse_timestamps(message) for message in messages]
                return {'messages': parsed_messages}, 200
    
    class GetAllConversations(Resource):
        def get(self, user_id):
            try:
                chats_ref = firestore_client.collection('users').document(user_id).collection('conversations')
                chat_docs = chats_ref.stream()

                chats = []
                for doc in chat_docs:
                    chat_data = doc.to_dict()
                    chat_data['chat_id'] = doc.id
                    chat_data = data_parser.parse_timestamps(chat_data)
                    chats.append(chat_data)

                return {'chats': chats}, 200

            except Exception as e:
                logging.error(f"Error getting all conversations for {user_id}: {e}")
                return {'message': f'An error occurred: {str(e)}'}, 500

    api.add_resource(CreateChat, '/create_chat/<string:user_id>')
    api.add_resource(StoreMessage, '/store_message/<string:user_id>/chat/<string:chat_id>/user')
    api.add_resource(StoreBotMessage, '/store_message/<string:user_id>/chat/<string:chat_id>/bot')
    api.add_resource(GetCacheMessages, '/get_messages/<string:user_id>/cache/<string:chat_id>')
    api.add_resource(GetConversationHistory, '/get_chat/<string:user_id>/chat/<string:chat_id>')
    api.add_resource(GetAllConversations, '/get_chats/<string:user_id>')