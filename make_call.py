import os
import certifi

# Fix for macOS SSL Certificate errors - MUST be before other imports
os.environ['SSL_CERT_FILE'] = certifi.where()

import argparse
import logging
from dotenv import load_dotenv
from twilio.rest import Client

# Load environment variables
load_dotenv(".env")

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("outbound-caller")

def main():
    parser = argparse.ArgumentParser(description="Make an outbound call via Twilio and FastAPI Agent.")
    parser.add_argument("--to", required=True, help="The phone number to call (e.g., +1234567890)")
    args = parser.parse_args()

    # 1. Validation
    phone_number = args.to.strip()
    if not phone_number.startswith("+"):
        print("Error: Phone number must start with '+' and country code.")
        return

    if len(phone_number) < 8:
        print(f"Error: Phone number '{phone_number}' looks too short.")
        return

    account_sid = os.getenv("TWILIO_ACCOUNT_SID")
    auth_token = os.getenv("TWILIO_AUTH_TOKEN")
    from_number = os.getenv("TWILIO_PHONE_NUMBER")
    server_url = os.getenv("SERVER_URL")

    if not (account_sid and auth_token and from_number and server_url):
        print("Error: Twilio credentials or SERVER_URL missing in .env")
        return

    # 2. Setup Twilio Client
    client = Client(account_sid, auth_token)

    # Webhook endpoint URL
    twiml_url = f"{server_url}/twiml/outbound"

    print(f"Initiating call from {from_number} to {phone_number}...")
    print(f"Callback TwiML URL: {twiml_url}")

    try:
        # 3. Create outbound call
        call = client.calls.create(
            to=phone_number,
            from_=from_number,
            url=twiml_url
        )

        print("\n✅ Call Dispatched Successfully!")
        print(f"Call SID: {call.sid}")
        print(f"Status: {call.status}")
        print("-" * 40)
        print("Your agent server will receive a WebSocket connection when the call is answered.")
        
    except Exception as e:
        print(f"\n❌ Error dispatching call: {e}")

if __name__ == "__main__":
    main()
