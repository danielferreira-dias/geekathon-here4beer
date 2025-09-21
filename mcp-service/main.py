import asyncio
import json

from fastmcp import Client
from fastmcp.client.transports import StreamableHttpTransport

# Create the transport with your MCP server URL
server_url = "https://mcp.zapier.com/api/mcp/s/N2ZjOGEwZjEtZjNlMy00OWI4LWI3MDQtNjIzMjA0NjRkNmRmOjAyODUyZTRhLWRjMTEtNGJmNS1iMjZkLTczYjI0NTBhODJiNQ==/mcp"
transport = StreamableHttpTransport(server_url)

# Initialize the client with the transport
client = Client(transport=transport)

async def main():
    # Connection is established here
    print("Connecting to MCP server...")
    async with client:
        print(f"Client connected: {client.is_connected()}")

        # Make MCP calls within the context
        print("Fetching available tools...")
        tools = await client.list_tools()

        print(f"Available tools: {json.dumps([t.name for t in tools], indent=2)}")
        # Tools returned would look like:
        # - name: "gmail_find_email"
        #   description: "Finds an email message."
        #   params: ["query"]
# - name: "gmail_send_email"
        #   description: "Create and send a new email message."
        #   params: ["cc","to","bcc", ...]
# - name: "gmail_create_draft"
        #   description: "Create a draft email message."
        #   params: ["cc","to","bcc", ...]

        # Example: Call a specific tool with parameters
        print("Calling gmail_find_email...")
        result = await client.call_tool(
            "gmail_find_email",
            {
                "instructions": "Execute the Gmail: Find Email tool with the following parameters",
                "query": "example-string",
            },
        )

        # Parse the JSON string from the TextContent and print it nicely formatted
        json_result = json.loads(result.content[0].text)
        print(
            f"\ngmail_find_email result:\n{json.dumps(json_result, indent=2)}"
        )

    # Connection is closed automatically when exiting the context manager
    print("Example completed")


if __name__ == "__main__":
    asyncio.run(main())
