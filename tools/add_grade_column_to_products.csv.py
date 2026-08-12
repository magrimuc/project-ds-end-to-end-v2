import pandas as pd
import re
import os

# --- 1. Datei laden ---
csv_path = "data/products.csv"  # Passen Sie den Pfad ggf. an
df = pd.read_csv(csv_path)

# --- 2. Mapping-Logik: Welche Klasse empfiehlt welches Produkt? ---

def map_grade(product_name: str) -> str:
    """
    Gibt zurück: '1-2', '3-4', '5-10' oder 'alle'
    """
    name = str(product_name).lower().strip()
    
    # --- A) Lineatur-Erkennung (häufigster Fall) ---
    # Suche nach "Lineatur X" oder "Lineatur X+" oder "Lineatur X/Y"
    lineatur_match = re.search(r'lineatur\s*([0-9]+)', name)
    if lineatur_match:
        num = int(lineatur_match.group(1))
        if num <= 2:
            return '1-2'
        elif num <= 4:
            return '3-4'
        else:
            return '5-10'
    
    # --- B) Spezifische Schulfächer / Materialien nach Klassenstufe ---
    # Unterstufe (1-2): Leseanfänger, große Kästchen
    if any(keyword in name for keyword in ['gitter', 'häuschen', 'abc', 'buchstaben']):
        return '1-2'
    
    # Mittelstufe (3-4): Bruchrechnen, Schreibschrift
    if any(keyword in name for keyword in ['zirkel', 'geodreieck', 'bruch', 'tintenpatrone', 'füller']):
        return '3-4'
    
    # Oberstufe (5-10): Feinmechanik, komplexe Geometrie
    if any(keyword in name for keyword in ['lineal 50', 'winkelmesser', 'dynamo', 'facharbeit']):
        return '5-10'
    
    # --- C) Universelle Produkte (Standard für alle) ---
    universelle_keywords = [
        'bleistift', 'radiergummi', 'spitzer', 'heft', 'block', 'mappe',
        'ordner', 'schnellhefter', 'decke', 'turnbeutel', 'wasserflasche',
        'schere', 'kleber', 'stift', 'filzstift', 'buntstift', 'druckbleistift'
    ]
    if any(keyword in name for keyword in universelle_keywords):
        return 'alle'
    
    # --- D) Fallback: Wenn nichts zutrifft, standardmäßig "alle" ---
    # (besser, als das Produkt auszuschließen)
    return 'alle'


# --- 3. Neue Spalte anwenden ---
df['empfohlene_klasse'] = df['name'].apply(map_grade)  # 'name' ist euer Produktnamen-Spaltenname
# Falls Ihre CSV anders heißt (z.B. 'product_name' oder 'Artikel'), passen Sie die Spalte an.

# --- 4. Optional: Statistik anzeigen ---
print("Verteilung der empfohlenen Klassen:")
print(df['empfohlene_klasse'].value_counts())

# --- 5. Speichern ---
output_path = "data/products_with_grade.csv"
df.to_csv(output_path, index=False, encoding='utf-8')
print(f"✅ Neue CSV gespeichert unter: {output_path}")

# --- 6. Alte Datei überschreiben (optional - nur nach Prüfung!) ---
# Überschreiben Sie die alte Datei nur, wenn die Statistik plausibel aussieht.
# df.to_csv(csv_path, index=False, encoding='utf-8')