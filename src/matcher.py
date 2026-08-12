import pandas as pd
import difflib
import re
import os
import pickle

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

def clean_text(text: str) -> str:
    """Cleans text for better matching comparison."""
    text = text.lower()
    
    # Normalize din a4 / din a5
    text = re.sub(r'dina(\d)', r'din a\1', text)
    
    # Normalize compound nouns containing "heft"
    text = re.sub(r'schulheft', 'schul heft', text)
    text = re.sub(r'schreibheft', 'schreib heft', text)
    text = re.sub(r'hausheft', 'haus heft', text)
    text = re.sub(r'rechenheft', 'rechen heft', text)
    text = re.sub(r'vokabelheft', 'vokabel heft', text)
    text = re.sub(r'regelheft', 'regel heft', text)
    text = re.sub(r'mitteilungsheft', 'mitteilungs heft', text)
    text = re.sub(r'schreiblernheft', 'schreiblern heft', text)
    text = re.sub(r'doppelheft', 'doppel heft', text)
    text = re.sub(r'notenheft', 'noten heft', text)
    text = re.sub(r'arbeitsheft', 'arbeits heft', text)
    text = re.sub(r'übungsheft', 'übungs heft', text)
    
    # Normalize pappschnellhefter to schnellhefter
    text = re.sub(r'pappschnellhefter', 'papp schnellhefter', text)
    
    text = re.sub(r'[^a-z0-9\säöüß]', ' ', text)
    return " ".join(text.split())

def get_similarity_score(str1: str, str2: str) -> float:
    """Computes a similarity score between two strings."""
    clean1 = clean_text(str1)
    clean2 = clean_text(str2)
    
    if not clean1 or not clean2:
        return 0.0
        
    words1 = set(clean1.split())
    words2 = set(clean2.split())
    
    # Ensure "heft" products and "hefter/schnellhefter" products are mutually exclusive
    is_heft_1 = any(w == "heft" for w in words1)
    is_hefter_1 = any("hefter" in w for w in words1)
    is_heft_2 = any(w == "heft" for w in words2)
    is_hefter_2 = any("hefter" in w for w in words2)
    
    if (is_heft_1 and is_hefter_2) or (is_hefter_1 and is_heft_2):
        return 0.0
        
    seq_ratio = difflib.SequenceMatcher(None, clean1, clean2).ratio()
    
    if not words1 or not words2:
        return seq_ratio
        
    overlap = words1.intersection(words2)
    overlap_ratio = len(overlap) / max(len(words1), len(words2))
    
    return 0.4 * seq_ratio + 0.6 * overlap_ratio

def find_best_match(raw_text: str, products: list, threshold: float = 0.3) -> dict:
    """Finds the best matching product from the catalog for a given raw text using ML classifier if available, with fuzzy fallback."""
    
    # 1. Try model prediction if model is loaded
    if _model_data and "pipeline" in _model_data:
        try:
            pipeline = _model_data["pipeline"]
            pred_id = int(pipeline.predict([raw_text])[0])
            
            # Predict probabilities to gauge confidence
            probs = pipeline.predict_proba([raw_text])[0]
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
                            "high_confidence": max_prob >= 0.65
                        }
        except Exception as e:
            pass

    # 2. Fuzzy fallback
    best_product = None
    best_score = 0.0
    
    clean_query = clean_text(raw_text)
    query_words = set(clean_query.split())
    
    for prod in products:
        display_name = f"{prod['name']} {prod['brand']}"
        score = get_similarity_score(raw_text, display_name)
        
        score_name = get_similarity_score(raw_text, prod['name'])
        score = max(score, score_name)
        
        if 'description' in prod and isinstance(prod['description'], str) and prod['description'].strip():
            score_desc = get_similarity_score(raw_text, prod['description'])
            
            clean_desc = clean_text(prod['description'])
            desc_words = set(clean_desc.split())
            if query_words and query_words.issubset(desc_words):
                is_heft_q = any(w == "heft" for w in query_words)
                is_hefter_d = any("hefter" in w for w in desc_words)
                is_hefter_q = any("hefter" in w for w in query_words)
                is_heft_d = any(w == "heft" for w in desc_words)
                
                if not ((is_heft_q and is_hefter_d) or (is_hefter_q and is_heft_d)):
                    score_desc = max(score_desc, 0.85)
                    
            score = max(score, score_desc)
            
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
