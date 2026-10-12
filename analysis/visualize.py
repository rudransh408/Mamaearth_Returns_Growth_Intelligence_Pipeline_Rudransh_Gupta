import pandas as pd
import matplotlib.pyplot as plt
from pathlib import Path

# Locate project folders
BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
OUTPUT_DIR = BASE_DIR / "visualizations"

OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# Load original CSV files
orders = pd.read_csv(DATA_DIR / "orders.csv")
customers = pd.read_csv(DATA_DIR / "customers.csv")
products = pd.read_csv(DATA_DIR / "products.csv")

# Standardize payment methods
orders["payment_method"] = (
    orders["payment_method"].str.strip().str.upper()
)

# Remove duplicates using the natural key
natural_key = [
    "customer_id",
    "product_id",
    "order_date",
    "quantity",
    "discount_pct",
    "payment_method",
    "rating",
    "returned",
]

orders = orders.drop_duplicates(
    subset=natural_key,
    keep="first"
).copy()

# Impute missing values
orders["discount_pct"] = orders["discount_pct"].fillna(0)
orders["rating"] = orders["rating"].fillna(orders["rating"].median())

# Merge orders with products and customers
merged = (
    orders
    .merge(products, on="product_id", how="left")
    .merge(customers, on="customer_id", how="left")
)

# Calculate order value
merged["order_value"] = (
    merged["quantity"]
    * merged["price"]
    * (1 - merged["discount_pct"] / 100)
)

# ============================================================
# CHART 1: RETURN RATE BY PAYMENT METHOD
# ============================================================

payment_returns = (
    merged.groupby("payment_method")["returned"]
    .mean()
    .mul(100)
    .sort_values(ascending=False)
)

fig, ax = plt.subplots(figsize=(8, 5))

bars = ax.bar(
    payment_returns.index,
    payment_returns.values
)

ax.bar_label(
    bars,
    labels=[f"{value:.1f}%" for value in payment_returns.values],
    padding=4
)

ax.set_title("COD Returns at 44.4% — 3x Card")
ax.set_xlabel("Payment Method")
ax.set_ylabel("Return Rate (%)")
ax.set_ylim(0, max(payment_returns.values) * 1.18)

fig.tight_layout()

chart_path = OUTPUT_DIR / "return_rate_by_payment.png"
fig.savefig(chart_path, dpi=300, bbox_inches="tight")
plt.close(fig)

print(f"Saved: {chart_path}")
print("\nReturn rates by payment method:")
print(payment_returns.round(1))


# ============================================================
# CHART 2: OUTLIER-CORRECTED MONTHLY REVENUE
# ============================================================

# Calculate IQR bounds without deleting outlier rows
q1 = merged["quantity"].quantile(0.25)
q3 = merged["quantity"].quantile(0.75)
iqr = q3 - q1

lower = q1 - 1.5 * iqr
upper = q3 + 1.5 * iqr

merged["is_outlier"] = (
    (merged["quantity"] < lower)
    | (merged["quantity"] > upper)
)

# Convert dates and calculate monthly revenue
merged["order_date"] = pd.to_datetime(merged["order_date"])
merged["year_month"] = merged["order_date"].dt.to_period("M").astype(str)

monthly_revenue = (
    merged.loc[~merged["is_outlier"]]
    .groupby("year_month")["order_value"]
    .sum()
    .sort_index()
)

peak_month = monthly_revenue.idxmax()

fig, ax = plt.subplots(figsize=(9, 5))

ax.plot(
    monthly_revenue.index,
    monthly_revenue.values,
    marker="o"
)

ax.set_title(
    f"Outlier-Corrected Monthly Revenue — Peak: {peak_month}"
)
ax.set_xlabel("Month")
ax.set_ylabel("Revenue (₹)")
ax.tick_params(axis="x", rotation=45)

fig.tight_layout()

chart_path = OUTPUT_DIR / "monthly_revenue_trend.png"
fig.savefig(chart_path, dpi=300, bbox_inches="tight")
plt.close(fig)

print(f"\nSaved: {chart_path}")
print("\nOutlier-corrected monthly revenue:")
print(monthly_revenue.round(2))
print(f"\nTrue peak month: {peak_month}")
