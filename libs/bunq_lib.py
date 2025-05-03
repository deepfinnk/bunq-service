import json
import socket
from os import remove
from os.path import isfile
from time import sleep
from typing import Union, List, Optional

import requests
from bunq import Pagination
from bunq.sdk.context.api_context import ApiContext, ApiEnvironmentType
from bunq.sdk.context.bunq_context import BunqContext
from bunq.sdk.exception.bunq_exception import BunqException
from bunq.sdk.exception.forbidden_exception import ForbiddenException
from bunq.sdk.model.core.notification_filter_url_user_internal import (
    NotificationFilterUrlUserInternal,
)
from bunq.sdk.model.generated.endpoint import (
    UserCompany,
    UserPerson,
    MonetaryAccountBank,
    UserLight,
    User,
    Payment,
    RequestInquiry,
    Card,
    NotificationFilterUrlUser,
    SandboxUserPerson,
)
from bunq.sdk.model.generated.object_ import Amount, NotificationFilterUrl
from bunq.sdk.model.generated.object_ import CardPinAssignment
from bunq.sdk.model.generated.object_ import Pointer

NOTIFICATION_DELIVERY_METHOD_URL = "URL"

NOTIFICATION_CATEGORY_MUTATION = "MUTATION"


class BunqLib(object):
    _ERROR_COULD_NOT_DETERMINE_CONF = "Could not find the bunq configuration file."
    _ERROR_COULD_NOT_CREATE_NEW_SANDBOX_USER = "Could not create new sandbox user."
    _BUNQ_CONF_PRODUCTION = "bunq-production.conf"
    _BUNQ_CONF_SANDBOX = "bunq-sandbox.conf"

    _MONETARY_ACCOUNT_STATUS_ACTIVE = "ACTIVE"

    _CARD_PIN_ASSIGNMENT_TYPE = "PRIMARY"

    _DEFAULT_COUNT = 10
    _POINTER_TYPE_EMAIL = "EMAIL"
    _CURRENCY_EUR = "EUR"
    _DEVICE_DESCRIPTION = "python tinker"

    _REQUEST_SPENDING_MONEY_AMOUNT = "500.0"
    _REQUEST_SPENDING_MONEY_RECIPIENT = "sugardaddy@bunq.com"
    _REQUEST_SPENDING_MONEY_DESCRIPTION = "Requesting some spending money."
    _REQUEST_SPENDING_MONEY_WAIT_TIME_SECONDS = 1

    _ZERO_BALANCE = 0.0

    def __init__(self, env: ApiEnvironmentType):
        """Initializes the BunqLib instance.

        Args:
            env: The API environment type (PRODUCTION or SANDBOX).
        """
        self.user = None
        self.env = env
        self.setup_context()
        self.setup_current_user()
        self.__request_spending_money_if_needed()

    def setup_context(self, reset_config_if_needed=True):
        """Sets up the API context.

        Restores the context from the configuration file if it exists.
        If the environment is SANDBOX and the config file doesn't exist,
        it generates a new sandbox user and creates the context.

        Args:
            reset_config_if_needed: If True and a ForbiddenException occurs
                (likely due to an invalid config), the config file will be
                removed (in SANDBOX) and setup will be retried. Defaults to True.

        Raises:
            BunqException: If the environment is PRODUCTION and the config file
                cannot be found.
            ForbiddenException: If context restoration fails and
                reset_config_if_needed is False.
        """
        if isfile(self.determine_bunq_conf_filename()):
            pass  # Config is already present
        elif self.env == ApiEnvironmentType.SANDBOX:
            sandbox_user = self.generate_new_sandbox_user()
            ApiContext.create(
                ApiEnvironmentType.SANDBOX, sandbox_user.api_key, socket.gethostname()
            ).save(self.determine_bunq_conf_filename())
        else:
            raise BunqException(self._ERROR_COULD_NOT_DETERMINE_CONF)

        try:
            api_context = ApiContext.restore(self.determine_bunq_conf_filename())
            api_context.ensure_session_active()
            api_context.save(self.determine_bunq_conf_filename())

            BunqContext.load_api_context(api_context)
        except ForbiddenException as forbidden_exception:
            if reset_config_if_needed:
                self.__handle_forbidden_exception(forbidden_exception)
            else:
                raise forbidden_exception

    def determine_bunq_conf_filename(self):
        """Determines the bunq configuration filename based on the environment.

        Returns:
            The filename for the bunq configuration file.
        """
        if self.env == ApiEnvironmentType.PRODUCTION:
            return self._BUNQ_CONF_PRODUCTION
        else:
            return self._BUNQ_CONF_SANDBOX

    def __handle_forbidden_exception(self, forbidden_exception):
        """Handles a ForbiddenException, typically by resetting the config in SANDBOX.

        Args:
            forbidden_exception: The caught ForbiddenException.

        Raises:
            ForbiddenException: Re-raises the exception if the environment is PRODUCTION.
        """
        if self.env == ApiEnvironmentType.SANDBOX:
            remove(self.determine_bunq_conf_filename())
            self.setup_context(False)
        else:
            raise forbidden_exception

    def setup_current_user(self):
        """Get the current user from the context and assign to self.user."""
        user = User.get().value.get_referenced_object()
        if (
            isinstance(user, UserPerson)
            or isinstance(user, UserCompany)
            or isinstance(user, UserLight)
        ):
            self.user = user

    def update_context(self):
        """Saves the current API context to the configuration file."""
        BunqContext.api_context().save(self.determine_bunq_conf_filename())

    def get_current_user(self) -> Union[UserCompany, UserPerson]:
        """Returns the currently logged-in user object.

        Returns:
            The UserCompany or UserPerson object representing the current user.
        """
        return self.user

    def get_all_monetary_account_active(
        self, count: int = _DEFAULT_COUNT
    ) -> List[MonetaryAccountBank]:
        """Retrieves all active monetary accounts for the current user.

        Args:
            count: The maximum number of accounts to retrieve. Defaults to _DEFAULT_COUNT.

        Returns:
            A list of active MonetaryAccountBank objects.
        """
        pagination = Pagination()
        pagination.count = count

        all_monetary_account_bank = MonetaryAccountBank.list(
            pagination.url_params_count_only
        ).value
        all_monetary_account_bank_active = []

        for monetary_account_bank in all_monetary_account_bank:
            if monetary_account_bank.status == self._MONETARY_ACCOUNT_STATUS_ACTIVE:
                all_monetary_account_bank_active.append(monetary_account_bank)

        return all_monetary_account_bank_active

    def get_all_payment(self, count: int = _DEFAULT_COUNT) -> List[Payment]:
        """Retrieves all payments for the primary monetary account.

        Args:
            count: The maximum number of payments to retrieve. Defaults to _DEFAULT_COUNT.

        Returns:
            A list of Payment objects.
        """
        pagination = Pagination()
        pagination.count = count

        return Payment.list(params=pagination.url_params_count_only).value

    def get_all_request(self, count: int = _DEFAULT_COUNT) -> List[RequestInquiry]:
        """Retrieves all requests (inquiries) for the primary monetary account.

        Args:
            count: The maximum number of requests to retrieve. Defaults to _DEFAULT_COUNT.

        Returns:
            A list of RequestInquiry objects.
        """
        pagination = Pagination()
        pagination.count = count

        return RequestInquiry.list(params=pagination.url_params_count_only).value

    def get_all_card(self, count: int = _DEFAULT_COUNT) -> List[Card]:
        """Retrieves all cards associated with the user.

        Args:
            count: The maximum number of cards to retrieve. Defaults to _DEFAULT_COUNT.

        Returns:
            A list of Card objects.
        """
        pagination = Pagination()
        pagination.count = count

        return Card.list(pagination.url_params_count_only).value

    def make_payment(self, amount_string: str, description: str, recipient: str):
        """Creates a new payment from the primary monetary account.

        Args:
            amount_string: The amount of the payment as a string (e.g., "10.00").
            description: The description for the payment.
            recipient: The email address of the recipient.
        """
        Payment.create(
            amount=Amount(amount_string, self._CURRENCY_EUR),
            counterparty_alias=Pointer(self._POINTER_TYPE_EMAIL, recipient),
            description=description,
        )

    def make_request(self, amount_string: str, description: str, recipient: str):
        """Creates a new payment request (inquiry).

        Args:
            amount_string: The amount requested as a string (e.g., "10.00").
            description: The description for the request.
            recipient: The email address of the person to request from.
        """
        RequestInquiry.create(
            amount_inquired=Amount(amount_string, self._CURRENCY_EUR),
            counterparty_alias=Pointer(self._POINTER_TYPE_EMAIL, recipient),
            description=description,
            allow_bunqme=True,
        )

    def link_card(self, card_id: int, account_id: int):
        """Links a card to a specific monetary account as its primary account.

        Args:
            card_id: The ID of the card to link.
            account_id: The ID of the monetary account to link the card to.
        """
        Card.update(
            card_id=card_id,
            pin_code_assignment=[
                CardPinAssignment(
                    type_=self._CARD_PIN_ASSIGNMENT_TYPE, monetary_account_id=account_id
                )
            ],
        )

    def add_callback_url(self, callback_url: str):
        """Adds a notification callback URL for mutation events.

        If the URL already exists for mutations, it ensures it's present.
        If other URLs exist, they are preserved.

        Args:
            callback_url: The URL to be notified for mutation events.
        """
        all_notification_filter_current = NotificationFilterUrlUser.list().value
        all_notification_filter_updated = []

        for notification_filter_url_user in all_notification_filter_current:
            for (
                notification_filter_url
            ) in notification_filter_url_user.notification_filters:
                if callback_url == notification_filter_url.notification_target:
                    all_notification_filter_updated.append(notification_filter_url)

        all_notification_filter_updated.append(
            NotificationFilterUrl(NOTIFICATION_CATEGORY_MUTATION, callback_url)
        )

        NotificationFilterUrlUserInternal.create_with_list_response(
            all_notification_filter_updated
        )

    def update_account(self, name: str, account_id: int):
        """Updates the description (name) of a monetary account.

        Args:
            name: The new description/name for the account.
            account_id: The ID of the monetary account to update.
        """
        MonetaryAccountBank.update(
            monetary_account_bank_id=account_id, description=name
        )

    def create_account(self, description: str, daily_limit: Optional[Amount]):
        """Creates a new monetary account. Can be used to create an account for budgeting."""
        user = self.get_current_user()
        if isinstance(user, UserPerson):
            name = user.legal_name
        elif isinstance(user, UserCompany):
            name = user.name
        else:
            name = ""
        return MonetaryAccountBank.create(
            daily_limit=daily_limit,
            currency="EUR",
            display_name=name,
            description=description,
        )

    def get_all_user_alias(self) -> List[Pointer]:
        """Retrieves all aliases (e.g., email, phone number) for the current user.

        Returns:
            A list of Pointer objects representing the user's aliases.
        """
        return self.get_current_user().alias

    def generate_new_sandbox_user(
        self,
    ) -> SandboxUserPerson:
        """Generates a new sandbox user via the bunq API.

        Returns:
            A SandboxUserPerson object containing the API key for the new user.

        Raises:
            BunqException: If the sandbox user creation fails.
        """
        url = ApiEnvironmentType.SANDBOX.uri_base + "sandbox-user-person"

        headers = {
            "x-bunq-client-request-id": "uniqueness-is-required",
            "cache-control": "no-cache",
            "x-bunq-geolocation": "0 0 0 0 NL",
            "x-bunq-language": "en_US",
            "x-bunq-region": "en_US",
        }

        response = requests.request("POST", url, headers=headers)

        if response.status_code == 200:
            response_json = json.loads(response.text)
            return SandboxUserPerson.from_json(
                json.dumps(response_json["Response"][0]["ApiKey"])
            )

        raise BunqException(self._ERROR_COULD_NOT_CREATE_NEW_SANDBOX_USER)

    def __request_spending_money_if_needed(self):
        """Example usage of the lib. Requests spending money from the bunq sandbox Sugardaddy if the balance is zero
        and the environment is SANDBOX.
        """
        if self.__should_request_spending_money():
            RequestInquiry.create(
                amount_inquired=Amount(
                    self._REQUEST_SPENDING_MONEY_AMOUNT, self._CURRENCY_EUR
                ),
                counterparty_alias=Pointer(
                    self._POINTER_TYPE_EMAIL, self._REQUEST_SPENDING_MONEY_RECIPIENT
                ),
                description=self._REQUEST_SPENDING_MONEY_DESCRIPTION,
                allow_bunqme=False,
            )
            sleep(self._REQUEST_SPENDING_MONEY_WAIT_TIME_SECONDS)

    def __should_request_spending_money(self):
        """Example usage of the lib. Checks if spending money should be requested from the sandbox.

        Returns:
            True if the environment is SANDBOX and the primary account balance is zero or less,
            False otherwise.
        """
        return (
            self.env == ApiEnvironmentType.SANDBOX
            and float(BunqContext.user_context().primary_monetary_account.balance.value)
            <= self._ZERO_BALANCE
        )
