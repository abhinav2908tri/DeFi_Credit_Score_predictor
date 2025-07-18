# DeFi_Credit_Score_predictor
Objective
Assign a credit score (0–1000) to DeFi wallets based on their transaction behavior on the Aave V2 protocol. Higher scores reflect responsible usage, while lower scores suggest riskier behavior.

Working
- Input: JSON transaction logs from Aave V2 (deposit, borrow, repay, etc.)
- Feature Engineering:
  - Total Deposited, Borrowed, Repaid (USD)
  - Repayment Ratio
  - Borrow-to-Deposit Ratio
  - Liquidation count
  - Activity metrics (frequency, diversity, duration)
- Model: RandomForestRegressor trained on synthetic scoring logic
- Output: Scaled credit scores from 0 to 1000
