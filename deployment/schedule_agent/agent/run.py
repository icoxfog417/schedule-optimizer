"""CLI entry point for running the schedule agent."""

import re
from schedule_agent.core.data_store import DataStore
from schedule_agent.agent.agent import create_schedule_agent
from schedule_agent.agent.config import AVAILABLE_MODELS


def extract_model_from_prompt(prompt: str) -> tuple[str, str]:
    """Extract model specification from user prompt.
    
    Args:
        prompt: User input that may contain model specification
        
    Returns:
        Tuple of (model_key, cleaned_prompt)
    """
    # Look for model specification like "use claude-sonnet-4-5" or "model: claude-haiku-4-5"
    model_pattern = r'(?:use|model:?)\s+(claude-[a-z0-9-]+)'
    match = re.search(model_pattern, prompt.lower())
    
    if match:
        model_key = match.group(1)
        if model_key in AVAILABLE_MODELS:
            # Remove model specification from prompt
            cleaned_prompt = re.sub(model_pattern, '', prompt, flags=re.IGNORECASE).strip()
            return model_key, cleaned_prompt
    
    return None, prompt


def main():
    """Run the schedule agent in interactive mode."""
    data_store = DataStore()
    current_model = None
    agent = None
    
    print("Hospital Schedule Agent initialized.")
    print(f"Available models: {', '.join(AVAILABLE_MODELS.keys())}")
    print("Specify model with: 'use claude-sonnet-4-5' or 'model: claude-haiku-4-5'")
    print("Type 'exit' or 'quit' to end the session.\n")
    
    try:
        while True:
            user_input = input("You: ").strip()
            
            if user_input.lower() in ['exit', 'quit']:
                print("Ending session...")
                break
            
            if not user_input:
                continue
            
            # Extract model specification from prompt
            model_key, cleaned_prompt = extract_model_from_prompt(user_input)
            
            # Create new agent if model changed or first time
            if model_key != current_model:
                if model_key:
                    print(f"Switching to model: {model_key}")
                    current_model = model_key
                agent = create_schedule_agent(data_store, current_model)
            elif agent is None:
                agent = create_schedule_agent(data_store)
            
            response = agent(cleaned_prompt)
            print(f"\nAgent: {response}\n")
    
    except KeyboardInterrupt:
        print("\n\nSession interrupted by user.")
    finally:
        data_store.cleanup()
        print("Session ended.")


if __name__ == "__main__":
    main()
