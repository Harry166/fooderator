document.addEventListener("DOMContentLoaded", () => {
    const cameraBtn = document.getElementById('cameraBtn');
    const fileInput = document.getElementById('fileInput');
    const searchBtn = document.getElementById('searchBtn');
    const barcodeInput = document.getElementById('barcodeInput');
    const languageSelect = document.getElementById('language');

    // Modal elements
    const modal = document.getElementById("cameraModal");
    const closeModalBtn = document.getElementsByClassName("close")[0];
    const video = document.getElementById("video");
    const canvas = document.getElementById("canvas");
    const captureBtn = document.getElementById("captureBtn");

    // Loading and Result elements
    const loadingElement = document.getElementById('loading');
    const resultsElement = document.getElementById('results');
    const errorElement = document.getElementById('error');
    const errorMessage = document.getElementById('errorMessage');

    // Product info elements
    const productImage = document.getElementById('productImage');
    const productName = document.getElementById('productName');
    const productBrand = document.getElementById('productBrand');
    const barcodeDisplay = document.getElementById('barcode');
    const ingredientsList = document.getElementById('ingredientsList');

    // Tabs
    const tabButtons = document.querySelectorAll('.tab-btn');
    const tabContents = document.querySelectorAll('.tab-content');
    const nutritionGrid = document.querySelector('.nutrition-grid');

    // Camera state
    let scanning = false;
    let stream = null;
    let scanInterval = null;

    // Camera access handler with better configuration
    cameraBtn.addEventListener('click', async () => {
        modal.style.display = "block";
        try {
            // Request camera with optimal settings for barcode scanning
            const constraints = {
                video: {
                    facingMode: 'environment', // Use back camera on mobile
                    width: { ideal: 1280 },
                    height: { ideal: 720 },
                    aspectRatio: { ideal: 16/9 }
                }
            };
            
            stream = await navigator.mediaDevices.getUserMedia(constraints);
            video.srcObject = stream;
            video.play();
            
            // Start continuous scanning
            startContinuousScanning();
            
        } catch (err) {
            console.error('Camera access error:', err);
            showError('Unable to access camera. Please ensure camera permissions are granted.');
            closeModal();
        }
    });

    // Continuous scanning function
    function startContinuousScanning() {
        scanning = true;
        captureBtn.textContent = '🔍 Scanning...';
        captureBtn.disabled = true;
        
        scanInterval = setInterval(() => {
            if (video.readyState === video.HAVE_ENOUGH_DATA) {
                scanFrame();
            }
        }, 300); // Scan every 300ms
    }

    // Scan a single frame
    function scanFrame() {
        const context = canvas.getContext('2d');
        canvas.width = video.videoWidth;
        canvas.height = video.videoHeight;
        context.drawImage(video, 0, 0, canvas.width, canvas.height);
        
        canvas.toBlob(async (blob) => {
            const imageUrl = URL.createObjectURL(blob);
            const base64Image = await convertImageToBase64(imageUrl);
            
            // Try to detect barcode
            try {
                const response = await fetch('/api/scan-barcode', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json'
                    },
                    body: JSON.stringify({ image: base64Image })
                });
                
                if (response.ok) {
                    const result = await response.json();
                    if (result.barcode) {
                        // Barcode found!
                        stopScanning();
                        // Visual feedback
                        captureBtn.textContent = '✅ Barcode Found!';
                        captureBtn.style.backgroundColor = '#4CAF50';
                        
                        // Fetch product after short delay
                        setTimeout(() => {
                            fetchProduct(result.barcode);
                            closeModal();
                        }, 1000);
                    }
                }
            } catch (error) {
                // Continue scanning if error
            }
            
            URL.revokeObjectURL(imageUrl);
        }, 'image/jpeg', 0.8);
    }

    // Stop continuous scanning
    function stopScanning() {
        scanning = false;
        if (scanInterval) {
            clearInterval(scanInterval);
            scanInterval = null;
        }
    }

    // Manual capture button (now acts as a fallback)
    captureBtn.addEventListener('click', () => {
        if (!scanning) {
            // Take a single shot if not already scanning
            const context = canvas.getContext('2d');
            canvas.width = video.videoWidth;
            canvas.height = video.videoHeight;
            context.drawImage(video, 0, 0, canvas.width, canvas.height);
            canvas.toBlob(async (blob) => {
                const imageUrl = URL.createObjectURL(blob);
                const base64Image = await convertImageToBase64(imageUrl);
                processImage(base64Image);
                closeModal();
            }, 'image/jpeg');
        }
    });

    closeModalBtn.addEventListener('click', () => {
        closeModal();
    });

    window.addEventListener('click', (event) => {
        if (event.target == modal) {
            closeModal();
        }
    });

    function closeModal() {
        modal.style.display = "none";
        stopScanning();
        
        // Reset button state
        captureBtn.textContent = '📸 Capture';
        captureBtn.disabled = false;
        captureBtn.style.backgroundColor = '';
        
        // Stop camera stream
        if (video.srcObject) {
            const tracks = video.srcObject.getTracks();
            tracks.forEach(track => track.stop());
            video.srcObject = null;
        }
    }

    fileInput.addEventListener('change', () => {
        const file = fileInput.files[0];
        const reader = new FileReader();
        reader.onload = (e) => {
            const base64Image = e.target.result;
            processImage(base64Image);
        };
        reader.readAsDataURL(file);
    });

    searchBtn.addEventListener('click', () => {
        const barcode = barcodeInput.value.trim();
        if (barcode) {
            fetchProduct(barcode);
        }
    });

    function convertImageToBase64(url) {
        return new Promise((resolve, reject) => {
            const img = new Image();
            img.crossOrigin = 'Anonymous';
            img.onload = function () {
                const canvas = document.createElement('canvas');
                canvas.width = img.width;
                canvas.height = img.height;
                const ctx = canvas.getContext('2d');
                ctx.drawImage(img, 0, 0);
                const dataURL = canvas.toDataURL("image/jpeg");
                resolve(dataURL);
            };
            img.onerror = reject;
            img.src = url;
        });
    }

    async function processImage(base64Image) {
        showLoading();
        try {
            const response = await fetch('/api/scan-barcode', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({ image: base64Image })
            });
            if (!response.ok) throw new Error('Failed to scan barcode');
            const result = await response.json();
            const barcode = result.barcode;
            fetchProduct(barcode);
        } catch (error) {
            showError(error.message);
        }
    }

    async function fetchProduct(barcode) {
        showLoading();
        const language = languageSelect.value;
        try {
            const response = await fetch(`/api/product/${barcode}?lang=${language}`);
            if (!response.ok) throw new Error('Product not found');
            const product = await response.json();
            displayProduct(product);
        } catch (error) {
            showError(error.message);
        }
    }

    function displayProduct(product) {
        hideLoading();
        resultsElement.style.display = 'block';
        // Set product image
        productImage.src = product.image_url || 'default-product.png';
        productImage.alt = product.name;
        // Set product info
        productName.textContent = product.name || 'Unknown Product';
        productBrand.textContent = `Brand: ${product.brand || 'N/A'}`;
        barcodeDisplay.textContent = `Barcode: ${product.barcode}`;
        // Display ingredients with better formatting
        if (product.ingredients && product.ingredients !== 'Ingredients not available in database') {
            ingredientsList.textContent = product.ingredients;
        } else {
            ingredientsList.innerHTML = '<em style="color: #666;">Ingredients not available in database. The product information may be incomplete.</em>';
        }
        const nutrition = product.nutrition || {};
        
        // Comprehensive nutrition labels mapping
        const labels = product.nutrition_labels || {
            energy: 'Calories',
            energy_kj: 'Energy (kJ)',
            fat: 'Total Fat',
            saturated_fat: 'Saturated Fat',
            monounsaturated_fat: 'Monounsaturated Fat',
            polyunsaturated_fat: 'Polyunsaturated Fat',
            trans_fat: 'Trans Fat',
            cholesterol: 'Cholesterol',
            carbohydrates: 'Total Carbohydrates',
            sugars: 'Sugars',
            added_sugars: 'Added Sugars',
            fiber: 'Dietary Fiber',
            proteins: 'Protein',
            salt: 'Salt',
            sodium: 'Sodium',
            potassium: 'Potassium',
            calcium: 'Calcium',
            iron: 'Iron',
            magnesium: 'Magnesium',
            phosphorus: 'Phosphorus',
            zinc: 'Zinc',
            copper: 'Copper',
            manganese: 'Manganese',
            selenium: 'Selenium',
            iodine: 'Iodine',
            vitamin_a: 'Vitamin A',
            vitamin_a_iu: 'Vitamin A (IU)',
            vitamin_c: 'Vitamin C',
            vitamin_d: 'Vitamin D',
            vitamin_e: 'Vitamin E',
            vitamin_k: 'Vitamin K',
            vitamin_b1: 'Thiamin (B1)',
            vitamin_b2: 'Riboflavin (B2)',
            niacin: 'Niacin (B3)',
            vitamin_b6: 'Vitamin B6',
            folate: 'Folate',
            vitamin_b12: 'Vitamin B12',
            pantothenic_acid: 'Pantothenic Acid',
            biotin: 'Biotin',
            caffeine: 'Caffeine',
            alcohol: 'Alcohol'
        };
        
        // Units for different nutrients
        const units = {
            energy: 'kcal',
            energy_kj: 'kJ',
            cholesterol: 'mg',
            sodium: 'mg',
            potassium: 'mg',
            calcium: 'mg',
            iron: 'mg',
            magnesium: 'mg',
            phosphorus: 'mg',
            zinc: 'mg',
            copper: 'mg',
            manganese: 'mg',
            selenium: 'μg',
            iodine: 'μg',
            vitamin_a: 'μg',
            vitamin_a_iu: 'IU',
            vitamin_c: 'mg',
            vitamin_d: 'μg',
            vitamin_e: 'mg',
            vitamin_k: 'μg',
            vitamin_b1: 'mg',
            vitamin_b2: 'mg',
            niacin: 'mg',
            vitamin_b6: 'mg',
            folate: 'μg',
            vitamin_b12: 'μg',
            pantothenic_acid: 'mg',
            biotin: 'μg',
            caffeine: 'mg',
            alcohol: 'g'
        };
        
        // Check if nutrition is an object and has data
        if (typeof nutrition === 'object' && nutrition !== null && Object.keys(nutrition).length > 0) {
            // Group nutrients by category for better display
            const macronutrients = ['energy', 'energy_kj', 'fat', 'saturated_fat', 'monounsaturated_fat', 'polyunsaturated_fat', 'trans_fat', 'cholesterol', 'carbohydrates', 'fiber', 'sugars', 'added_sugars', 'proteins', 'salt', 'sodium'];
            const vitamins = ['vitamin_a', 'vitamin_a_iu', 'vitamin_c', 'vitamin_d', 'vitamin_e', 'vitamin_k', 'vitamin_b1', 'vitamin_b2', 'niacin', 'vitamin_b6', 'folate', 'vitamin_b12', 'pantothenic_acid', 'biotin'];
            const minerals = ['potassium', 'calcium', 'iron', 'magnesium', 'phosphorus', 'zinc', 'copper', 'manganese', 'selenium', 'iodine'];
            const others = ['caffeine', 'alcohol'];
            
            let nutritionHTML = '';
            
            // Display macronutrients
            const macroData = Object.entries(nutrition).filter(([key]) => macronutrients.includes(key));
            if (macroData.length > 0) {
                macroData.forEach(([key, value]) => {
                    const label = labels[key] || key.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase());
                    const unit = units[key] || 'g';
                    const displayValue = value !== null && value !== undefined && value !== 'N/A'
                        ? `${typeof value === 'number' ? value.toFixed(2).replace(/\.00$/, '') : value}${unit}`
                        : 'N/A';
                    nutritionHTML += `
                        <div class="nutrition-item">
                            <div class="label">${label}</div>
                            <div class="value">${displayValue}</div>
                        </div>
                    `;
                });
            }
            
            // Display vitamins if available
            const vitaminData = Object.entries(nutrition).filter(([key]) => vitamins.includes(key));
            if (vitaminData.length > 0) {
                nutritionHTML += '<div class="nutrition-category">Vitamins</div>';
                vitaminData.forEach(([key, value]) => {
                    const label = labels[key] || key.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase());
                    const unit = units[key] || 'mg';
                    const displayValue = value !== null && value !== undefined && value !== 'N/A'
                        ? `${typeof value === 'number' ? value.toFixed(2).replace(/\.00$/, '') : value}${unit}`
                        : 'N/A';
                    nutritionHTML += `
                        <div class="nutrition-item">
                            <div class="label">${label}</div>
                            <div class="value">${displayValue}</div>
                        </div>
                    `;
                });
            }
            
            // Display minerals if available
            const mineralData = Object.entries(nutrition).filter(([key]) => minerals.includes(key));
            if (mineralData.length > 0) {
                nutritionHTML += '<div class="nutrition-category">Minerals</div>';
                mineralData.forEach(([key, value]) => {
                    const label = labels[key] || key.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase());
                    const unit = units[key] || 'mg';
                    const displayValue = value !== null && value !== undefined && value !== 'N/A'
                        ? `${typeof value === 'number' ? value.toFixed(2).replace(/\.00$/, '') : value}${unit}`
                        : 'N/A';
                    nutritionHTML += `
                        <div class="nutrition-item">
                            <div class="label">${label}</div>
                            <div class="value">${displayValue}</div>
                        </div>
                    `;
                });
            }
            
            // Display other nutrients if available
            const otherData = Object.entries(nutrition).filter(([key]) => others.includes(key));
            if (otherData.length > 0) {
                nutritionHTML += '<div class="nutrition-category">Other</div>';
                otherData.forEach(([key, value]) => {
                    const label = labels[key] || key.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase());
                    const unit = units[key] || 'g';
                    const displayValue = value !== null && value !== undefined && value !== 'N/A'
                        ? `${typeof value === 'number' ? value.toFixed(2).replace(/\.00$/, '') : value}${unit}`
                        : 'N/A';
                    nutritionHTML += `
                        <div class="nutrition-item">
                            <div class="label">${label}</div>
                            <div class="value">${displayValue}</div>
                        </div>
                    `;
                });
            }
            
            nutritionGrid.innerHTML = nutritionHTML || '<p>No nutrition information available</p>';
        } else {
            nutritionGrid.innerHTML = '<p>Nutrition information not available</p>';
        }

        // Setup tabs
        setupTabs();
    }

    function setupTabs() {
        tabButtons.forEach((btn, index) => {
            btn.addEventListener('click', () => {
                tabButtons.forEach((button, idx) => {
                    button.classList[idx === index ? 'add' : 'remove']('active');
                    tabContents[idx].classList[idx === index ? 'add' : 'remove']('active');
                });
            });
        });
    }

    function showLoading() {
        loadingElement.style.display = 'block';
        resultsElement.style.display = 'none';
        errorElement.style.display = 'none';
    }

    function hideLoading() {
        loadingElement.style.display = 'none';
    }

    function showError(message) {
        hideLoading();
        errorElement.style.display = 'block';
        resultsElement.style.display = 'none';
        errorMessage.textContent = message;
    }
});

