"""Main entry point for the schedule agent."""

from schedule_agent.core.data_store import DataStore
from schedule_agent.agent.agent import create_schedule_agent


def main():
    """Run the schedule agent in interactive mode."""
    data_store = DataStore()
    agent = create_schedule_agent(data_store)
    
    print("Hospital Schedule Agent initialized.")
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
    finally:
        data_store.cleanup()
        print("Session ended.")


if __name__ == "__main__":
    main()
