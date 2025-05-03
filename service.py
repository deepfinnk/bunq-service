import sys
import json
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

try:
    from mcp_server_bunq import (
        get_user,
        get_accounts,
        update_account,
        create_account,
        get_payments,
        make_payment,
        get_requests,
        make_request,
        get_cards,
        link_card,
        get_aliases,
        add_callback_url,
        get_overview,
        get_environment,
        BunqLib,
        ShareLib,
        ShareLibOptions,
    )

    bunq_tools_available = True
except ImportError as e:
    print(
        f"Warning: Could not import mcp_server_bunq. Bunq endpoints will not be available. Error: {e}"
    )
    bunq_tools_available = False

    class BunqLib:
        pass

    class ShareLib:
        pass

    class ShareLibOptions:
        pass

    class ApiEnvironmentType:
        SANDBOX = None
        PRODUCTION = None
        name = "UNKNOWN"

    def get_user(ctx):
        raise NotImplementedError("Bunq tools not loaded")

    def get_accounts(ctx):
        raise NotImplementedError("Bunq tools not loaded")


from owly.utils.enhanced_role_playing import OwlRolePlaying, arun_society


load_dotenv()
set_log_level(level="DEBUG")
app = Flask(__name__)
swagger = Swagger(app)

bunq_instance = None
environment_type = None
if bunq_tools_available:
    try:
        all_option = ShareLibOptions()
        environment_type = ShareLib.determine_environment_type_from_all_option(
            all_option
        )
        bunq_instance = BunqLib(environment_type)
        print(f"BunqLib initialized for environment: {environment_type.name}")
    except Exception as e:
        print(f"Error initializing BunqLib: {e}")
        bunq_instance = None
        environment_type = None
        bunq_tools_available = False


class MockLifespanContext:
    def __init__(self, bunq, env_type):
        self.bunq = bunq
        self.environment_type = env_type


class MockRequestContext:
    def __init__(self, lifespan_ctx):
        self.lifespan_context = lifespan_ctx


class MockContext:
    def __init__(self, request_ctx):
        self.request_context = request_ctx


def get_mock_context():
    if not bunq_tools_available or not bunq_instance or not environment_type:
        raise ConnectionError("BunqLib is not available or failed to initialize.")
    mock_lifespan_ctx = MockLifespanContext(bunq_instance, environment_type)
    mock_request_ctx = MockRequestContext(mock_lifespan_ctx)
    return MockContext(mock_request_ctx)


def process_tool_result(result):
    if isinstance(result, str):
        try:
            return jsonify(json.loads(result))
        except json.JSONDecodeError:
            return jsonify({"message": result})
    return jsonify(result)


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

        default_task = "Create a budgeting plan based on my financial information from bunq. Use envelope style and create monetary accounts with daily limits for each budget. When done, retrieve the existing accounts and print them nicely. After creating any budget account, mention what you created."

        task = sys.argv[1] if len(sys.argv) > 1 else default_task

        tools = [*mcp_toolkit.get_tools()]
        society = await construct_society(task, tools)
        answer, chat_history, token_count = await arun_society(society, round_limit=1)
        print(f"\033[94mAnswer: {answer}\033[0m")

    finally:
        try:
            await mcp_toolkit.disconnect()
        except Exception:
            print("Disconnect failed")


@app.route("/agent/task", methods=["POST"])
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


@app.route("/bunq/health", methods=["GET"])
async def bunq_health_check():
    """
    Check the health of the Bunq integration.
    ---
    tags:
      - Bunq
    description: Returns the status of the Bunq library initialization and the configured environment.
    responses:
      200:
        description: Bunq integration is OK.
        schema:
          type: object
          properties:
            status:
              type: string
              example: ok
            bunq_environment:
              type: string
              example: SANDBOX
      500:
        description: Bunq integration is not available or not initialized.
        schema:
          type: object
          properties:
            status:
              type: string
              example: error
            message:
              type: string
              example: Bunq integration not available or not initialized
    """
    if bunq_tools_available and bunq_instance:
        return jsonify({"status": "ok", "bunq_environment": environment_type.name})
    else:
        return jsonify(
            {
                "status": "error",
                "message": "Bunq integration not available or not initialized",
            }
        ), 500


@app.route("/bunq/user", methods=["GET"])
async def route_get_user():
    """
    Get current Bunq user information.
    ---
    tags:
      - Bunq
    description: Retrieves information about the currently authenticated Bunq user.
    responses:
      200:
        description: User information retrieved successfully.
        schema:
          # Assuming the result is a JSON representation of the Bunq User object
          type: object
          properties:
            # Add specific user properties based on the Bunq SDK User object structure
            id: 
              type: integer
            display_name:
              type: string
            # ... other user fields
      500:
        description: Internal server error or error retrieving user info.
        schema:
          $ref: '#/definitions/Error'
      503:
        description: Bunq integration not available.
        schema:
          $ref: '#/definitions/Error'
    """
    if not bunq_tools_available:
        return jsonify({"error": "Bunq integration not available"}), 503
    try:
        ctx = get_mock_context()
        result = get_user(ctx)
        return process_tool_result(result)
    except Exception as e:
        print(f"Error in /bunq/user: {e}")
        return jsonify({"error": str(e)}), 500


@app.route("/bunq/accounts", methods=["GET"])
async def route_get_accounts():
    """
    Get all active Bunq monetary accounts.
    ---
    tags:
      - Bunq
    description: Retrieves a list of all active monetary accounts for the current user.
    responses:
      200:
        description: List of accounts retrieved successfully.
        schema:
          type: array
          items:
            # Assuming the result is a JSON representation of Bunq MonetaryAccount objects
            type: object
            properties:
              id:
                type: integer
              description:
                type: string
              balance:
                type: object # Bunq Amount object
                properties:
                   currency: { type: string }
                   value: { type: string }
              # ... other account fields
      500:
        description: Internal server error or error retrieving accounts.
        schema:
          $ref: '#/definitions/Error'
      503:
        description: Bunq integration not available.
        schema:
          $ref: '#/definitions/Error'
    """
    if not bunq_tools_available:
        return jsonify({"error": "Bunq integration not available"}), 503
    try:
        ctx = get_mock_context()
        result = get_accounts(ctx)
        return process_tool_result(result)
    except Exception as e:
        print(f"Error in /bunq/accounts: {e}")
        return jsonify({"error": str(e)}), 500


@app.route("/bunq/accounts/<int:account_id>", methods=["PUT"])
async def route_update_account(account_id):
    """
    Update a Bunq monetary account.
    ---
    tags:
      - Bunq
    description: Updates the description (name) of a specific monetary account.
    parameters:
      - name: account_id
        in: path
        required: true
        description: The ID of the monetary account to update.
        type: integer
      - name: body
        in: body
        required: true
        schema:
          type: object
          required:
            - name
          properties:
            name:
              type: string
              description: The new description (name) for the account.
              example: My Updated Savings
    responses:
      200:
        description: Account updated successfully.
        schema:
          type: object
          properties:
            message:
              type: string
              example: "Account 12345 has been renamed to 'My Updated Savings'"
      400:
        description: Bad Request - Missing 'name' in request body.
        schema:
          $ref: '#/definitions/Error'
      500:
        description: Internal server error or error updating account.
        schema:
          $ref: '#/definitions/Error'
      503:
        description: Bunq integration not available.
        schema:
          $ref: '#/definitions/Error'
    """
    if not bunq_tools_available:
        return jsonify({"error": "Bunq integration not available"}), 503
    try:
        data = await request.get_json()
        if not data or "name" not in data:
            return jsonify({"error": "Missing 'name' in request body"}), 400
        name = data["name"]
        ctx = get_mock_context()
        result = update_account(ctx, name=name, account_id=account_id)
        if bunq_instance and hasattr(bunq_instance, "update_context"):
            bunq_instance.update_context()
        return process_tool_result(result)
    except Exception as e:
        print(f"Error in /bunq/accounts/<id>: {e}")
        return jsonify({"error": str(e)}), 500


@app.route("/bunq/accounts", methods=["POST"])
async def route_create_account():
    """
    Create a new Bunq monetary account.
    ---
    tags:
      - Bunq
    description: Creates a new monetary account (e.g., savings account) with a specified name and optional daily limit.
    parameters:
      - name: body
        in: body
        required: true
        schema:
          type: object
          required:
            - name
          properties:
            name:
              type: string
              description: The name for the new account.
              example: Holiday Fund
            daily_limit:
              type: number
              format: float
              description: Optional daily spending limit for the account.
              example: 100.00
    responses:
      200:
        description: Account created successfully.
        schema:
          # Assuming the result is the ID or details of the new account
          type: object
          properties:
             id: { type: integer }
             # ... other potential response fields
      400:
        description: Bad Request - Missing 'name' in request body.
        schema:
          $ref: '#/definitions/Error'
      500:
        description: Internal server error or error creating account.
        schema:
          $ref: '#/definitions/Error'
      503:
        description: Bunq integration not available.
        schema:
          $ref: '#/definitions/Error'
    """
    if not bunq_tools_available:
        return jsonify({"error": "Bunq integration not available"}), 503
    try:
        data = await request.get_json()
        if not data or "name" not in data:
            return jsonify({"error": "Missing 'name' in request body"}), 400
        name = data["name"]
        daily_limit = data.get("daily_limit")
        ctx = get_mock_context()
        result = create_account(ctx, name=name, daily_limit=daily_limit)
        if bunq_instance and hasattr(bunq_instance, "update_context"):
            bunq_instance.update_context()
        return process_tool_result(result)
    except Exception as e:
        print(f"Error in /bunq/accounts POST: {e}")
        return jsonify({"error": str(e)}), 500


@app.route("/bunq/payments", methods=["GET"])
async def route_get_payments():
    """
    Get recent payments.
    ---
    tags:
      - Bunq
    description: Retrieves a list of recent payments for the user.
    responses:
      200:
        description: List of payments retrieved successfully.
        schema:
          type: array
          items:
            # Assuming the result is a JSON representation of Bunq Payment objects
            type: object
            properties:
              id: { type: integer }
              amount: { $ref: '#/definitions/Amount' }
              description: { type: string }
              # ... other payment fields
      500:
        description: Internal server error or error retrieving payments.
        schema:
          $ref: '#/definitions/Error'
      503:
        description: Bunq integration not available.
        schema:
          $ref: '#/definitions/Error'
    """
    if not bunq_tools_available:
        return jsonify({"error": "Bunq integration not available"}), 503
    try:
        ctx = get_mock_context()
        result = get_payments(ctx)
        return process_tool_result(result)
    except Exception as e:
        print(f"Error in /bunq/payments GET: {e}")
        return jsonify({"error": str(e)}), 500


@app.route("/bunq/payments", methods=["POST"])
async def route_make_payment():
    """
    Make a payment.
    ---
    tags:
      - Bunq
    description: Initiates a payment to a specified recipient.
    parameters:
      - name: body
        in: body
        required: true
        schema:
          type: object
          required:
            - amount
            - description
            - recipient
          properties:
            amount:
              type: number
              format: float
              description: The amount to pay.
              example: 10.50
            description:
              type: string
              description: The payment description.
              example: Dinner with friends
            recipient:
              type: string # Or could be an object depending on how recipient is specified (IBAN, email, phone)
              description: The recipient identifier (e.g., IBAN, email, phone number).
              example: NL91ABNA0417164300
    responses:
      200:
        description: Payment initiated successfully.
        schema:
          # Assuming the result confirms payment initiation
          type: object
          properties:
            payment_id: { type: integer }
            status: { type: string }
            # ... other potential response fields
      400:
        description: Bad Request - Missing required fields in request body.
        schema:
          $ref: '#/definitions/Error'
      500:
        description: Internal server error or error making payment.
        schema:
          $ref: '#/definitions/Error'
      503:
        description: Bunq integration not available.
        schema:
          $ref: '#/definitions/Error'
    """
    if not bunq_tools_available:
        return jsonify({"error": "Bunq integration not available"}), 503
    try:
        data = await request.get_json()
        required_fields = ["amount", "description", "recipient"]
        if not data or not all(field in data for field in required_fields):
            return jsonify(
                {"error": f"Missing one or more required fields: {required_fields}"}
            ), 400

        amount = data["amount"]
        description = data["description"]
        recipient = data["recipient"]

        ctx = get_mock_context()
        result = make_payment(
            ctx, amount=amount, description=description, recipient=recipient
        )
        if bunq_instance and hasattr(bunq_instance, "update_context"):
            bunq_instance.update_context()
        return process_tool_result(result)
    except Exception as e:
        print(f"Error in /bunq/payments POST: {e}")
        return jsonify({"error": str(e)}), 500


@app.route("/bunq/requests", methods=["GET"])
async def route_get_requests():
    """
    Get payment requests.
    ---
    tags:
      - Bunq
    description: Retrieves a list of payment requests (sent or received).
    responses:
      200:
        description: List of requests retrieved successfully.
        schema:
          type: array
          items:
            # Assuming the result is a JSON representation of Bunq RequestInquiry/RequestResponse objects
            type: object
            properties:
              id: { type: integer }
              amount_inquired: { $ref: '#/definitions/Amount' }
              description: { type: string }
              status: { type: string }
              # ... other request fields
      500:
        description: Internal server error or error retrieving requests.
        schema:
          $ref: '#/definitions/Error'
      503:
        description: Bunq integration not available.
        schema:
          $ref: '#/definitions/Error'
    """
    if not bunq_tools_available:
        return jsonify({"error": "Bunq integration not available"}), 503
    try:
        ctx = get_mock_context()
        result = get_requests(ctx)
        return process_tool_result(result)
    except Exception as e:
        print(f"Error in /bunq/requests GET: {e}")
        return jsonify({"error": str(e)}), 500


@app.route("/bunq/requests", methods=["POST"])
async def route_make_request():
    """
    Make a payment request.
    ---
    tags:
      - Bunq
    description: Creates and sends a payment request to a specified recipient.
    parameters:
      - name: body
        in: body
        required: true
        schema:
          type: object
          required:
            - amount
            - description
            - recipient
          properties:
            amount:
              type: number
              format: float
              description: The amount to request.
              example: 25.00
            description:
              type: string
              description: The reason for the request.
              example: Contribution for gift
            recipient:
              type: string # Or object
              description: The recipient identifier (e.g., email, phone number).
              example: user@example.com
    responses:
      200:
        description: Payment request sent successfully.
        schema:
          # Assuming the result confirms request creation
          type: object
          properties:
            request_id: { type: integer }
            status: { type: string }
            # ... other potential response fields
      400:
        description: Bad Request - Missing required fields in request body.
        schema:
          $ref: '#/definitions/Error'
      500:
        description: Internal server error or error making request.
        schema:
          $ref: '#/definitions/Error'
      503:
        description: Bunq integration not available.
        schema:
          $ref: '#/definitions/Error'
    """
    if not bunq_tools_available:
        return jsonify({"error": "Bunq integration not available"}), 503
    try:
        data = await request.get_json()
        required_fields = ["amount", "description", "recipient"]
        if not data or not all(field in data for field in required_fields):
            return jsonify(
                {"error": f"Missing one or more required fields: {required_fields}"}
            ), 400

        amount = data["amount"]
        description = data["description"]
        recipient = data["recipient"]

        ctx = get_mock_context()
        result = make_request(
            ctx, amount=amount, description=description, recipient=recipient
        )
        if bunq_instance and hasattr(bunq_instance, "update_context"):
            bunq_instance.update_context()
        return process_tool_result(result)
    except Exception as e:
        print(f"Error in /bunq/requests POST: {e}")
        return jsonify({"error": str(e)}), 500


@app.route("/bunq/cards", methods=["GET"])
async def route_get_cards():
    """
    Get all cards.
    ---
    tags:
      - Bunq
    description: Retrieves a list of all cards associated with the user.
    responses:
      200:
        description: List of cards retrieved successfully.
        schema:
          type: array
          items:
            # Assuming the result is a JSON representation of Bunq Card objects
            type: object
            properties:
              id: { type: integer }
              type: { type: string }
              status: { type: string }
              # ... other card fields
      500:
        description: Internal server error or error retrieving cards.
        schema:
          $ref: '#/definitions/Error'
      503:
        description: Bunq integration not available.
        schema:
          $ref: '#/definitions/Error'
    """
    if not bunq_tools_available:
        return jsonify({"error": "Bunq integration not available"}), 503
    try:
        ctx = get_mock_context()
        result = get_cards(ctx)
        return process_tool_result(result)
    except Exception as e:
        print(f"Error in /bunq/cards GET: {e}")
        return jsonify({"error": str(e)}), 500


@app.route("/bunq/cards/<int:card_id>/link", methods=["PUT"])
async def route_link_card(card_id):
    """
    Link a card to a monetary account.
    ---
    tags:
      - Bunq
    description: Links a specific card to a specific monetary account by their IDs.
    parameters:
      - name: card_id
        in: path
        required: true
        description: The ID of the card to link.
        type: integer
      - name: body
        in: body
        required: true
        schema:
          type: object
          required:
            - account_id
          properties:
            account_id:
              type: integer
              description: The ID of the monetary account to link the card to.
              example: 98765
    responses:
      200:
        description: Card linked successfully.
        schema:
          # Assuming the result confirms the link
          type: object
          properties:
             message: { type: string, example: "Card 123 linked to account 98765" }
             # ... other potential response fields
      400:
        description: Bad Request - Missing 'account_id' in request body.
        schema:
          $ref: '#/definitions/Error'
      500:
        description: Internal server error or error linking card.
        schema:
          $ref: '#/definitions/Error'
      503:
        description: Bunq integration not available.
        schema:
          $ref: '#/definitions/Error'
    """
    if not bunq_tools_available:
        return jsonify({"error": "Bunq integration not available"}), 503
    try:
        data = await request.get_json()
        if not data or "account_id" not in data:
            return jsonify({"error": "Missing 'account_id' in request body"}), 400
        account_id = data["account_id"]
        ctx = get_mock_context()
        result = link_card(ctx, card_id=card_id, account_id=account_id)
        if bunq_instance and hasattr(bunq_instance, "update_context"):
            bunq_instance.update_context()
        return process_tool_result(result)
    except Exception as e:
        print(f"Error in /bunq/cards/<id>/link PUT: {e}")
        return jsonify({"error": str(e)}), 500


@app.route("/bunq/aliases", methods=["GET"])
async def route_get_aliases():
    """
    Get all aliases (pointers) for the user.
    ---
    tags:
      - Bunq
    description: Retrieves a list of all aliases (like IBANs, email, phone numbers) associated with the user's accounts.
    responses:
      200:
        description: List of aliases retrieved successfully.
        schema:
          type: array
          items:
            # Assuming the result is a JSON representation of Bunq Pointer objects
            type: object
            properties:
              type: { type: string, example: IBAN }
              value: { type: string, example: NL91ABNA0417164300 }
              name: { type: string, example: "Primary Account" }
              # ... other alias fields
      500:
        description: Internal server error or error retrieving aliases.
        schema:
          $ref: '#/definitions/Error'
      503:
        description: Bunq integration not available.
        schema:
          $ref: '#/definitions/Error'
    """
    if not bunq_tools_available:
        return jsonify({"error": "Bunq integration not available"}), 503
    try:
        ctx = get_mock_context()
        result = get_aliases(ctx)
        return process_tool_result(result)
    except Exception as e:
        print(f"Error in /bunq/aliases GET: {e}")
        return jsonify({"error": str(e)}), 500


@app.route("/bunq/callbacks", methods=["POST"])
async def route_add_callback_url():
    """
    Add a notification callback URL.
    ---
    tags:
      - Bunq
    description: Registers a URL to receive notifications (webhooks) for specific event types from Bunq.
    parameters:
      - name: body
        in: body
        required: true
        schema:
          type: object
          required:
            - callback_url
          properties:
            callback_url:
              type: string
              format: url
              description: The URL to which Bunq should send notifications.
              example: https://my-app.com/bunq/webhook
            # Potentially add 'category' parameter if the tool supports it
    responses:
      200:
        description: Callback URL added successfully.
        schema:
          # Assuming the result confirms the callback registration
          type: object
          properties:
             callback_id: { type: integer }
             status: { type: string, example: "ACTIVE" }
             # ... other potential response fields
      400:
        description: Bad Request - Missing 'callback_url' in request body.
        schema:
          $ref: '#/definitions/Error'
      500:
        description: Internal server error or error adding callback.
        schema:
          $ref: '#/definitions/Error'
      503:
        description: Bunq integration not available.
        schema:
          $ref: '#/definitions/Error'
    """
    if not bunq_tools_available:
        return jsonify({"error": "Bunq integration not available"}), 503
    try:
        data = await request.get_json()
        if not data or "callback_url" not in data:
            return jsonify({"error": "Missing 'callback_url' in request body"}), 400
        callback_url = data["callback_url"]
        ctx = get_mock_context()
        result = add_callback_url(ctx, callback_url=callback_url)
        if bunq_instance and hasattr(bunq_instance, "update_context"):
            bunq_instance.update_context()
        return process_tool_result(result)
    except Exception as e:
        print(f"Error in /bunq/callbacks POST: {e}")
        return jsonify({"error": str(e)}), 500


@app.route("/bunq/overview", methods=["GET"])
async def route_get_overview():
    """
    Get a financial overview.
    ---
    tags:
      - Bunq
    description: Retrieves a summary overview of the user's financial status (e.g., total balance, recent transactions).
    responses:
      200:
        description: Overview retrieved successfully.
        schema:
          # Define the structure based on the expected output of get_overview
          type: object
          properties:
            total_balance: { $ref: '#/definitions/Amount' }
            account_balances:
              type: array
              items:
                 type: object
                 properties:
                    account_id: { type: integer }
                    description: { type: string }
                    balance: { $ref: '#/definitions/Amount' }
            # ... other overview fields
      500:
        description: Internal server error or error retrieving overview.
        schema:
          $ref: '#/definitions/Error'
      503:
        description: Bunq integration not available.
        schema:
          $ref: '#/definitions/Error'
    """
    if not bunq_tools_available:
        return jsonify({"error": "Bunq integration not available"}), 503
    try:
        ctx = get_mock_context()
        result = get_overview(ctx)
        return process_tool_result(result)
    except Exception as e:
        print(f"Error in /bunq/overview GET: {e}")
        return jsonify({"error": str(e)}), 500


@app.route("/bunq/environment", methods=["GET"])
async def route_get_environment():
    """
    Get Bunq API environment info.
    ---
    tags:
      - Bunq
    description: Retrieves information about the Bunq API environment being used (Sandbox or Production).
    responses:
      200:
        description: Environment info retrieved successfully.
        schema:
          type: object
          properties:
            environment:
              type: string
              example: SANDBOX # or PRODUCTION
      500:
        description: Internal server error or error retrieving environment info.
        schema:
          $ref: '#/definitions/Error'
      503:
        description: Bunq integration not available.
        schema:
          $ref: '#/definitions/Error'
    """
    if not bunq_tools_available:
        return jsonify({"error": "Bunq integration not available"}), 503
    try:
        ctx = get_mock_context()
        result = get_environment(ctx)
        return jsonify(result)
    except Exception as e:
        print(f"Error in /bunq/environment GET: {e}")
        return jsonify({"error": str(e)}), 500


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=42069)

app.config['SWAGGER'] = {
    'title': 'MCP Service API',
    'uiversion': 3,
    'definitions': {
        'Error': {
            'type': 'object',
            'properties': {
                'error': {
                    'type': 'string',
                    'description': 'Error message detail.'
                }
            }
        },
        'Amount': {
            'type': 'object',
            'properties': {
                'currency': {
                    'type': 'string',
                    'description': 'The currency code (e.g., EUR).',
                    'example': 'EUR'
                },
                'value': {
                    'type': 'string', # Bunq uses string for amounts
                    'description': 'The amount value as a string.',
                    'example': '123.45'
                }
            }
        }
        # Add other common object definitions here if needed
    }
}

swagger = Swagger(app)
