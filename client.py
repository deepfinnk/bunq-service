import asyncio
import sys
from pathlib import Path
from typing import List

from dotenv import load_dotenv

from camel.models import ModelFactory
from camel.toolkits import FunctionTool
from camel.types import ModelPlatformType, ModelType
from camel.logger import set_log_level
from camel.toolkits import MCPToolkit

from owly.utils.enhanced_role_playing import OwlRolePlaying, arun_society


load_dotenv()
set_log_level(level="DEBUG")


async def construct_society(
    question: str,
    tools: List[FunctionTool],
) -> OwlRolePlaying:
    r"""build a multi-agent OwlRolePlaying instance.

    Args:
        question (str): The question to ask.
        tools (List[FunctionTool]): The MCP tools to use.
    """
    models = {
        "user": ModelFactory.create(
            model_platform=ModelPlatformType.OPENAI,
            model_type=ModelType.GPT_4O,
            model_config_dict={"temperature": 0},
        ),
        "assistant": ModelFactory.create(
            model_platform=ModelPlatformType.OPENAI,
            model_type=ModelType.GPT_4O,
            model_config_dict={"temperature": 0},
        ),
    }

    user_agent_kwargs = {"model": models["user"]}
    assistant_agent_kwargs = {
        "model": models["assistant"],
        "tools": tools,
    }

    task_kwargs = {
        "task_prompt": question,
        "with_task_specify": False,
    }

    society = OwlRolePlaying(
        **task_kwargs,
        user_role_name="user",
        user_agent_kwargs=user_agent_kwargs,
        assistant_role_name="assistant",
        assistant_agent_kwargs=assistant_agent_kwargs,
    )
    return society


async def main():
    config_path = Path(__file__).parent / "mcp_servers_config.json"
    mcp_toolkit = MCPToolkit(config_path=str(config_path))

    try:
        await mcp_toolkit.connect()

        # Default task
        default_task = (
            "I'd like a academic report about Andrew Ng, including "
            "his research direction, published papers (At least 3),"
            " institutions, etc. "
        )

        # Override default task if command line argument is provided
        task = sys.argv[1] if len(sys.argv) > 1 else default_task

        # Connect to all MCP toolkits
        tools = [*mcp_toolkit.get_tools()]
        society = await construct_society(task, tools)
        answer, chat_history, token_count = await arun_society(society)
        print(f"\033[94mAnswer: {answer}\033[0m")

    finally:
        # Make sure to disconnect safely after all operations are completed.
        try:
            await mcp_toolkit.disconnect()
        except Exception:
            print("Disconnect failed")


if __name__ == "__main__":
    asyncio.run(main())
