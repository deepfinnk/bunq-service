import json
from bunq.sdk.context.user_context import UserCompany
from mcp.server.fastmcp import FastMCP
from libs.share_lib import ShareLib, ShareLibOptions
from libs.bunq_lib import BunqLib
from bunq import ApiEnvironmentType
from typing import Dict
from camel.logger import get_logger

logger = get_logger(__name__)


all_option = ShareLibOptions()
environment_type = ShareLib.determine_environment_type_from_all_option(all_option)

# Create bunq connection
bunq = BunqLib(environment_type)


# Create an MCP server
mcp = FastMCP("Bunq Banking API")


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
@mcp.resource("bunq://user", mime_type="application/json")
def get_user():
    """
    Get current user information from Bunq.

    Returns details about the currently authenticated user including name, email,
    and other account information.
    """
    logger.info("Attempting to get user information")
    user = bunq.get_current_user()
    logger.info("Successfully retrieved user information")
    return json.dumps(serialize_bunq_object(user))


# ACCOUNTS


@mcp.resource("bunq://accounts", mime_type="application/json")
def get_accounts():
    """
    Get all active monetary accounts.

    Retrieves a list of all active bank accounts for the current user.

    Returns:
        List of monetary account details including balance, description, and status.
    """
    logger.info("Attempting to get active monetary accounts")
    accounts = bunq.get_all_monetary_account_active()
    logger.info(f"Successfully retrieved {len(accounts)} active accounts")
    return json.dumps(serialize_bunq_object(accounts))


@mcp.tool()
def update_account(name: str, account_id: int) -> str:
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
    bunq.update_account(name, account_id)
    bunq.update_context()
    logger.info(f"Successfully updated account {account_id} name to '{name}'")
    return f"Account {account_id} has been renamed to '{name}'"


# PAYMENTS


@mcp.resource("bunq://payments", mime_type="application/json")
def get_payments():
    """
    Get recent payments.

    Retrieves a list of recent payments from the primary monetary account.

    Returns:
        List of payment details including amount, description, and counterparty.
    """
    logger.info("Attempting to get recent payments")
    payments = bunq.get_all_payment()
    logger.info(f"Successfully retrieved {len(payments)} payments")
    return json.dumps(serialize_bunq_object(payments))


@mcp.tool()
def make_payment(amount: str, description: str, recipient: str) -> str:
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
        f"Attempting to make payment of €{amount} to {recipient} for '{description}'"
    )
    bunq.make_payment(amount, description, recipient)
    bunq.update_context()
    logger.info(f"Successfully made payment of €{amount} to {recipient}")
    return f"Payment of €{amount} sent to {recipient} with description: {description}"


# REQUESTS


@mcp.resource("bunq://requests", mime_type="application/json")
def get_requests():
    """
    Get payment requests.

    Retrieves a list of payment requests (money requests) from the primary monetary account.

    Returns:
        List of request details including amount, description, and requestee.
    """
    logger.info("Attempting to get payment requests")
    requests = bunq.get_all_request()
    logger.info(f"Successfully retrieved {len(requests)} requests")
    return json.dumps(serialize_bunq_object(requests))


@mcp.tool()
def make_request(amount: str, description: str, recipient: str) -> str:
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
    logger.info(f"Attempting to request €{amount} from {recipient} for '{description}'")
    bunq.make_request(amount, description, recipient)
    bunq.update_context()
    logger.info(f"Successfully requested €{amount} from {recipient}")
    return f"Payment request of €{amount} sent to {recipient} with description: {description}"


# CARDS


@mcp.resource("bunq://cards", mime_type="application/json")
def get_cards():
    """
    Get cards.

    Retrieves a list of cards associated with the user's account.

    Returns:
        List of card details including type, status, and expiry date.
    """
    logger.info("Attempting to get cards")
    cards = bunq.get_all_card()
    logger.info(f"Successfully retrieved {len(cards)} cards")
    return json.dumps(serialize_bunq_object(cards))


@mcp.tool()
def link_card(card_id: int, account_id: int) -> str:
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
    bunq.link_card(card_id, account_id)
    bunq.update_context()
    logger.info(f"Successfully linked card {card_id} to account {account_id}")
    return f"Card {card_id} has been linked to account {account_id}"


# ALIASES


@mcp.resource("bunq://aliases", mime_type="application/json")
def get_aliases():
    """
    Get all user aliases.

    Retrieves all aliases (e.g., email, phone number) for the current user.
    Only available in sandbox mode.

    Returns:
        List of alias details.
    """
    logger.info("Attempting to get aliases")
    if environment_type != ApiEnvironmentType.SANDBOX:
        logger.warning("Attempted to get aliases in non-sandbox environment")
        return json.dumps([{"error": "Aliases can only be retrieved in sandbox mode"}])

    aliases = bunq.get_all_user_alias()
    logger.info(f"Successfully retrieved {len(aliases)} aliases")
    return json.dumps(serialize_bunq_object(aliases))


# NOTIFICATIONS


@mcp.tool()
def add_callback_url(callback_url: str) -> str:
    """
    Add a notification callback URL.

    Adds a URL to be notified for mutation events on the account.

    Args:
        callback_url: The URL to be notified for mutation events

    Returns:
        Confirmation message
    """
    logger.info(f"Attempting to add callback URL: {callback_url}")
    bunq.add_callback_url(callback_url)
    bunq.update_context()
    logger.info(f"Successfully added callback URL: {callback_url}")
    return f"Callback URL {callback_url} has been added for notifications"


# OVERVIEW


@mcp.resource("bunq://overview", mime_type="application/json")
def get_overview():
    """
    Get a complete account overview.

    Returns a comprehensive view of the user's Bunq account including user info,
    accounts, payments, requests, cards, and aliases (in sandbox mode).

    Returns:
        Dictionary containing all account information.
    """
    logger.info("Attempting to get complete account overview")
    user = bunq.get_current_user()
    accounts = bunq.get_all_monetary_account_active()
    payments = bunq.get_all_payment()
    requests = bunq.get_all_request()
    cards = bunq.get_all_card()

    overview = {
        "user": json.dumps(serialize_bunq_object(user)),
        "accounts": json.dumps(serialize_bunq_object(accounts)),
        "payments": json.dumps(serialize_bunq_object(payments)),
        "requests": json.dumps(serialize_bunq_object(requests)),
        "cards": json.dumps(serialize_bunq_object(cards)),
    }

    if environment_type == ApiEnvironmentType.SANDBOX:
        logger.info("Retrieving aliases for sandbox environment overview")
        aliases = bunq.get_all_user_alias()
        overview["aliases"] = json.dumps(serialize_bunq_object(aliases))

    logger.info("Successfully generated account overview")
    return overview


# Environment info


@mcp.resource("bunq://environment", mime_type="application/json")
def get_environment() -> Dict[str, str]:
    """
    Get information about the current Bunq environment.

    Returns whether the server is connected to the PRODUCTION or SANDBOX environment.

    Returns:
        Dictionary with environment information.
    """
    logger.info("Retrieving environment information")
    env_type = (
        "PRODUCTION" if environment_type == ApiEnvironmentType.PRODUCTION else "SANDBOX"
    )
    config_file = bunq.determine_bunq_conf_filename()
    logger.info(f"Environment type: {env_type}, Config file: {config_file}")
    return {
        "type": env_type,
        "config_file": config_file,
    }


# Run the server
if __name__ == "__main__":
    mcp.run()
