import os
import re
import pandas as pd
import pypdf
import difflib

def clean_text(text: str) -> str:
    """Cleans text for better comparison."""
    text = text.lower()
    text = re.sub(r'dina(\d)', r'din a\1', text)
    text = re.sub(r'\b(lin[ei]at[ur]+|liniatur|linatur|lineatr|lin)\b\.?', 'lineatur', text)
    text = re.sub(r'[^a-z0-9\säöüß]', ' ', text)
    return " ".join(text.split())

def extract_unique_lines(pdf_dir: str) -> list:
    """Extracts all unique non-empty lines from the PDFs in the directory."""
    unique_lines = set()
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
                                unique_lines.add(line)
            except Exception as e:
                print(f"Error reading {f}: {e}")
    return sorted(list(unique_lines))

def parse_line_properties(line: str):
    """Parses a text line to extract properties like quantity, size, color, lineatur, ruling."""
    clean_line = clean_text(line)
    
    # 1. Quantity extraction
    qty = 1
    qty_match = re.match(
        r'^(\d+)\s*(?:x|stk\.?|stück|stck\.?|pack\.?|pck\.?|pkg\.?|packung|set)?\s', 
        clean_line
    )
    if qty_match:
        qty = int(qty_match.group(1))
        compare_str = clean_line[qty_match.end():].strip()
    else:
        qty_internal = re.search(r'\b(\d+)\s*(?:x|stk\.?|stück|stck\.?|pack\.?|pck\.?|pkg\.?|packung|set)\b', clean_line)
        if qty_internal:
            qty = int(qty_internal.group(1))
        compare_str = clean_line

    # 2. Size extraction
    size = None
    if "din a4" in compare_str or "a4" in compare_str:
        size = "A4"
    elif "din a5" in compare_str or "a5" in compare_str:
        size = "A5"
    elif "din a3" in compare_str or "a3" in compare_str:
        size = "A3"
        
    # 3. Color extraction
    colors = ["rot", "blau", "grün", "gelb", "weiß", "lila", "schwarz", "transparent", "hellblau", "dunkelblau", "orange"]
    found_colors = []
    for c in colors:
        if re.search(rf'\b{c}\b', compare_str):
            found_colors.append(c)
            
    # 4. Ruling type (liniert, kariert, blanko)
    ruling = None
    if "liniert" in compare_str or "lin" in compare_str:
        ruling = "liniert"
    elif "kariert" in compare_str or "kar" in compare_str:
        ruling = "kariert"
    elif "blanko" in compare_str or "ohne linien" in compare_str:
        ruling = "blanko"
        
    # 5. Lineatur number
    lineatur = None
    lineatur_match = re.search(r'lineatur\s*(\d+[a-z]?)', compare_str)
    if lineatur_match:
        lineatur = lineatur_match.group(1)
    else:
        nums = re.findall(r'\b(\d+)\b', compare_str)
        for num in nums:
            if num not in ["3", "4", "5", "30", "12", "16", "32", "80", "20", "15", "100"]:
                lineatur = num
                break
                
    # 6. Type detection (category keywords)
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
            
    return {
        "compare_str": compare_str,
        "qty": qty,
        "size": size,
        "colors": found_colors,
        "ruling": ruling,
        "lineatur": lineatur,
        "item_type": item_type
    }

def get_token_set_ratio(s1: str, s2: str) -> float:
    """Computes a token set ratio similarity score (similar to rapidfuzz)."""
    words1 = set(s1.split())
    words2 = set(s2.split())
    if not words1 or not words2:
        return 0.0
    intersection = words1.intersection(words2)
    diff1 = words1 - words2
    diff2 = words2 - words1
    
    # Sort and reconstruct strings
    sorted_inter = sorted(list(intersection))
    sorted_d1 = sorted(list(diff1))
    sorted_d2 = sorted(list(diff2))
    
    t0 = " ".join(sorted_inter).strip()
    t1 = (" ".join(sorted_inter) + " " + " ".join(sorted_d1)).strip()
    t2 = (" ".join(sorted_inter) + " " + " ".join(sorted_d2)).strip()
    
    r0 = difflib.SequenceMatcher(None, t0, t1).ratio() if t0 else 0.0
    r1 = difflib.SequenceMatcher(None, t0, t2).ratio() if t0 else 0.0
    r2 = difflib.SequenceMatcher(None, t1, t2).ratio()
    return max(r0, r1, r2) * 100.0

def score_product(props, prod):
    """Calculates a match score between line properties and a product dict."""
    prod_name_clean = clean_text(prod['name'])
    prod_desc_clean = clean_text(str(prod.get('description', '')))
    combined_prod_text = f"{prod_name_clean} {prod_desc_clean}"
    
    # 1. Type validation:
    prod_category = str(prod['category']).lower()
    prod_name_lower = prod['name'].lower()
    
    # Verify heft
    if props['item_type'] == 'heft':
        if 'heft' not in prod_name_lower and 'hefte' not in prod_category:
            return 0.0
    # Verify schnellhefter vs heft
    if props['item_type'] == 'schnellhefter' and 'schnellhefter' not in prod_name_lower:
        return 0.0
    if props['item_type'] == 'umschlag' and 'umschlag' not in prod_name_lower and 'einband' not in prod_name_lower:
        return 0.0
    if props['item_type'] == 'ordner' and 'ordner' not in prod_name_lower and 'ringbuch' not in prod_name_lower:
        return 0.0
    if props['item_type'] == 'mappe' and 'mappe' not in prod_name_lower and 'eckspannmappe' not in prod_name_lower:
        return 0.0

    score = 0.0
    
    # 2. Size match
    if props['size']:
        prod_size = None
        if "a4" in prod_name_clean:
            prod_size = "A4"
        elif "a5" in prod_name_clean:
            prod_size = "A5"
        elif "a3" in prod_name_clean:
            prod_size = "A3"
            
        if prod_size == props['size']:
            score += 3.0
        elif prod_size is not None:
            return 0.0

    # 3. Lineatur match (especially for Hefte)
    if props['lineatur'] and props['item_type'] == 'heft':
        if re.search(rf'\blineatur\s*{props["lineatur"]}\b', prod_name_clean) or \
           re.search(rf'\b{props["lineatur"]}\b', prod_name_clean):
            score += 4.0
        elif re.search(rf'\blineatur\s*{props["lineatur"]}\b', prod_desc_clean) or \
             re.search(rf'\b{props["lineatur"]}\b', prod_desc_clean):
            score += 2.0
        else:
            return 0.0
            
    # 4. Ruling match
    if props['ruling']:
        if props['ruling'] in prod_name_clean or props['ruling'] in prod_desc_clean:
            score += 2.0
        else:
            if props['ruling'] == 'liniert' and 'kariert' in prod_name_clean:
                return 0.0
            if props['ruling'] == 'kariert' and 'liniert' in prod_name_clean:
                return 0.0

    # 5. Fuzzy match score
    fuzzy_sim = get_token_set_ratio(props['compare_str'], combined_prod_text)
    score += fuzzy_sim / 20.0
    
    return score

def main():
    pdf_dir = "data/input32/downloads"
    print(f"Extracting lines from PDFs in {pdf_dir}...")
    lines = extract_unique_lines(pdf_dir)
    print(f"Extracted {len(lines)} unique lines.")
    
    products_df = pd.read_csv("project-ds-end-to-end-v2/data/products.csv")
    products = products_df.to_dict('records')
    
    records = []
    
    for line in lines:
        props = parse_line_properties(line)
        
        # Determine if multiple items are requested (e.g. multiple colors)
        if len(props['colors']) > 1 and props['item_type'] in ['schnellhefter', 'umschlag', 'mappe']:
            items_to_match = []
            for col in props['colors']:
                sub_props = props.copy()
                sub_props['colors'] = [col]
                sub_props['compare_str'] = f"{props['item_type']} {col} {props['size'] or ''}"
                items_to_match.append((col, sub_props))
                
            qty_per_item = max(1, props['qty'] // len(props['colors']))
            
            for col, sub_props in items_to_match:
                best_prod = None
                best_score = 0.0
                for prod in products:
                    color_boost = 0.0
                    if col in clean_text(prod['name']) or col in clean_text(str(prod.get('description', ''))):
                        color_boost = 5.0
                        
                    s = score_product(sub_props, prod)
                    if s > 0:
                        s += color_boost
                        if s > best_score:
                            best_score = s
                            best_prod = prod
                            
                if best_prod and best_score > 3.0:
                    records.append({
                        "raw_line": line,
                        "product_id": best_prod['id'],
                        "quantity": qty_per_item
                    })
        else:
            best_prod = None
            best_score = 0.0
            
            color = props['colors'][0] if props['colors'] else None
            
            for prod in products:
                color_boost = 0.0
                if color:
                    if color in clean_text(prod['name']) or color in clean_text(str(prod.get('description', ''))):
                        color_boost = 5.0
                        
                s = score_product(props, prod)
                if s > 0:
                    s += color_boost
                    if s > best_score:
                        best_score = s
                        best_prod = prod
                        
            if best_prod and best_score > 3.0:
                records.append({
                    "raw_line": line,
                    "product_id": best_prod['id'],
                    "quantity": props['qty']
                })
            else:
                records.append({
                    "raw_line": line,
                    "product_id": 0,
                    "quantity": 0
                })
                
    df_out = pd.DataFrame(records)
    out_path = "project-ds-end-to-end-v2/data/pdf_lines_mapped.csv"
    df_out.to_csv(out_path, index=False)
    print(f"Saved {len(df_out)} mapped records to {out_path}")

if __name__ == "__main__":
    main()
