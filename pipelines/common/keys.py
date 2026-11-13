import pandas as pd
import hashlib

def add_txn_key(df: pd.DataFrame, key_cols: list[str]) -> pd.DataFrame:
    occ = df.groupby(key_cols, dropna=False).cumcount()

    df['txn_key'] = [
        hashlib.sha256('|'.join(map(str, r)).encode()).hexdigest()[:16]
        for r in df[key_cols].assign(_occ=occ).itertuples(index=False)
    ]

    return df