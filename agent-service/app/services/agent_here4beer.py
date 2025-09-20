from here4beer_agent import Here4BeerAgent

# Initialize the agent
agent_instance = Here4BeerAgent()

if __name__ == "__main__":
    while True:
        user_input = input("You: ")
        if user_input.lower() in ["quit", "exit"]:
            break
        resp = agent_instance.query_with_memory(user_input)
        print("Agent:", resp)


