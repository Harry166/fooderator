# Fooderator - Food Product Scanner & Translator

A mobile and web-friendly application that scans food product barcodes and translates nutrition information, ingredients, and allergen warnings into your preferred language.

## Features

- 📷 Scan barcodes using camera
- 🌍 Translate product information into 12+ languages
- 📊 View nutrition facts
- 🥜 Check allergen information
- 📱 Works on mobile and desktop

## Backend Setup

1. Create a virtual environment:
```bash
python -m venv venv
```

2. Activate the virtual environment:
```bash
# On Windows
venv\Scripts\activate

# On Mac/Linux
source venv/bin/activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

Note: On Windows, you might need to install additional dependencies for pyzbar:
- Download Visual C++ Redistributable
- Or install zbar separately

4. Run the backend:
```bash
python app.py
```

The API will be available at http://localhost:5000

## API Endpoints

### 1. Scan Barcode from Image
**POST** `/api/scan-barcode`

Request body:
```json
{
  "image": "data:image/jpeg;base64,..."
}
```

Response:
```json
{
  "barcode": "3017620422003",
  "type": "EAN13"
}
```

### 2. Get Product Information
**GET** `/api/product/{barcode}?lang={language_code}`

Example: `/api/product/3017620422003?lang=es`

Response:
```json
{
  "barcode": "3017620422003",
  "name": "Nutella",
  "brand": "Ferrero",
  "ingredients": "Sugar, palm oil, hazelnuts...",
  "allergens": "Contains: Milk, Hazelnuts",
  "nutrition": {
    "energy": 539,
    "fat": 30.9,
    "saturated_fat": 10.6,
    "carbohydrates": 57.5,
    "sugars": 56.3,
    "fiber": 3.5,
    "proteins": 6.3,
    "salt": 0.107,
    "sodium": 0.0428
  },
  "nutrition_labels": {
    "energy": "Calorías",
    "fat": "Grasa",
    ...
  },
  "image_url": "https://...",
  "translated_to": "es"
}
```

### 3. Translate Text
**POST** `/api/translate`

Request body:
```json
{
  "text": "Contains milk",
  "target_lang": "fr",
  "source_lang": "auto"
}
```

### 4. Get Supported Languages
**GET** `/api/languages`

## Supported Languages

- English (en)
- Spanish (es)
- French (fr)
- German (de)
- Italian (it)
- Portuguese (pt)
- Chinese Simplified (zh-cn)
- Japanese (ja)
- Korean (ko)
- Arabic (ar)
- Hindi (hi)
- Russian (ru)

## Frontend Integration

To use with a frontend:

1. Capture image from camera
2. Convert to base64
3. Send to `/api/scan-barcode`
4. Use returned barcode to fetch product info with preferred language
5. Display translated information

## Data Source

Product information is fetched from OpenFoodFacts, a free and open database of food products from around the world.

## Deployment on Render

### Prerequisites

1. A GitHub account
2. A Render account (sign up at https://render.com)
3. (Optional) A USDA API key from https://fdc.nal.usda.gov/api-key-signup.html

### Step-by-Step Deployment

1. **Push to GitHub**
   ```bash
   git init
   git add .
   git commit -m "Initial commit"
   git branch -M main
   git remote add origin https://github.com/YOUR-USERNAME/fooderator.git
   git push -u origin main
   ```

2. **Deploy on Render**
   - Log in to [Render](https://render.com)
   - Click "New +" and select "Web Service"
   - Connect your GitHub account if not already connected
   - Select your Fooderator repository
   - Fill in the service details:
     - **Name**: fooderator (or your preferred name)
     - **Environment**: Python 3
     - **Build Command**: `pip install -r requirements.txt`
     - **Start Command**: `gunicorn app:app`
   
3. **Configure Environment Variables**
   - In the Environment section, add:
     - Key: `USDA_API_KEY`
     - Value: Your USDA API key (if you have one)
   
4. **Deploy**
   - Click "Create Web Service"
   - Render will automatically deploy your app
   - Your app will be available at `https://fooderator.onrender.com` (or your chosen subdomain)

### Important Notes

1. **Free Tier Limitations**: 
   - Render's free tier services spin down after 15 minutes of inactivity
   - First request after inactivity may take 30-50 seconds

2. **Camera Permissions**:
   - The camera feature requires HTTPS (provided by Render)
   - Users need to grant camera permissions in their browser

3. **API Limits**:
   - OpenFoodFacts API is free with no hard limits
   - USDA API requires a free API key (optional)
   - Barcode Lookup API has limited free requests

4. **Static Files**:
   - All static files (HTML, CSS, JS) are served by Flask
   - No additional configuration needed for Render
