import os
import pytest
from src.matcher import load_products, find_best_match, split_by_colors

@pytest.fixture
def products():
    # Load products catalog
    csv_path = os.path.join("data", "products.csv")
    return load_products(csv_path)

def test_nlp_matching_robustness(products):
    # Test matching on slightly modified/noisy list lines
    match_heft = find_best_match("Schulheft A5 Lin 2 mit Kontrast", products)
    assert match_heft is not None
    assert match_heft["product_id"] == 1035  # Lineatur 2 mit Kontrast
    
    match_umschlag = find_best_match("Umschlag rt dina5", products)
    assert match_umschlag is not None
    assert match_umschlag["product_id"] == 1025  # Umschlag rot A5
    
    match_bleistift = find_best_match("Bleistift Faber-Castell", products)
    assert bleistift_ok(match_bleistift)
    
def bleistift_ok(m):
    return m is not None and m["product_id"] == 1004

def test_split_by_colors(products):
    # Line mentioning 3 colors
    text = "4 Schnellhefter (rot, blau, grün)"
    base_match = find_best_match(text, products)
    
    splits = split_by_colors(text, 4, base_match, products)
    assert len(splits) == 3
    
    # Verify we got a red (1016), blue (1015) and green (1017) Schnellhefter A4
    product_ids = [s["product_id"] for s in splits]
    assert 1016 in product_ids
    assert 1015 in product_ids
    assert 1017 in product_ids
    for s in splits:
        assert s["quantity"] == 1

