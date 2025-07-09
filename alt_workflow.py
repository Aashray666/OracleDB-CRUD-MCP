# main_workflow.py
import asyncio
from langchain_mcp_adapters.client import MultiServerMCPClient
from langgraph.graph import StateGraph, MessagesState, START
from langgraph.prebuilt import ToolNode, tools_condition
from langchain_groq import ChatGroq
from langchain_core.messages import SystemMessage, HumanMessage, ToolMessage # Import necessary message types
import os
from dotenv import load_dotenv
import re

# Load environment variables from .env file
load_dotenv()
os.environ["GROQ_API_KEY"] = os.getenv("GROQ_API_KEY")

# Initialize the chat model.
model = ChatGroq(
    api_key=os.getenv("GROQ_API_KEY"),
    model_name="llama-3.1-8b-instant" # Using a Groq model as per your previous successful traces
)

# --- IMPORTANT ---
# You MUST run oracle_crud_server.py in a separate terminal BEFORE running this script.
# Example: python -u oracle_crud_server.py
#
# Make sure to update the 'args' argument below to the full absolute path
# to your oracle_crud_server.py file on your system.
# For example, if your oracle_crud_server.py is in C:/Users/youruser/my_project/oracle_crud_server.py
# then the args would be ["C:/Users/youruser/my_project/oracle_crud_server.py"]
# -----------------
client = MultiServerMCPClient(
    {
        "oracle_crud": {
            "command": "python",
            "args": ["C:/Users/aashr/Desktop/OracleMcp/new_server.py"], # <<< ENSURE THIS PATH IS CORRECT
            "transport": "stdio",
        },
    }
)

async def get_mcp_tools():
    """Asynchronously fetches tools from the MCP client."""
    print("Fetching MCP tools...", flush=True)
    return await client.get_tools()

# Define the function that calls the LLM with the available tools
def call_model(state: MessagesState):
    """
    Invokes the LLM with the current messages state, binding the available tools.
    """
    print("\n--- Agent Calling LLM ---", flush=True)
    
    # Prepend a detailed system message to guide the LLM's behavior and tool usage.
    # This is crucial for the LLM to understand context, table names, and expected data formats.
    messages_with_system_prompt = [
        SystemMessage(content=(
            "You are an intelligent AI assistant capable of performing CRUD (Create, Read, Update, Delete) "
            "operations on an Oracle database. You have access to the following tables: 'USERS' and 'PRODUCTS'. "
            "Your available tools are: 'create_record', 'read_records', 'update_record', and 'delete_record'.\n\n"
            "**Tool Usage Guidelines:**\n"
            "- **Always use the provided tools** when a database operation is requested.\n"
            "- **Table Names:** Refer to tables as 'USERS' or 'PRODUCTS' (uppercase is best practice for Oracle).\n"
            "- **'create_record' tool:**\n"
            "  - Use for adding new entries. Provide 'table_name' (e.g., 'USERS') and 'data' (a dictionary).\n"
            "  - Example `data`: {'NAME': 'Alice', 'EMAIL': 'alice@example.com', 'AGE': 30}.\n"
            "  - DO NOT provide SQL data types (e.g., 'VARCHAR2', 'NUMBER') as values in 'data'. Provide actual values.\n"
            "- **'read_records' tool:**\n"
            "  - Use for retrieving data. Provide 'table_name'.\n"
            "  - The 'query' parameter MUST be a Python dictionary for filtering (e.g., {'NAME': 'Alice', 'AGE': 30}).\n"
            "  - If no specific filter is needed, pass 'query=None' or 'query={}' to read all records from the table.\n"
            "  - DO NOT provide raw SQL queries (e.g., 'SELECT * FROM users') in the 'query' parameter.\n"
            "- **'update_record' tool:**\n"
            "  - Use for modifying existing records. Provide 'table_name', 'record_id' (the unique ID of the record), and 'new_data' (a dictionary of columns to update).\n"
            "  - Example `new_data`: {'AGE': 31, 'EMAIL': 'new.email@example.com'}.\n"
            "- **'delete_record' tool:**\n"
            "  - Use for removing records. Provide 'table_name' and 'record_id'.\n\n"
            "**Response Guidelines:**\n"
            "- After a successful tool execution, **summarize the result clearly for the user** in natural language.\n"
            "- If a tool operation returns an empty list (e.g., from 'read_records'), state that no records were found.\n"
            "- If a tool returns an error, report the error message to the user and suggest how they might rephrase their request or what might be wrong (e.g., 'table not found', 'invalid ID').\n"
            "- If you have fully answered the user's request, provide a concise final answer and stop generating tool calls."
        ))
    ] + state["messages"] # Prepend the system message to the existing messages

    response = model.bind_tools(tools).invoke(messages_with_system_prompt)
    print(f"LLM Response: {response}", flush=True)
    return {"messages": [response]}

# Main asynchronous function to run the graph
async def main():
    global tools
    tools = await get_mcp_tools()
    print(f"Available tools: {[tool.name for tool in tools]}", flush=True)

    builder = StateGraph(MessagesState)
    builder.add_node("call_model", call_model)
    builder.add_node("tools", ToolNode(tools))

    builder.add_edge(START, "call_model")

    builder.add_conditional_edges(
        "call_model",
        tools_condition,
        {"tools": "tools", "__end__": "__end__"}
    )

    builder.add_edge("tools", "call_model")

    graph = builder.compile()

    print("\n--- Starting LangGraph Agentic Workflow for Oracle CRUD ---", flush=True)

    # Define a common configuration for ainvoke calls to limit recursion
    # This prevents infinite loops by stopping the agent after a certain number of steps.
    # A typical tool call + LLM response cycle is 2 steps. Adjust as needed.
    invoke_config = {"recursion_limit": 10} 

    # --- Test Case 1: Create a user record ---
    print("\n--- Test Case 1: Create a user record (Alice) ---", flush=True)
    create_alice_response = await graph.ainvoke(
        {"messages": [HumanMessage(content="Create a user named 'Aashray' with email 'aashray@example.com' and age 22.")]},
        config=invoke_config
    )
    print(f"Final state after creating Alice: {create_alice_response['messages'][-1].content}", flush=True)

    # --- Test Case 2: Read all user records ---
    print("\n--- Test Case 2: Read all user records ---", flush=True)
    read_all_users_response = await graph.ainvoke(
        {"messages": [HumanMessage(content="Show me all users.")]},
        config=invoke_config
    )
    print(f"Final state after reading all users: {read_all_users_response['messages'][-1].content}", flush=True)

    # # --- Test Case 3: Create another user record (Bob) ---
    # print("\n--- Test Case 3: Create another user record (Bob) ---", flush=True)
    # create_bob_response = await graph.ainvoke(
    #     {"messages": [HumanMessage(content="Add a new user named 'Bob' with email 'bob@example.com' and age 25.")]},
    #     config=invoke_config
    # )
    # print(f"Final state after creating Bob: {create_bob_response['messages'][-1].content}", flush=True)

    # # --- Test Case 4: Read a specific user by name ---
    # print("\n--- Test Case 4: Read user named 'Alice' ---", flush=True)
    # read_alice_by_name_response = await graph.ainvoke(
    #     {"messages": [HumanMessage(content="Find the user named 'Alice'.")]},
    #     config=invoke_config
    # )
    # print(f"Final state after finding Alice by name: {read_alice_by_name_response['messages'][-1].content}", flush=True)

    # # --- Test Case 5: Update Alice's age (requires extracting ID) ---
    # print("\n--- Test Case 5: Update Alice's age (requires knowing her ID) ---", flush=True)
    # alice_id_to_update = None
    # # Attempt to extract Alice's ID from the previous read response
    # # This parsing is brittle; in a real app, you might have more structured tool outputs or LLM parsing logic.
    # match = re.search(r"'ID': '([^']+)'", str(read_alice_by_name_response['messages'][-1].content))
    # if match:
    #     alice_id_to_update = match.group(1)
    #     print(f"Extracted Alice's ID for update: {alice_id_to_update}", flush=True)
    #     update_alice_response = await graph.ainvoke(
    #         {"messages": [HumanMessage(content=f"Update user with ID '{alice_id_to_update}' to have age 31 and email 'alice.new@example.com'.")]},
    #         config=invoke_config
    #     )
    #     print(f"Final state after updating Alice: {update_alice_response['messages'][-1].content}", flush=True)
    # else:
    #     print("Could not extract Alice's ID from the response to perform update. Skipping update test.", flush=True)

    # # --- Test Case 6: Create a product record ---
    # print("\n--- Test Case 6: Create a product record (Laptop Pro) ---", flush=True)
    # create_product_response = await graph.ainvoke(
    #     {"messages": [HumanMessage(content="Add a new product named 'Laptop Pro' with price 1500.99 and category 'Electronics'.")]},
    #     config=invoke_config
    # )
    # print(f"Final state after creating product: {create_product_response['messages'][-1].content}", flush=True)

    # # --- Test Case 7: Read all products ---
    # print("\n--- Test Case 7: Read all products ---", flush=True)
    # read_all_products_response = await graph.ainvoke(
    #     {"messages": [HumanMessage(content="What products do you have?")]},
    #     config=invoke_config
    # )
    # print(f"Final state after reading products: {read_all_products_response['messages'][-1].content}", flush=True)

    # # --- Test Case 8: Delete Bob ---
    # print("\n--- Test Case 8: Delete Bob (requires knowing his ID) ---", flush=True)
    # bob_id_to_delete = None
    # # First, find Bob's ID
    # read_bob_response = await graph.ainvoke(
    #     {"messages": [HumanMessage(content="Find the user named 'Bob'.")]},
    #     config=invoke_config
    # )
    # print(f"Read Bob's info: {read_bob_response['messages'][-1].content}", flush=True)
    # match_bob = re.search(r"'ID': '([^']+)'", str(read_bob_response['messages'][-1].content))
    # if match_bob:
    #     bob_id_to_delete = match_bob.group(1)
    #     print(f"Extracted Bob's ID for deletion: {bob_id_to_delete}", flush=True)
    #     delete_bob_response = await graph.ainvoke(
    #         {"messages": [HumanMessage(content=f"Delete the user with ID '{bob_id_to_delete}'.")]},
    #         config=invoke_config
    #     )
    #     print(f"Final state after deleting Bob: {delete_bob_response['messages'][-1].content}", flush=True)
    # else:
    #     print("Could not extract Bob's ID from the response to perform deletion. Skipping delete test.", flush=True)

    # # --- Test Case 9: Verify Bob is deleted ---
    # print("\n--- Test Case 9: Verify Bob is deleted ---", flush=True)
    # verify_delete_bob_response = await graph.ainvoke(
    #     {"messages": [HumanMessage(content="Find the user named 'Bob'.")]},
    #     config=invoke_config
    # )
    # print(f"Final state after verifying Bob deletion: {verify_delete_bob_response['messages'][-1].content}", flush=True)

    print("\n--- LangGraph Agentic Workflow Finished ---", flush=True)

if __name__ == "__main__":
    asyncio.run(main())
