import requests
import json

# Test with the actual starting URL
url = "https://semaphorical-hyperbolic-buddy.ngrok-free.dev"
payload = {
    "email": "24f3001658@ds.study.iitm.ac.in",
    "secret": "tds_p2_secure_7x9k2m_iitm_2025",
    "url": "https://tds-llm-analysis.s-anand.net/project2"
}

print("Sending request to your API...")
print(f"Payload: {json.dumps(payload, indent=2)}")

response = requests.post(url, json=payload)
print(f"\nStatus Code: {response.status_code}")
print(f"Response: {response.json()}")
print("\nNow check your server logs to see the quiz solving in action!")
