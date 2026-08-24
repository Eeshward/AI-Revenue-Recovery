"""
ReviveAI - Synthetic Payment Dataset Generator-----------------------------------------------
Generates a realistic synthetic merchant transaction dataset that mimics
the kind of data a payment gateway (e.g. Razorpay) would have available
for revenue-recovery modelling.
Run directly to create data/transactions.csv:
    python data/generate_data.py
"""
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
import random
RANDOM_SEED = 42
np.random.seed(RANDOM_SEED)
random.seed(RANDOM_SEED)
PAYMENT_METHODS = ["Credit Card", "Debit Card", "UPI", "Netbanking", "Wallet"]
FAILURE_REASONS = [
    "Insufficient Funds",
    "Bank Server Timeout",
    "Card Declined",
    "Network Error",
    "Incorrect OTP",
    "Customer Abandoned Checkout",
    "Bank Server Down",
    "Fraud Risk Flag",
    "None",  # for successful transactions
]
STATUS_OPTIONS = ["Success", "Failed", "Abandoned"]
def _pick_failure_reason(status: str) -> str:
    if status == "Success":
        return "None"
    if status == "Abandoned":
        return "Customer Abandoned Checkout"
    # Failed
    reasons = [r for r in FAILURE_REASONS if r not in ("None", "Customer Abandoned Checkout")]
    weights = [0.28, 0.18, 0.20, 0.14, 0.08, 0.07, 0.05]
    return random.choices(reasons, weights=weights, k=1)[0]
def _recoverability_bias(failure_reason: str) -> float:
    """Base probability that a failed/abandoned transaction is recoverable,
    driven by the underlying failure cause (temporary vs permanent)."""
    mapping = {
        "Bank Server Timeout": 0.78,
        "Network Error": 0.75,
        "Bank Server Down": 0.70,
        "Incorrect OTP": 0.55,
        "Customer Abandoned Checkout": 0.45,
        "Insufficient Funds": 0.35,
        "Card Declined": 0.25,
        "Fraud Risk Flag": 0.05,
        "None": 0.0,
    }
    return mapping.get(failure_reason, 0.3)
def generate_dataset(n_rows: int = 6000) -> pd.DataFrame:
    rows = []
    start_date = datetime(2025, 1, 1)
    for i in range(n_rows):
        txn_id = f"TXN{100000 + i}"
        amount = round(float(np.random.lognormal(mean=7.0, sigma=1.0)), 2)
        amount = max(50.0, min(amount, 250000.0))  # clip to realistic range
        payment_method = random.choices(
            PAYMENT_METHODS, weights=[0.28, 0.20, 0.32, 0.12, 0.08], k=1
        )[0]
        status = random.choices(STATUS_OPTIONS, weights=[0.72, 0.19, 0.09], k=1)[0]
        failure_reason = _pick_failure_reason(status)
        retry_count = 0
        if status != "Success":
            retry_count = np.random.poisson(1.2)
            retry_count = int(min(retry_count, 5))
        customer_payment_history = int(np.random.poisson(6))  # past successful payments
        customer_value = round(float(np.random.gamma(shape=2.0, scale=4000)), 2)  # lifetime value \
     proxy
        checkout_duration_sec = int(np.random.exponential(scale=45)) + 5
        subscription_status = random.choices(
            ["Subscriber", "One-Time"], weights=[0.35, 0.65], k=1
        )[0]
        txn_time = start_date + timedelta(
            days=random.randint(0, 210),
            hours=random.randint(0, 23),
            minutes=random.randint(0, 59),
        )
        # Previous recovery outcome (label for supervised learning) only meaningful
        # for non-success transactions; success rows are recovery-irrelevant (recovered=NA)
        recovered = 0
        if status != "Success":
            base_p = _recoverability_bias(failure_reason)
            # Adjust probability using contextual signals
            p = base_p
            p += 0.05 if subscription_status == "Subscriber" else 0
            p += 0.05 if customer_payment_history >= 5 else -0.05
            p += 0.04 if retry_count <= 2 else -0.08
            p += 0.03 if checkout_duration_sec < 60 else -0.02
            p -= 0.10 if amount > 50000 else 0
            p = float(np.clip(p, 0.02, 0.95))
            recovered = int(np.random.rand() < p)
        rows.append(
            {
                "transaction_id": txn_id,
                "transaction_time": txn_time.strftime("%Y-%m-%d %H:%M:%S"),
                "amount": amount,
                "payment_method": payment_method,
                "payment_status": status,
                "failure_reason": failure_reason,
                "retry_count": retry_count,
                "customer_payment_history": customer_payment_history,
                "customer_value": customer_value,
                "checkout_duration_sec": checkout_duration_sec,
                "subscription_status": subscription_status,
                "previous_recovery_outcome": recovered,
            }
        )
    df = pd.DataFrame(rows)
    return df
if __name__ == "__main__":
    df = generate_dataset()
    df.to_csv("data/transactions.csv", index=False)
    print(f"Generated {len(df)} synthetic transactions -> data/transactions.csv")
    print(df["payment_status"].value_counts())
