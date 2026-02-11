
import os
import sys
from dotenv import load_dotenv
from groq import Groq, APIConnectionError, AuthenticationError, APIStatusError

# Load environment variables
load_dotenv()

api_key = os.getenv("GROQ_API_KEY")

print(f"Checking GROQ_API_KEY...")
if not api_key:
    print("ERROR: GROQ_API_KEY is not set in environment or .env file.")
    sys.exit(1)

print(f"Key found: {api_key[:4]}...{api_key[-4:]} (Length: {len(api_key)})")

if not api_key.startswith("gsk_"):
    print("WARNING: Key does not start with 'gsk_'. This might be invalid.")

print("\nAttempting to connect to Groq API...")

try:
    client = Groq(api_key=api_key)
    # Try a simple completion with a lightweight model
    chat_completion = client.chat.completions.create(
        messages=[
            {
                "role": "user",
                "content": "Hello",
            }
        ],
        model="llama-3.3-70b-versatile",
    )
    print("Connection SUCCESSFUL!")
    print(f"Response: {chat_completion.choices[0].message.content}")

except AuthenticationError as e:
    print(f"\nAUTHENTICATION ERROR: {e}")
    print("Please check if your API key is correct and active.")

except APIConnectionError as e:
    print(f"\nCONNECTION ERROR: {e}")
    print("The server could not be reached.")
    print(f"Details: {e.__cause__}")

except APIStatusError as e:
    print(f"\nAPI STATUS ERROR: {e}")
    print(f"Status Code: {e.status_code}")
    print(f"Response: {e.response}")

except Exception as e:
    print(f"\nUNKNOWN ERROR: {type(e).__name__}: {e}")
    import traceback
    traceback.print_exc()
