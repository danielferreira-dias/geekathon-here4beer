import sys
import os
import time
from langchain_aws.chat_models.bedrock import ChatBedrock, ToolMessage
from langchain_core.tools import tool
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_aws import ChatBedrock
from dotenv import load_dotenv
from langgraph.prebuilt import create_react_agent
from langchain.memory import ConversationSummaryMemory
from langchain_core.stores import InMemoryStore

load_dotenv()

# Add the parent directory to sys.path to import provider_queries
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'tools'))
from provider_queries import get_provider_db


class Here4BeerAgent:
    def __init__(self):
        # Initialize the provider database
        self.provider_db = get_provider_db()

        # Create tools as functions that reference self
        self.tools = self._create_tools()

        # Initialize LLM
        self.llm = ChatBedrock(
            model_id=os.getenv("BEDROCK_MODEL_ID"),
            provider="anthropic",
            region_name=os.getenv("AWS_REGION"),
            aws_access_key_id=os.getenv("AWS_ACCESS_KEY_ID"),
            aws_secret_access_key=os.getenv("AWS_SECRET_ACCESS_KEY"),
            aws_session_token=os.getenv("AWS_SESSION_TOKEN"),
            model_kwargs={"temperature": 0.5}
        )

        # Store for chat conversations
        self.store = InMemoryStore()

        # Create the agent
        self.agent = create_react_agent(
            model=self.llm,
            tools=self.tools,
            store=self.store,
        )

        # System prompt
        self.system_prompt = """You are a Food Provider Assistant AI that helps users find and search through a database of food providers. You have access to a comprehensive database containing information about meat, seafood, eggs, and other food providers.

## Available Tools

You have access to the following database query functions through the ProviderDatabase class:

1. **get_all_providers()** - Returns all providers in the database
   - Use when: User asks for "all providers", "show me everything", "list all"

2. **get_provider_by_id(provider_id: int)** - Gets a specific provider by ID
   - Use when: User mentions a specific provider ID number

3. **get_providers_by_location(location: str)** - Finds providers in a specific location
   - Use when: User asks about providers "in [location]", "near [city/state]", "from [place]"
   - Examples: "Texas", "California", "Seattle"

4. **get_providers_by_item(item: str)** - Finds providers selling a specific item
   - Use when: User searches for specific food items
   - Examples: "steak", "chicken", "eggs", "salmon", "beef"

5. **get_providers_by_price_range(min_price: float, max_price: float)** - Finds providers within price range
   - Use when: User mentions price constraints like "under $20", "between $10 and $25", "cheap options"

6. **get_providers_in_stock(min_stock: int = 1)** - Finds providers with available stock
   - Use when: User asks about "availability", "in stock", "what's available"
   - Default min_stock=1, but can specify higher minimums

7. **search_providers(search_term: str)** - General search across provider names, items, and locations
   - Use when: User provides general search terms that could match multiple fields
   - Best for broad searches

8. **get_cheapest_providers(limit: int = 5)** - Gets the cheapest options
   - Use when: User asks for "cheapest", "lowest price", "budget options"
   - Default limit=5, adjust based on user request

9. **get_providers_by_name(provider_name: str)** - Finds providers by company name
   - Use when: User asks about specific company names like "Prime Meat Co", "Ocean Catch"

10. **get_stock_summary()** - Gets overall statistics about the database
    - Use when: User asks for "summary", "statistics", "overview", "how many providers"

## Database Schema

Each provider record contains:
- **id**: Unique identifier
- **provider_name**: Company name
- **item**: Food item (steak, chicken, eggs, etc.)
- **price**: Price in USD
- **location**: City/State location
- **stock**: Available quantity
- **distance**: Distance from reference point (e.g., "15km")
- **price_spent_on_location**: Amount invested in that location
- **expiration_date**: When the item expires
- **provider_email**: Contact email

## Instructions for Tool Selection

1. **Parse user intent carefully** - Look for keywords that indicate which function to use
2. **Use the most specific function** - If user asks for "steak providers", use get_providers_by_item("steak") rather than search_providers("steak")
3. **Handle multiple criteria** - If user has multiple filters, start with the most restrictive and explain you can further filter
4. **Provide context** - Always explain what information you're showing and suggest follow-up queries
5. **Handle errors gracefully** - If no results found, suggest alternative searches

## Response Format

Always structure your responses as:
1. Brief acknowledgment of the request
2. Tool function call with appropriate parameters
3. Clear presentation of results with relevant details
4. Helpful suggestions for follow-up queries

## Very Important

Only REPLY to queries that are related to the database above, for exemple if someone asks something not related like "Who is Ronaldo?", reply with the following: "I'm an AI Food Agent Assistant, I cannot provide you with that information";"""

        # Initialize message history
        self.history_messages = [SystemMessage(content=self.system_prompt)]

    def _create_tools(self):
        """Create tools that can access the instance methods"""

        @tool("get_all_providers_tool", return_direct=True, description="Lists all food providers available in the database. Use this when user asks to see all providers or wants a complete list.")
        def get_all_providers_tool():
            """Lists all food providers in the database"""
            try:
                providers = self.provider_db.get_all_providers()
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
                providers = self.provider_db.get_providers_by_item(item)
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
                providers = self.provider_db.get_providers_by_location(location)
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
                providers = self.provider_db.get_cheapest_providers(limit_int)
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
                providers = self.provider_db.get_providers_by_price_range(min_p, max_p)
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
                summary = self.provider_db.get_stock_summary()
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
                providers = self.provider_db.search_providers(search_term)
                if not providers:
                    return f"No results found for '{search_term}'."

                result = f"Search results for '{search_term}':\n"
                for provider in providers:
                    result += f"- {provider['provider_name']}: {provider['item']} (${provider['price']}) - {provider['location']}\n"
                return result
            except Exception as e:
                return f"Error searching for '{search_term}': {str(e)}"

        @tool("write_draft_email_too", return_direct=True, description="Generates a professional follow-up email draft to a specific provider. Use this when user asks to write a follow-up email to a provider. Input should be the provider name.")
        def write_draft_email_too(provider_name: str):
            """Generates a follow-up email draft to a specific provider"""
            try:
                # Search for the provider to get their details
                providers = self.provider_db.search_providers(provider_name)
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
            
        @tool("send_draft_email_tool", return_direct=True, description="Simulates sending a draft email to a provider. Use this when user asks to send an email. Input should be the provider name and email content.")
        def send_draft_email_tool(provider_name: str, provider_email: str, subject: str ,email_content: str):
            """Simulates sending a draft email to a provider"""
            ##re_ADWaEnmZ_PeXhkfQ79CHyWuA6cjBFUUUp
            try:
                return f"Email successfully sent to {provider_name} at {provider_email}."

            except Exception as e:
                return f"Error sending email to provider '{provider_name}': {str(e)}"

        @tool("parse_email_order_tool", return_direct=True, description="Parses an email file and extracts order information from a buyer. Use this when user asks to analyze or check an email order. Takes the email file path as input.")
        def parse_email_order_tool(email_file_path: str = "app/tools/file_example.eml"):
            """Parses an email file and creates a summary of what the buyer wants to order"""
            try:
                import email
                import re
                import os

                # Default to the example file if no path provided
                if not email_file_path or email_file_path == "default":
                    email_file_path = os.path.join(os.path.dirname(__file__), '..', 'tools', 'file_example.eml')

                # Read and parse the email file
                with open(email_file_path, 'r', encoding='utf-8') as file:
                    email_content = file.read()

                # Parse the email
                msg = email.message_from_string(email_content)

                # Extract basic email information
                sender = msg.get('From', 'Unknown')
                recipient = msg.get('To', 'Unknown')
                subject = msg.get('Subject', 'No Subject')
                date = msg.get('Date', 'Unknown Date')

                # Extract the email body (look for text/plain content)
                email_body = ""
                if msg.is_multipart():
                    for part in msg.walk():
                        if part.get_content_type() == "text/plain":
                            email_body = part.get_payload(decode=True).decode('utf-8')
                            break
                else:
                    email_body = msg.get_payload(decode=True).decode('utf-8')

                # Parse order details from the email body
                order_items = []
                po_number = "Not specified"
                delivery_date = "Not specified"
                total_value = "Not specified"
                contact_info = "Not specified"

                # Extract PO number
                po_match = re.search(r'PO[#\-\s]*([A-Z0-9\-]+)', email_body, re.IGNORECASE)
                if po_match:
                    po_number = po_match.group(1)

                # Extract delivery date
                delivery_match = re.search(r'Delivery Date[:\s]*([^\n]+)', email_body, re.IGNORECASE)
                if delivery_match:
                    delivery_date = delivery_match.group(1).strip()

                # Extract total value
                value_match = re.search(r'Total.*value[:\s]*\$?([\d,\-\s]+)', email_body, re.IGNORECASE)
                if value_match:
                    total_value = value_match.group(1).strip()

                # Extract contact information
                contact_match = re.search(r'Contact[:\s]*([^\n]+)', email_body, re.IGNORECASE)
                if contact_match:
                    contact_info = contact_match.group(1).strip()

                # Extract order items (looking for patterns like "Item: quantity units")
                item_patterns = [
                    r'- ([^:]+):\s*(\d+)\s*units',
                    r'([^:]+):\s*(\d+)\s*units',
                ]

                for pattern in item_patterns:
                    matches = re.findall(pattern, email_body, re.IGNORECASE)
                    for match in matches:
                        item_name = match[0].strip()
                        quantity = match[1].strip()
                        order_items.append(f"{item_name}: {quantity} units")

                # Create summary
                summary = f"""
EMAIL ORDER SUMMARY
==================

📧 Email Details:
   From: {sender}
   To: {recipient}
   Subject: {subject}
   Date: {date}

📋 Order Information:
   Purchase Order: {po_number}
   Delivery Date: {delivery_date}
   Estimated Value: {total_value}
   Contact: {contact_info}

📦 Items Requested:
"""

                if order_items:
                    for item in order_items:
                        summary += f"   • {item}\n"
                else:
                    summary += "   • No specific items found in standard format\n"

                # Add total items count
                total_items = len(order_items)
                total_units = 0
                for item in order_items:
                    units_match = re.search(r'(\d+)\s*units', item)
                    if units_match:
                        total_units += int(units_match.group(1))

                summary += f"\n📊 Order Summary:\n"
                summary += f"   Total Item Types: {total_items}\n"
                summary += f"   Total Units Requested: {total_units}\n"

                # Check availability against our database
                summary += f"\n🔍 Availability Check:\n"
                try:
                    # Check each item against our providers
                    for item_line in order_items:
                        item_name = item_line.split(':')[0].strip()
                        requested_qty = re.search(r'(\d+)', item_line.split(':')[1])

                        if requested_qty:
                            qty = int(requested_qty.group(1))

                            # Convert item name to match our database format
                            item_db_name = item_name.lower().replace(' ', '_')

                            # Check providers for this item
                            providers = self.provider_db.get_providers_by_item(item_db_name)
                            if providers:
                                total_stock = sum(p['stock'] for p in providers)
                                cheapest = min(providers, key=lambda x: x['price'])
                                summary += f"   • {item_name}: {len(providers)} providers available, total stock: {total_stock}, cheapest: ${cheapest['price']} from {cheapest['provider_name']}\n"
                            else:
                                summary += f"   • {item_name}: No providers found in our database\n"
                except Exception as e:
                    summary += f"   • Error checking availability: {str(e)}\n"

                return summary

            except FileNotFoundError:
                return f"Error: Email file not found at path: {email_file_path}"
            except Exception as e:
                return f"Error parsing email: {str(e)}"

        return [
            get_all_providers_tool,
            search_providers_by_item_tool,
            search_providers_by_location_tool,
            get_cheapest_providers_tool,
            search_providers_by_price_range_tool,
            get_stock_summary_tool,
            general_search_tool,
            write_draft_email_too,
            send_draft_email_tool,
            parse_email_order_tool
        ]

    def query_with_memory(self, user_input: str, max_rounds: int = 5):
        # Ensure the first message is SystemMessage
        if not isinstance(self.history_messages[0], SystemMessage):
            self.history_messages.insert(0, SystemMessage(content=self.system_prompt))

        # Add user input
        self.history_messages.append(HumanMessage(content=user_input))

        result = self.agent.invoke({"messages": self.history_messages})

        # Assume result["messages"] contains message history, including SystemMessage as first
        out_messages = result.get("messages", [])
        if out_messages:
            # Verify again that the first is SystemMessage
            if not isinstance(out_messages[0], SystemMessage):
                # Fix if necessary
                out_messages.insert(0, SystemMessage(content=self.system_prompt))
            self.history_messages[:] = out_messages

        # Return the last response message
        last = self.history_messages[-1]
        return getattr(last, "content", str(last))