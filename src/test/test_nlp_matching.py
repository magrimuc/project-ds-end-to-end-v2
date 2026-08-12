import os
import pytest
from src.matcher import load_products, find_best_match

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
    assert match_bleistift is not None
    assert match_bleistift["product_id"] == 1004  # Bleistift HB Grip 2001
