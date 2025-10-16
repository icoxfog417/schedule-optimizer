from bedrock_agentcore.runtime import BedrockAgentCoreApp, BedrockAgentCoreContext
from schedule_agent.core.data_store import DataStore
from schedule_agent.agent.agent import create_schedule_agent

app = BedrockAgentCoreApp()

# Session-specific DataStore storage
session_datastores = {}

@app.entrypoint
def invoke(payload):
    """Process user input with schedule agent"""
    session_id = BedrockAgentCoreContext.get_session_id()
    
    # Debug: log session ID
    print(f"DEBUG: Session ID = {session_id}")
    print(f"DEBUG: Current sessions = {list(session_datastores.keys())}")
    
    # Extract model from payload (optional)
    model_key = payload.get("model")
    if model_key:
        print(f"DEBUG: Using model: {model_key}")
    else:
        print("DEBUG: Using default model")
    
    # Require valid session ID for security
    if not session_id:
        return {"result": "Error: No session ID provided"}
    
    # Handle file uploads if present
    if "therapist_csv" in payload:
        print(f"DEBUG: Uploading files for session {session_id}")
        
        # Clean up old session if it exists
        if session_id in session_datastores:
            print(f"DEBUG: Cleaning up old DataStore for session {session_id}")
            old_data_store = session_datastores[session_id]
            old_data_store.cleanup()
        
        # Create new DataStore for this session
        data_store = DataStore()
        data_store.initialize()  # Initialize without context manager
        
        data_store.copy_therapist_file_from_bytes(payload)
        data_store.copy_prescription_file_from_bytes(payload)
        data_store.copy_shift_file_from_bytes(payload)
        
        # Store DataStore for this session
        session_datastores[session_id] = data_store
        
        print(f"DEBUG: Stored DataStore for session {session_id}")
        
        user_message = payload.get("prompt", "")
        schedule_request = f"""Files have been uploaded successfully. Please create a schedule for target date: 2025-10-15

{user_message}"""
        
    elif session_id in session_datastores:
        print(f"DEBUG: Reusing DataStore for session {session_id}")
        data_store = session_datastores[session_id]
        schedule_request = payload.get("prompt", "Hello")
        
    else:
        print(f"DEBUG: No DataStore found for session {session_id}, creating new one")
        data_store = DataStore()
        schedule_request = payload.get("prompt", "Hello")
    
    # Create agent once with the determined DataStore and model
    agent = create_schedule_agent(data_store, model_key)
    response = agent(schedule_request)
    
    return {"result": str(response)}

if __name__ == "__main__":
    app.run()
