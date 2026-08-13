import pandas as pd
import re
import os

def determine_subject(row):
    name = str(row.get('name', '')).lower()
    desc = str(row.get('description', '')).lower()
    cat = str(row.get('category', '')).lower()
    
    # 1. Mathe
    mathe_keywords = ["mathematik", "mathe", "rechnen", "rechenheft", "zirkel", "kompass", "geodreieck", "geometrie", "taschenrechner"]
    if any(k in name or k in desc for k in mathe_keywords):
        return "Mathe"
        
    # 2. Deutsch
    deutsch_keywords = ["deutsch", "schreibheft", "aufsatzheft", "geschichtenheft", "fibel", "duden", "schulwörterbuch deutsch"]
    if any(k in name or k in desc for k in deutsch_keywords):
        return "Deutsch"
        
    # 3. Fremdsprachen
    fremd_keywords = ["vokabelheft", "fremdsprache", "englisch", "französisch", "schulwörterbuch englisch"]
    if any(k in name or k in desc for k in fremd_keywords):
        return "Fremdsprachen"
        
    # 4. Kunst
    kunst_keywords = ["kunst", "malen", "zeichnen", "zeichenblock", "tuschkasten", "pinsel", "wasserfarben", "malkittel", "wachsmalstifte", "fasermaler", "buntstifte"]
    if any(k in name or k in desc for k in kunst_keywords) or cat == "malen & zeichnen":
        return "Kunst"
        
    # 5. Musik
    musik_keywords = ["musik", "notenheft", "noten"]
    if any(k in name or k in desc for k in musik_keywords):
        return "Musik"
        
    return "Allgemein"

def determine_level(row):
    desc = str(row.get('description', '')).lower()
    name = str(row.get('name', '')).lower()
    
    # Search in description
    match_range = re.search(r'klasse\s*(\d+)\s*[-–]\s*(\d+)', desc)
    if match_range:
        return f"{match_range.group(1)}-{match_range.group(2)}"
        
    match_plus = re.search(r'klasse\s*(\d+)\s*\+', desc)
    if match_plus:
        return f"{match_plus.group(1)}+"
        
    match_single = re.search(r'klasse\s*(\d+)', desc)
    if match_single:
        return match_single.group(1)
        
    if "grundschule" in desc or "grundschule" in name:
        return "1-4"
        
    return "Allgemein"

if __name__ == "__main__":
    csv_path = "data/products.csv"
    if os.path.exists(csv_path):
        df = pd.read_csv(csv_path)
        df['subject'] = df.apply(determine_subject, axis=1)
        df['level'] = df.apply(determine_level, axis=1)
        
        # Save back
        df.to_csv(csv_path, index=False)
        print("Successfully updated products.csv with subject and level columns!")
        
        # Display some value distributions
        print("\nSubject distribution:")
        print(df['subject'].value_counts())
        print("\nLevel distribution:")
        print(df['level'].value_counts())
    else:
        print(f"Error: {csv_path} not found")
