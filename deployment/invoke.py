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
        
        # Create agent and request schedule creation
        agent = create_schedule_agent(data_store)
        user_message = payload.get("prompt", "")
        
        schedule_request = f"""Files have been uploaded successfully. Please create a schedule for target date: 2025-10-15

{user_message}"""
        
        response = agent(schedule_request)
        return {"result": str(response)}
    
    # Check if session has DataStore
    elif session_id in session_datastores:
        print(f"DEBUG: Reusing DataStore for session {session_id}")
        
        # Reuse existing DataStore for this session
        data_store = session_datastores[session_id]
        
        # Create agent and process message
        agent = create_schedule_agent(data_store)
        user_message = payload.get("prompt", "Hello")
        response = agent(user_message)
        return {"result": str(response)}
    
    # No DataStore for this session - regular conversation
    print(f"DEBUG: No DataStore found for session {session_id}, creating new one")
    data_store = DataStore()
    agent = create_schedule_agent(data_store)
    user_message = payload.get("prompt", "Hello")
    response = agent(user_message)
    
    return {"result": str(response)}

if __name__ == "__main__":
    app.run()
