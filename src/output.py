from pathlib import Path
import pandas as pd

from params import Params

def save_series(df: pd.DataFrame, kwargs: Params, prefix: str = ""):
    target_file = Path("/out") / f"{prefix}{kwargs.variable}"
    df.to_csv(target_file.with_suffix(".csv"), index=False)
    df.set_index('time', inplace=True)
    df.to_parquet(target_file.with_suffix(".parquet"))