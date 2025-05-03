import asyncio
import sys
from pathlib import Path
from typing import List
from flask import Flask, request, jsonify
from flasgger import Swagger

from dotenv import load_dotenv

from camel.models import ModelFactory
from camel.toolkits import FunctionTool
from camel.types import ModelPlatformType, ModelType
from camel.logger import set_log_level
from camel.toolkits import MCPToolkit

from owly.utils.enhanced_role_playing import OwlRolePlaying, arun_society


load_dotenv()
set_log_level(level="DEBUG")
app = Flask(__name__)
swagger = Swagger(app)


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


config_path = Path(__file__).parent / "mcp_servers_config.json"
mcp_toolkit = MCPToolkit(config_path=str(config_path))


async def main():
    try:
        await mcp_toolkit.connect()

        # Default task
        default_task = "Create a budgeting plan based on my financial information from bunq. Use envelope style and create monetary accounts with daily limits for each budget. When done, retrieve the existing accounts and print them nicely. After creating any budget account, mention what you created."

        # Override default task if command line argument is provided
        task = sys.argv[1] if len(sys.argv) > 1 else default_task

        # Connect to all MCP toolkits
        tools = [*mcp_toolkit.get_tools()]
        society = await construct_society(task, tools)
        answer, chat_history, token_count = await arun_society(society, round_limit=1)
        print(f"\033[94mAnswer: {answer}\033[0m")

    finally:
        # Make sure to disconnect safely after all operations are completed.
        try:
            await mcp_toolkit.disconnect()
        except Exception:
            print("Disconnect failed")


@app.route("/task", methods=["POST"])
async def execute_task():
    """
    Tell the agent to execute a task.
    ---
    description: Tell the agent to execute a task
    parameters:
      - name: task
        in: body
        required: true
        schema:
          type: object
          properties:
            task:
              type: string
    responses:
      200:
        description: Task executed successfully.
        schema:
          type: object
          properties:
            answer:
              type: string
            chat_history:
              type: array
              items:
                type: string
            token_count:
              type: integer
    """
    task = request.get_json()["task"]
    await mcp_toolkit.connect()
    tools = [*mcp_toolkit.get_tools()]
    society = await construct_society(task, tools)
    answer, chat_history, token_count = await arun_society(society, round_limit=1)
    print(f"\033[94mAnswer: {answer}\033[0m")
    return jsonify(
        {"answer": answer, "chat_history": chat_history, "token_count": token_count}
    )


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=42069)
