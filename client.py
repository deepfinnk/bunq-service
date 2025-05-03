import asyncio  # Manages asynchronous operations
import os  # Provide interaction with the operating system.
import sys
from pathlib import Path
from dotenv import load_dotenv  # for api keys

from camel.agents import ChatAgent  # creates Agents
from camel.models import ModelFactory  # encapsulates LLM
from camel.toolkits import MCPToolkit  # import tools
from camel.types import ModelPlatformType


load_dotenv()


async def interactive_input_loop(agent: ChatAgent):
    loop = asyncio.get_event_loop()
    print("\nEntering interactive mode. Type 'exit' at any prompt to quit.")

    while True:  # the loop
        choice = await loop.run_in_executor(
            None,
            input,
            "\nChoose an action:\n"
            "1. Read a file\n"
            "2. List a directory\nYour choice (1/2): ",
        )
        choice = choice.strip().lower()
        if choice == "exit":  # if exit then end loop
            print("Exiting interactive mode.")
            break

        if choice == "1":  # if choice is 1 then read the file
            file_path = await loop.run_in_executor(
                None, input, "Enter the file path (default: README.md): "
            )
            file_path = file_path.strip() or "README.md"
            query = f"Use the read_file tool to display the content of {file_path}. Do not generate an answer from your internal knowledge."
        elif choice == "2":
            dir_path = await loop.run_in_executor(
                None, input, "Enter the directory path (default: .): "
            )
            dir_path = dir_path.strip() or "."  # either this or current dir
            query = f"Call the list_directory tool to show me all files in {dir_path}. Do not answer directly."
        else:
            print("Invalid choice. Please enter 1 or 2.")
            continue

        response = await agent.astep(query)
        print(f"\nYour Query: {query}")  # prinitng the output
        print("Full Agent Response:")
        print(response.info)
        if response.msgs and response.msgs[0].content:
            print("Agent Output:")
            print(
                response.msgs[0].content.rstrip()
            )  # paste the content displayed by the agent
        else:
            print("No output received.")


async def main(server_transport: str = "stdio"):
    if server_transport == "stdio":
        server_script_path = Path(__file__).resolve().parent / "server.py"
        if not server_script_path.is_file():
            print(f"Error: Server script not found at {server_script_path}")
            return
        server = _MCPServer(
            command_or_url=sys.executable, args=[str(server_script_path)]
        )
        mcp_toolkit = MCPToolkit(servers=[server])  # camels toolkit to define mcp tools

    async with mcp_toolkit.connection() as toolkit:
        tools = toolkit.get_tools()
        sys_msg = (
            "You are a helpful assistant. Always use the provided external tools for bunq bank operations "
            "Also remember to use the tools to answer questions about the user's financial situation."
            "Always use the tools when asked, rather than relying on your internal knowledge."
            "Make sure to keep the messages short and to the point so that tokens are not wasted. "
            "Ensure that your final answer does not end with any trailing whitespace."
        )
        model = ModelFactory.create(  # define the LLM to create agent
            model_platform=ModelPlatformType.ANTHROPIC,
            model_type="claude-3-7-sonnet-20250219",
            api_key=os.getenv("ANTHROPIC_API_KEY"),
            model_config_dict={"temperature": 0.8, "max_tokens": 4096},
        )
        camel_agent = ChatAgent(  # create agent with our mcp tools
            system_message=sys_msg,
            model=model,
            tools=tools,
        )
        camel_agent.reset()  # reset after each loop
        camel_agent.memory.clear()
        await interactive_input_loop(camel_agent)  # start the interactive loop


if __name__ == "__main__":
    asyncio.run(main())
