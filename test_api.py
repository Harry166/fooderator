import requests
import json

# Test the API endpoints
base_url = "http://localhost:5000"

print("Testing Fooderator API...")
print("-" * 50)

# Test 1: Home endpoint
print("\n1. Testing home endpoint:")
response = requests.get(f"{base_url}/")
print(f"Status: {response.status_code}")
print(f"Response: {json.dumps(response.json(), indent=2)}")

# Test 2: Get languages
print("\n2. Testing languages endpoint:")
response = requests.get(f"{base_url}/api/languages")
print(f"Status: {response.status_code}")
print(f"Available languages: {list(response.json().keys())}")

# Test 3: Get product info (using a common barcode - Coca Cola)
print("\n3. Testing product lookup (Coca Cola):")
barcode = "5449000000996"  # Coca Cola barcode
response = requests.get(f"{base_url}/api/product/{barcode}?lang=es")
print(f"Status: {response.status_code}")
if response.status_code == 200:
    data = response.json()
    print(f"Product: {data.get('name', 'N/A')}")
    print(f"Brand: {data.get('brand', 'N/A')}")
    print(f"Translated to: {data.get('translated_to', 'N/A')}")

# Test 4: Translate text
print("\n4. Testing translation:")
translate_data = {
    "text": "Contains milk and nuts",
    "target_lang": "es",
    "source_lang": "en"
}
response = requests.post(f"{base_url}/api/translate", json=translate_data)
print(f"Status: {response.status_code}")
if response.status_code == 200:
    data = response.json()
    print(f"Original: {data['original']}")
    print(f"Translated: {data['translated']}")

print("\n" + "-" * 50)
print("Testing complete!")
print("\nNote: For barcode scanning, you'll need to send an actual image.")
print("This requires a frontend with camera access.")
