"""Main agent implementation using Strands Agents."""

from strands import Agent
from strands.models import BedrockModel
from schedule_agent.core.data_store import DataStore
from schedule_agent.agent.tools import create_schedule_tools
from schedule_agent.agent.config import (
    AGENT_NAME,
    SYSTEM_PROMPT,
    AGENT_DESCRIPTION,
    DEFAULT_MODEL_CONFIG,
    AVAILABLE_MODELS,
)


def create_schedule_agent(data_store: DataStore = None, model_key: str = None) -> Agent:
    """Create and configure the unified schedule agent.
    
    Args:
        data_store: Optional DataStore instance. If None, creates a new one.
        model_key: Model key from AVAILABLE_MODELS. If None, uses default.
        
    Returns:
        Configured Agent instance ready for use
    """
    if data_store is None:
        data_store = DataStore()
    
    tools = create_schedule_tools(data_store)
    
    # Get model ID from key or use default
    if model_key and model_key in AVAILABLE_MODELS:
        model_id = AVAILABLE_MODELS[model_key]
    else:
        model_id = DEFAULT_MODEL_CONFIG["model_id"]
    
    model = BedrockModel(
        model_id=model_id,
        temperature=DEFAULT_MODEL_CONFIG["temperature"],
        max_tokens=DEFAULT_MODEL_CONFIG["max_tokens"],
    )
    
    agent = Agent(
        name=AGENT_NAME,
        description=AGENT_DESCRIPTION,
        system_prompt=SYSTEM_PROMPT,
        model=model,
        tools=tools,
    )
    
    return agent
