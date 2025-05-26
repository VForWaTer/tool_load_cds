import time
import earthkit.data as ekd
import pandas as pd

from params import Params, map_variable
from json2args.logger import logger

def download_era5_series(params: Params) -> pd.DataFrame:
    dataset = "reanalysis-era5-single-levels"

    variable_name = map_variable(params.variable, "era5-daily", "cds")
    date_range = [params.start_date.strftime('%Y-%m-%d'), params.end_date.strftime('%Y-%m-%d')]

    request = {
        "variable": [variable_name],
        "date": date_range,
        "location": {"longitude": params.longitude, "latitude": params.latitude}
    }

    logger.debug(f"Request: {request}")
    start = time.time()
    response = ekd.from_source("cds", dataset, request)
    end = time.time()
    logger.debug(f"Download time from CDS: {end - start:.2f} seconds")
    
    df = response.to_pandas()

    return df