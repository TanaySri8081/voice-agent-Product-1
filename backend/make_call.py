import asyncio
import argparse
import sys
from backend.config.settings import settings
from backend.integrations.vobiz.client import VobizClient

async def main():
    parser = argparse.ArgumentParser(description="Trigger outbound Vobiz call to a patient.")
    parser.add_argument("--to", required=True, help="Patient phone number to call (e.g. +91XXXXXXXXXX)")
    args = parser.parse_args()

    to_number = args.to.strip()
    if not to_number.startswith("+"):
        print("Error: Phone number must start with '+' and country code.")
        sys.exit(1)
        
    vobiz = VobizClient()
    
    # The answer_url is Vobiz's callback when patient answers
    # In outbound calls, we pass From as our registered DID and to as the patient
    answer_url = f"{settings.SERVER_URL}/api/calls/twiml/outbound?to={to_number}&From={settings.VOBIZ_OUTBOUND_NUMBER}"
    
    print(f"Initiating Vobiz outbound call from {settings.VOBIZ_OUTBOUND_NUMBER} to {to_number}...")
    print(f"Callback Answer URL: {answer_url}")
    
    result = await vobiz.initiate_call(to_number=to_number, answer_url=answer_url)
    if result["success"]:
        print("\n✅ Vobiz Outbound Call triggered successfully!")
        print(f"Details: {result['data']}")
    else:
        print(f"\n❌ Failed to trigger call: {result['error']}")

if __name__ == "__main__":
    asyncio.run(main())
