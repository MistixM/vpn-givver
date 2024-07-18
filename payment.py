# Using YooKassa API implement payments for TG bot
import yookassa
from yookassa import Payment
import uuid
import time

# Get config with all important data
from config import ACCOUNT_ID, SECRET_KEY

# Apply account_id and secret_key here
yookassa.Configuration.account_id = ACCOUNT_ID
yookassa.Configuration.secret_key = SECRET_KEY

# Implement function that will create offer to the user and return tuple with data
def create(amount, chat_id, description) -> tuple:
    # Generate id_key for offer
    id_key = str(uuid.uuid4())

    # Create Payment object
    payment = Payment.create({
    "amount": {
      "value": amount,
      "currency": "RUB"
    },
    "payment_method_data": {
      "type": "bank_card"
    },
    "confirmation": {
      "type": "redirect",
      "return_url": "https://t.me/vpngivverbot"
    },
    "capture": True,
    "metadata": {
        'chat_id': chat_id
    },
    'description': description}, id_key)

    # Return all data from payment object
    return payment.confirmation.confirmation_url, payment.id

# Implement function that will check all data from the generated payment by id
def check(payment_id) -> bool:
    while True:
      time.sleep(3)

      payment = yookassa.Payment.find_one(payment_id)

      if payment.status == 'succeeded':
          return payment.metadata
      else:
          return False
