import pandas as pd
import difflib
import re
import os
import pickle
from src.text_optimizer import clean_text
from sentence_transformers import SentenceTransformer, util

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

_transformer_model = None
_product_embeddings = {}

def get_transformer_model():
    global _transformer_model
    if _transformer_model is None:
        try:
            # paraphrase-multilingual-MiniLM-L12-v2 is an excellent small multilingual/German model
            _transformer_model = SentenceTransformer("paraphrase-multilingual-MiniLM-L12-v2")
        except Exception as e:
            print(f"Failed to load sentence-transformer model: {e}")
    return _transformer_model

def get_product_embedding(prod, model):
    prod_id = prod['id']
    if prod_id not in _product_embeddings:
        desc = prod.get('description', '')
        if not isinstance(desc, str):
            desc = ''
        text_to_embed = f"{prod['name']} {prod['brand']} {desc}".strip()
        # Compute embedding using model
        _product_embeddings[prod_id] = model.encode(text_to_embed, convert_to_tensor=True)
    return _product_embeddings[prod_id]

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
    # 1. Size mismatch (A3 vs A4 vs A5)
    has_a3_1 = "a3" in words1
    has_a4_1 = "a4" in words1
    has_a5_1 = "a5" in words1
    
    has_a3_2 = "a3" in words2
    has_a4_2 = "a4" in words2
    has_a5_2 = "a5" in words2
    
    if (has_a3_1 and not has_a3_2) or (not has_a3_1 and has_a3_2 and (has_a4_1 or has_a5_1)):
        return True
    if (has_a4_1 and not has_a4_2) or (not has_a4_1 and has_a4_2 and (has_a3_1 or has_a5_1)):
        return True
    if (has_a5_1 and not has_a5_2) or (not has_a5_1 and has_a5_2 and (has_a3_1 or has_a4_1)):
        return True

    # 2. Lineatur mismatch
    def extract_lineatur(words):
        s = " ".join(words)
        nums = re.findall(r'\b(?:lineatur|lin|lineat|lineatr)\s*(\d+[a-z]?)\b', s)
        # Also grab single digits from words if query is like "Heft 2"
        for w in words:
            if w.isdigit() and len(w) == 1:
                nums.append(w)
        return set(nums)
        
    lin1 = extract_lineatur(words1)
    lin2 = extract_lineatur(words2)
    if lin1 and lin2 and not lin1.intersection(lin2):
        return True

    # 3. Product type matching
    types = [
        "bleistift", "buntstifte", "radiergummi", "füllfederhalter", "füller", 
        "tintenpatronen", "tuschkasten", "pinsel", "geodreieck", "zirkel", 
        "collegeblock", "zeichenblock", "anspitzer", "lineal", "schere", 
        "klebestift", "wachsmalstifte", "fasermaler", "kugelschreiber", 
        "taschenrechner", "ringordner", "trennblätter", "malkittel", 
        "spiralblock", "haftnotizen", "karteikasten", "karteikarten", 
        "tintenkiller", "druckbleistift", "usb", "vokabelheft", "hausaufgabenheft",
        "schnellhefter", "block", "heft", "umschlag", "mappe"
    ]
    for t in types:
        if t in words1:
            if not any(t in w for w in words2):
                return True
                
    # 3.5 Bleistift vs Druckbleistift
    is_druck_1 = "druck" in words1 or "druckbleistift" in words1
    is_druck_2 = "druck" in words2 or "druckbleistift" in words2
    is_bleistift_1 = any("bleistift" in w for w in words1)
    is_bleistift_2 = any("bleistift" in w for w in words2)
    if (is_bleistift_1 or is_bleistift_2) and (is_druck_1 != is_druck_2):
        return True

    # 4. Heft vs Hefter
    is_heft_1 = any(w == "heft" for w in words1)
    is_hefter_1 = any("hefter" in w for w in words1)
    is_heft_2 = any(w == "heft" for w in words2)
    is_hefter_2 = any("hefter" in w for w in words2)
    if (is_heft_1 and is_hefter_2) or (is_hefter_1 and is_heft_2):
        return True
        
    # 5. Heft vs Umschlag/Hülle/Schoner
    is_umschlag_1 = any(w in ["umschlag", "hülle", "schoner"] or "umschlag" in w or "hülle" in w or "schoner" in w for w in words1)
    is_umschlag_2 = any(w in ["umschlag", "hülle", "schoner"] or "umschlag" in w or "hülle" in w or "schoner" in w for w in words2)
    if (is_heft_1 and is_umschlag_2) or (is_umschlag_1 and is_heft_2):
        return True
        
    # 6. Musik/Notenhefte
    is_musik_prod = any(w in ["musik", "noten"] for w in words2)
    is_musik_query = any(w in ["musik", "noten"] for w in words1)
    if is_musik_prod and not is_musik_query:
        return True
        
    # 7. Schreibhäuschen
    is_haus_prod = any("haus" in w or "häus" in w for w in words2)
    is_haus_query = any("haus" in w or "häus" in w for w in words1)
    if is_haus_prod and not is_haus_query:
        return True
        
    # 8. Ruling type mismatch (liniert, kariert, blanko)
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

def is_metadata_compatible(level_query: str, level_prod: str, subject_query: str, subject_prod: str) -> bool:
    if subject_query and subject_prod:
        if subject_query != 'Allgemein' and subject_prod != 'Allgemein':
            if subject_query.lower() != subject_prod.lower():
                return False
                
    if level_query and level_prod:
        if level_query != 'Allgemein' and level_prod != 'Allgemein':
            def get_all_levels(lvl_str):
                levels = set()
                range_match = re.search(r'(\d+)\s*[-–]\s*(\d+)', lvl_str)
                if range_match:
                    start, end = int(range_match.group(1)), int(range_match.group(2))
                    return set(range(start, end + 1))
                plus_match = re.search(r'(\d+)\s*\+', lvl_str)
                if plus_match:
                    start = int(plus_match.group(1))
                    return set(range(start, start + 5))
                single_match = re.findall(r'\d+', lvl_str)
                for num in single_match:
                    levels.add(int(num))
                return levels
            
            q_set = get_all_levels(level_query)
            p_set = get_all_levels(level_prod)
            if q_set and p_set and not q_set.intersection(p_set):
                return False
    return True

def find_best_match(raw_text: str, products: list, threshold: float = 0.3, level: str = None, subject: str = None) -> dict:
    """Finds the best matching product from the catalog for a given raw text using SentenceTransformer semantic similarity and ML classifier."""
    # Clean the input text at the very beginning of the decision process
    cleaned_text = clean_text(raw_text)
    
    # 1. Run semantic matching / sentence transformer similarity
    best_product = None
    best_score = 0.0
    query_words = set(cleaned_text.split())
    
    model = get_transformer_model()
    if model is not None:
        try:
            query_emb = model.encode(cleaned_text, convert_to_tensor=True)
            for prod in products:
                # Apply metadata filtering
                if not is_metadata_compatible(level, prod.get('level'), subject, prod.get('subject')):
                    score = 0.0
                    continue
                    
                # Apply separation rules to display name
                display_name = f"{prod['name']} {prod['brand']}"
                words_name = set(clean_text(display_name).split())
                
                # If display name is separated, score is 0.0
                if is_separated(query_words, words_name):
                    score = 0.0
                else:
                    prod_emb = get_product_embedding(prod, model)
                    score = float(util.cos_sim(query_emb, prod_emb)[0][0])
                    
                    # Boost if query words are a subset of description words
                    desc_text = prod.get('description', '')
                    if isinstance(desc_text, str) and desc_text.strip():
                        words_desc = set(clean_text(desc_text).split())
                        if query_words and words_desc and query_words.issubset(words_desc):
                            score = max(score, 0.85)
                
                if score > best_score:
                    best_score = score
                    best_product = prod
        except Exception as e:
            print(f"Error during semantic embedding search: {e}")
            model = None # Force fallback to fuzzy match below
            
    # Fuzzy match fallback if model failed or couldn't load
    if model is None:
        for prod in products:
            # Apply metadata filtering
            if not is_metadata_compatible(level, prod.get('level'), subject, prod.get('subject')):
                continue
                
            display_name = f"{prod['name']} {prod['brand']}"
            
            # Apply separation rules to display name
            words_name = set(clean_text(display_name).split())
            if is_separated(query_words, words_name):
                score = 0.0
            else:
                score = get_similarity_score(cleaned_text, display_name)
                score_name = get_similarity_score(cleaned_text, prod['name'])
                score = max(score, score_name)
                
                if 'description' in prod and isinstance(prod['description'], str) and prod['description'].strip():
                    clean_desc = clean_text(prod['description'])
                    desc_words = set(clean_desc.split())
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

    # 3. Fallback to the best similarity match if it satisfies the minimum threshold
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
