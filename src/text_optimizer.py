import re

class TextOptimizer:
    def __init__(self):
        # Spelling corrections for colors and key terms
        self.replacements = [
            # Normalize dinas/dinat OCR errors
            (r'(?i)\bdinas\b', 'din a5'),
            (r'(?i)\bdin\s+as\b', 'din a5'),
            (r'(?i)\bdinat\b', 'din a4'),
            (r'(?i)\bdin\s+at\b', 'din a4'),
            
            # Normalize sizes
            (r'(?i)\b(?:din\s*)?a\s*([345])\b', r'DIN A\1'),
            (r'(?i)\bdina([345])\b', r'DIN A\1'),
            
            # Correct common misspellings of Lineatur and consume trailing dots
            (r'(?i)\b(lin[ei]at[ur]+|liniatur|linatur|lineatr|lin)\b\.?', 'Lineatur'),
            
            # Normalize colors
            (r'(?i)\b(rt|rot)\b', 'rot'),
            (r'(?i)\b(grün|gruen|grun|gn)\b', 'grün'),
            (r'(?i)\b(lila|violett)\b', 'lila'),
            (r'(?i)\b(weiß|weiss|weiB|ws)\b', 'weiß'),
            (r'(?i)\b(schwarz|sw)\b', 'schwarz'),
            (r'(?i)\b(orange|or)\b', 'orange'),
            (r'(?i)\b(gelb|gb)\b', 'gelb'),
            (r'(?i)\b(blau|bl)\b', 'blau'),
            (r'(?i)\bhell\s*blau\b', 'hellblau'),
            (r'(?i)\bdunkel\s*blau\b', 'dunkelblau'),
            (r'(?i)\btrans\w*\b', 'transparent'),
            
            # Normalize Rand specifications
            (r'(?i)\bm\.?\s*r\.?\b', 'mit Rand'),
            (r'(?i)\bo\.?\s*r\.?\b', 'ohne Rand'),
            (r'(?i)\bmit\s+rand\b', 'mit Rand'),
            (r'(?i)\bohne\s+rand\b', 'ohne Rand'),
            (r'(?i)\b(?:mit\s+)?doppel\s*rand\b', 'mit Doppelrand'),
        ]

    def optimize_line(self, line: str) -> str:
        """
        Optimizes a single line of OCR text using rule-based enhancements.
        """
        # Save quantity if it's there (e.g. "3x ", "2 ")
        qty_match = re.match(
            r'^(\s*\d+\s*(?:x|X|stk\.?|Stk\.?|stück|Stück|stck\.?|Stck\.?|pack\.?|Pack\.?|pck\.?|Pck\.?|pkg\.?|Pkg\.?|packung|Packung|set|Set)?\s+)(.*)$',
            line,
            re.IGNORECASE
        )
        if qty_match:
            prefix = qty_match.group(1)
            content = qty_match.group(2)
        else:
            prefix = ""
            content = line

        # Apply basic replacements/corrections first
        for pattern, replacement in self.replacements:
            content = re.sub(pattern, replacement, content)

        content_lower = content.lower()

        # Rule 1: Hefte (Lineatur 1-53, DIN A4/A5, Rand)
        is_heft = any(k in content_lower for k in ["heft", "hefte", "schulheft", "schreibheft", "vokabelheft", "rechenheft", "hausaufgabenheft"])
        if is_heft:
            # Check if DIN A4 or DIN A5 is present. Default to DIN A4 if not specified but Heft.
            if "DIN A5" not in content and "DIN A4" not in content:
                # Try to search if "A5" or "A4" was captured as single characters
                if "5" in content:
                    content += " DIN A5"
                else:
                    content += " DIN A4"  # default
            
            # Check for Lineatur number
            has_lineatur_word = "Lineatur" in content
            if not has_lineatur_word:
                # Look for a number that is not DIN size or sheet counts (Blatt)
                text_without_din = re.sub(r'DIN\s*A\d', '', content)
                num_without_din_match = re.search(
                    r'\b(5[0-3]|[1-4]\d|[1-9])\b(?!\s*(?:blatt|bl\.?|stk\.?|stück|x|set|packung))',
                    text_without_din,
                    re.IGNORECASE
                )
                if num_without_din_match:
                    num_val = num_without_din_match.group(1)
                    content = re.sub(rf'\b{num_val}\b', f'Lineatur {num_val}', content, count=1)
            
            # Check for Rand
            if "mit Rand" not in content and "ohne Rand" not in content and "mit Doppelrand" not in content:
                # Default behavior: if no Rand info is there, check common patterns or do nothing to avoid hallucinating
                pass

        # Rule 2: Umschlag / Einband (DIN A4/A5, Color)
        is_umschlag = any(k in content_lower for k in ["umschlag", "einband", "heftumschlag", "schoner", "heftschoner", "hefteinband"])
        if is_umschlag:
            # Ensure "Umschlag" or "Einband" is clean
            if not any(k in content for k in ["Umschlag", "Einband"]):
                content = "Umschlag " + content
            # Ensure DIN size A4 or A5 is present
            if "DIN A5" not in content and "DIN A4" not in content:
                if "5" in content:
                    content += " DIN A5"
                else:
                    content += " DIN A4"

        # Rule 3: Schnellhefter / Ordner (DIN A4/A3, Color)
        is_hefter = any(k in content_lower for k in ["schnellhefter", "hefter", "ordner", "ringbuch", "pappschnellhefter"])
        if is_hefter:
            # Ensure "Schnellhefter" is formatted
            if "Schnellhefter" not in content and "Ordner" not in content:
                content = "Schnellhefter " + content
            if "DIN A4" not in content and "DIN A3" not in content:
                if "3" in content:
                    content += " DIN A3"
                else:
                    content += " DIN A4"

        # Rule 4: Dokumentenmappe / Eckspannmappe
        is_mappe = any(k in content_lower for k in ["mappe", "eckspannmappe", "dokumentenmappe", "sammelmappe"])
        if is_mappe:
            if "Eckspannmappe" not in content and "Sammelmappe" not in content and "Dokumentenmappe" not in content:
                content = "Eckspannmappe " + content

        # Clean up any extra whitespaces and trailing dots on keywords if they were captured
        content = " ".join(content.split())
        return prefix + content

    def optimize(self, text: str) -> str:
        """
        Optimizes a multi-line OCR text block.
        """
        if not text:
            return ""
        optimized_lines = []
        for line in text.splitlines():
            cleaned = line.strip()
            if cleaned:
                optimized_lines.append(self.optimize_line(cleaned))
        return "\n".join(optimized_lines)
