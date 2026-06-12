import os
import httpx
from dotenv import load_dotenv

load_dotenv()

api_key = os.getenv("GROQ_API_KEY")
if not api_key:
    print("❌ GROQ_API_KEY not found in .env file.")
    exit(1)

print(f"Using API Key: {api_key[:6]}...{api_key[-6:]}")

url = "https://api.groq.com/openai/v1/chat/completions"
headers = {
    "Authorization": f"Bearer {api_key}",
    "Content-Type": "application/json",
}
data = {
    "model": "llama-3.3-70b-versatile",
    "messages": [
        {
            "role": "user",
            "content": "Respond with 'Groq API is working!' if you can read this."
        }
    ],
    "temperature": 0.2
}

try:
    print("Sending test prompt to Groq...")
    with httpx.Client() as client:
        response = client.post(url, headers=headers, json=data, timeout=15.0)
    
    if response.status_code == 200:
        result = response.json()
        print(f"✅ Success! Response: {result['choices'][0]['message']['content'].strip()}")
    else:
        print(f"❌ Groq API Failed: Status {response.status_code} - {response.text}")
except Exception as e:
    print(f"❌ Error occurred: {e}")
