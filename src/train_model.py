import pandas as pd
import numpy as np
import pickle
import os

def train():
    # Load dataset and catalog
    products_path = "data/products.csv"
    baskets_path = "data/shopping_baskets.csv"
    
    if not os.path.exists(products_path) or not os.path.exists(baskets_path):
        raise FileNotFoundError("Products or shopping baskets file missing in data/")
        
    products_df = pd.read_csv(products_path)
    baskets_df = pd.read_csv(baskets_path)
    
    # Get all unique product IDs
    product_ids = sorted(products_df['id'].unique())
    num_products = len(product_ids)
    prod_id_to_idx = {pid: idx for idx, pid in enumerate(product_ids)}
    
    # Group by basket_id to build features
    print("Preparing training features...")
    grouped = baskets_df.groupby('basket_id')
    
    X_list = []
    y_list = []
    
    for basket_id, group in grouped:
        # Create a binary feature vector for this basket
        feature_vector = np.zeros(num_products, dtype=int)
        for _, row in group.iterrows():
            pid = row['product_id']
            if pid in prod_id_to_idx:
                feature_vector[prod_id_to_idx[pid]] = 1
                
        # The target label is the school year
        label = group.iloc[0]['schuljahr_label']
        
        X_list.append(feature_vector)
        y_list.append(label)
        
    X = np.array(X_list)
    y = np.array(y_list)
    
    # Train a classifier
    # Logistic Regression with L2 regularization is robust and fast for sparse binary features
    from sklearn.linear_model import LogisticRegression
    print("Training Logistic Regression classifier...")
    model = LogisticRegression(max_iter=500, random_state=42)
    model.fit(X, y)
    
    # Evaluate on training data
    train_acc = model.score(X, y)
    print(f"Training accuracy: {train_acc:.4f}")
    
    # Save the model and mappings
    model_data = {
        "model": model,
        "product_ids": product_ids,
        "prod_id_to_idx": prod_id_to_idx,
        "classes": model.classes_
    }
    
    model_path = "src/model.pkl"
    with open(model_path, "wb") as f:
        pickle.dump(model_data, f)
        
    print(f"Model successfully saved to {model_path}")

if __name__ == "__main__":
    train()
