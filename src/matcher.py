import pandas as pd
import difflib
import re

def load_products(csv_path: str = "data/products.csv") -> list:
    """Loads the products catalog from the CSV file."""
    try:
        df = pd.read_csv(csv_path)
        return df.to_dict('records')
    except Exception as e:
        print(f"Error loading products: {e}")
        return []

def clean_text(text: str) -> str:
    """Cleans text for better matching comparison."""
    text = text.lower()
    text = re.sub(r'[^a-z0-9\säöüß]', ' ', text)
    return " ".join(text.split())

def get_similarity_score(str1: str, str2: str) -> float:
    """Computes a similarity score between two strings."""
    clean1 = clean_text(str1)
    clean2 = clean_text(str2)
    
    if not clean1 or not clean2:
        return 0.0
        
    seq_ratio = difflib.SequenceMatcher(None, clean1, clean2).ratio()
    
    words1 = set(clean1.split())
    words2 = set(clean2.split())
    
    if not words1 or not words2:
        return seq_ratio
        
    overlap = words1.intersection(words2)
    overlap_ratio = len(overlap) / max(len(words1), len(words2))
    
    return 0.4 * seq_ratio + 0.6 * overlap_ratio

def find_best_match(raw_text: str, products: list, threshold: float = 0.3) -> dict:
    """Finds the best matching product from the catalog for a given raw text."""
    best_product = None
    best_score = 0.0
    
    for prod in products:
        display_name = f"{prod['name']} {prod['brand']}"
        score = get_similarity_score(raw_text, display_name)
        
        score_name = get_similarity_score(raw_text, prod['name'])
        score = max(score, score_name)
        
        if score > best_score:
            best_score = score
            best_product = prod
            
    if best_product and best_score >= threshold:
        return {
            "product_id": best_product['id'],
            "name": best_product['name'],
            "brand": best_product['brand'],
            "price": best_product['price'],
            "unit": best_product['unit'],
            "score": best_score,
            "high_confidence": best_score >= 0.55
        }
        
    return None
