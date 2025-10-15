"""Main entry point for the schedule agent."""

import argparse
import base64
import json
import boto3
import yaml
from pathlib import Path
from schedule_agent.core.data_store import DataStore
from schedule_agent.agent.agent import create_schedule_agent


def load_agentcore_config():
    """Load AgentCore configuration from deployment directory."""
    config_path = Path("deployment/.bedrock_agentcore.yaml")
    if not config_path.exists():
        raise FileNotFoundError("AgentCore config not found. Run deployment first.")
    
    with open(config_path) as f:
        config = yaml.safe_load(f)
    return config


def encode_files():
    """Encode data files to base64."""
    data_dir = Path("data")
    files = {}
    
    # Encode therapist.csv
    therapist_file = data_dir / "therapist.csv"
    if therapist_file.exists():
        with open(therapist_file, 'rb') as f:
            files["therapist_csv"] = base64.b64encode(f.read()).decode()
    
    # Encode prescription.csv
    prescription_file = data_dir / "prescription.csv"
    if prescription_file.exists():
        with open(prescription_file, 'rb') as f:
            files["prescription_csv"] = base64.b64encode(f.read()).decode()
    
    # Encode shift Excel file (find any .xlsx file)
    shift_files = list(data_dir.glob("*.xlsx"))
    if shift_files:
        with open(shift_files[0], 'rb') as f:
            files["shift_excel"] = base64.b64encode(f.read()).decode()
    
    return files


def invoke_remote_agent(prompt, files=None, session_id=None):
    """Invoke deployed AgentCore agent."""
    config = load_agentcore_config()
    agent_name = config['default_agent']
    agent_arn = config['agents'][agent_name]['bedrock_agentcore']['agent_arn']
    region = config['agents'][agent_name]['aws']['region']
    
    # Prepare payload
    payload = {"prompt": prompt}
    if files:
        payload.update(files)
    
    # Use provided session ID or generate one
    if not session_id:
        import uuid
        session_id = f"test-session-{str(uuid.uuid4())}"
    
    # Invoke agent
    client = boto3.client('bedrock-agentcore', region_name=region)
    response = client.invoke_agent_runtime(
        agentRuntimeArn=agent_arn,
        runtimeSessionId=session_id,
        payload=json.dumps(payload)
    )
    
    # Parse response
    response_body = response['response'].read()
    return json.loads(response_body)


def main():
    """Run the schedule agent in interactive mode."""
    parser = argparse.ArgumentParser(description="Hospital Schedule Agent")
    parser.add_argument("--remote", action="store_true", 
                       help="Use deployed AgentCore agent instead of local")
    args = parser.parse_args()
    
    if args.remote:
        print("Hospital Schedule Agent (Remote AgentCore)")
        print("Type 'exit' or 'quit' to end the session.")
        print("Type 'upload' to send data files to agent.\n")
        
        # Generate one session ID for the entire conversation
        import uuid
        session_id = f"test-session-{str(uuid.uuid4())}"
        print(f"Session ID: {session_id}\n")
        
        try:
            while True:
                user_input = input("You: ").strip()
                
                if user_input.lower() in ['exit', 'quit']:
                    print("Ending session...")
                    break
                
                if not user_input:
                    continue
                
                # Handle file upload
                files = None
                if user_input.lower() == 'upload':
                    print("Encoding and uploading data files...")
                    files = encode_files()
                    user_input = "I've uploaded the data files. Please process them and create a schedule."
                
                # Invoke remote agent with consistent session ID
                response = invoke_remote_agent(user_input, files, session_id)
                result = response.get('result', str(response))
                print(f"\nAgent: {result}\n")
        
        except KeyboardInterrupt:
            print("\n\nSession interrupted by user.")
        except Exception as e:
            print(f"Error: {e}")
    
    else:
        # Original local mode
        data_store = DataStore()
        
        with data_store.session():
            # Load test data files
            test_data_dir = Path("data")
            if test_data_dir.exists():
                therapist_file = test_data_dir / "therapist.csv"
                prescription_file = test_data_dir / "prescription.csv"
                shift_files = list(test_data_dir.glob("*.xlsx"))
                
                if therapist_file.exists():
                    data_store.copy_therapist_file(str(therapist_file))
                    print(f"✓ Loaded therapist data from {therapist_file.name}")
                
                if prescription_file.exists():
                    data_store.copy_prescription_file(str(prescription_file))
                    print(f"✓ Loaded prescription data from {prescription_file.name}")
                
                if shift_files:
                    data_store.copy_shift_file(str(shift_files[0]))
                    print(f"✓ Loaded shift data from {shift_files[0].name}")
            
            agent = create_schedule_agent(data_store)
            
            print("\nHospital Schedule Agent initialized.")
            print("Type 'exit' or 'quit' to end the session.\n")
        
            try:
                while True:
                    user_input = input("You: ").strip()
                    
                    if user_input.lower() in ['exit', 'quit']:
                        print("Ending session...")
                        break
                    
                    if not user_input:
                        continue
                    
                    response = agent(user_input)
                    print(f"\nAgent: {response}\n")
            
            except KeyboardInterrupt:
                print("\n\nSession interrupted by user.")
        
        print("Session ended.")


if __name__ == "__main__":
    main()
