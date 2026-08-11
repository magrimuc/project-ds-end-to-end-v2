![logo_ironhack_blue 7](https://user-images.githubusercontent.com/23629340/40541063-a07a0a8a-601a-11e8-91b5-2f13e4e6b441.png)

# End to End Data Science Project

### **Final Project**

OCR School Supply Scanner & Basket Optimization
This workflow describes the journey from capturing a physical school supply list (Scan/Photo/PDF) to preparing an optimized, ready-to-order shopping cart. The core of this workflow is a data-driven confidence and quality check designed to minimize manual adjustments for the customer.

Default Assumption: Each upload/document represents a list for exactly one child (one grade level).
Recognition Focus: Quantities are generally well-readable; the system also supports handwritten additions and corrections made directly on the document.

---

## 🗺️ Project Milestones & Concept

Here is the structured implementation roadmap for the repository, incorporating a technical sanity check for each milestone:

### 🚀 Milestone 1: Streamlit App with OCR & PDF text extraction
* **Objective:** Capture school lists through a responsive Streamlit application.
* **Routing Logic:**
  * Detect if the client is running on a mobile browser (cell phone) vs. desktop.
  * **Mobile View:** Displays a photo upload button optimized for camera snapshots, starting the image OCR workflow.
  * **Desktop View:** Renders or redirects to a dedicated PDF upload section (`/pdf`) designed for digital document uploads and text parsing.
* **Technical Check / Feasibility:** 
  * *Challenge:* Streamlit is server-side and has no native device-detection.
  * *Solution:* We will use a lightweight custom HTML/JS component inside Streamlit or read header request metadata to identify mobile User-Agents and dynamically render the corresponding upload layout.

### 🔍 Milestone 2: NLP & Fuzzy Product Matching
* **Objective:** Map unstructured OCR text lines to the canonical catalog (`products.csv`).
* **Logic:** 
  * Parse raw text to extract quantity, item name, and specs (e.g., DIN A4, Lineatur 21).
  * Use fuzzy text matching algorithms (e.g. `rapidfuzz` or Levenshtein distance) to pair noisy list items with clean database products.
* **Technical Check / Feasibility:**
  * *Challenge:* OCR text often contains spelling mistakes, abbreviations, or lacks brand details.
  * *Solution:* We combine regex-based quantity extractors with fuzzy match scoring. If the match score is below a certain threshold, the item is marked as "low-confidence" for validation.
  * products.csv engineered with typical description values
  * certain mismatches avoided by hard encoding

### 🧠 Milestone 3: Machine Learning Clustering & Recommender Engine
* **Objective:** Train a classifier/clustering model on `shopping_baskets.csv` to predict the grade level and provide automated suggestions.
* **Logic:**
  * Convert baskets into a bag-of-words binary matrix.
  * Train a classification model (e.g., Naive Bayes, Random Forest, or Logistic Regression) to predict the target grade label (e.g., "Klasse 3").
  * Recommend items commonly purchased for the predicted grade that are not yet in the uploaded cart.
* **Technical Check / Feasibility:**
  * *Challenge:* Some orders are mixed-grade (multichild).
  * *Solution:* Our classifier will predict the primary grade. If the confidence is split (e.g. 50% Klasse 1, 50% Klasse 5), we can flag it as a multi-child order and recommend packages for both.

### 🛒 Milestone 4: Interactive Cart UI & Recommendations
* **Objective:** Render the shopping cart with extracted products, and display a list of recommended add-ons for the predicted grade.
* **Logic:**
  * Show matched products and quantities.
  * List the top 3-5 recommended items for that grade.
  * Include a simple "+" button next to each suggestion to add it to the cart with one click.

### 💳 Milestone 5: Checkout Integration & language en
* **Objective:** Prepare checkout or order dispatch.
* **Logic:**
  * Add support for exporting the shopping cart to external platforms (e.g., Rainforest/Amazon API, RapidAPI, Wolt) or formatting a PDF/email order list to send to local stationery shops.
