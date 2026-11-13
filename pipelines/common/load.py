from pathlib import Path
import pandas as pd

def load_parquet(df: pd.DataFrame, out_dir: str | Path, stem: str) -> Path:

    out_file = Path(out_dir) / f'{stem}.parquet'
    out_file.parent.mkdir(parents=True, exist_ok=True)

    df.to_parquet(out_file, index=False)

    return out_file

