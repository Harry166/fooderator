import requests
import json
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()
USDA_API_KEY = os.getenv('USDA_API_KEY')

print("Testing USDA API for Bourbon products...")
print("-" * 50)

# Common bourbon barcodes
bourbon_barcodes = [
    "080660958026",  # Buffalo Trace Bourbon
    "088004144715",  # Jim Beam Bourbon
    "080686967014",  # Wild Turkey 101
    "721059701013",  # Maker's Mark
    "080480015022",  # Woodford Reserve
    "096749002122",  # Jack Daniel's
]

def test_usda_api(barcode):
    """Test USDA API directly"""
    print(f"\nTesting barcode: {barcode}")
    
    try:
        # Search for product by barcode (GTIN/UPC)
        search_url = f"https://api.nal.usda.gov/fdc/v1/foods/search?api_key={USDA_API_KEY}"
        
        # Search by GTIN/UPC code
        search_params = {
            "query": barcode,
            "dataType": ["Branded"],  # Focus on branded products
            "pageSize": 10
        }
        
        response = requests.post(search_url, json=search_params, timeout=10)
        
        if response.status_code != 200:
            print(f"  API error: {response.status_code}")
            print(f"  Response: {response.text}")
            return None
            
        data = response.json()
        foods = data.get('foods', [])
        
        if not foods:
            print(f"  No results found")
            return None
        
        print(f"  Found {len(foods)} results")
        
        # Look for exact barcode match
        product = None
        for food in foods:
            # Check if GTIN/UPC matches
            if food.get('gtinUpc') == barcode:
                product = food
                break
        
        if not product and foods:
            # Take the first result if no exact match
            product = foods[0]
            print(f"  No exact match, using first result")
        
        if product:
            print(f"  Product: {product.get('description', 'Unknown')}")
            print(f"  Brand: {product.get('brandOwner', 'Unknown')}")
            print(f"  Category: {product.get('brandedFoodCategory', 'Unknown')}")
            print(f"  GTIN/UPC: {product.get('gtinUpc', 'Not specified')}")
            print(f"  Ingredients: {product.get('ingredients', 'Not available')}")
            
            # Show some nutrients
            nutrients = {}
            for nutrient in product.get('foodNutrients', []):
                name = nutrient.get('nutrientName', '')
                value = nutrient.get('value')
                unit = nutrient.get('unitName', '')
                if value is not None and name in ['Energy', 'Alcohol', 'Sugars, total including NLEA']:
                    nutrients[name] = f"{value} {unit}"
            
            if nutrients:
                print(f"  Nutrients: {json.dumps(nutrients, indent=4)}")
        
        return product
        
    except Exception as e:
        print(f"  Error: {e}")
        return None

# Test each bourbon barcode
found_count = 0
for barcode in bourbon_barcodes:
    result = test_usda_api(barcode)
    if result:
        found_count += 1

print("\n" + "-" * 50)
print(f"Summary: Found {found_count} out of {len(bourbon_barcodes)} bourbon products in USDA database")

# Also try searching by brand names
print("\n" + "-" * 50)
print("Testing brand name searches...")

bourbon_brands = ["Buffalo Trace", "Jim Beam", "Maker's Mark", "Jack Daniel's"]

for brand in bourbon_brands:
    print(f"\nSearching for brand: {brand}")
    
    try:
        search_url = f"https://api.nal.usda.gov/fdc/v1/foods/search?api_key={USDA_API_KEY}"
        search_params = {
            "query": f"{brand} bourbon whiskey",
            "dataType": ["Branded"],
            "pageSize": 5
        }
        
        response = requests.post(search_url, json=search_params, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            foods = data.get('foods', [])
            print(f"  Found {len(foods)} results")
            
            for i, food in enumerate(foods[:3]):  # Show first 3 results
                print(f"  {i+1}. {food.get('description', 'Unknown')} - {food.get('gtinUpc', 'No UPC')}")
                
    except Exception as e:
        print(f"  Error: {e}")

print("\n" + "-" * 50)
print("Testing complete!")
print("\nNote: USDA database may not have complete coverage of alcoholic beverages.")
print("OpenFoodFacts might have better coverage for international products.")
