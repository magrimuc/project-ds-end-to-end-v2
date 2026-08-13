import pandas as pd
import difflib
import re
import os
import pickle
from src.text_optimizer import clean_text

# Load model pipeline
_model_data = None
_model_path = "src/model.pkl"
if not os.path.exists(_model_path) and os.path.exists("project-ds-end-to-end-v2/src/model.pkl"):
    _model_path = "project-ds-end-to-end-v2/src/model.pkl"
    
if os.path.exists(_model_path):
    try:
        with open(_model_path, "rb") as f:
            _model_data = pickle.load(f)
    except Exception as e:
        print(f"Error loading model from {_model_path}: {e}")

def load_products(csv_path: str = "data/products.csv") -> list:
    """Loads the products catalog from the CSV file."""
    try:
        df = pd.read_csv(csv_path)
        return df.to_dict('records')
    except Exception as e:
        print(f"Error loading products: {e}")
        return []

def is_separated(words1: set, words2: set) -> bool:
    """Returns True if the two word sets represent distinct categories that should not match."""
    # 1. Heft vs Hefter
    is_heft_1 = any(w == "heft" for w in words1)
    is_hefter_1 = any("hefter" in w for w in words1)
    is_heft_2 = any(w == "heft" for w in words2)
    is_hefter_2 = any("hefter" in w for w in words2)
    if (is_heft_1 and is_hefter_2) or (is_hefter_1 and is_heft_2):
        return True
        
    # 2. Heft vs Umschlag/Hülle/Schoner
    is_umschlag_1 = any(w in ["umschlag", "hülle", "schoner"] or "umschlag" in w or "hülle" in w or "schoner" in w for w in words1)
    is_umschlag_2 = any(w in ["umschlag", "hülle", "schoner"] or "umschlag" in w or "hülle" in w or "schoner" in w for w in words2)
    if (is_heft_1 and is_umschlag_2) or (is_umschlag_1 and is_heft_2):
        return True
        
    # 3. Musik/Notenhefte
    is_musik_prod = any(w in ["musik", "noten"] for w in words2)
    is_musik_query = any(w in ["musik", "noten"] for w in words1)
    if is_musik_prod and not is_musik_query:
        return True
        
    # 4. Schreibhäuschen
    is_haus_prod = any("haus" in w or "häus" in w for w in words2)
    is_haus_query = any("haus" in w or "häus" in w for w in words1)
    if is_haus_prod and not is_haus_query:
        return True
        
    # 5. Ruling type mismatch (liniert, kariert, blanko)
    is_liniert_1 = "liniert" in words1
    is_kariert_1 = any(w in words1 for w in ["kariert", "rauten", "quadrate"])
    is_blanko_1 = any(w in words1 for w in ["blanko", "unliniert"])
    
    is_liniert_2 = "liniert" in words2
    is_kariert_2 = any(w in words2 for w in ["kariert", "rauten", "quadrate", "karo"])
    is_blanko_2 = any(w in words2 for w in ["blanko", "unliniert"])
    
    if is_liniert_1 and (is_kariert_2 or is_blanko_2):
        return True
    if is_kariert_1 and (is_liniert_2 or is_blanko_2):
        return True
    if is_blanko_1 and (is_liniert_2 or is_kariert_2):
        return True
        
    return False

def get_similarity_score(str1: str, str2: str) -> float:
    """Computes a similarity score between two strings."""
    clean1 = clean_text(str1)
    clean2 = clean_text(str2)
    
    if not clean1 or not clean2:
        return 0.0
        
    words1 = set(clean1.split())
    words2 = set(clean2.split())
    
    if is_separated(words1, words2):
        return 0.0
        
    seq_ratio = difflib.SequenceMatcher(None, clean1, clean2).ratio()
    
    if not words1 or not words2:
        return seq_ratio
        
    overlap = words1.intersection(words2)
    overlap_ratio = len(overlap) / max(len(words1), len(words2))
    
    return 0.4 * seq_ratio + 0.6 * overlap_ratio

def find_best_match(raw_text: str, products: list, threshold: float = 0.3) -> dict:
    """Finds the best matching product from the catalog for a given raw text using ML classifier if available, with fuzzy fallback."""
    # Clean the input text at the very beginning of the decision process
    cleaned_text = clean_text(raw_text)
    
    # 1. Run word similarities / fuzzy matching first
    best_product = None
    best_score = 0.0
    query_words = set(cleaned_text.split())
    
    for prod in products:
        display_name = f"{prod['name']} {prod['brand']}"
        score = get_similarity_score(cleaned_text, display_name)
        
        score_name = get_similarity_score(cleaned_text, prod['name'])
        score = max(score, score_name)
        
        if 'description' in prod and isinstance(prod['description'], str) and prod['description'].strip():
            clean_desc = clean_text(prod['description'])
            desc_words = set(clean_desc.split())
            
            if is_separated(query_words, desc_words):
                score_desc = 0.0
            else:
                score_desc = get_similarity_score(cleaned_text, prod['description'])
                if query_words and query_words.issubset(desc_words):
                    score_desc = max(score_desc, 0.85)
                    
            score = max(score, score_desc)
            
        if score > best_score:
            best_score = score
            best_product = prod
            
    # If we have an extremely high similarity match (>= 0.85), return it directly
    if best_product and best_score >= 0.85:
        return {
            "product_id": best_product['id'],
            "name": best_product['name'],
            "brand": best_product['brand'],
            "price": best_product['price'],
            "unit": best_product['unit'],
            "score": best_score,
            "high_confidence": True
        }

    # 2. Otherwise, try model prediction if model is loaded
    if _model_data and "pipeline" in _model_data:
        try:
            pipeline = _model_data["pipeline"]
            pred_id = int(pipeline.predict([cleaned_text])[0])
            probs = pipeline.predict_proba([cleaned_text])[0]
            max_prob = max(probs)
            
            if pred_id != 0 and max_prob >= 0.65:
                # Find product in list
                for prod in products:
                    if int(prod['id']) == pred_id:
                        return {
                            "product_id": prod['id'],
                            "name": prod['name'],
                            "brand": prod['brand'],
                            "price": prod['price'],
                            "unit": prod['unit'],
                            "score": max_prob,
                            "high_confidence": True
                        }
        except Exception as e:
            pass

    # 3. Fallback to the best fuzzy match if it satisfies the minimum threshold
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
