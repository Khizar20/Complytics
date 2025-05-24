async def init_db():
    try:
        # Initialize other collections
        // ... existing code ...

        # Initialize compliance chat history collection with new schema
        if 'compliance_chat_history' not in await db.list_collection_names():
            await db.create_collection('compliance_chat_history')
            # Create indexes for efficient querying
            await db.compliance_chat_history.create_index([('user_id', 1)])
            await db.compliance_chat_history.create_index([('session_id', 1)])
            await db.compliance_chat_history.create_index([('last_updated', -1)])
            # Create compound index for user_id and session_id
            await db.compliance_chat_history.create_index([
                ('user_id', 1),
                ('session_id', 1)
            ], unique=True)
            print("Created compliance_chat_history collection with indexes")

        # Migrate existing data if needed
        try:
            # Check if we need to migrate (look for a document with old schema)
            old_doc = await db.compliance_chat_history.find_one({
                "messages": {"$exists": False}
            })
            
            if old_doc:
                print("Migrating existing chat history to new schema...")
                # Get all old format documents
                old_docs = await db.compliance_chat_history.find({
                    "messages": {"$exists": False}
                }).to_list(length=None)
                
                # Group by session_id
                sessions = {}
                for doc in old_docs:
                    session_id = doc.get('session_id')
                    if session_id not in sessions:
                        sessions[session_id] = {
                            'user_id': doc['user_id'],
                            'session_id': session_id,
                            'messages': [],
                            'created_at': doc['timestamp'],
                            'last_updated': doc['timestamp']
                        }
                    
                    sessions[session_id]['messages'].append({
                        'query': doc['query'],
                        'response': doc['response'],
                        'experts_consulted': doc.get('experts_consulted', []),
                        'response_time': doc.get('response_time'),
                        'timestamp': doc['timestamp']
                    })
                    
                    if doc['timestamp'] > sessions[session_id]['last_updated']:
                        sessions[session_id]['last_updated'] = doc['timestamp']
                
                # Delete old documents
                await db.compliance_chat_history.delete_many({
                    "messages": {"$exists": False}
                })
                
                # Insert new format documents
                if sessions:
                    await db.compliance_chat_history.insert_many(list(sessions.values()))
                print("Migration completed successfully")
        except Exception as e:
            print(f"Error during migration: {e}")

    except Exception as e:
        print(f"Error initializing database: {e}") 