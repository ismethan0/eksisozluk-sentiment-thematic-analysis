import pandas as pd
import unicodedata
from pathlib import Path

def norm(x):
    text = str(x).strip().lower().replace("\u2019", "'").replace("\u2018", "'")
    text = unicodedata.normalize('NFKD', text)
    return text.encode('ascii', 'ignore').decode()

def main():
    out = Path('nlp-analyzer/Sonuc_full.xlsx')
    df = pd.read_excel(out)
    valid = df[(df['Tkategori'].notna()) & (df['Tkategori'] != '') & (df['Rkategori'].notna()) & (df['Rkategori'] != '')].copy()
    valid['Rnorm'] = valid['Rkategori'].apply(norm)
    valid['Tnorm'] = valid['Tkategori'].apply(norm)

    print('Counts R:')
    print(valid['Rnorm'].value_counts())

    print('\nCounts T:')
    print(valid['Tnorm'].value_counts())

    print('\nCrosstab:')
    print(pd.crosstab(valid['Rnorm'], valid['Tnorm']))

    correct = (valid['Rnorm'] == valid['Tnorm']).sum()
    total = len(valid)
    print(f"\nCorrect {correct} Total {total} Acc {correct/total:.4f}")

if __name__ == '__main__':
    main()
