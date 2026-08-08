import pickle
import pandas as pd
import numpy as np
import os

class Recommender:
    def __init__(self, model_path: str = "src/model.pkl", baskets_path: str = "data/shopping_baskets.csv"):
        self.model_data = None
        self.baskets_df = None
        
        if os.path.exists(model_path):
            with open(model_path, "rb") as f:
                self.model_data = pickle.load(f)
                
        if os.path.exists(baskets_path):
            self.baskets_df = pd.read_csv(baskets_path)
            
    def predict_grade(self, cart_product_ids: list) -> str:
        """Predicts the grade level based on the product IDs in the cart."""
        if not self.model_data or not cart_product_ids:
            return "Unbekannt"
            
        model = self.model_data["model"]
        prod_id_to_idx = self.model_data["prod_id_to_idx"]
        num_products = len(self.model_data["product_ids"])
        
        # Build binary feature vector
        x = np.zeros(num_products)
        for pid in cart_product_ids:
            if pid in prod_id_to_idx:
                x[prod_id_to_idx[pid]] = 1
                
        # Reshape for single sample prediction
        x = x.reshape(1, -1)
        pred_label = model.predict(x)[0]
        return pred_label
        
    def get_recommendations(self, cart_product_ids: list, top_n: int = 5) -> list:
        """
        Predicts the grade level, and returns the top_n most common products
        purchased for that grade level which are not currently in the cart.
        Returns a list of dicts: [{'product_id': int, 'name': str, 'brand': str, 'price': float, 'frequency': int}]
        """
        if self.baskets_df is None or not cart_product_ids:
            return []
            
        grade = self.predict_grade(cart_product_ids)
        if grade == "Unbekannt":
            return []
            
        # Filter transactions matching this grade
        grade_baskets = self.baskets_df[self.baskets_df['schuljahr_label'] == grade]
        
        # Calculate frequency of each product in this grade
        prod_counts = grade_baskets.groupby(['product_id', 'product_name']).size().reset_index(name='count')
        
        # Sort by frequency descending
        prod_counts = prod_counts.sort_values(by='count', ascending=False)
        
        # Filter out products already in the cart
        recommendations = []
        for _, row in prod_counts.iterrows():
            pid = int(row['product_id'])
            if pid not in cart_product_ids:
                # Fetch price and brand from products.csv
                products_path = "data/products.csv"
                if os.path.exists(products_path):
                    products_df = pd.read_csv(products_path)
                    prod_info = products_df[products_df['id'] == pid]
                    if not prod_info.empty:
                        info = prod_info.iloc[0]
                        recommendations.append({
                            "product_id": pid,
                            "name": info['name'],
                            "brand": info['brand'],
                            "price": float(info['price']),
                            "frequency": int(row['count'])
                        })
                        
            if len(recommendations) >= top_n:
                break
                
        return grade, recommendations
