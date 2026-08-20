import os
import sys
import re
import csv
import pypdf
import pandas as pd
import difflib

# Add root directory to sys.path so we can import src modules
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from src.text_optimizer import TextOptimizer


def clean_text(text: str) -> str:
    """Cleans text for better comparison."""
    text = text.lower()
    # Normalize DinA representations
    text = re.sub(r'dina(\d)', r'din a\1', text)
    text = re.sub(r'\b(lin[ei]at[ur]+|liniatur|linatur|lineatr|lin)\b\.?', 'lineatur', text)
    text = re.sub(r'[^a-z0-9\säöüß]', ' ', text)
    return " ".join(text.split())

def extract_all_lines(pdf_dir: str) -> list:
    """Extracts all non-empty lines from the PDFs in the directory."""
    lines = []
    if not os.path.exists(pdf_dir):
        # Let's try relative to the parent dir if not found
        if os.path.exists("../data/downloads"):
            pdf_dir = "../data/downloads"
        elif os.path.exists("data/downloads"):
            pdf_dir = "data/downloads"
        else:
            print(f"Directory {pdf_dir} does not exist!")
            return []
            
    for f in sorted(os.listdir(pdf_dir)):
        if f.endswith('.pdf'):
            path = os.path.join(pdf_dir, f)
            try:
                reader = pypdf.PdfReader(path)
                for page in reader.pages:
                    text = page.extract_text()
                    if text:
                        for line in text.splitlines():
                            line = line.strip()
                            if line and len(line) > 2 and not line.isdigit():
                                lines.append(line)
            except Exception as e:
                print(f"Error reading {f}: {e}")
    # De-duplicate while preserving order
    seen = set()
    unique_lines = []
    for l in lines:
        if l not in seen:
            seen.add(l)
            unique_lines.append(l)
    return unique_lines

def find_color_associations(line_text: str):
    """
    Finds which colors are closest to Umschlag/Einband or Schnellhefter/Hefter.
    Returns a dict mapping the item type ('umschlag', 'schnellhefter') to the color.
    """
    text = line_text.lower()
    colors = ["rot", "blau", "grün", "gelb", "weiß", "lila", "schwarz", "hellblau", "dunkelblau", "transparent", "orange"]
    
    # Find all occurrences of colors with their start positions
    color_positions = []
    for color in colors:
        for match in re.finditer(rf'\b{color}\b', text):
            color_positions.append((color, match.start()))
            
    # Find all occurrences of target nouns
    noun_positions = []
    for noun, patterns in [('umschlag', [r'\bumschlag', r'\beinband', r'\bschoner', r'\bhülle']), 
                           ('schnellhefter', [r'\bschnellhefter', r'\bhefter', r'\bpappschnellhefter'])]:
        for pattern in patterns:
            for match in re.finditer(pattern, text):
                noun_positions.append((noun, match.start()))
                
    associations = {}
    if not noun_positions or not color_positions:
        return associations
        
    # Associate each color to the closest noun
    for color, c_pos in color_positions:
        closest_noun = None
        min_dist = float('inf')
        for noun, n_pos in noun_positions:
            dist = abs(c_pos - n_pos)
            if dist < min_dist:
                min_dist = dist
                closest_noun = noun
        if closest_noun:
            # If the closest noun is already associated, keep the closer one
            if closest_noun in associations:
                prev_color, prev_dist = associations[closest_noun]
                if min_dist < prev_dist:
                    associations[closest_noun] = (color, min_dist)
            else:
                associations[closest_noun] = (color, min_dist)
                
    return {k: v[0] for k, v in associations.items()}

def parse_line_properties(line: str):
    """Parses a text line to extract properties like quantity, size, colors, lineatur, ruling."""
    clean_line = clean_text(line)
    
    # 1. Quantity extraction (Bigrams / amount + article recognition)
    qty = 1
    # Check start of line e.g., "5x", "3 Stk", "10"
    qty_match = re.match(
        r'^(\d+)\s*(?:x|stk\.?|stück|stck\.?|pack\.?|pck\.?|pkg\.?|packung|set)?\s', 
        clean_line
    )
    if qty_match:
        qty = int(qty_match.group(1))
        compare_str = clean_line[qty_match.end():].strip()
    else:
        # Check inside line
        qty_internal = re.search(r'\b(\d+)\s*(?:x|stk\.?|stück|stck\.?|pack\.?|pck\.?|pkg\.?|packung|set)\b', clean_line)
        if qty_internal:
            qty = int(qty_internal.group(1))
        compare_str = clean_line

    # 2. Size extraction (DIN A4, DIN A5, DIN A3)
    # The user requested: "DinA soll auf DinA4 und DinA5 matchen (für Umschläge und Hefte)"
    # So if "dina" or "din a" is present without 4 or 5, we keep track of it as "DinA_generic"
    size = None
    has_generic_dina = False
    if "din a4" in compare_str or "a4" in compare_str:
        size = "A4"
    elif "din a5" in compare_str or "a5" in compare_str:
        size = "A5"
    elif "din a3" in compare_str or "a3" in compare_str:
        size = "A3"
    elif "dina" in compare_str or "din a" in compare_str:
        has_generic_dina = True

    # 3. Ruling type (liniert, kariert, blanko)
    ruling = None
    if "liniert" in compare_str or "lin" in compare_str:
        ruling = "liniert"
    elif "kariert" in compare_str or "kar" in compare_str:
        ruling = "kariert"
    elif "blanko" in compare_str or "ohne linien" in compare_str:
        ruling = "blanko"
        
    # 4. Lineatur number
    lineatur = None
    lineatur_match = re.search(r'lineatur\s*(\d+[a-z]?)', compare_str)
    if lineatur_match:
        lineatur = lineatur_match.group(1)
    else:
        # Fallback to single numbers that aren't other counts
        nums = re.findall(r'\b(\d+)\b', compare_str)
        for num in nums:
            if num not in ["3", "4", "5", "30", "12", "16", "32", "80", "20", "15", "100", str(qty)]:
                lineatur = num
                break

    # 5. Type detection
    item_type = None
    type_keywords = {
        "heft": ["heft", "hefte", "schulheft", "schreibheft", "rechenheft", "vokabelheft", "regelheft", "mitteilungsheft", "schreiblernheft"],
        "schnellhefter": ["schnellhefter", "hefter", "pappschnellhefter"],
        "ordner": ["ordner", "ringbuch", "stehordner"],
        "umschlag": ["umschlag", "umschläge", "einband", "heftschoner", "heftumschlag", "schoner"],
        "mappe": ["mappe", "eckspannmappe", "sammelmappe", "dokumentenmappe", "postmappe", "eckspanner"],
        "bleistift": ["bleistift", "bleistifte"],
        "buntstifte": ["buntstift", "buntstifte", "holzbuntstifte", "farbstifte"],
        "radiergummi": ["radiergummi", "radierer"],
        "spitzer": ["spitzer", "anspitzer", "dosenspitzer"],
        "pinsel": ["pinsel", "borstenpinsel", "haarpinsel", "pinsel-set"],
        "schere": ["schere", "bastelschere"],
        "lineal": ["lineal", "geodreieck"],
        "zirkel": ["zirkel"],
        "collegeblock": ["collegeblock"],
        "zeichenblock": ["zeichenblock", "zeichenblock", "zeichenpapier"],
        "tuschkasten": ["tuschkasten", "wasserfarbkasten", "farbkasten"]
    }
    
    for t, keywords in type_keywords.items():
        if any(re.search(rf'\b{kw}', compare_str) for kw in keywords):
            item_type = t
            break

    # 6. Color proximity
    color_associations = find_color_associations(line)
    
    return {
        "compare_str": compare_str,
        "qty": qty,
        "size": size,
        "has_generic_dina": has_generic_dina,
        "color_associations": color_associations,
        "ruling": ruling,
        "lineatur": lineatur,
        "item_type": item_type
    }

def get_token_set_ratio(s1: str, s2: str) -> float:
    words1 = set(s1.split())
    words2 = set(s2.split())
    if not words1 or not words2:
        return 0.0
    intersection = words1.intersection(words2)
    diff1 = words1 - words2
    diff2 = words2 - words1
    
    sorted_inter = sorted(list(intersection))
    sorted_d1 = sorted(list(diff1))
    sorted_d2 = sorted(list(diff2))
    
    t0 = " ".join(sorted_inter).strip()
    t1 = (" ".join(sorted_inter) + " " + " ".join(sorted_d1)).strip()
    t2 = (" ".join(sorted_inter) + " " + " ".join(sorted_d2)).strip()
    
    r0 = difflib_ratio(t0, t1) if t0 else 0.0
    r1 = difflib_ratio(t0, t2) if t0 else 0.0
    r2 = difflib_ratio(t1, t2)
    return max(r0, r1, r2) * 100.0

def difflib_ratio(s1, s2):
    return difflib.SequenceMatcher(None, s1, s2).ratio()

def score_product(props, prod):
    prod_name_clean = clean_text(prod['name'])
    prod_desc_clean = clean_text(str(prod.get('description', '')))
    combined_prod_text = f"{prod_name_clean} {prod_desc_clean}"
    
    prod_category = str(prod['category']).lower()
    prod_name_lower = prod['name'].lower()
    
    # 1. Type validation
    if props['item_type'] == 'heft':
        if 'heft' not in prod_name_lower and 'hefte' not in prod_category:
            return 0.0
    elif props['item_type'] == 'schnellhefter':
        if 'schnellhefter' not in prod_name_lower:
            return 0.0
    elif props['item_type'] == 'umschlag':
        if 'umschlag' not in prod_name_lower and 'einband' not in prod_name_lower:
            return 0.0
    elif props['item_type'] == 'ordner':
        if 'ordner' not in prod_name_lower and 'ringbuch' not in prod_name_lower:
            return 0.0
    elif props['item_type'] == 'mappe':
        if 'mappe' not in prod_name_lower and 'eckspannmappe' not in prod_name_lower:
            return 0.0

    score = 0.0
    
    # 2. Size match (supporting user request "DinA soll auf DinA4 und DinA5 matchen")
    prod_size = None
    if "a4" in prod_name_clean:
        prod_size = "A4"
    elif "a5" in prod_name_clean:
        prod_size = "A5"
    elif "a3" in prod_name_clean:
        prod_size = "A3"
        
    if props['size']:
        if prod_size == props['size']:
            score += 3.0
        elif prod_size is not None:
            return 0.0
    elif props['has_generic_dina'] and props['item_type'] in ['heft', 'umschlag']:
        # If line says "DinA" generic, A4 and A5 are both valid! We give them a matching boost.
        if prod_size in ["A4", "A5"]:
            score += 2.0
            
    # 3. Color proximity check
    # Check if the associated color for this item type matches the product color
    if props['item_type'] in props['color_associations']:
        associated_color = props['color_associations'][props['item_type']]
        if associated_color in prod_name_clean or associated_color in prod_desc_clean:
            score += 5.0
        else:
            # Color mismatch for Umschlag or Schnellhefter is a strong negative
            return 0.0
            
    # 4. Lineatur match (especially for Hefte)
    if props['lineatur'] and props['item_type'] == 'heft':
        if re.search(rf'\blineatur\s*{props["lineatur"]}\b', prod_name_clean) or \
           re.search(rf'\b{props["lineatur"]}\b', prod_name_clean):
            score += 4.0
        elif re.search(rf'\blineatur\s*{props["lineatur"]}\b', prod_desc_clean) or \
             re.search(rf'\b{props["lineatur"]}\b', prod_desc_clean):
            score += 2.0
        else:
            return 0.0
            
    # 5. Ruling match
    if props['ruling']:
        if props['ruling'] in prod_name_clean or props['ruling'] in prod_desc_clean:
            score += 2.0
        else:
            if props['ruling'] == 'liniert' and 'kariert' in prod_name_clean:
                return 0.0
            if props['ruling'] == 'kariert' and 'liniert' in prod_name_clean:
                return 0.0

    # 6. Fuzzy match score
    fuzzy_sim = get_token_set_ratio(props['compare_str'], combined_prod_text)
    score += fuzzy_sim / 20.0
    
    return score

def main():
    pdf_dir = "data/downloads"
    print(f"Extracting lines from PDFs in {pdf_dir}...")
    lines = extract_all_lines(pdf_dir)
    print(f"Extracted {len(lines)} unique lines.")
    
    products_file = "project-ds-end-to-end-v2/data/products.csv"
    if not os.path.exists(products_file):
        products_file = "data/products.csv"
    products_df = pd.read_csv(products_file)
    products = products_df.to_dict('records')
    
    optimizer = TextOptimizer()
    records = []
    
    for line in lines:
        cleaned_line = optimizer.optimize_line(line)
        props = parse_line_properties(cleaned_line)
        
        # User request: "DinA soll auf DinA4 und DinA5 matchen (für Umschläge und Hefte)"
        # So if generic dina is specified, we match BOTH product options
        matches_found = []
        for prod in products:
            s = score_product(props, prod)
            if s > 3.0:
                matches_found.append((s, prod))
                
        if matches_found:
            matches_found.sort(key=lambda x: x[0], reverse=True)
            
            if props['has_generic_dina'] and props['item_type'] in ['heft', 'umschlag']:
                best_score = matches_found[0][0]
                for score, prod in matches_found:
                    if score >= best_score - 1.5:
                        records.append({
                            "raw_line": cleaned_line,
                            "product": prod['id'],
                            "amount": props['qty']
                        })
            else:
                best_prod = matches_found[0][1]
                records.append({
                    "raw_line": cleaned_line,
                    "product": best_prod['id'],
                    "amount": props['qty']
                })
        else:
            records.append({
                "raw_line": cleaned_line,
                "product": 0,
                "amount": 0
            })
            
    out_path = "project-ds-end-to-end-v2/data/training_set.csv"
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    
    df_out = pd.DataFrame(records)
    df_out.to_csv(out_path, index=False, quoting=csv.QUOTE_ALL)
    print(f"Saved {len(records)} records to {out_path}")

if __name__ == "__main__":
    main()
