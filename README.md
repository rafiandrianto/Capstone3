<h1> Hotel Booking Cancellation Prediction </h1>

## 1. Project Overview

This project develops a machine learning solution designed to predict hotel booking cancellations, explain guest Churn drivers, and optimize proactive retention campaigns. Unmanaged hotel cancellations result in unmitigated vacant inventory and substantial lost revenue. Traditional evaluation metrics (e.g., Accuracy, F1-Score) treat all errors equally, ignoring the business reality that a **False Negative (missed cancellation)** causes far greater financial loss than a **False Positive (wasted outreach)**.

To address this, this capstone project pairs an optimized **XGBoost Pipeline** with a **Dynamic Cost-Benefit Analysis (CBA)** using scraped market rates across 5 behavioral room tiers in Portugal (Lisbon and the Algarve).

### Key Objectives:
* **Predict Cancellation Risk:** Build a robust, production-ready pipeline to classify cancellation probabilities for incoming bookings without data leakage.
* **Explain Churn Drivers:** Utilize SHAP (SHapley Additive exPlanations) values to identify the primary behavioral features influencing guest cancellation behavior.
* **Financial Impact Modeling:** Establish dynamic market pricing proxies (`estimated_adr`) to quantify revenue losses under Baseline ("Do Nothing") vs. Model Intervention scenarios.
* **Optimize Business Threshold:** Calibrate the decision threshold ($0.49$) to maximize Net Recovered Revenue and campaign Return on Investment (ROI).

## 2. Data Sources

* **Primary Hotel Booking Dataset (`data_hotel_booking_demand.csv`):** Benchmark dataset containing demand, timing, customer demographics, and anonymized room codes (`A` through `P`).
* **Scraped Market Pricing Data (`hotel_room_prices.csv`):** Web-scraped pricing dataset covering 194 unique room listings across 55 hotels in Lisbon and the Algarve. Expressed in IDR to serve as market Average Daily Rate (ADR) proxies across 5 behavioral tiers:
  * **Standard / Economy (A):** ~IDR 3.92M
  * **Select / Deluxe (D):** ~IDR 4.72M
  * **Premium Executive / Business (B, C, H):** ~IDR 5.55M
  * **Family / Group Suites (E, F, G):** ~IDR 11.61M
  * **Outliers (L, P):** ~IDR 639k

## 3. Technologies Used

* **Core Runtime & Environment:** Python 3.12, Jupyter Notebook
* **Data Manipulation & Analysis:** Pandas, NumPy
* **Data Visualization:** Matplotlib, Seaborn
* **Data Preprocessing & Feature Engineering:**
  * **Scalers & Imputers:** `scikit-learn` (`RobustScaler`, `MinMaxScaler`, `SimpleImputer`)
  * **Encoders:** `scikit-learn` (`OneHotEncoder`, `OrdinalEncoder`), `category_encoders` (`BinaryEncoder`)
  * **Feature Selection & Extraction:** `feature_engine` (`DatetimeFeatures`, `DropFeatures`), `scikit-learn` (`SelectKBest`, `ColumnTransformer`)
  * **Outlier Handling:** `feature_engine` (`Winsorizer`, `OutlierTrimmer`)
* **Class Imbalance Handling:** `imbalanced-learn` (`SMOTE`, `RandomOverSampler`, `RandomUnderSampler`, `ImbPipeline`)
* **Machine Learning Frameworks & Algorithms Evaluated:**
  * **Tree-Based Ensembles:** XGBoost (`XGBClassifier`), Random Forest, Extra Trees, Gradient Boosting, AdaBoost, Decision Tree
  * **Meta-Estimators & Bagging:** Stacking Classifier, Voting Classifier, Bagging Classifier
  * **Linear & Distance Models:** Logistic Regression, K-Nearest Neighbors (KNN)
* **Model Validation, Hyperparameter Tuning & Pipelines:**
  * `scikit-learn` (`Pipeline`, `StratifiedKFold`, `GridSearchCV`, `RandomizedSearchCV`, `cross_validate`)
* **Model Evaluation Metrics:** Precision, Recall, F1-Score, ROC-AUC, Confusion Matrix
* **Model Explainability & Serialization:** SHAP (SHapley Additive exPlanations), Pickle

---

## 4. Project Structure

```
├── README.md           <- Top-level README outlining the repository and business objectives.
├── data
│   ├── web_scrapping   <- Web scrapped hotel room prices.
│   └── raw             <- Original hotel booking dataset.
│
├── notebooks           <- Jupyter notebooks for EDA, preprocessing, model tuning, SHAP, and CBA.
│   └── models          <- Serialized XGBoost pipeline (.pkl/.joblib) and inference service wrapper.
│
├── references          <- Data dictionaries, paper citations (Nuno Antonio et al., 2018), and manual guides.
│
├── requirements.txt    <- Dependencies file for reproducing the environment.
│
└── src                 <- Modular source code for custom transformers and production inference wrappers.

```
## 5. Summary of Findings

### 5.1 Business Insights

* **Financial Revenue Recovery:** On the evaluation test set, implementing the tuned XGBoost model at a calibrated threshold of $0.48$ reduces unmitigated cancellation losses from a baseline of **IDR 29.31 Billion** down to **IDR 23.89 Billion**, preserving **IDR 5,411,962,956** in room revenue.
* **Exceptional Campaign ROI:** With an operational intervention cost of **IDR 50,000** per targeted outreach, the campaign spent **IDR 357,800,000** across 7,156 flagged bookings—yielding a **1,512.57% ROI** (returning **IDR 15.12** for every **IDR 1.00** spent).
* **Key Risk Drivers (SHAP Analysis):**
  * **Non-Refundable Deposits:** Strongest positive predictor of cancellation (+4.0 to +9.0 SHAP), driven by wholesale agency and group bookings that cancel in blocks.
  * **OTA Channels:** Online Travel Agencies exhibit higher volatility than Direct/Corporate channels due to low-friction reservation processes.
  * **Commitment Signals:** Requests for parking spaces ($\ge 1$) or special requests (pillow types, floor preferences) strongly indicate show-up intent, pushing SHAP values down to -8.0.

### 5.2 Actionable Recommendations

* **Tier-Based Retention Outreach:**
  * Allocate higher-touch retention budgets (e.g., direct calls or room upgrade vouchers) for high-ADR categories (**Family/Group Suites** and **Executive Rooms** with rates $> \text{IDR 5.5M}$).
  * Maintain low-cost automated messaging (SMS/email re-confirmation prompts) for baseline **Standard Economy** bookings to keep unit costs $\le \text{IDR } 50,000$.
* **Re-evaluate Wholesale & Deposit Policies:** Transition non-refundable agency/OTA bookings toward flexible date-modification windows rather than immediate cancellation penalties.
* **Incentivize Guest Commitment:** Encourage guests to customize their stay (parking, extra amenities) during booking, as active engagement directly correlates with confirmed check-ins.
* **Technical Maintenance:** Retrain the model quarterly to mitigate data drift, and perform live A/B testing on 50% of incoming traffic to evaluate real-world retention conversion rates.
