from pathlib import Path
from datetime import datetime, timedelta
import pandas as pd
import ee
from json2args.logger import logger

from params import Params, map_dataset, map_variable


def download_era5_series(kwargs: Params) -> pd.DataFrame:
    point = ee.Geometry.Point(kwargs.longitude, kwargs.latitude)

    start_date = kwargs.start_date
    if kwargs.end_date is None:
        end_date = datetime.now()
    else:
        end_date = kwargs.end_date

    # map variable name and dataset
    variable_name = map_variable(kwargs.variable, "era5-daily", "earthengine")
    dataset = map_dataset("era5-daily", "earthengine")
    era5 = ee.ImageCollection(dataset)

    # Split into chunks of 4 years (to stay well under 5000 elements)
    chunk_size = timedelta(days=4*365)
    current_start = start_date
    all_data = []

    while current_start < end_date:
        current_end = min(current_start + chunk_size, end_date)
        logger.info(f"Downloading chunk from {current_start} to {current_end}")
        
        collection = era5.filterDate(
            current_start.strftime("%Y-%m-%d"),
            current_end.strftime("%Y-%m-%d")
        ).select(variable_name)

        # Get values at the point location for each day
        def get_value(image):
            value = image.reduceRegion(
                reducer=ee.Reducer.first(),
                geometry=point,
                scale=1000
            ).get(variable_name)
            return ee.Feature(None, {
                'time': image.date().millis(),
                kwargs.variable: value
            })
        
        features = collection.map(get_value)
        data_list = features.getInfo()['features']
        
        # Convert to DataFrame
        chunk_data = []
        for d in data_list:
            p = d['properties']
            chunk_data.append({
                "time": datetime.fromtimestamp(p['time'] / 1000),
                kwargs.variable: p[kwargs.variable]
            })
        
        all_data.extend(chunk_data)
        current_start = current_end

    df = pd.DataFrame(all_data)
    return df
    