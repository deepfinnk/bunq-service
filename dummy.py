import numpy as np
import requests
import random
from libs.bunq_lib import BunqLib
from libs.share_lib import ShareLib

# --- Configuration ---
RECIPIENT_EMAIL = "sugardaddy@bunq.com"
NUMBER_OF_TRANSACTIONS = 30  # How many transactions to simulate
MIN_A   MOUNT = 0.50
MAX_AMOUNT = 500.00
DELAY_BETWEEN_CALLS_S = 2  # Seconds to wait between API calls

all_option = ShareLib.parse_all_option()
environment_type = ShareLib.determine_environment_type_from_all_option(all_option)

bunq_lib = BunqLib(environment_type)

user = bunq_lib.get_current_user()
user_id = user.id_
print(user.id_)

all_monetary_account_bank_active = bunq_lib.get_all_monetary_account_active(1)
monetary_account_id = all_monetary_account_bank_active[0].id_
print(monetary_account_id)

# monetary_account_id = bunq_lib.update_monetary_account_details(monetary_account_id, 'piggy bank', daily_limit={"value": '50000', "currency": 'EUR'})
# print(f'Adjusted limit: {all_monetary_account_bank_active[0].daily_limit.value} {all_monetary_account_bank_active[0].daily_limit.currency}')

amount = np.round(max(MIN_AMOUNT, random.random() * MAX_AMOUNT), 2)

for _ in range(NUMBER_OF_TRANSACTIONS):
    print(f"TRANSACTION requesting: {amount} EUR")
    bunq_lib.make_request(str(amount), "pls send money", "sugardaddy@bunq.com")

balance = bunq_lib.get_balance(monetary_account_id)
print(f"Current balance: {balance.currency}{balance.value}")


# ShareLib.print_all_monetary_account_bank(all_monetary_account_bank_active)
#
all_payment = bunq_lib.get_all_payment(1)
ShareLib.print_all_payment(all_payment)
