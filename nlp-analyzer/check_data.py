"""
Test verisini kontrol et
"""
import pandas as pd

file = 'test2.xlsx'
df = pd.read_excel(file)

print(f"Total rows: {len(df)}")
print(f"\nColumns: {list(df.columns)}")

print("\n=== Data Info ===")
print(df.info())

print("\n=== First 5 rows ===")
print(df.head())

print("\n=== Null counts ===")
print(df.isnull().sum())

print("\n=== Empty string counts ===")
for col in ['body', 'RDuygu', 'Rkategori']:
    if col in df.columns:
        empty = (df[col] == '').sum()
        nan = df[col].isna().sum()
        print(f"{col}: {nan} null, {empty} empty strings")

print("\n=== Sample RDuygu values ===")
if 'RDuygu' in df.columns:
    print(df['RDuygu'].value_counts())

print("\n=== Sample Rkategori values ===")
if 'Rkategori' in df.columns:
    print(df['Rkategori'].value_counts())
