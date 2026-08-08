import re

def parse_ocr_text(text: str) -> list:
    """
    Parses raw OCR text line by line to extract requested quantities and item names.
    Returns a list of dicts: [{'raw_text': str, 'quantity': int}]
    """
    parsed_items = []
    
    # Common bullet points and separators at the start of a line to remove
    bullet_cleanup_re = re.compile(r'^[\s\-\*\•\+\d\.\,\/]*\s*')
    
    # Patterns to match quantity at the start of a line
    # Examples: "3x Bleistift", "5 Stk. Hefte", "2 Packungen Buntstifte", "10 Geodreiecke"
    patterns = [
        # Number followed by unit/x (e.g., "3x", "3 Stk.", "3 Stück", "3 Pack.") and then text
        re.compile(r'^(\d+)\s*(?:x|X|stk\.?|Stk\.?|stück|Stück|stck\.?|Stck\.?|pack\.?|Pack\.?|pck\.?|Pck\.?|pkg\.?|Pkg\.?|packung|Packung|set|Set)?\s+(.*)$', re.IGNORECASE),
        # Number followed by separator (e.g. "3 - Hefte", "3, Hefte", "3. Hefte") and then text
        re.compile(r'^(\d+)\s*[\-\,\.\:\/]\s+(.*)$'),
        # Just a number at the start followed by space and text (e.g. "3 Hefte")
        re.compile(r'^(\d+)\s+(.*)$')
    ]

    for line in text.splitlines():
        line = line.strip()
        if not line:
            continue
            
        # Clean up leading bullet points and separators at the start (except digits)
        line = re.sub(r'^[\s\-\*\•\+\,\;\(\)]+', '', line).strip()
            
        matched = False
        for pattern in patterns:
            match = pattern.match(line)
            if match:
                qty_str, rest = match.groups()
                rest = rest.strip()
                rest = re.sub(r'^[\-\*\•\+\.\,\s]+', '', rest).strip()
                
                if rest:
                    try:
                        qty = int(qty_str)
                    except ValueError:
                        qty = 1
                    parsed_items.append({
                        "raw_text": rest,
                        "quantity": qty
                    })
                    matched = True
                    break
        
        if not matched:
            cleaned_line = re.sub(r'^[\-\*\•\+\.\,\s]+', '', line).strip()
            if cleaned_line:
                parsed_items.append({
                    "raw_text": cleaned_line,
                    "quantity": 1
                })
                
    return parsed_items
