import sys
import os
import time
from langchain_aws.chat_models.bedrock import ChatBedrock, ToolMessage # modelo de chat Bedrock
from langchain_core.tools import tool
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_aws import ChatBedrock
from dotenv import load_dotenv
from langgraph.prebuilt import create_react_agent
from langchain.memory import ConversationSummaryMemory

load_dotenv()

# Add the parent directory to sys.path to import provider_queries
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'tools'))
from provider_queries import get_provider_db

# Initialize the provider database
provider_db = get_provider_db()

@tool("get_all_providers_tool", return_direct=True, description="Lists all food providers available in the database. Use this when user asks to see all providers or wants a complete list.")
def get_all_providers_tool():
    """Lists all food providers in the database"""
    try:
        providers = provider_db.get_all_providers()
        if not providers:
            return "No providers found in the database."

        result = "All food providers:\n"
        for provider in providers:
            result += f"- {provider['provider_name']}: {provider['item']} (${provider['price']}) - {provider['location']}, Distance: {provider['distance']}\n"
        return result
    except Exception as e:
        return f"Error retrieving providers: {str(e)}"

@tool("search_providers_by_item_tool", return_direct=True, description="Searches for providers selling a specific food item. Use this when user asks for specific foods like 'steak', 'chicken', 'eggs', etc. Input should be the food item name.")
def search_providers_by_item_tool(item: str):
    """Searches for providers selling a specific food item"""
    try:
        providers = provider_db.get_providers_by_item(item)
        if not providers:
            return f"No providers found selling '{item}'."

        result = f"Providers selling '{item}':\n"
        for provider in providers:
            result += f"- {provider['provider_name']}: ${provider['price']} - {provider['location']} (Stock: {provider['stock']}, Distance: {provider['distance']})\n"
        return result
    except Exception as e:
        return f"Error searching for item '{item}': {str(e)}"

@tool("search_providers_by_location_tool", return_direct=True, description="Searches for providers in a specific location. Use this when user asks about providers in a city or state. Input should be the location name.")
def search_providers_by_location_tool(location: str):
    """Searches for providers in a specific location"""
    try:
        providers = provider_db.get_providers_by_location(location)
        if not providers:
            return f"No providers found in '{location}'."

        result = f"Providers in '{location}':\n"
        for provider in providers:
            result += f"- {provider['provider_name']}: {provider['item']} (${provider['price']}) - Distance: {provider['distance']}\n"
        return result
    except Exception as e:
        return f"Error searching for location '{location}': {str(e)}"


@tool("get_cheapest_providers_tool", return_direct=True, description="Gets the cheapest food options available. Use this when user asks for budget options or cheapest items. Input should be the number of results to return (default 5).")
def get_cheapest_providers_tool(limit: str = "5"):
    """Gets the cheapest food options available"""
    try:
        limit_int = int(limit)
        providers = provider_db.get_cheapest_providers(limit_int)
        if not providers:
            return "No providers found."

        result = f"Top {limit_int} cheapest options:\n"
        for provider in providers:
            result += f"- {provider['item']}: ${provider['price']} from {provider['provider_name']} ({provider['location']})\n"
        return result
    except Exception as e:
        return f"Error getting cheapest providers: {str(e)}"

@tool("search_providers_by_price_range_tool", return_direct=True, description="Searches for providers within a specific price range. Use this when user mentions price constraints. Requires two inputs: minimum price and maximum price.")
def search_providers_by_price_range_tool(min_price: str, max_price: str):
    """Searches for providers within a specific price range"""
    try:
        min_p = float(min_price)
        max_p = float(max_price)
        providers = provider_db.get_providers_by_price_range(min_p, max_p)
        if not providers:
            return f"No providers found with prices between ${min_price} and ${max_price}."

        result = f"Providers with prices between ${min_price} and ${max_price}:\n"
        for provider in providers:
            result += f"- {provider['provider_name']}: {provider['item']} (${provider['price']}) - {provider['location']}\n"
        return result
    except Exception as e:
        return f"Error searching price range: {str(e)}"

@tool("get_stock_summary_tool", return_direct=True, description="Gets overall statistics about the food provider database including total providers, stock information. Use this when user asks for overview or summary information.")
def get_stock_summary_tool():
    """Gets overall statistics about the food provider database"""
    try:
        summary = provider_db.get_stock_summary()
        if not summary:
            return "No summary data available."

        result = "Database Summary:\n"
        result += f"- Total providers: {summary.get('total_providers', 0)}\n"
        result += f"- Total stock: {summary.get('total_stock', 0)} items\n"
        result += f"- Average stock per provider: {summary.get('avg_stock', 0):.1f} items\n"
        result += f"- Minimum stock: {summary.get('min_stock', 0)} items\n"
        result += f"- Maximum stock: {summary.get('max_stock', 0)} items\n"
        return result
    except Exception as e:
        return f"Error getting summary: {str(e)}"

@tool("general_search_tool", return_direct=True, description="General search across provider names, items, and locations. Use this for broad searches when user query doesn't fit specific categories. Input should be the search term.")
def general_search_tool(search_term: str):
    """General search across provider names, items, and locations"""
    try:
        providers = provider_db.search_providers(search_term)
        if not providers:
            return f"No results found for '{search_term}'."

        result = f"Search results for '{search_term}':\n"
        for provider in providers:
            result += f"- {provider['provider_name']}: {provider['item']} (${provider['price']}) - {provider['location']}\n"
        return result
    except Exception as e:
        return f"Error searching for '{search_term}': {str(e)}"

@tool("write_followup_email_tool", return_direct=True, description="Generates a professional follow-up email draft to a specific provider. Use this when user asks to write a follow-up email to a provider. Input should be the provider name.")
def write_followup_email_tool(provider_name: str):
    """Generates a follow-up email draft to a specific provider"""
    try:
        # Search for the provider to get their details
        providers = provider_db.search_providers(provider_name)
        if not providers:
            return f"Provider '{provider_name}' not found in database. Please check the name and try again."

        # Use the first matching provider
        provider = providers[0]

        # Generate email draft
        email_draft = f"""Subject: Follow-up: Food Supply Partnership Opportunity

        Dear {provider['provider_name']} Team,

        I hope this email finds you well. I am writing to follow up on a potential partnership opportunity regarding your food supply services.

        Based on our database, I see that you offer:
        - Product: {provider['item']}
        - Price: ${provider['price']}
        - Location: {provider['location']}
        - Current Stock: {provider.get('stock', 'N/A')} items

        We are interested in discussing:
        1. Bulk ordering possibilities and potential discounts
        2. Delivery schedules and logistics
        3. Quality assurance and freshness guarantees
        4. Long-term partnership terms

        Would you be available for a brief call or meeting this week to discuss how we can work together? I believe there could be mutual benefits in establishing a regular supply relationship.

        Please let me know your availability, and I'll be happy to accommodate your schedule.

        Best regards,
        [Your Name]
        [Your Company]
        [Your Contact Information]

        ---
        This email draft has been generated based on provider information from our database. Please review and customize as needed before sending."""

        return email_draft

    except Exception as e:
        return f"Error generating email for provider '{provider_name}': {str(e)}"


tools =[ get_all_providers_tool,
    search_providers_by_item_tool,
    search_providers_by_location_tool,
    get_cheapest_providers_tool,
    search_providers_by_price_range_tool,
    get_stock_summary_tool,
    general_search_tool,
    write_followup_email_tool
]

# Instancia o modelo de chat Bedrock
llm = ChatBedrock(
    model_id=os.getenv("BEDROCK_MODEL_ID"),
    provider="anthropic",
    region_name=os.getenv("AWS_REGION"),
    aws_access_key_id=os.getenv("AWS_ACCESS_KEY_ID"),
    aws_secret_access_key=os.getenv("AWS_SECRET_ACCESS_KEY"),
    aws_session_token=os.getenv("AWS_SESSION_TOKEN"),
    model_kwargs={"temperature": 0.5}
)

# Liga as tools
llm_with_tools = llm.bind_tools(tools)

# Opção de store para memória
from langchain_core.stores import InMemoryStore

## Store Chat Conversations to keep context;
store = InMemoryStore()

# Cria o agente com React, usando o store
agent = create_react_agent(
    model=llm,
    tools=tools,
    store=store,
)

SYSTEM_PROMPT = "You are a helpful agent for food providers. Use the tools available to answer users completely."

# depois, histórico de mensagens
history_messages = [
    SystemMessage(content=SYSTEM_PROMPT)
]

def query_with_memory(user_input: str, max_rounds: int = 5):
    # garante que a primeira mensagem é SystemMessage
    if not isinstance(history_messages[0], SystemMessage):
        history_messages.insert(0, SystemMessage(content=SYSTEM_PROMPT))
    
    # adiciona a entrada do utilizador
    history_messages.append(HumanMessage(content=user_input))

    result = agent.invoke({"messages": history_messages})

    # supõe que result["messages"] contem mensagens do histórico, incluindo SystemMessage como primeiro
    out_messages = result.get("messages", [])
    if out_messages:
        # Verifica novamente que o primeiro é SystemMessage
        if not isinstance(out_messages[0], SystemMessage):
            # Corrige se necessário
            out_messages.insert(0, SystemMessage(content=SYSTEM_PROMPT))
        history_messages[:] = out_messages

    # devolve a última mensagem de resposta
    last = history_messages[-1]
    return getattr(last, "content", str(last))

if __name__ == "__main__":
    while True:
        user_input = input("You: ")
        if user_input.lower() in ["quit", "exit"]:
            break
        resp = query_with_memory(user_input)
        print("Agent:", resp)

        


