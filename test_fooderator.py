import requests
import json

# Test barcode (Coca-Cola)
test_barcode = "049000006346"

# Base URL
base_url = "http://localhost:5000"

def test_product_api():
    """Test the product API endpoint"""
    print("Testing Product API...")
    
    # Test without language parameter (default English)
    url = f"{base_url}/api/product/{test_barcode}"
    response = requests.get(url)
    
    if response.status_code == 200:
        data = response.json()
        print("\n✅ Product found!")
        print(f"Name: {data.get('name', 'N/A')}")
        print(f"Brand: {data.get('brand', 'N/A')}")
        print(f"Data Source: {data.get('data_source', 'N/A')}")
        
        # Check ingredients
        ingredients = data.get('ingredients', 'N/A')
        print(f"\nIngredients: {ingredients[:100]}..." if len(ingredients) > 100 else f"\nIngredients: {ingredients}")
        
        # Check nutrition
        nutrition = data.get('nutrition', {})
        if nutrition:
            print("\nNutrition Facts:")
            for nutrient, value in list(nutrition.items())[:10]:  # Show first 10 nutrients
                print(f"  {nutrient}: {value}")
            if len(nutrition) > 10:
                print(f"  ... and {len(nutrition) - 10} more nutrients")
        else:
            print("\nNo nutrition data available")
            
    else:
        print(f"❌ Error: {response.status_code}")
        print(response.text)

def test_translation():
    """Test product API with translation"""
    print("\n\nTesting Translation to Spanish...")
    
    url = f"{base_url}/api/product/{test_barcode}?lang=es"
    response = requests.get(url)
    
    if response.status_code == 200:
        data = response.json()
        print("\n✅ Product found and translated!")
        print(f"Name: {data.get('name', 'N/A')}")
        print(f"Brand: {data.get('brand', 'N/A')}")
        
        # Check if nutrition labels were translated
        nutrition_labels = data.get('nutrition_labels', {})
        if nutrition_labels:
            print("\nTranslated Nutrition Labels:")
            for key, label in list(nutrition_labels.items())[:5]:
                print(f"  {key}: {label}")
    else:
        print(f"❌ Error: {response.status_code}")

def test_manual_barcode():
    """Test with a manual barcode entry"""
    print("\n\nTesting with different barcode...")
    
    # Test with another common barcode (e.g., Oreo cookies)
    test_barcode2 = "044000032029"
    url = f"{base_url}/api/product/{test_barcode2}"
    response = requests.get(url)
    
    if response.status_code == 200:
        data = response.json()
        print(f"\n✅ Product: {data.get('name', 'N/A')}")
        print(f"Ingredients available: {'Yes' if data.get('ingredients') and data.get('ingredients') != 'Ingredients not available in database' else 'No'}")
        print(f"Nutrition facts count: {len(data.get('nutrition', {}))}")
    else:
        print(f"❌ Product not found")

if __name__ == "__main__":
    print("🧪 Testing Fooderator API...\n")
    
    try:
        # Check if server is running
        response = requests.get(base_url)
        if response.status_code == 200:
            print("✅ Server is running!")
            
            test_product_api()
            test_translation()
            test_manual_barcode()
            
        else:
            print("❌ Server is not responding")
    except requests.exceptions.ConnectionError:
        print("❌ Cannot connect to server. Make sure the Flask app is running on http://localhost:5000")
    except Exception as e:
        print(f"❌ Error: {e}")
