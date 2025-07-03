from uuid import uuid4
from datetime import datetime, timedelta
import pandas as pd
import ee
from json2args.logger import logger
from google.cloud import storage
import time

from params import Params, ParamsCMIP6, map_dataset, map_variable

FAIL_MESSAGE = """Direct data fetch failed: {e}
This usually happens when the dataset is too large to download directly via getInfo().
Proceeding with export to Google Cloud Storage bucket: '{bucket}'...
"""
PROCESSING_MESSAGE = """
Earth Engine export task started. Check your Earth Engine Tasks tab (https://code.earthengine.google.com/tasks)
Once complete, your CSV will be available in the '{bucket}' Google Cloud Storage bucket.
You will need to manually pivot the data using Pandas/Excel after downloading it from GCS if you want models as columns.
"""

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


def download_cmip6_series(kwargs: ParamsCMIP6) -> pd.DataFrame:
    point = ee.Geometry.Point(kwargs.longitude, kwargs.latitude)
    
    start_date = kwargs.start_date
    if kwargs.end_date is None:
        end_date = datetime.now()
    else:
        end_date = kwargs.end_date

    storage_client = storage.Client()
    bucket = storage_client.bucket(kwargs.bucket)

    # map variable name and dataset
    variable_name = map_variable(kwargs.variable, "cmip6", "earthengine")
    dataset = map_dataset("cmip6", "earthengine")
    cmip6 = ee.ImageCollection(dataset)
    
    # filter by scenario
    cmip6 = cmip6.filterDate(start_date.strftime("%Y-%m-%d"), end_date.strftime("%Y-%m-%d")).filter(ee.Filter.eq('scenario', kwargs.scenario))

    cmip6 = cmip6.filter(ee.Filter.inList('model', kwargs.model))
    
    # Function to extract data for a single model and date
    def extract_single_model_data(image):
        date = image.date().format('YYYY-MM-dd')
        model = image.get('model')

        # The band name for CMIP6 variables is usually just the variable name (e.g., 'tas')
        band_name = variable_name

        # Use the nominal scale of the image's projection
        scale = image.projection().nominalScale()

        # Reduce region to get the value at the point
        value = image.reduceRegion(
            reducer=ee.Reducer.first(), # Use first() for single point extraction
            geometry=point,
            scale=scale,
            crs=image.projection()
        ).get(band_name) # Get the value for the specific variable band

        # Return a feature with date, model, and the extracted value
        return ee.Feature(None, {
            'date': date,
            'model': model,
            'value': ee.Algorithms.If(value, value, -9999) # Use -9999 for null values
        })

    # Map the extraction function over the filtered image collection
    features_to_export = cmip6.map(extract_single_model_data)

    # try:
    #     logger.info("Attempting to fetch data directly (might be slow/fail for large datasets)...")
    #     data_list = features_to_export.getInfo()['features']

    #     parsed_data = []
    #     for f in data_list:
    #         properties = f['properties']
    #         parsed_data.append({
    #             'date': properties['date'],
    #             'model': properties['model'],
    #             'value': properties['value']
    #         })

    #     # Create a Pandas DataFrame
    #     df = pd.DataFrame(parsed_data)

    #     # Pivot the DataFrame to have models as columns
    #     df_pivot = df.pivot_table(index='date', columns='model', values='value')

    #     # Rename columns for clarity (e.g., 'tas_GFDL_ESM4')
    #     df_pivot.columns = [f"{kwargs.variable}_{col.replace('-', '_')}" for col in df_pivot.columns]

    #     # Reset index to make 'date' a regular column and sort by date
    #     df_pivot = df_pivot.reset_index()
    #     df_pivot['date'] = pd.to_datetime(df_pivot['date'])
    #     df_pivot = df_pivot.sort_values(by='date')

    #     return df_pivot

    # except Exception as e:
    #     logger.info(FAIL_MESSAGE.format(e=e, bucket=kwargs.bucket))
    #     pass

    # Selectors ensure only the desired columns are exported
    selectors = ['date', 'model', 'value']

    file_name = f"cmip_export_{uuid4()}"

    task = ee.batch.Export.table.toCloudStorage(
        collection=features_to_export,
        description=f'CMIP6_Export_{kwargs.variable}_{kwargs.scenario}',
        bucket=kwargs.bucket,
        fileNamePrefix=file_name,
        fileFormat='CSV',
        selectors=selectors
    )
    task.start()
    logger.info(PROCESSING_MESSAGE.format(bucket=kwargs.bucket))

    # Wait for the export to complete
    while task.active():
        logger.debug("Exporting to Cloud Storage...")
        time.sleep(30)  # Check every 30 seconds
    
    if task.status()['state'] == 'COMPLETED':
        logger.info(f"Export completed successfully! Check the '{kwargs.bucket}' for {file_name}.csv")

        blob = bucket.blob(f"{file_name}.csv")
        with blob.open() as f:
            df = pd.read_csv(f)
        
        blob.delete()
        return df
    else:
        logger.error(f"Export failed: {task.status()}")
