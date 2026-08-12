import re
import csv

# ------------------------------------------------------------
# 1. Ihre vollständige Produktliste (ID, Name, Schlüsselwörter)
# ------------------------------------------------------------
# Hier habe ich für jedes Produkt eine Liste von Suchbegriffen hinterlegt.
# Sie können diese Liste beliebig erweitern oder anpassen.

product_keywords = {
    1001: ["heft dina4 kariert", "lineatur 22", "kariert ohne rand", "5x5mm"],
    1002: ["heft dina4 liniert", "lineatur 21", "liniert ohne rand", "abstand 10mm"],
    1003: ["vokabelheft a5", "lineatur 53", "zweispaltig", "dreispaltig"],
    1004: ["bleistift hb", "grip 2001", "hb bleistift"],
    1005: ["buntstifte 12er", "12 buntstifte", "dreikant buntstifte"],
    1006: ["radiergummi plast-clean", "radiergummi", "plastikradierer"],
    1007: ["füllfederhalter safari", "lamy safari", "füller m"],
    1008: ["tintenpatronen t10", "t10 patrone", "lamy tintenpatronen"],
    1009: ["tuschkasten k12", "deckfarbkasten 12", "wasserfarbkasten 12", "pelikan k12"],
    1010: ["borstenpinsel-set", "borstenpinsel", "borsten pinsel"],
    1011: ["geodreieck 16 cm", "geodreieck", "geo-dreieck"],
    1012: ["schulkompass", "zirkel", "kompass"],
    1013: ["collegeblock a4 kariert", "collegeblock kariert", "block a4 kariert"],
    1014: ["zeichenblock a3", "block a3", "malblock a3"],
    1015: ["schnellhefter blau", "schnellhefter a4 blau", "pappschnellhefter blau"],
    1016: ["schnellhefter rot", "schnellhefter a4 rot", "pappschnellhefter rot"],
    1017: ["schnellhefter grün", "schnellhefter a4 grün", "pappschnellhefter grün"],
    1018: ["anspitzer-dose", "spitzer dose", "triogrip"],
    1019: ["lineal 30 cm", "lineal 30cm", "langes lineal"],
    1020: ["bastelschere rund", "bastelschere rechtshänder", "schere rund"],
    1021: ["umschlag a4 rot", "einband a4 rot", "roter umschlag a4"],
    1022: ["umschlag a4 grün", "einband a4 grün", "grüner umschlag a4"],
    1023: ["umschlag a4 blau", "einband a4 blau", "blauer umschlag a4"],
    1024: ["umschlag a4 weiß", "einband a4 weiß", "weißer umschlag a4"],
    1025: ["umschlag a5 rot", "einband a5 rot", "roter umschlag a5"],
    1026: ["umschlag a5 grün", "einband a5 grün", "grüner umschlag a5"],
    1027: ["umschlag a5 blau", "einband a5 blau", "blauer umschlag a5"],
    1028: ["umschlag a5 weiß", "einband a5 weiß", "weißer umschlag a5"],
    1031: ["geschichtenheft a4", "lineatur 2g", "geschichtenheft"],
    1032: ["zeichenblock a4", "block a4 malen", "malblock a4"],
    1033: ["heft a5 lineatur 0", "schreibhäuschen", "lineatur 0"],
    1034: ["heft a5 lineatur 1", "lineatur 1 kontrast", "schreiblernheft"],
    1035: ["heft a5 lineatur 2", "lineatur 2 kontrast", "mitteilungsheft"],
    1036: ["heft a5 lineatur 3", "lineatur 3", "zwei linien"],
    1037: ["heft a5 lineatur 3r", "lineatur 3r mit rand", "rand"],
    1038: ["heft a5 lineatur 4", "lineatur 4", "abstand 10mm"],
    1039: ["heft a5 kariert lineatur 5", "lineatur 5", "kariert ohne rand a5"],
    1040: ["heft a5 kariert lineatur 7", "lineatur 7", "große kästchen 7x7"],
    1041: ["heft a5 kariert lineatur 10", "lineatur 10", "mit umrandung"],
    1042: ["heft a4 liniert lineatur 25", "lineatur 25 mit rand"],
    1043: ["heft a4 kariert lineatur 26", "lineatur 26 mit rand"],
    1044: ["heft a4 liniert lineatur 27", "lineatur 27 doppelrand"],
    1045: ["heft a4 kariert lineatur 28", "lineatur 28 doppelrand"],
    1046: ["schnellhefter weiß", "schnellhefter a4 weiß", "pappschnellhefter weiß"],
    1047: ["haarpinsel-set", "haarpinsel", "haar pinsel"],
    1048: ["block tonpapier a4", "tonpapierblock", "buntes tonpapier"],
    1049: ["eckspannmappe rot", "eckspanner rot", "sammelmappe rot"],
    1050: ["eckspannmappe blau", "eckspanner blau", "sammelmappe blau"],
    1051: ["eckspannmappe grün", "eckspanner grün", "sammelmappe grün"],
    1052: ["eckspannmappe weiß", "eckspanner weiß", "sammelmappe weiß"],
    1053: ["eckspannmappe gelb", "eckspanner gelb", "sammelmappe gelb", "postmappe gelb"],
    1054: ["schnellhefter schwarz", "schnellhefter a4 schwarz"],
    1055: ["schnellhefter lila", "schnellhefter a4 lila", "pappschnellhefter lila"],
    1056: ["heft a5 blanko", "blanko a5", "lineatur 6 a5"],
    1057: ["heft a4 blanko", "blanko a4", "lineatur 6 a4"],
    1059: ["heft a4 kariert lineatur 40", "lineatur 40 umlaufender rand"],
    1060: ["umschlag a4 hellblau", "hellblauer umschlag"],
    1061: ["umschlag a4 dunkelblau", "dunkelblauer umschlag"],
    1062: ["umschlag a4 transparent", "transparenten umschlag", "durchsichtiger umschlag"],
    1063: ["vokabelheft a5 lineatur 53", "vokabelheft zweispaltig a5"],
    1064: ["vokabelheft a4 lineatur 54", "vokabelheft dreispaltig a4"],
    1065: ["federmäppchen", "mäppchen leer", "etui"],
    1066: ["klebestift", "kleber", "klebstift", "pritt", "uhu"],
    1067: ["wachsmalstifte 12", "wachsmalstifte dick", "wachskreiden"],
    1068: ["fasermaler 10er", "fasermaler", "fineliner", "filzstifte dünn"],
    1069: ["kugelschreiber blau", "kuli blau", "kugelschreiber"],
    1070: ["hausaufgabenheft", "schulplaner", "hausaufgabenheft a5"],
    1071: ["taschenrechner", "taschenrechner wissenschaftlich", "casio"],
    1072: ["ringordner a4", "ringordner 80 mm", "4-ring-ordner"],
    1073: ["trennblätter a4", "register", "trennblätter farbig"],
    1074: ["klarsichthüllen a4", "klarsichthülle", "prospekthülle"],
    1075: ["bastelschere linkshänder", "linkshänderschere", "schere links"],
    1076: ["knetradiergummi", "knetradierer", "radiergummi knetbar"],
    1077: ["buchschoner a4", "buchschutz", "flexible hülle"],
    1078: ["malkittel", "malerkittel", "kinderschürze"],
    1079: ["notenheft", "musikheft", "notenlinien"],
    1080: ["spiralblock a4", "spiralblock kariert"],
    1081: ["haftnotizen", "post-it", "hafnotizen"],
    1082: ["karteikasten a5", "karteikasten", "lernkartei kasten"],
    1083: ["karteikarten a5", "karteikarten", "lernkartei"],
    1084: ["tintenkiller", "tintenlöscher", "korrekturschreiber"],
    1085: ["druckbleistift 0,7", "druckbleistift", "mechanical pencil"],
    1086: ["druckbleistift-minen", "minen 0,7", "ersatzminen"],
    1087: ["tintenpatronen pelikan", "pelikan 4001", "standardpatronen"],
    1088: ["füller anfänger", "pelikan twist", "einsteigerfüller"],
    1089: ["usb-stick 32gb", "usb-stick", "32 gb usb"],
    1090: ["geometrie-schablone", "schablone geometrie", "formen schablone"],
    1091: ["lineal 15 cm", "kurzes lineal", "lineal 15cm"],
    1092: ["wörterbuch duden", "schulwörterbuch", "duden grundschule"],
    1093: ["korrekturroller", "tipp-ex", "korrekturroller weiß"],
    1094: ["wasserbecher", "malbecher", "wasserbecher kunststoff"],
    1095: ["mischpalette", "palette", "farbpalette"],
    1096: ["zeichenmappe a3", "sammelmappe a3", "zeichenmappe"]
}

# Zusätzliche Spezialfälle für häufige Abkürzungen
special_mapping = {
    "lin": 1002,           # oft für liniertes Heft
    "kar": 1001,           # kariertes Heft
    "mathe": 1001,         # Matheheft meist kariert
    "deutsch": 1002,       # Deutschheft meist liniert
    "rechenheft": 1001,    # Rechenheft kariert
    "schreibheft": 1002,   # Schreibheft liniert
    "heft nr. 25": 1042,   # Lineatur 25
    "heft nr. 28": 1045,   # Lineatur 28
    "heft nr. 27": 1044,   # Lineatur 27
    "heft nr. 26": 1043,   # Lineatur 26
    "heft nr. 22": 1001,   # Lineatur 22
    "heft nr. 21": 1002,   # Lineatur 21
}

# ------------------------------------------------------------
# 2. Hilfsfunktionen
# ------------------------------------------------------------
def extract_quantity(text):
    """Extrahiert die erste Zahl aus dem Text, z.B. '2 Bleistifte' -> 2, sonst 1."""
    match = re.search(r'\b(\d+)\s*(?:x|stück|mal|paket)?\s*(?:Bleistift|Heft|Block|...)?', text, re.IGNORECASE)
    if match:
        return int(match.group(1))
    # Wenn keine Zahl, dann 1
    return 1

def find_product_id(line):
    """Versucht, die passende product_id für eine raw_line zu finden."""
    line_lower = line.lower()
    
    # 1. Spezialfälle zuerst prüfen
    for pattern, pid in special_mapping.items():
        if pattern in line_lower:
            return pid
    
    # 2. Über die Keyword-Liste
    best_match = None
    best_score = 0
    for pid, keywords in product_keywords.items():
        for kw in keywords:
            if kw in line_lower:
                # Gewichtung: längeres Keyword = höhere Trefferwahrscheinlichkeit
                score = len(kw)
                if score > best_score:
                    best_score = score
                    best_match = pid
    return best_match  # kann None sein

# ------------------------------------------------------------
# 3. Datei einlesen und verarbeiten
# ------------------------------------------------------------
input_file = "pdf_lines_mapped.csv"
output_file = "pdf_lines_mapped_filled.csv"

with open(input_file, "r", encoding="utf-8") as infile, \
     open(output_file, "w", encoding="utf-8", newline="") as outfile:

    reader = csv.reader(infile)
    writer = csv.writer(outfile)
    
    header = next(reader)  # erste Zeile ist Kopf
    writer.writerow(header)  # Kopf unverändert übernehmen
    
    for row in reader:
        raw_line = row[0]
        current_pid = row[1].strip()
        current_qty = row[2].strip()
        
        # Wenn bereits eine ID vorhanden ist, einfach übernehmen
        if current_pid != "0":
            writer.writerow(row)
            continue
        
        # Sonst: versuchen, eine ID zu finden
        new_pid = find_product_id(raw_line)
        if new_pid is None:
            # keine Zuordnung möglich -> 0 lassen
            writer.writerow(row)
            continue
        
        # Menge extrahieren
        new_qty = extract_quantity(raw_line)
        
        # Zeile aktualisieren
        row[1] = str(new_pid)
        row[2] = str(new_qty)
        writer.writerow(row)

print(f"Fertig! Die neue Datei heißt '{output_file}'.")