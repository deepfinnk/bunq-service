import argparse
import os
import sys
from typing import List, Union, Optional
from dataclasses import dataclass
from bunq import ApiEnvironmentType
from bunq.sdk.exception.bunq_exception import BunqException
from bunq.sdk.model.generated.endpoint import (
    Card,
    MonetaryAccountBank,
    UserCompany,
    UserLight,
    UserPerson,
)
from bunq.sdk.model.generated.object_ import LabelMonetaryAccount, Pointer


@dataclass
class ShareLibOptions:
    production: bool = False
    amount: Optional[str] = None
    description: Optional[str] = None
    recipient: Optional[str] = None
    card_id: Optional[str] = None
    account_id: Optional[str] = None
    callback_url: Optional[str] = None
    name: Optional[str] = None


class ShareLib(object):
    _ERROR_COULD_NOT_FIND_IBAN_POINTER = (
        "Could not determine IBAN for Monetary Account."
    )

    _OPTION_PRODUCTION = "--production"
    _OPTION_AMOUNT = "--amount"
    _OPTION_DESCRIPTION = "--description"
    _OPTION_RECIPIENT = "--recipient"
    _OPTION_CARD_ID = "--card-id"
    _OPTION_ACCOUNT_ID = "--account-id"
    _OPTION_CALLBACK_URL = "--callback-url"
    _OPTION_NAME = "--name"

    _ECHO_USER = os.linesep + "   User"
    _ECHO_MONETARY_ACCOUNT = os.linesep + "   Monetary Accounts"
    _ECHO_PAYMENT = os.linesep + "   Payments"
    _ECHO_REQUEST = os.linesep + "   Request"
    _ECHO_CARD = os.linesep + "   Card"
    _ECHO_AMOUNT_IN_EUR = os.linesep + "    Amount (EUR): "
    _ECHO_DESCRIPTION = os.linesep + "    Description: "
    _ECHO_RECIPIENT = os.linesep + "    Recipient (%s): "
    _ECHO_CARD_ID = os.linesep + "    Card (ID): "
    _ECHO_ACCOUNT_ID = os.linesep + "    Account (ID): "
    _ECHO_CALLBACK_URL = os.linesep + "    Callback URL: "
    _ECHO_NEW_NAME = os.linesep + "    New Name: "

    _DEFAULT_CARD_SECOND_LINE = "bunq card"
    _DEFAULT_RECIPIENT_EMAIL = "e.g. bravo@bunq.com"

    _POINTER_TYPE_EMAIL = "EMAIL"
    _POINTER_TYPE_IBAN = "IBAN"
    _POINTER_TYPE_PHONE = "PHONE_NUMBER"

    environment_type: Optional[ApiEnvironmentType] = None

    @classmethod
    def parse_all_option(cls):
        """Parses command line arguments using argparse.

        Defines expected arguments like --production, --amount, etc.

        Returns:
            The parsed arguments object.
        """
        parser = argparse.ArgumentParser()
        parser.add_argument(cls._OPTION_PRODUCTION, action="store_true")
        parser.add_argument(cls._OPTION_AMOUNT)
        parser.add_argument(cls._OPTION_DESCRIPTION)
        parser.add_argument(cls._OPTION_RECIPIENT)
        parser.add_argument(cls._OPTION_CARD_ID)
        parser.add_argument(cls._OPTION_ACCOUNT_ID)
        parser.add_argument(cls._OPTION_CALLBACK_URL)
        parser.add_argument(cls._OPTION_NAME)
        return ShareLibOptions(**parser.parse_args().__dict__)

    @classmethod
    def determine_environment_type_from_all_option(
        cls, all_option
    ) -> ApiEnvironmentType:
        """Determines the API environment (PRODUCTION or SANDBOX) based on options.

        Sets the class variable `environment_type`.

        Args:
            all_option: The parsed command line arguments object.

        Returns:
            The determined ApiEnvironmentType.
        """
        if all_option.production:
            cls.environment_type = ApiEnvironmentType.PRODUCTION
        else:
            cls.environment_type = ApiEnvironmentType.SANDBOX

        if cls.environment_type is None:
            raise ValueError("Environment type not determined")

        return cls.environment_type

    @classmethod
    def determine_amount_from_all_option_or_std_in(cls, all_option) -> str:
        """Gets the amount from command line options or prompts the user.

        Args:
            all_option: The parsed command line arguments object.

        Returns:
            The amount string.
        """
        if all_option.amount:
            return all_option.amount
        else:
            print(cls._ECHO_AMOUNT_IN_EUR, end="")

            return sys.stdin.readline().strip()

    @classmethod
    def determine_description_from_all_option_or_std_in(cls, all_option) -> str:
        """Gets the description from command line options or prompts the user.

        Args:
            all_option: The parsed command line arguments object.

        Returns:
            The description string.
        """
        if all_option.description:
            return all_option.description
        else:
            print(cls._ECHO_DESCRIPTION, end="")

            return sys.stdin.readline().strip()

    @classmethod
    def determine_recipient_from_all_option_or_std_in(cls, all_option) -> str:
        """Gets the recipient from command line options or prompts the user.

        Provides a hint based on the environment (SANDBOX or PRODUCTION).

        Args:
            all_option: The parsed command line arguments object.

        Returns:
            The recipient string (e.g., email address).
        """
        if all_option.recipient:
            return all_option.recipient
        else:
            if ApiEnvironmentType.SANDBOX == cls.environment_type:
                input_hint = cls._DEFAULT_RECIPIENT_EMAIL
            else:
                input_hint = cls._POINTER_TYPE_EMAIL

            print(cls._ECHO_RECIPIENT % input_hint, end="")
            return sys.stdin.readline().strip()

    @classmethod
    def determine_card_id_from_all_option_or_std_in(cls, all_option) -> str:
        """Gets the card ID from command line options or prompts the user.

        Args:
            all_option: The parsed command line arguments object.

        Returns:
            The card ID string.
        """
        if all_option.card_id:
            return all_option.card_id
        else:
            print(cls._ECHO_CARD_ID, end="")

            return sys.stdin.readline().strip()

    @classmethod
    def determine_account_id_from_all_option_or_std_in(cls, all_option) -> str:
        """Gets the account ID from command line options or prompts the user.

        Args:
            all_option: The parsed command line arguments object.

        Returns:
            The account ID string.
        """
        if all_option.account_id:
            return all_option.account_id
        else:
            print(cls._ECHO_ACCOUNT_ID, end="")

            return sys.stdin.readline().strip()

    @classmethod
    def determine_callback_url_from_all_option_or_std_in(cls, all_option) -> str:
        """Gets the callback URL from command line options or prompts the user.

        Args:
            all_option: The parsed command line arguments object.

        Returns:
            The callback URL string.
        """
        if all_option.callback_url:
            return all_option.callback_url
        else:
            print(cls._ECHO_CALLBACK_URL, end="")
            return sys.stdin.readline().strip()
        pass

    @classmethod
    def determine_name_from_all_option_or_std_in(cls, all_option) -> str:
        """Gets the name (e.g., for account update) from command line options or prompts the user.

        Args:
            all_option: The parsed command line arguments object.

        Returns:
            The name string.
        """
        if all_option.name:
            return all_option.name
        else:
            print(cls._ECHO_NEW_NAME, end="")

            return sys.stdin.readline().strip()
        pass

    @classmethod
    def print_header(cls):
        """Prints the header for the tinker script output."""
        if ApiEnvironmentType.SANDBOX == cls.environment_type:
            print("""
\033[94m
  ████████╗██╗███╗   ██╗██╗  ██╗███████╗██████╗ ██╗███╗   ██╗ ██████╗
  ╚══██╔══╝██║████╗  ██║██║ ██╔╝██╔════╝██╔══██╗██║████╗  ██║██╔════╝
     ██║   ██║██╔██╗ ██║█████╔╝ █████╗  ██████╔╝██║██╔██╗ ██║██║  ███╗
     ██║   ██║██║╚██╗██║██╔═██╗ ██╔══╝  ██╔══██╗██║██║╚██╗██║██║   ██║
     ██║   ██║██║ ╚████║██║  ██╗███████╗██║  ██║██║██║ ╚████║╚██████╔╝
     ╚═╝   ╚═╝╚═╝  ╚═══╝╚═╝  ╚═╝╚══════╝╚═╝  ╚═╝╚═╝╚═╝  ╚═══╝ ╚═════╝
\033[0m
            """)
        else:
            print("""
\033[93m
  ██████╗ ██████╗  ██████╗ ██████╗ ██╗   ██╗ ██████╗████████╗██╗ ██████╗ ███╗   ██╗
  ██╔══██╗██╔══██╗██╔═══██╗██╔══██╗██║   ██║██╔════╝╚══██╔══╝██║██╔═══██╗████╗  ██║
  ██████╔╝██████╔╝██║   ██║██║  ██║██║   ██║██║        ██║   ██║██║   ██║██╔██╗ ██║
  ██╔═══╝ ██╔══██╗██║   ██║██║  ██║██║   ██║██║        ██║   ██║██║   ██║██║╚██╗██║
  ██║     ██║  ██║╚██████╔╝██████╔╝╚██████╔╝╚██████╗   ██║   ██║╚██████╔╝██║ ╚████║
  ╚═╝     ╚═╝  ╚═╝ ╚═════╝ ╚═════╝  ╚═════╝  ╚═════╝   ╚═╝   ╚═╝ ╚═════╝ ╚═╝  ╚═══╝
\033[0m
            """)

    @classmethod
    def print_user(cls, user: Union[UserPerson, UserCompany, UserLight]):
        """Prints formatted information about a user.

        Args:
            user: The user object (UserPerson, UserCompany, or UserLight).
        """
        print(cls._ECHO_USER)
        print(f"""
  ┌───────────────────┬────────────────────────────────────────────────────
  │ ID                │ {user.id_}
  ├───────────────────┼────────────────────────────────────────────────────
  │ Username          │ {user.display_name}
  └───────────────────┴────────────────────────────────────────────────────""")

    @classmethod
    def print_all_monetary_account_bank(
        cls, all_monetary_account_bank: List[MonetaryAccountBank]
    ):
        """Prints formatted information for a list of monetary accounts.

        Args:
            all_monetary_account_bank: A list of MonetaryAccountBank objects.
        """
        print(cls._ECHO_MONETARY_ACCOUNT)

        for monetary_account_bank in all_monetary_account_bank:
            cls.print_monetary_account_bank(monetary_account_bank)

    @classmethod
    def print_monetary_account_bank(cls, monetary_account_bank: MonetaryAccountBank):
        """Prints formatted details of a single monetary account.

        Args:
            monetary_account_bank: The MonetaryAccountBank object to print.
        """
        pointer_iban = cls.get_first_pointer_iban(monetary_account_bank)

        print(f"""
  ┌───────────────────┬────────────────────────────────────────────────────
  │ ID                │ {monetary_account_bank.id_}
  ├───────────────────┼────────────────────────────────────────────────────
  │ Description       │ {monetary_account_bank.description}
  ├───────────────────┼────────────────────────────────────────────────────
  │ IBAN              │ {pointer_iban.value}""")

        if monetary_account_bank.balance is not None:
            print(f"""  ├───────────────────┼────────────────────────────────────────────────────
  │ Balance           │ {monetary_account_bank.balance.currency} {monetary_account_bank.balance.value}""")

        print(
            "  └───────────────────┴────────────────────────────────────────────────────"
        )

    @classmethod
    def get_first_pointer_iban(cls, monetary_account_bank) -> Pointer:
        """Retrieves the first IBAN pointer from a monetary account's aliases.

        Args:
            monetary_account_bank: The monetary account object.

        Returns:
            The first Pointer object with type IBAN.

        Raises:
            BunqException: If no IBAN pointer is found.
        """
        for alias in monetary_account_bank.alias:
            if alias.type_ == cls._POINTER_TYPE_IBAN:
                return alias

        raise BunqException(cls._ERROR_COULD_NOT_FIND_IBAN_POINTER)

    @classmethod
    def print_all_payment(cls, all_payment):
        """Prints formatted information for a list of payments.

        Args:
            all_payment: A list of Payment objects.
        """
        print(cls._ECHO_PAYMENT)

        for payment in all_payment:
            cls.print_payment(payment)

    @classmethod
    def print_payment(cls, payment):
        """Prints formatted details of a single payment.

        Args:
            payment: The Payment object to print.
        """
        print(f"""
  ┌───────────────────┬────────────────────────────────────────────────────
  │ ID                │ {payment.id_}
  ├───────────────────┼────────────────────────────────────────────────────
  │ Description       │ {payment.description}
  ├───────────────────┼────────────────────────────────────────────────────
  │ Amount            │ {payment.amount.currency} {payment.amount.value}
  ├───────────────────┼────────────────────────────────────────────────────
  │ Recipient         │ {payment.counterparty_alias.label_monetary_account.display_name}
  └───────────────────┴────────────────────────────────────────────────────""")

    @classmethod
    def print_all_request(cls, all_request):
        """Prints formatted information for a list of requests (inquiries).

        Args:
            all_request: A list of RequestInquiry objects.
        """
        print(cls._ECHO_REQUEST)

        for request in all_request:
            cls.print_request(request)

    @classmethod
    def print_request(cls, request):
        """Prints formatted details of a single request (inquiry).

        Args:
            request: The RequestInquiry object to print.
        """
        print(f"""
  ┌───────────────────┬────────────────────────────────────────────────────
  │ ID                │ {request.id_}
  ├───────────────────┼────────────────────────────────────────────────────
  │ Description       │ {request.description}
  ├───────────────────┼────────────────────────────────────────────────────
  │ Status            │ {request.status}
  ├───────────────────┼────────────────────────────────────────────────────
  │ Amount            │ {request.amount_inquired.currency} {request.amount_inquired.value}
  ├───────────────────┼────────────────────────────────────────────────────
  │ Recipient         │ {request.counterparty_alias.label_monetary_account.display_name}
  └───────────────────┴────────────────────────────────────────────────────""")

    @classmethod
    def print_all_card(cls, all_card, all_monetary_account):
        """Prints formatted information for a list of cards.

        Args:
            all_card: A list of Card objects.
            all_monetary_account: A list of all MonetaryAccountBank objects
                (used to resolve linked account details).
        """
        print(cls._ECHO_CARD)

        for card in all_card:
            cls.print_card(card, all_monetary_account)

    @classmethod
    def print_card(cls, card: Card, all_monetary_account: List[MonetaryAccountBank]):
        """Prints formatted details of a single card, including its linked account.

        Args:
            card: The Card object to print.
            all_monetary_account: A list of all MonetaryAccountBank objects
                (used to resolve linked account details).
        """
        if card.label_monetary_account_current is None:
            linked_account = "No account linked yet."
        else:
            monetary_account = cls.get_monetary_account_from_label(
                card.label_monetary_account_current.label_monetary_account,
                all_monetary_account,
            )

            linked_account = (
                (
                    f"{monetary_account.description} "
                    f"({card.label_monetary_account_current.label_monetary_account.iban})"
                )
                if monetary_account
                else "NONE"
            )
        print(f"""
  ┌───────────────────┬────────────────────────────────────────────────────
  │ ID                │ {card.id_}
  ├───────────────────┼────────────────────────────────────────────────────
  │ Type              │ {card.type_}
  ├───────────────────┼────────────────────────────────────────────────────
  │ Name on Card      │ {card.name_on_card}
  ├───────────────────┼────────────────────────────────────────────────────
  │ Description       │ {card.second_line or cls._DEFAULT_CARD_SECOND_LINE}
  ├───────────────────┼────────────────────────────────────────────────────
  │ Linked Account    │ {linked_account}
  └───────────────────┴────────────────────────────────────────────────────""")

    @classmethod
    def get_monetary_account_from_label(
        cls,
        label_monetary_account_current: LabelMonetaryAccount,
        all_monetary_account: List[MonetaryAccountBank],
    ) -> Union[MonetaryAccountBank, None]:
        """Finds a monetary account matching a given label (IBAN).

        Used to link card labels back to full account objects.

        Args:
            label_monetary_account_current: The label containing the IBAN to search for.
            all_monetary_account: The list of all monetary accounts to search within.

        Returns:
            The matching MonetaryAccountBank object, or None if not found.
        """
        iban_label = label_monetary_account_current.iban

        for monetary_account in all_monetary_account:
            iban_monetary_account = cls.get_first_pointer_iban(monetary_account).value

            if iban_label == iban_monetary_account:
                return monetary_account

        return None

    @staticmethod
    def print_all_user_alias(all_user_alias: List[Pointer]):
        """Prints formatted details for a list of user aliases (Pointers).

        Also includes information relevant for Sandbox login (confirmation/login codes).

        Args:
            all_user_alias: A list of Pointer objects representing user aliases.
        """
        print(
            "\n"
            + "   You can use these login credentials to login in to the bunq sandbox app."
        )

        for alias in all_user_alias:
            print(f"""
  ┌───────────────────┬────────────────────────────────────────────────────
  │ Value             │ {alias.value}
  ├───────────────────┼────────────────────────────────────────────────────
  │ Type              │ {alias.type_}
  ├───────────────────┼────────────────────────────────────────────────────""")
            if alias.type_ == ShareLib._POINTER_TYPE_PHONE:
                print("""  │ Confirmation Code │ 123456
  ├───────────────────┼────────────────────────────────────────────────────""")
            print("""  │ Login Code        │ 000000
  └───────────────────┴────────────────────────────────────────────────────""")
