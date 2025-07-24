import os
import sys
from datetime import datetime as dt
from pathlib import Path
import pandas as pd

from json2args import get_parameter
from json2args.logger import logger
from __version__ import __version__
#from json2args.data import get_data

import cds
import ekit
import earthengine
import credentials
import output
import cache


# check if a toolname was set in env
toolname = os.environ.get('TOOL_RUN', 'download_era5_series').lower()

# get a few settings, that cannot be configured by the user
autodelete = os.environ.get('AUTODELETE', 'true').lower() == 'true'

# switch the tool
if toolname == 'download_era5_series':
    logger.info(f"#TOOL START - download_era5_series - v{__version__}")

    # parse parameters
    kwargs = get_parameter(typed=True)
    logger.debug(f"Loaded parameters: {kwargs}")
    
    try:
        if kwargs.backend == 'cds':
            credentials.build_cds_credentials(kwargs.cds_api_key)
        elif kwargs.backend == 'earthengine':
            credentials.build_ee_credentials()
    except Exception as e:
        logger.error(f"Error building API credentials: {e}")
        sys.exit(1)
    
    if kwargs.backend == 'cds':
        target_file = Path("/out") / f"{kwargs.variable}.zip"
        if not target_file.exists():
            #cds.retrieve_era5_series(target_file, kwargs.variable, kwargs.start_date, kwargs.end_date)
            data = ekit.download_era5_series(kwargs)
    elif kwargs.backend == 'earthengine':
        try:
            data = earthengine.download_era5_series(kwargs)
        except Exception as e:
            logger.error(f"Error downloading data from Earth Engine: {e}")
            sys.exit(1)
        
    output.save_series(data, kwargs, prefix="era5_")
    logger.info("#TOOL END")

elif toolname == 'download_cmip6_series':
    logger.info(f"#TOOL START - download_cmip6_series - v{__version__}")

    # parse parameters
    kwargs = get_parameter(typed=True)
    logger.debug(f"Loaded parameters: {kwargs}")

    # checking if the data is already in the cache
    data = None
    missing_models = []
    for model_name in kwargs.model:
        cached = cache.get_data(
            model_name=model_name,
            variable=kwargs.variable,
            longitude=kwargs.longitude,
            latitude=kwargs.latitude,
            scenario=kwargs.scenario,
            start_time=kwargs.start_date,
            end_time=kwargs.end_date
        )
        if cached.empty:
            missing_models.append(model_name)
            continue
        if cached.index.iloc[0] > kwargs.start_date:
            missing_models.append(model_name)
            continue
        if cached.index.iloc[-1] < kwargs.end_date:
            missing_models.append(model_name)
            continue
        
        # we can use the cached data
        logger.info(f"Using cached data for {model_name}")
        if data is None:
            data = cached
        else:
            data = pd.concat([data, cached])
    
    if len(missing_models) > 0:
        logger.info(f"The following models are not entirely in the cache: {missing_models}")

        # currently we only support Earth Engine
        try:
            credentials.build_ee_credentials()
        except Exception as e:
            logger.error(f"Error building API credentials: {e}")
            sys.exit(1)

        try:
            df = earthengine.download_cmip6_series(kwargs, autodelete=autodelete)
        except Exception as e:
            logger.error(f"Error downloading data from Earth Engine: {e}")
            sys.exit(1)
        
        if data is not None:
            data = pd.concat([data, df])
        else:
            data = df

    output.save_series(data, kwargs, prefix=f"cmip6_{kwargs.scenario}_{str(kwargs.longitude).replace('.', '_')}_{str(kwargs.latitude).replace('.', '_')}_")
    logger.info("#TOOL END")
    
# In any other case, it was not clear which tool to run
else:
    raise AttributeError(f"[{dt.now().isocalendar()}] Either no TOOL_RUN environment variable available, or '{toolname}' is not valid.\n")
