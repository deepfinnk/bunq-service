from mcp.server.fastmcp import FastMCP
from libs.share_lib import ShareLib, ShareLibOptions
from libs.bunq_lib import BunqLib
from bunq import ApiEnvironmentType
from typing import Dict

all_option = ShareLibOptions()
environment_type = ShareLib.determine_environment_type_from_all_option(all_option)

# Create bunq connection
bunq = BunqLib(environment_type)

# Create an MCP server
mcp = FastMCP("Bunq Banking API")


# USER INFORMATION
@mcp.resource("bunq://user", mime_type="application/json")
def get_user():
    """
    Get current user information from Bunq.

    Returns details about the currently authenticated user including name, email,
    and other account information.
    """
    return bunq.get_current_user()


# ACCOUNTS


@mcp.resource("bunq://accounts", mime_type="application/json")
def get_accounts():
    """
    Get all active monetary accounts.

    Retrieves a list of all active bank accounts for the current user.

    Returns:
        List of monetary account details including balance, description, and status.
    """
    accounts = bunq.get_all_monetary_account_active()
    print(accounts)
    return accounts


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
    bunq.update_account(name, account_id)
    bunq.update_context()
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
    payments = bunq.get_all_payment()
    return payments


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
    bunq.make_payment(amount, description, recipient)
    bunq.update_context()
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
    requests = bunq.get_all_request()
    return requests


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
    bunq.make_request(amount, description, recipient)
    bunq.update_context()
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
    cards = bunq.get_all_card()
    return cards


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
    bunq.link_card(card_id, account_id)
    bunq.update_context()
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
    if environment_type != ApiEnvironmentType.SANDBOX:
        return [{"error": "Aliases can only be retrieved in sandbox mode"}]

    aliases = bunq.get_all_user_alias()
    return aliases


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
    bunq.add_callback_url(callback_url)
    bunq.update_context()
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
    user = bunq.get_current_user()
    accounts = bunq.get_all_monetary_account_active()
    payments = bunq.get_all_payment()
    requests = bunq.get_all_request()
    cards = bunq.get_all_card()

    overview = {
        "user": user,
        "accounts": accounts,
        "payments": payments,
        "requests": requests,
        "cards": cards,
    }

    if environment_type == ApiEnvironmentType.SANDBOX:
        aliases = bunq.get_all_user_alias()
        overview["aliases"] = aliases

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
    return {
        "type": "PRODUCTION"
        if environment_type == ApiEnvironmentType.PRODUCTION
        else "SANDBOX",
        "config_file": bunq.determine_bunq_conf_filename(),
    }


# Run the server
if __name__ == "__main__":
    mcp.run()
