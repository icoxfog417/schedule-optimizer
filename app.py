"""Streamlit application for Hospital Schedule Agent."""

import streamlit as st
import base64
import json
import boto3
import yaml
import uuid
import re
from pathlib import Path
import streamlit.components.v1 as components


st.set_page_config(page_title="Hospital Schedule Agent", page_icon="🏥", layout="wide")


@st.cache_resource
def load_agentcore_config():
    """Load AgentCore configuration."""
    config_path = Path("deployment/.bedrock_agentcore.yaml")
    if not config_path.exists():
        st.error("AgentCore config not found. Run deployment first.")
        st.stop()
    
    with open(config_path) as f:
        return yaml.safe_load(f)


def encode_file(file_bytes):
    """Encode file to base64."""
    return base64.b64encode(file_bytes).decode()


def invoke_agent(prompt, files=None):
    """Invoke AgentCore agent."""
    config = load_agentcore_config()
    agent_name = config['default_agent']
    agent_arn = config['agents'][agent_name]['bedrock_agentcore']['agent_arn']
    region = config['agents'][agent_name]['aws']['region']
    
    payload = {"prompt": prompt}
    if files:
        payload.update(files)
    
    client = boto3.client('bedrock-agentcore', region_name=region)
    response = client.invoke_agent_runtime(
        agentRuntimeArn=agent_arn,
        runtimeSessionId=st.session_state.session_id,
        payload=json.dumps(payload)
    )
    
    return json.loads(response['response'].read())


def extract_mermaid(text):
    """Extract Mermaid diagram from text and return text without mermaid, mermaid code."""
    pattern = r'```mermaid\n(.*?)\n```'
    match = re.search(pattern, text, re.DOTALL)
    if match:
        mermaid_code = match.group(1)
        text_without_mermaid = re.sub(pattern, '', text, flags=re.DOTALL).strip()
        return text_without_mermaid, mermaid_code
    return text, None


def extract_file_content(response):
    """Extract base64 file content from agent response."""
    result = response.get('result', '')
    # Check if result contains file_content
    if 'file_content' in str(result):
        import json
        # Try to parse as JSON if it's a tool result
        if isinstance(result, str) and '{' in result:
            # Extract JSON from text
            start = result.find('{')
            end = result.rfind('}') + 1
            if start >= 0 and end > start:
                data = json.loads(result[start:end])
                if 'file_content' in data:
                    return data['file_content'], data.get('file_path', 'schedule.xlsx')
    return None, None


def render_mermaid(mermaid_code):
    """Render Mermaid diagram."""
    html = f"""
    <html>
    <head>
    <script src="https://cdn.jsdelivr.net/npm/mermaid@10/dist/mermaid.min.js"></script>
    <script>
        mermaid.initialize({{ startOnLoad: true }});
    </script>
    </head>
    <body>
    <div class="mermaid">
    {mermaid_code}
    </div>
    </body>
    </html>
    """
    components.html(html, height=600, scrolling=True)


# Initialize session state
if 'session_id' not in st.session_state:
    st.session_state.session_id = f"streamlit-{str(uuid.uuid4())}"
if 'messages' not in st.session_state:
    st.session_state.messages = []

# UI
st.title("🏥 Hospital Schedule Agent")
st.caption(f"Session: {st.session_state.session_id}")

# Sidebar for file upload
with st.sidebar:
    st.header("📁 Upload Data Files")
    
    therapist_file = st.file_uploader("therapist.csv", type=['csv'])
    prescription_file = st.file_uploader("prescription.csv", type=['csv'])
    shift_file = st.file_uploader("shift Excel", type=['xlsx'])
    
    if st.button("Upload Files", disabled=not (therapist_file and prescription_file and shift_file)):
        files = {
            "therapist_csv": encode_file(therapist_file.read()),
            "prescription_csv": encode_file(prescription_file.read()),
            "shift_excel": encode_file(shift_file.read())
        }
        
        with st.spinner("Uploading files..."):
            response = invoke_agent("I've uploaded the data files. Please process them.", files)
            result = response.get('result', str(response))
            st.session_state.messages.append({"role": "assistant", "content": result})
            st.rerun()

# Chat interface
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        text, mermaid = extract_mermaid(msg["content"])
        st.markdown(text)
        if mermaid:
            render_mermaid(mermaid)
        
        # Check for downloadable file
        if msg["role"] == "assistant" and "file_download" in msg:
            file_content = msg["file_download"]["content"]
            file_name = msg["file_download"]["name"]
            st.download_button(
                label=f"📥 Download {file_name}",
                data=base64.b64decode(file_content),
                file_name=file_name,
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )

# Chat input
if prompt := st.chat_input("Ask the agent..."):
    st.session_state.messages.append({"role": "user", "content": prompt})
    
    with st.chat_message("user"):
        st.write(prompt)
    
    with st.chat_message("assistant"):
        with st.spinner("Thinking..."):
            response = invoke_agent(prompt)
            result = response.get('result', str(response))
            text, mermaid = extract_mermaid(result)
            st.markdown(text)
            if mermaid:
                render_mermaid(mermaid)
            
            # Check for downloadable file
            file_content, file_path = extract_file_content(response)
            if file_content:
                file_name = file_path.split('/')[-1] if '/' in file_path else file_path
                st.download_button(
                    label=f"📥 Download {file_name}",
                    data=base64.b64decode(file_content),
                    file_name=file_name,
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                )
                # Store for message history
                st.session_state.messages[-1]["file_download"] = {
                    "content": file_content,
                    "name": file_name
                }
    
    st.session_state.messages.append({"role": "assistant", "content": result})
    st.rerun()
