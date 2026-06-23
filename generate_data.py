import pandas as pd
import numpy as np

np.random.seed(42)

# Number of assets
n = 200

# Asset types relevant to water utility
asset_types = ['Water Pipe', 'Pumping Station', 'Valve', 'Reservoir', 'Treatment Works']

# UK Midlands area — coordinates around Coventry/Birmingham
# Severn Trent's actual service area!
lat_min, lat_max = 52.2, 52.8
lon_min, lon_max = -2.0, -1.2

# Generate dataset
data = {
    'asset_id': [f'ST-{str(i).zfill(4)}' for i in range(1, n+1)],
    'asset_type': np.random.choice(asset_types, n),
    'latitude': np.random.uniform(lat_min, lat_max, n),
    'longitude': np.random.uniform(lon_min, lon_max, n),
    'age_years': np.random.randint(1, 80, n),
    'last_inspection_years_ago': np.random.randint(0, 10, n),
    'condition_score': np.random.randint(1, 11, n),  # 1=worst, 10=best
    'area_deprivation_score': np.round(np.random.uniform(1, 10, n), 2),
    'material': np.random.choice(['Cast Iron', 'PVC', 'Steel', 'Concrete', 'HDPE'], n),
    'zone': np.random.choice(['North', 'South', 'East', 'West', 'Central'], n),
}

df = pd.DataFrame(data)

# Calculate risk score (higher = more at risk)
df['risk_score'] = (
    (df['age_years'] / 80 * 40) +           # Age contributes 40%
    (df['last_inspection_years_ago'] / 10 * 30) +  # Inspection contributes 30%
    ((10 - df['condition_score']) / 10 * 30)  # Condition contributes 30%
).round(2)

# Risk category
def categorise_risk(score):
    if score >= 60:
        return 'High'
    elif score >= 35:
        return 'Medium'
    else:
        return 'Low'

df['risk_category'] = df['risk_score'].apply(categorise_risk)

# Save to CSV
df.to_csv('assets.csv', index=False)

print(f"✅ Dataset generated successfully!")
print(f"Total assets: {len(df)}")
print(f"High risk: {len(df[df['risk_category']=='High'])}")
print(f"Medium risk: {len(df[df['risk_category']=='Medium'])}")
print(f"Low risk: {len(df[df['risk_category']=='Low'])}")
print(f"\nSample data:")
print(df.head())