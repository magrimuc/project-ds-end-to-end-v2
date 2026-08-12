import os
import pytest
from src.matcher import load_products, find_best_match, get_similarity_score

@pytest.fixture
def products():
    # Relative path from project root
    csv_path = os.path.join("data", "products.csv")
    return load_products(csv_path)

def test_load_products(products):
    assert len(products) > 0
    assert "id" in products[0]
    assert "name" in products[0]

def test_find_best_match_perfect(products):
    match = find_best_match("Schulheft A4 liniert Brunnen", products)
    assert match is not None
    assert match["product_id"] in [1002, 1042]

def test_find_best_match_partial(products):
    match = find_best_match("Bleistift Faber", products)
    assert match is not None
    assert match["product_id"] == 1004

def test_no_match(products):
    match = find_best_match("XYZ Unbekannter Artikel", products, threshold=0.5)
    assert match is None

def test_heft_schnellhefter_separation(products):
    # Heft queries should NOT match Schnellhefter products
    score = get_similarity_score("heft", "schnellhefter")
    assert score == 0.0
    
    score_papp = get_similarity_score("heft", "pappschnellhefter")
    assert score_papp == 0.0

def test_pappschnellhefter_matches_schnellhefter(products):
    # Pappschnellhefter query should match a Schnellhefter product
    match = find_best_match("Pappschnellhefter", products)
    assert match is not None
    assert "schnellhefter" in match["name"].lower()

def test_description_matches(products):
    # Query "Regelheft" should match Heft liniert Lineatur 27 (1044)
    match_regel = find_best_match("Regelheft", products)
    assert match_regel is not None
    assert match_regel["product_id"] == 1044

    # Query "Mitteilungsheft" should match Heft DIN A5 liniert Lineatur 3 or 4
    match_mitteilung = find_best_match("Mitteilungsheft", products)
    assert match_mitteilung is not None
    assert "mitteilungsheft" in [p["description"].lower() for p in products if p["id"] == match_mitteilung["product_id"]][0]

    # Query "Schreiblernheft" should match Heft DIN A5 liniert Lineatur 1 (1034)
    match_schreib = find_best_match("Schreiblernheft", products)
    assert match_schreib is not None
    assert match_schreib["product_id"] == 1034

    # Query "Hausheft" or "Deutsch" should match default Heft (1001 or 1002)
    match_haus = find_best_match("Hausheft", products)
    assert match_haus is not None
