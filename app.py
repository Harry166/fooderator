from flask import Flask, jsonify, request, render_template, send_from_directory
from flask_cors import CORS
from deep_translator import GoogleTranslator
import base64
import io
from PIL import Image
import cv2
import numpy as np
from pyzbar import pyzbar
import requests
import json
import os
from dotenv import load_dotenv

load_dotenv()
USDA_API_KEY = os.getenv('USDA_API_KEY')

app = Flask(__name__, static_folder='.', static_url_path='')
CORS(app)

# No need to initialize translator globally with deep-translator

# OpenFoodFacts API endpoint
OPENFOODFACTS_API = "https://world.openfoodfacts.org/api/v0/product/"

# Supported languages
LANGUAGES = {
    'en': 'English',
    'es': 'Spanish', 
    'fr': 'French',
    'de': 'German',
    'it': 'Italian',
    'pt': 'Portuguese',
    'zh-cn': 'Chinese (Simplified)',
    'ja': 'Japanese',
    'ko': 'Korean',
    'ar': 'Arabic',
    'hi': 'Hindi',
    'ru': 'Russian'
}

@app.route('/')
def home():
    return send_from_directory('.', 'index.html')

@app.route('/<path:path>')
def serve_static(path):
    return send_from_directory('.', path)

@app.route('/api/languages', methods=['GET'])
def get_languages():
    return jsonify(LANGUAGES)

@app.route('/api/scan-barcode', methods=['POST'])
def scan_barcode():
    try:
        data = request.get_json()
        image_data = data.get('image')
        
        if not image_data:
            return jsonify({'error': 'No image provided'}), 400
        
        # Decode base64 image
        image_bytes = base64.b64decode(image_data.split(',')[1] if ',' in image_data else image_data)
        image = Image.open(io.BytesIO(image_bytes))
        
        # Convert to OpenCV format
        cv_image = cv2.cvtColor(np.array(image), cv2.COLOR_RGB2BGR)
        
        # Try multiple image processing techniques for better barcode detection
        barcodes = []
        
        # 1. Try with original image
        barcodes = pyzbar.decode(cv_image)
        
        # 2. If no barcode found, try with grayscale
        if not barcodes:
            gray = cv2.cvtColor(cv_image, cv2.COLOR_BGR2GRAY)
            barcodes = pyzbar.decode(gray)
        
        # 3. Try with enhanced contrast
        if not barcodes:
            # Increase contrast
            lab = cv2.cvtColor(cv_image, cv2.COLOR_BGR2LAB)
            l, a, b = cv2.split(lab)
            clahe = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(8,8))
            l = clahe.apply(l)
            enhanced = cv2.merge([l, a, b])
            enhanced = cv2.cvtColor(enhanced, cv2.COLOR_LAB2BGR)
            enhanced_gray = cv2.cvtColor(enhanced, cv2.COLOR_BGR2GRAY)
            barcodes = pyzbar.decode(enhanced_gray)
        
        # 4. Try with binary threshold
        if not barcodes:
            _, binary = cv2.threshold(gray, 127, 255, cv2.THRESH_BINARY)
            barcodes = pyzbar.decode(binary)
        
        # 5. Try with adaptive threshold
        if not barcodes:
            adaptive = cv2.adaptiveThreshold(gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 11, 2)
            barcodes = pyzbar.decode(adaptive)
        
        if not barcodes:
            return jsonify({'error': 'No barcode found in image'}), 404
        
        # Get the first barcode
        barcode_data = barcodes[0].data.decode('utf-8')
        
        # Clean up the barcode data (remove any extra whitespace)
        barcode_data = barcode_data.strip()
        
        return jsonify({
            'barcode': barcode_data,
            'type': barcodes[0].type
        })
        
    except Exception as e:
        print(f"Barcode scanning error: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/product/<barcode>', methods=['GET'])
def get_product(barcode):
    try:
        # Get target language from query params
        target_lang = request.args.get('lang', 'en')
        
        # Try multiple sources to get complete product information
        product_info = get_product_from_multiple_sources(barcode, USDA_API_KEY)
        
        if not product_info:
            return jsonify({'error': 'Product not found'}), 404
        
        # Translate if needed
        if target_lang != 'en' and target_lang in LANGUAGES:
            product_info = translate_product_info(product_info, target_lang)
        
        return jsonify(product_info)
        
    except Exception as e:
        print(f"Error getting product: {e}")
        return jsonify({'error': str(e)}), 500

def get_product_from_multiple_sources(barcode, usda_api_key):
    """Try multiple sources to get complete product information"""
    print(f"\nSearching for product: {barcode}")
    
    # Initialize product info
    product_info = None
    
    # 1. Try OpenFoodFacts first (most comprehensive)
    print("Trying OpenFoodFacts...")
    off_data = get_from_openfoodfacts(barcode)
    if off_data:
        product_info = off_data
        print(f"Found in OpenFoodFacts: {product_info.get('name', 'Unknown')}")
    
    # 2. Try Barcode Lookup API (free tier available)
    if not product_info or not product_info.get('ingredients') or product_info.get('ingredients') == 'Ingredients not available in database':
        print("Trying Barcode Lookup...")
        barcode_lookup_data = get_from_barcode_lookup(barcode)
        if barcode_lookup_data:
            if product_info:
                product_info = merge_product_info(product_info, barcode_lookup_data)
            else:
                product_info = barcode_lookup_data
    
    # 3. Try USDA FoodData Central (US products)
    if not product_info or not product_info.get('ingredients') or product_info.get('ingredients') == 'Ingredients not available in database':
        print("Trying USDA FoodData Central...")
        usda_data = get_from_usda(barcode, usda_api_key)
        if usda_data:
            if product_info:
                product_info = merge_product_info(product_info, usda_data)
            else:
                product_info = usda_data
    
    # 4. Try web scraping as last resort for missing ingredients
    if product_info and (not product_info.get('ingredients') or product_info.get('ingredients') == 'Ingredients not available in database'):
        print("Note: Ingredients not found in any database")
        # For now, we'll show what data we have
        # Web scraping would require specific implementations per brand/site
    
    return product_info

def extract_openfoodfacts_nutrition(nutriments):
    """Extract all available nutrition information from OpenFoodFacts nutriments"""
    nutrition = {}
    
    # Map of OpenFoodFacts nutrient keys to our standard names
    nutrient_mapping = {
        'energy-kcal_100g': 'energy',
        'energy_100g': 'energy_kj',
        'fat_100g': 'fat',
        'saturated-fat_100g': 'saturated_fat',
        'monounsaturated-fat_100g': 'monounsaturated_fat',
        'polyunsaturated-fat_100g': 'polyunsaturated_fat',
        'trans-fat_100g': 'trans_fat',
        'cholesterol_100g': 'cholesterol',
        'carbohydrates_100g': 'carbohydrates',
        'sugars_100g': 'sugars',
        'fiber_100g': 'fiber',
        'proteins_100g': 'proteins',
        'salt_100g': 'salt',
        'sodium_100g': 'sodium',
        'vitamin-a_100g': 'vitamin_a',
        'vitamin-c_100g': 'vitamin_c',
        'vitamin-d_100g': 'vitamin_d',
        'vitamin-e_100g': 'vitamin_e',
        'vitamin-k_100g': 'vitamin_k',
        'vitamin-b1_100g': 'vitamin_b1',
        'vitamin-b2_100g': 'vitamin_b2',
        'vitamin-b6_100g': 'vitamin_b6',
        'vitamin-b12_100g': 'vitamin_b12',
        'vitamin-pp_100g': 'niacin',
        'folates_100g': 'folate',
        'pantothenic-acid_100g': 'pantothenic_acid',
        'biotin_100g': 'biotin',
        'calcium_100g': 'calcium',
        'phosphorus_100g': 'phosphorus',
        'iron_100g': 'iron',
        'magnesium_100g': 'magnesium',
        'zinc_100g': 'zinc',
        'copper_100g': 'copper',
        'manganese_100g': 'manganese',
        'selenium_100g': 'selenium',
        'iodine_100g': 'iodine',
        'potassium_100g': 'potassium',
        'chloride_100g': 'chloride',
        'alcohol_100g': 'alcohol',
        'caffeine_100g': 'caffeine'
    }
    
    # Extract all available nutrients
    for off_key, our_key in nutrient_mapping.items():
        if off_key in nutriments:
            value = nutriments[off_key]
            if value is not None and value != 'N/A':
                nutrition[our_key] = value
    
    # Also check for any serving size specific nutrients
    for key in nutriments:
        if key.endswith('_serving') and key.replace('_serving', '_100g') not in nutriments:
            # If we only have serving data, include it with a note
            base_key = key.replace('_serving', '')
            if base_key in nutrient_mapping.values():
                nutrition[f"{base_key}_per_serving"] = nutriments[key]
    
    return nutrition

def get_from_openfoodfacts(barcode):
    """Get product info from OpenFoodFacts"""
    try:
        response = requests.get(f"{OPENFOODFACTS_API}{barcode}.json", timeout=5)
        if response.status_code != 200:
            return None
        
        data = response.json()
        if data['status'] != 1:
            return None
        
        product = data['product']
        
        # Extract all possible ingredient fields
        ingredients = (product.get('ingredients_text') or 
                      product.get('ingredients_text_en') or 
                      product.get('ingredients_text_with_allergens') or 
                      product.get('ingredients_text_fr') or  # Try French
                      product.get('ingredients_text_es') or  # Try Spanish
                      '')
        
        # Extract allergens from multiple sources
        allergens = product.get('allergens') or product.get('allergens_en') or ''
        allergen_tags = product.get('allergens_tags', [])
        if allergen_tags and not allergens:
            allergens = ', '.join([tag.replace('en:', '').replace('-', ' ').title() for tag in allergen_tags])
        
        # Also check traces for allergen information
        traces = product.get('traces', '') or product.get('traces_tags', [])
        if isinstance(traces, list):
            traces = ', '.join([t.replace('en:', '').replace('-', ' ').title() for t in traces])
        
        if traces and allergens:
            allergens += f", May contain: {traces}"
        elif traces:
            allergens = f"May contain: {traces}"
        
        # Get categories
        categories = product.get('categories', '') or product.get('categories_tags', [])
        if isinstance(categories, list):
            categories = ', '.join([c.replace('en:', '').replace('-', ' ') for c in categories[:3]])
        
        return {
            'barcode': barcode,
            'name': product.get('product_name') or product.get('product_name_en') or 'Unknown Product',
            'brand': product.get('brands') or 'Unknown Brand',
            'ingredients': ingredients or 'Ingredients not available in database',
            'allergens': allergens or 'No allergen information available',
            'categories': categories,
            'nutrition': extract_openfoodfacts_nutrition(product.get('nutriments', {})),
            'image_url': product.get('image_url') or product.get('image_front_url') or product.get('image_small_url') or '',
            'countries': product.get('countries', ''),
            'stores': product.get('stores', ''),
            'data_source': 'OpenFoodFacts'
        }
    except Exception as e:
        print(f"Error with OpenFoodFacts: {e}")
        return None

def get_from_barcode_lookup(barcode):
    """Try to get product info from Barcode Lookup API"""
    try:
        # This is a free API but has limited requests
        # You can sign up for a free API key at https://www.barcodelookup.com/api
        # For now, using without API key (very limited)
        url = f"https://api.upcitemdb.com/prod/trial/lookup?upc={barcode}"
        response = requests.get(url, timeout=5)
        
        if response.status_code == 200:
            data = response.json()
            if data.get('items') and len(data['items']) > 0:
                item = data['items'][0]
                # Don't use description as ingredients - it's usually just the product name
                # Only return basic product info from this source
                return {
                    'barcode': barcode,
                    'name': item.get('title', 'Unknown Product'),
                    'brand': item.get('brand', 'Unknown Brand'),
                    'ingredients': '',  # Don't use description as ingredients
                    'allergens': '',
                    'categories': item.get('category', ''),
                    'image_url': item.get('images', [''])[0] if item.get('images') else '',
                    'data_source': 'UPC Database'
                }
    except Exception as e:
        print(f"Error with Barcode Lookup: {e}")
    return None

def extract_usda_nutrition(food_nutrients):
    """Extract comprehensive nutrition information from USDA food nutrients"""
    nutrients = {}
    
    # Comprehensive USDA nutrient mapping
    nutrient_mapping = {
        'Energy': 'energy',
        'Total lipid (fat)': 'fat',
        'Fatty acids, total saturated': 'saturated_fat',
        'Fatty acids, total monounsaturated': 'monounsaturated_fat',
        'Fatty acids, total polyunsaturated': 'polyunsaturated_fat',
        'Fatty acids, total trans': 'trans_fat',
        'Cholesterol': 'cholesterol',
        'Carbohydrate, by difference': 'carbohydrates',
        'Fiber, total dietary': 'fiber',
        'Sugars, total including NLEA': 'sugars',
        'Sugars, added': 'added_sugars',
        'Protein': 'proteins',
        'Sodium, Na': 'sodium',
        'Potassium, K': 'potassium',
        'Calcium, Ca': 'calcium',
        'Iron, Fe': 'iron',
        'Magnesium, Mg': 'magnesium',
        'Phosphorus, P': 'phosphorus',
        'Zinc, Zn': 'zinc',
        'Copper, Cu': 'copper',
        'Manganese, Mn': 'manganese',
        'Selenium, Se': 'selenium',
        'Vitamin C, total ascorbic acid': 'vitamin_c',
        'Thiamin': 'vitamin_b1',
        'Riboflavin': 'vitamin_b2',
        'Niacin': 'niacin',
        'Pantothenic acid': 'pantothenic_acid',
        'Vitamin B-6': 'vitamin_b6',
        'Folate, total': 'folate',
        'Vitamin B-12': 'vitamin_b12',
        'Vitamin A, RAE': 'vitamin_a',
        'Vitamin A, IU': 'vitamin_a_iu',
        'Vitamin E (alpha-tocopherol)': 'vitamin_e',
        'Vitamin D (D2 + D3)': 'vitamin_d',
        'Vitamin K (phylloquinone)': 'vitamin_k',
        'Caffeine': 'caffeine',
        'Alcohol, ethyl': 'alcohol'
    }
    
    for nutrient in food_nutrients:
        nutrient_name = nutrient.get('nutrientName', '')
        if nutrient_name in nutrient_mapping:
            value = nutrient.get('value')
            unit = nutrient.get('unitName', '')
            
            if value is not None:
                # Store values with their original units from USDA
                # The frontend will handle unit display appropriately
                nutrients[nutrient_mapping[nutrient_name]] = value
    
    # Calculate salt from sodium (salt = sodium * 2.5)
    if 'sodium' in nutrients:
        nutrients['salt'] = nutrients['sodium'] * 2.5
    
    return nutrients

def get_from_usda(barcode, api_key):
    """Get product info from USDA FoodData Central"""
    if not api_key:
        print("USDA API key not configured")
        return None
        
    try:
        # Search for product by barcode (GTIN/UPC)
        search_url = f"https://api.nal.usda.gov/fdc/v1/foods/search?api_key={api_key}"
        
        # Search by GTIN/UPC code
        search_params = {
            "query": barcode,
            "dataType": ["Branded"],  # Focus on branded products
            "pageSize": 10
        }
        
        response = requests.post(search_url, json=search_params, timeout=10)
        
        if response.status_code != 200:
            print(f"USDA API error: {response.status_code}")
            return None
            
        data = response.json()
        foods = data.get('foods', [])
        
        # Look for exact barcode match
        product = None
        for food in foods:
            # Check if GTIN/UPC matches
            if food.get('gtinUpc') == barcode:
                product = food
                break
        
        if not product:
            # Try to find by checking if barcode is in the description
            for food in foods:
                if barcode in str(food.get('description', '')) or barcode in str(food.get('additionalDescriptions', '')):
                    product = food
                    break
        
        if not product:
            return None
            
        # Extract ingredients
        ingredients = product.get('ingredients', '')
        
        # Extract comprehensive nutrients
        nutrients = extract_usda_nutrition(product.get('foodNutrients', []))
        
        return {
            'barcode': barcode,
            'name': product.get('description', 'Unknown Product'),
            'brand': product.get('brandOwner', 'Unknown Brand'),
            'ingredients': ingredients or 'Ingredients not available in database',
            'allergens': '',  # USDA doesn't provide allergen info directly
            'categories': product.get('brandedFoodCategory', ''),
            'nutrition': nutrients,
            'data_source': 'USDA FoodData Central'
        }
        
    except Exception as e:
        print(f"Error with USDA API: {e}")
        return None

def search_ingredients_online(product_name, brand):
    """Try to find ingredients by searching online (last resort)"""
    try:
        # Search for product ingredients using a simple web search
        # This is a basic implementation - could be enhanced
        search_query = f"{brand} {product_name} ingredients"
        
        # Try searching on a ingredients database or manufacturer website
        # For now, returning None as this would require web scraping
        # which is complex and site-specific
        
        # You could implement specific scrapers for major brands
        # or use a service like SerpAPI for web search results
        
        return None
    except Exception as e:
        print(f"Error searching online: {e}")
        return None

def merge_product_info(primary, secondary):
    """Merge product information from multiple sources"""
    merged = primary.copy()
    
    # Only update empty or missing fields
    for key, value in secondary.items():
        if key == 'nutrition':
            # Merge nutrition data specially
            if 'nutrition' not in merged or not merged['nutrition']:
                merged['nutrition'] = value
            else:
                # Merge nutrition dictionaries
                for nutrient, nutrient_value in value.items():
                    if nutrient not in merged['nutrition'] or merged['nutrition'][nutrient] in ['N/A', None]:
                        merged['nutrition'][nutrient] = nutrient_value
        elif key not in merged or not merged[key] or merged[key] in ['Unknown', 'N/A', 'Ingredients not available in database', 'No allergen information available']:
            merged[key] = value
    
    # Combine data sources
    if 'data_source' in secondary:
        if 'data_source' in merged:
            merged['data_source'] = f"{merged['data_source']}, {secondary['data_source']}"
        else:
            merged['data_source'] = secondary['data_source']
    
    return merged

@app.route('/api/translate', methods=['POST'])
def translate_text():
    try:
        data = request.get_json()
        text = data.get('text')
        target_lang = data.get('target_lang', 'en')
        source_lang = data.get('source_lang', 'auto')
        
        if not text:
            return jsonify({'error': 'No text provided'}), 400
        
        if source_lang == 'auto':
            translator = GoogleTranslator(source='auto', target=target_lang)
        else:
            translator = GoogleTranslator(source=source_lang, target=target_lang)
        
        translated_text = translator.translate(text)
        
        return jsonify({
            'original': text,
            'translated': translated_text,
            'source_lang': source_lang,
            'target_lang': target_lang
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

def translate_product_info(product_info, target_lang):
    """Translate product information to target language"""
    try:
        translator = GoogleTranslator(source='auto', target=target_lang)
        
        # Translate name
        if product_info['name'] != 'Unknown':
            product_info['name'] = translator.translate(product_info['name'])
        
        # Translate brand
        if product_info['brand'] != 'Unknown':
            product_info['brand'] = translator.translate(product_info['brand'])
        
        # Translate ingredients
        if product_info['ingredients'] and product_info['ingredients'] != 'Ingredients not available in database':
            product_info['ingredients'] = translator.translate(product_info['ingredients'])
        elif product_info['ingredients'] == 'Ingredients not available in database':
            product_info['ingredients'] = translator.translate('Ingredients not available in database')
        
        # Translate allergens
        if product_info['allergens'] and product_info['allergens'] != 'No allergen information available':
            product_info['allergens'] = translator.translate(product_info['allergens'])
        elif product_info['allergens'] == 'No allergen information available':
            product_info['allergens'] = translator.translate('No allergen information available')
        
        # Add comprehensive nutrition labels in target language
        nutrition_labels = {
            'energy': translator.translate('Calories'),
            'energy_kj': translator.translate('Energy (kJ)'),
            'fat': translator.translate('Total Fat'),
            'saturated_fat': translator.translate('Saturated Fat'),
            'monounsaturated_fat': translator.translate('Monounsaturated Fat'),
            'polyunsaturated_fat': translator.translate('Polyunsaturated Fat'),
            'trans_fat': translator.translate('Trans Fat'),
            'cholesterol': translator.translate('Cholesterol'),
            'carbohydrates': translator.translate('Total Carbohydrates'),
            'sugars': translator.translate('Sugars'),
            'added_sugars': translator.translate('Added Sugars'),
            'fiber': translator.translate('Dietary Fiber'),
            'proteins': translator.translate('Protein'),
            'salt': translator.translate('Salt'),
            'sodium': translator.translate('Sodium'),
            'potassium': translator.translate('Potassium'),
            'calcium': translator.translate('Calcium'),
            'iron': translator.translate('Iron'),
            'magnesium': translator.translate('Magnesium'),
            'phosphorus': translator.translate('Phosphorus'),
            'zinc': translator.translate('Zinc'),
            'copper': translator.translate('Copper'),
            'manganese': translator.translate('Manganese'),
            'selenium': translator.translate('Selenium'),
            'iodine': translator.translate('Iodine'),
            'vitamin_a': translator.translate('Vitamin A'),
            'vitamin_c': translator.translate('Vitamin C'),
            'vitamin_d': translator.translate('Vitamin D'),
            'vitamin_e': translator.translate('Vitamin E'),
            'vitamin_k': translator.translate('Vitamin K'),
            'vitamin_b1': translator.translate('Thiamin (B1)'),
            'vitamin_b2': translator.translate('Riboflavin (B2)'),
            'niacin': translator.translate('Niacin (B3)'),
            'vitamin_b6': translator.translate('Vitamin B6'),
            'folate': translator.translate('Folate'),
            'vitamin_b12': translator.translate('Vitamin B12'),
            'pantothenic_acid': translator.translate('Pantothenic Acid'),
            'biotin': translator.translate('Biotin'),
            'caffeine': translator.translate('Caffeine'),
            'alcohol': translator.translate('Alcohol')
        }
        
        product_info['nutrition_labels'] = nutrition_labels
        product_info['translated_to'] = target_lang
        
    except Exception as e:
        print(f"Translation error: {e}")
        product_info['translation_error'] = str(e)
    
    return product_info

if __name__ == '__main__':
    print("\n🍔 Starting Fooderator...")
    print("\n✅ Frontend and Backend running together!")
    print("\n📱 Access the app at:")
    print("   - Local: http://localhost:5000")
    print("   - Network: http://YOUR_IP:5000")
    print("\n🌐 API Endpoints:")
    print("   - POST /api/scan-barcode")
    print("   - GET /api/product/<barcode>?lang=<code>")
    print("   - POST /api/translate")
    print("   - GET /api/languages")
    print("\n")
    app.run(debug=True, host='0.0.0.0', port=5000)
