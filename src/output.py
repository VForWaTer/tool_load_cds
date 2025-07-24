from pathlib import Path
import pandas as pd

from params import Params

def save_series(df: pd.DataFrame, kwargs: Params, prefix: str = ""):
    # it is possible, that the datetime column is not called 'time', but 'date' or 'datetime' or 'timestamp'
    df.rename(columns=dict(
        date='time',
        datetime='time',
        timestamp='time'
    ), inplace=True)
    
    target_file = Path("/out") / f"{prefix}{kwargs.variable}"
    df.to_csv(target_file.with_suffix(".csv"), index=False)
    df.set_index('time', inplace=True)
    df.to_parquet(target_file.with_suffix(".parquet"))