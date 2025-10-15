"""Main agent implementation using Strands Agents."""

from strands import Agent
from strands.models import BedrockModel
from schedule_agent.core.data_store import DataStore
from schedule_agent.agent.tools import create_schedule_tools
from schedule_agent.agent.config import (
    AGENT_NAME,
    SYSTEM_PROMPT,
    AGENT_DESCRIPTION,
    MODEL_CONFIG,
)


def create_schedule_agent(data_store: DataStore = None) -> Agent:
    """Create and configure the unified schedule agent.
    
    Args:
        data_store: Optional DataStore instance. If None, creates a new one.
        
    Returns:
        Configured Agent instance ready for use
    """
    if data_store is None:
        data_store = DataStore()
    
    tools = create_schedule_tools(data_store)
    
    model = BedrockModel(
        model_id=MODEL_CONFIG["model_id"],
        temperature=MODEL_CONFIG["temperature"],
        max_tokens=MODEL_CONFIG["max_tokens"],
    )
    
    agent = Agent(
        name=AGENT_NAME,
        description=AGENT_DESCRIPTION,
        system_prompt=SYSTEM_PROMPT,
        model=model,
        tools=tools,
    )
    
    return agent
