import pandas as pd
import pickle
import os
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import make_pipeline

def train():
    # Load mapped data and catalog
    mapped_path = "data/pdf_lines_mapped.csv"
    if not os.path.exists(mapped_path):
        mapped_path = "project-ds-end-to-end-v2/data/pdf_lines_mapped.csv"
        
    products_path = "data/products.csv"
    if not os.path.exists(products_path):
        products_path = "project-ds-end-to-end-v2/data/products.csv"
        
    if not os.path.exists(mapped_path):
        raise FileNotFoundError(f"Mapped lines file missing: {mapped_path}")
    if not os.path.exists(products_path):
        raise FileNotFoundError(f"Products file missing: {products_path}")
        
    df_mapped = pd.read_csv(mapped_path)
    
    # Fill NAs
    df_mapped['raw_line'] = df_mapped['raw_line'].fillna("")
    
    # Filter out empty lines
    df_mapped = df_mapped[df_mapped['raw_line'].str.strip() != ""]
    
    X = df_mapped['raw_line'].values
    y = df_mapped['product_id'].values
    
    print(f"Training on {len(X)} samples with {len(set(y))} unique product IDs...")
    
    # Use character n-grams to be extremely robust to OCR spelling errors
    vectorizer = TfidfVectorizer(
        analyzer='char_wb',
        ngram_range=(3, 6),
        min_df=1,
        sublinear_tf=True
    )
    
    classifier = LogisticRegression(
        C=20.0,
        class_weight='balanced',
        max_iter=2000,
        random_state=42
    )
    
    pipeline = make_pipeline(vectorizer, classifier)
    pipeline.fit(X, y)
    
    # Evaluate
    train_acc = pipeline.score(X, y)
    print(f"Training Accuracy: {train_acc:.4f}")
    
    # Save the model
    model_data = {
        "pipeline": pipeline,
        "classes": classifier.classes_
    }
    
    model_path = "src/model.pkl"
    if not os.path.exists("src") and os.path.exists("project-ds-end-to-end-v2/src"):
        model_path = "project-ds-end-to-end-v2/src/model.pkl"
        
    with open(model_path, "wb") as f:
        pickle.dump(model_data, f)
        
    print(f"Model successfully saved to {model_path}")

if __name__ == "__main__":
    train()
