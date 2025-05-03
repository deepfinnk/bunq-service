import json
from contextlib import asynccontextmanager
from collections.abc import AsyncIterator
from dataclasses import dataclass

from mcp.server.fastmcp import Context, FastMCP
from libs.share_lib import ShareLib, ShareLibOptions
from libs.bunq_lib import BunqLib
from bunq import ApiEnvironmentType
from typing import Dict
from camel.logger import get_logger

logger = get_logger(__name__)


@dataclass
class AppContext:
    bunq: BunqLib
    environment_type: ApiEnvironmentType


@asynccontextmanager
async def app_lifespan(server: FastMCP) -> AsyncIterator[AppContext]:
    """Manage application lifecycle with type-safe context"""
    # Initialize on startup
    all_option = ShareLibOptions()
    environment_type = ShareLib.determine_environment_type_from_all_option(all_option)
    bunq_instance = BunqLib(environment_type)
    # No async connect/disconnect seems available in BunqLib, managing instance directly
    try:
        yield AppContext(bunq=bunq_instance, environment_type=environment_type)
    finally:
        # Cleanup on shutdown (if needed, e.g., saving context)
        # bunq_instance.update_context() # Example if needed
        pass


# Create an MCP server with lifespan and dependency declaration
mcp = FastMCP("Bunq Banking API", lifespan=app_lifespan, dependencies=["bunq-sdk"])


def serialize_bunq_object(obj):
    if hasattr(obj, "__dict__"):
        return {
            key: serialize_bunq_object(value) for key, value in obj.__dict__.items()
        }
    elif isinstance(obj, list):
        return [serialize_bunq_object(item) for item in obj]
    elif isinstance(obj, dict):
        return {key: serialize_bunq_object(value) for key, value in obj.items()}
    else:
        return obj


# USER INFORMATION
@mcp.tool()
def get_user(ctx: Context):
    """
    Get current user information from Bunq.

    Returns details about the currently authenticated user including name, email,
    and other account information.
    """
    logger.info("Attempting to get user information")
    bunq_instance = ctx.request_context.lifespan_context.bunq
    user = bunq_instance.get_current_user()
    logger.info("Successfully retrieved user information")
    return json.dumps(serialize_bunq_object(user))


# ACCOUNTS


@mcp.tool()
def get_accounts(ctx: Context):
    """
    Get all active monetary accounts.

    Retrieves a list of all active bank accounts for the current user.

    Returns:
        List of monetary account details including balance, description, and status.
    """
    logger.info("Attempting to get active monetary accounts")
    bunq_instance = ctx.request_context.lifespan_context.bunq
    accounts = bunq_instance.get_all_monetary_account_active()
    logger.info(f"Successfully retrieved {len(accounts)} active accounts")
    return json.dumps(serialize_bunq_object(accounts))


@mcp.tool()
def update_account(ctx: Context, name: str, account_id: int) -> str:
    """
    Update a monetary account's description/name.

    Changes the name/description of a specified monetary account.

    Args:
        name: New description/name for the account
        account_id: ID of the monetary account to update

    Returns:
        Confirmation message
    """
    logger.info(f"Attempting to update account {account_id} name to '{name}'")
    bunq_instance = ctx.request_context.lifespan_context.bunq
    bunq_instance.update_account(name, account_id)
    bunq_instance.update_context()
    logger.info(f"Successfully updated account {account_id} name to '{name}'")
    return f"Account {account_id} has been renamed to '{name}'"


# PAYMENTS


@mcp.tool()
def get_payments(ctx: Context):
    """
    Get recent payments.

    Retrieves a list of recent payments from the primary monetary account.

    Returns:
        List of payment details including amount, description, and counterparty.
    """
    logger.info("Attempting to get recent payments")
    bunq_instance = ctx.request_context.lifespan_context.bunq
    payments = bunq_instance.get_all_payment()
    logger.info(f"Successfully retrieved {len(payments)} payments")
    return json.dumps(serialize_bunq_object(payments))


@mcp.tool()
def make_payment(ctx: Context, amount: str, description: str, recipient: str) -> str:
    """
    Make a payment to another Bunq user.

    Sends money from your primary account to another user identified by email.

    Args:
        amount: Amount to send as a string (e.g., "10.00")
        description: Payment description
        recipient: Email address of the recipient

    Returns:
        Confirmation message
    """
    logger.info(
        f"Attempting to make payment: {amount} to {recipient} ('{description}')"
    )
    bunq_instance = ctx.request_context.lifespan_context.bunq
    bunq_instance.make_payment(
        amount_string=amount,
        description=description,
        recipient=recipient,
    )
    bunq_instance.update_context()
    logger.info(f"Successfully made payment of €{amount} to {recipient}")
    return f"Payment of €{amount} sent to {recipient} with description: {description}"


# REQUESTS


@mcp.tool()
def get_requests(ctx: Context):
    """
    Get payment requests.

    Retrieves a list of payment requests (money requests) from the primary monetary account.

    Returns:
        List of request details including amount, description, and requestee.
    """
    logger.info("Attempting to get payment requests")
    bunq_instance = ctx.request_context.lifespan_context.bunq
    requests = bunq_instance.get_all_request()
    logger.info(f"Successfully retrieved {len(requests)} requests")
    return json.dumps(serialize_bunq_object(requests))


@mcp.tool()
def make_request(ctx: Context, amount: str, description: str, recipient: str) -> str:
    """
    Request money from another Bunq user.

    Creates a payment request from another user identified by email.

    Args:
        amount: Amount to request as a string (e.g., "10.00")
        description: Request description
        recipient: Email address of the person to request from

    Returns:
        Confirmation message
    """
    logger.info(
        f"Attempting to make request: {amount} from {recipient} ('{description}')"
    )
    bunq_instance = ctx.request_context.lifespan_context.bunq
    bunq_instance.make_request(
        amount_string=amount,
        description=description,
        recipient=recipient,
    )
    bunq_instance.update_context()
    logger.info(f"Successfully requested €{amount} from {recipient}")
    return f"Payment request of €{amount} sent to {recipient} with description: {description}"


# CARDS


@mcp.tool()
def get_cards(ctx: Context):
    """
    Get cards.

    Retrieves a list of cards associated with the user's account.

    Returns:
        List of card details including type, status, and expiry date.
    """
    logger.info("Attempting to get cards")
    bunq_instance = ctx.request_context.lifespan_context.bunq
    cards = bunq_instance.get_all_card()
    logger.info(f"Successfully retrieved {len(cards)} cards")
    return json.dumps(serialize_bunq_object(cards))


@mcp.tool()
def link_card(ctx: Context, card_id: int, account_id: int) -> str:
    """
    Link a card to a monetary account.

    Links a card to a specific monetary account as its primary account.

    Args:
        card_id: ID of the card to link
        account_id: ID of the monetary account to link the card to

    Returns:
        Confirmation message
    """
    logger.info(f"Attempting to link card {card_id} to account {account_id}")
    bunq_instance = ctx.request_context.lifespan_context.bunq
    bunq_instance.link_card(card_id, account_id)
    bunq_instance.update_context()
    logger.info(f"Successfully linked card {card_id} to account {account_id}")
    return f"Card {card_id} linked to account {account_id}"


# ALIASES (SANDBOX ONLY)


@mcp.tool()
def get_aliases(ctx: Context):
    """
    Get user aliases (Sandbox only).

    Retrieves all aliases (e.g., email, phone number) for the current user.
    Only available in sandbox mode.

    Returns:
        List of alias details.
    """
    logger.info("Attempting to get user aliases")
    bunq_instance = ctx.request_context.lifespan_context.bunq
    environment_type = ctx.request_context.lifespan_context.environment_type

    if environment_type != ApiEnvironmentType.SANDBOX:
        logger.warning("Attempted to get aliases in non-sandbox environment")
        return json.dumps([{"error": "Aliases can only be retrieved in sandbox mode"}])

    aliases = bunq_instance.get_all_user_alias()
    logger.info(f"Successfully retrieved {len(aliases)} aliases")
    return json.dumps(serialize_bunq_object(aliases))


# NOTIFICATIONS


@mcp.tool()
def add_callback_url(ctx: Context, callback_url: str) -> str:
    """
    Add a notification callback URL.

    Adds a URL to be notified for mutation events on the account.

    Args:
        callback_url: The URL to be notified for mutation events

    Returns:
        Confirmation message
    """
    logger.info(f"Attempting to add callback URL: {callback_url}")
    bunq_instance = ctx.request_context.lifespan_context.bunq
    bunq_instance.add_callback_url(callback_url)
    bunq_instance.update_context()
    logger.info(f"Successfully added callback URL: {callback_url}")
    return f"Callback URL {callback_url} has been added for notifications"


# OVERVIEW


@mcp.tool()
def get_overview(ctx: Context):
    """
    Get a complete account overview.

    Returns a comprehensive view of the user's Bunq account including user info,
    accounts, payments, requests, cards, and aliases (in sandbox mode).

    Returns:
        Dictionary containing all account information.
    """
    logger.info("Attempting to get complete account overview")
    bunq_instance = ctx.request_context.lifespan_context.bunq
    environment_type = ctx.request_context.lifespan_context.environment_type

    user = bunq_instance.get_current_user()
    accounts = bunq_instance.get_all_monetary_account_active()
    payments = bunq_instance.get_all_payment()
    requests = bunq_instance.get_all_request()
    cards = bunq_instance.get_all_card()

    overview = {
        "user": json.dumps(serialize_bunq_object(user)),
        "accounts": json.dumps(serialize_bunq_object(accounts)),
        "payments": json.dumps(serialize_bunq_object(payments)),
        "requests": json.dumps(serialize_bunq_object(requests)),
        "cards": json.dumps(serialize_bunq_object(cards)),
    }

    if environment_type == ApiEnvironmentType.SANDBOX:
        logger.info("Retrieving aliases for sandbox environment overview")
        aliases = bunq_instance.get_all_user_alias()
        overview["aliases"] = json.dumps(serialize_bunq_object(aliases))

    logger.info("Successfully generated account overview")
    return overview


# Environment info


@mcp.tool()
def get_environment(ctx: Context) -> Dict[str, str]:
    """
    Get information about the current Bunq environment.

    Returns whether the server is connected to the PRODUCTION or SANDBOX environment.

    Returns:
        Dictionary with environment information.
    """
    logger.info("Retrieving environment information")
    bunq_instance = ctx.request_context.lifespan_context.bunq
    environment_type = ctx.request_context.lifespan_context.environment_type

    env_type = (
        "PRODUCTION" if environment_type == ApiEnvironmentType.PRODUCTION else "SANDBOX"
    )
    config_file = bunq_instance.determine_bunq_conf_filename()
    logger.info(f"Environment type: {env_type}, Config file: {config_file}")
    return {
        "type": env_type,
        "config_file": config_file,
    }


def main(transport: str = "stdio"):
    r"""Runs the Filesystem MCP Server.

    Args:
        transport (str): The transport mode ('stdio' or 'sse').
    """
    if transport == "stdio":  # standard input output
        mcp.run(transport="stdio")
    elif transport == "sse":  # sse
        mcp.run(transport="sse")
    else:
        print(f"Unknown transport mode: {transport}")


# Run the server
if __name__ == "__main__":
    import sys

    transport_mode = sys.argv[1] if len(sys.argv) > 1 else "stdio"
    main(transport_mode)  # runn in the defined transport mode
