# -*- coding: utf-8 -*-
"""DeFi_CScore_predictor.ipynb

Automatically generated by Colab.

Original file is located at
    https://colab.research.google.com/drive/1gP9k7ckPEkSqFtckhGzqPod50lUBVNtg
"""

import json
import pandas as pd
import numpy as np
from datetime import datetime
from sklearn.ensemble import RandomForestRegressor
from sklearn.preprocessing import MinMaxScaler
from sklearn.model_selection import train_test_split
import joblib
import os
import zipfile

# CONFIG #
ZIP_PATH = "/content/user-wallet-transactions.json.zip"
EXTRACT_DIR = "unzipped"
JSON_FILENAME = "user-wallet-transactions.json"
MODEL_OUTPUT = "credit_score_model.pkl"
CSV_OUTPUT = "wallet_scores.csv"


# Unzip the JSON file
with zipfile.ZipFile(ZIP_PATH, 'r') as zip_ref:
    zip_ref.extractall(EXTRACT_DIR)

# Load the JSON data
json_path = os.path.join(EXTRACT_DIR, JSON_FILENAME)
with open(json_path, 'r') as f:
    transactions = json.load(f)

# Convert raw transaction list to DataFrame
df = pd.DataFrame(transactions)

# Normalize and extract necessary info
def parse_transaction(row):
    action = row['action'].lower()
    wallet = row['userWallet']
    timestamp = row['timestamp']

    try:
        amount = float(row['actionData'].get('amount', 0)) / 1e18  # Convert to base units
        price = float(row['actionData'].get('assetPriceUSD', 1))
        usd_value = amount * price
    except:
        usd_value = 0

    return pd.Series([wallet, action, timestamp, usd_value])

df_parsed = df.apply(parse_transaction, axis=1)
df_parsed.columns = ['wallet', 'action', 'timestamp', 'usd_value']

# Group by wallet and compute features
def generate_wallet_features(df_group):
    df_group = df_group.sort_values(by='timestamp')
    features = {}

    actions = df_group['action'].value_counts().to_dict()
    actions_sum = df_group.groupby('action')['usd_value'].sum().to_dict()

    features['total_deposited_usd'] = actions_sum.get('deposit', 0)
    features['total_borrowed_usd'] = actions_sum.get('borrow', 0)
    features['total_repaid_usd'] = actions_sum.get('repay', 0)
    features['net_flow_usd'] = features['total_deposited_usd'] - features['total_borrowed_usd']

    features['repayment_ratio'] = (
        features['total_repaid_usd'] / features['total_borrowed_usd']
        if features['total_borrowed_usd'] > 0 else 0
    )

    features['borrow_to_deposit_ratio'] = (
        features['total_borrowed_usd'] / features['total_deposited_usd']
        if features['total_deposited_usd'] > 0 else 0
    )

    features['num_liquidations'] = actions.get('liquidationcall', 0)
    features['num_transactions'] = len(df_group)
    features['unique_actions'] = df_group['action'].nunique()

    timestamps = df_group['timestamp'].values
    if len(timestamps) > 1:
        time_diffs = np.diff(np.sort(timestamps))
        features['avg_time_between_tx'] = np.mean(time_diffs)
        features['num_days_active'] = len(set(pd.to_datetime(timestamps, unit='s').date))
    else:
        features['avg_time_between_tx'] = 0
        features['num_days_active'] = 1

    return pd.Series(features)

wallet_features = df_parsed.groupby('wallet').apply(generate_wallet_features).fillna(0)

# Generate synthetic "true scores" for training
np.random.seed(42)
wallet_features['true_score'] = (
    1000
    - 300 * wallet_features['borrow_to_deposit_ratio']
    - 200 * wallet_features['num_liquidations']
    + 200 * wallet_features['repayment_ratio']
    + 0.01 * wallet_features['net_flow_usd']
)
wallet_features['true_score'] = wallet_features['true_score'].clip(0, 1000)

# Train/test split
X = wallet_features.drop(columns='true_score')
y = wallet_features['true_score']
X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

# Train model
model = RandomForestRegressor(n_estimators=100, random_state=42)
model.fit(X_train, y_train)

# Evaluate model
train_score = model.score(X_train, y_train)
test_score = model.score(X_test, y_test)

print(f" Training R² Score: {train_score:.4f}")
print(f" Test R² Score:     {test_score:.4f}")


# Predict credit scores
wallet_features['predicted_score'] = model.predict(X)

# Scale scores to 0–1000
scaler = MinMaxScaler(feature_range=(0, 1000))
wallet_features['final_score'] = scaler.fit_transform(wallet_features[['predicted_score']])

# Save to CSV
wallet_features[['final_score']].to_csv(CSV_OUTPUT)
print(f" Saved scores to {CSV_OUTPUT}")

# Save model
joblib.dump(model, MODEL_OUTPUT)
print(f" Model saved to {MODEL_OUTPUT}")

# Predict credit scores for all wallets
wallet_features['predicted_score'] = model.predict(X)

# Scale to 0–1000
scaler = MinMaxScaler(feature_range=(0, 1000))
wallet_features['credit_score'] = scaler.fit_transform(wallet_features[['predicted_score']])

# Reset index to include wallet addresses
wallet_scores_df = wallet_features[['credit_score']].reset_index()

# Print top wallet scores
print("\n Sample Wallet Credit Scores:")
print(wallet_scores_df.head(10).to_string(index=False))

# Save to CSV
wallet_scores_df.to_csv(CSV_OUTPUT, index=False)
print(f"\n All wallet scores saved to: {CSV_OUTPUT}")