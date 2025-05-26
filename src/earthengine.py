from pathlib import Path
from datetime import datetime, timedelta
import pandas as pd
import ee
from json2args.logger import logger
import time

from params import Params, ParamsCMIP6, map_dataset, map_variable, EE_CMIP6_MODELS, EE_CMIP6_MODELS_SHORT


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

    # map variable name and dataset
    variable_name = map_variable(kwargs.variable, "cmip6", "earthengine")
    dataset = map_dataset("cmip6", "earthengine")
    cmip6 = ee.ImageCollection(dataset)
    
    # filter by scenario
    cmip6 = cmip6.filterDate(start_date.strftime("%Y-%m-%d"), end_date.strftime("%Y-%m-%d")).filter(ee.Filter.eq('scenario', kwargs.scenario))

    cmip6 = cmip6.filter(ee.Filter.inList('model', EE_CMIP6_MODELS_SHORT))

    # Create a feature collection with all the data
    def get_value(image):
        value = image.reduceRegion(
            reducer=ee.Reducer.first(),
            geometry=point,
            scale=1000
        )

        return ee.Feature(None, {
            'time': image.date().millis(),
            **{f"{kwargs.variable}_{model_name.replace('-', '_')}": value.get(f"{variable_name}_{model_name}", -9999) for model_name in EE_CMIP6_MODELS}
        })
    
    def extract_data(image):
        # Get date, model, and value
        date = image.date().format('YYYY-MM-dd') # Format date as string
        model = image.get('model')

        # Extract the value at the point.
        # Using scale from the dataset's projection if possible, or a default.
        # The nominal scale for GDDP-CMIP6 is 0.25 arc degrees (~27830 meters at equator)
        scale = image.projection().nominalScale() # Use image's native scale
        # Use reduceRegion to get the value. Use firstNonNull reducer.
        data_dict = image.reduceRegion(
            reducer=ee.Reducer.firstNonNull(),
            geometry=point,
            scale=scale,
            crs=image.projection() # Ensure sampling in image's CRS
        )

        # Get the value for the variable, handle potential nulls
        value = data_dict.get(variable_name)

        # Return a Feature with properties. Set null value marker if necessary
        return ee.Feature(None, {
            'date': date,
            'model': model,
            variable_name: ee.Algorithms.If(value, value, -9999) # Use -9999 for null
        })

    # Create the feature collection
    # features = cmip6.filterDate(
    #     start_date.strftime("%Y-%m-%d"),
    #     end_date.strftime("%Y-%m-%d")
    # ).filterBounds(point).map(get_value)  # Filter to our point of interest
    features = cmip6.map(extract_data)

    # Export to Cloud Storage
    task = ee.batch.Export.table.toCloudStorage(
        collection=features,
        description=f"CMIP6_{kwargs.variable}_{kwargs.scenario}_{kwargs.longitude}_{kwargs.latitude}",
        bucket="ee_loader_export",
        fileNamePrefix=f"CMIP6_{kwargs.variable}_{kwargs.scenario}_{kwargs.longitude}_{kwargs.latitude}",
        fileFormat="CSV",
        selectors=['date', 'model', variable_name] # Specify columns to export
    )
    
    # Start the export
    task.start()
    
    # Wait for the export to complete
    while task.active():
        logger.info("Exporting to Cloud Storage...")
        time.sleep(30)  # Check every 30 seconds
    
    if task.status()['state'] == 'COMPLETED':
        logger.info("Export completed successfully!")
        # Return a message instead of a DataFrame
        return pd.DataFrame({"status": ["Export completed successfully"]})
    else:
        logger.error(f"Export failed: {task.status()}")
        raise RuntimeError(f"Export failed: {task.status()}")