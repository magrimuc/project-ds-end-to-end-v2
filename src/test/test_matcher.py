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
    match = find_best_match("Schulheft A4 kariert Brunnen", products)
    assert match is not None
    assert match["product_id"] == 1001
    assert match["high_confidence"] is True

def test_find_best_match_partial(products):
    match = find_best_match("Bleistift Faber", products)
    assert match is not None
    assert match["product_id"] == 1004

def test_no_match(products):
    match = find_best_match("XYZ Unbekannter Artikel", products, threshold=0.5)
    assert match is None
