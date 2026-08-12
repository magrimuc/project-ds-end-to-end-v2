import pandas as pd
import numpy as np
import os

class Recommender:
    def __init__(self, model_path: str = "src/model.pkl", baskets_path: str = "data/shopping_baskets.csv"):
        self.baskets_df = None
        
        # Resolve paths
        if not os.path.exists(baskets_path) and os.path.exists("project-ds-end-to-end-v2/data/shopping_baskets.csv"):
            baskets_path = "project-ds-end-to-end-v2/data/shopping_baskets.csv"
            
        if os.path.exists(baskets_path):
            self.baskets_df = pd.read_csv(baskets_path)
            
    def predict_grade(self, cart_product_ids: list) -> str:
        """Predicts the grade level based on the product IDs in the cart using historical basket occurrences."""
        if self.baskets_df is None or not cart_product_ids:
            return "Unbekannt"
            
        # Filter transactions matching product IDs in cart
        matched_transactions = self.baskets_df[self.baskets_df['product_id'].isin(cart_product_ids)]
        if matched_transactions.empty:
            return "Unbekannt"
            
        # Group by grade level and find the most common one
        grade_counts = matched_transactions['schuljahr_label'].value_counts()
        if grade_counts.empty:
            return "Unbekannt"
            
        return grade_counts.index[0]
        
    def get_recommendations(self, cart_product_ids: list, top_n: int = 5) -> tuple:
        """
        Predicts the grade level, and returns the top_n most common products
        purchased for that grade level which are not currently in the cart.
        Returns a tuple: (predicted_grade, recommendations_list)
        """
        if self.baskets_df is None or not cart_product_ids:
            return "Unbekannt", []
            
        grade = self.predict_grade(cart_product_ids)
        if grade == "Unbekannt":
            return "Unbekannt", []
            
        # Filter transactions matching this grade
        grade_baskets = self.baskets_df[self.baskets_df['schuljahr_label'] == grade]
        
        # Calculate frequency of each product in this grade
        prod_counts = grade_baskets.groupby(['product_id', 'product_name']).size().reset_index(name='count')
        
        # Sort by frequency descending
        prod_counts = prod_counts.sort_values(by='count', ascending=False)
        
        # Filter out products already in the cart
        recommendations = []
        
        # Resolve products path
        products_path = "data/products.csv"
        if not os.path.exists(products_path) and os.path.exists("project-ds-end-to-end-v2/data/products.csv"):
            products_path = "project-ds-end-to-end-v2/data/products.csv"
            
        if os.path.exists(products_path):
            products_df = pd.read_csv(products_path)
            for _, row in prod_counts.iterrows():
                pid = int(row['product_id'])
                if pid not in cart_product_ids:
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
