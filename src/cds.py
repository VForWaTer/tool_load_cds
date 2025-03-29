from typing import Generator
from pathlib import Path
from datetime import datetime

import cdsapi
from json2args.logger import logger

from params import Params


def build_request_parameters(kwargs: Params) -> Generator[dict, None, None]:
    if kwargs.end_date is None:
        kwargs.end_date = datetime.now()

    start_year = kwargs.start_date.year
    end_year = kwargs.end_date.year
    for year in range(start_year, end_year + 1):
        yield {
            "variable": [kwargs.variable],
            "year": [str(year)],
            "month": [
                "01", "02", "03",
                "04", "05", "06",
                "07", "08", "09",
                "10", "11", "12",
            ],
            "day": [
                "01", "02", "03",
                "04", "05", "06",
                "07", "08", "09",
                "10", "11", "12",
                "13", "14", "15",
                "16", "17", "18",
                "19", "20", "21",
                "22", "23", "24",
                "25", "26", "27",
                "28", "29", "30",
                "31"
            ],
            "time": [
                "00:00", "01:00", "02:00",
                "03:00", "04:00", "05:00",
                "06:00", "07:00", "08:00",
                "09:00", "10:00", "11:00",
                "12:00", "13:00", "14:00",
                "15:00", "16:00", "17:00",
                "18:00", "19:00", "20:00",
                "21:00", "22:00", "23:00"
            ],
            "data_format": "grib",
            "download_format": "zip",
            "area": [kwargs.latitude + 0.001, kwargs.longitude, kwargs.latitude, kwargs.longitude + 0.001]
        }

def retrieve_era5_series(kwargs: Params, target_file: Path):    
    for request in  build_request_parameters(kwargs):
        logger.debug(f"Request parameters: {request}")

        client = cdsapi.Client()
        client.retrieve("reanalysis-era5-land", request, str(target_file))
    
    