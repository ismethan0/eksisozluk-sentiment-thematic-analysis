"""
Hata analizi - Hangi tahminler yanlış?
"""
import pandas as pd

df = pd.read_excel('Sonuc.xlsx')

# Yanlış tahminleri bul
df['correct'] = df['RDuygu'] == df['Tduygu']
errors = df[~df['correct']]

print(f"Total errors: {len(errors)}/{len(df)} ({len(errors)/len(df)*100:.1f}%)")

# Hata tiplerine göre grupla
print("\n=== Error Types ===")
error_types = errors.groupby(['RDuygu', 'Tduygu']).size().reset_index(name='count')
error_types = error_types.sort_values('count', ascending=False)

labels = {0: 'negative', 1: 'neutral', 2: 'positive'}
print("\nTrue -> Predicted : Count")
for _, row in error_types.iterrows():
    true_label = labels.get(row['RDuygu'], row['RDuygu'])
    pred_label = labels.get(row['Tduygu'], row['Tduygu'])
    print(f"{true_label:8} -> {pred_label:8} : {row['count']}")

# En çok hata yapılan örnekleri göster
print("\n=== Sample Errors ===")
for idx, row in errors.head(10).iterrows():
    true_label = labels.get(row['RDuygu'], row['RDuygu'])
    pred_label = labels.get(row['Tduygu'], row['Tduygu'])
    body = row['body'][:100]
    print(f"\n[{idx}] TRUE: {true_label} | PRED: {pred_label}")
    print(f"    {body}...")

# Doğru tahminleri de göster (karşılaştırma için)
correct = df[df['correct']]
print(f"\n\n=== Sample Correct Predictions ===")
for idx, row in correct.head(5).iterrows():
    label = labels.get(row['RDuygu'], row['RDuygu'])
    body = row['body'][:100]
    print(f"\n[{idx}] {label}")
    print(f"    {body}...")

# Kaydet
errors.to_excel('Errors_Analysis.xlsx', index=False)
print(f"\n✅ Error analysis saved to: Errors_Analysis.xlsx")
