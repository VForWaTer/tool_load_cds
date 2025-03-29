import os
import sys
from datetime import datetime as dt
from pathlib import Path

from json2args import get_parameter
from json2args.logger import logger
from __version__ import __version__
#from json2args.data import get_data

import cds
import earthengine
import credentials


# check if a toolname was set in env
toolname = os.environ.get('TOOL_RUN', 'download_era5_series').lower()

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
            cds.retrieve_era5_series(target_file, kwargs.variable, kwargs.start_date, kwargs.end_date)
    elif kwargs.backend == 'earthengine':
        try:
            df = earthengine.download_era5_series(kwargs)
        except Exception as e:
            logger.error(f"Error downloading data from Earth Engine: {e}")
            sys.exit(1)
        
        # TODO: move this into a separated function
        target_file = Path("/out") / f"{kwargs.variable}"
        df.to_csv(target_file.with_suffix(".csv"), index=False)
        df.set_index('time', inplace=True)
        df.to_parquet(target_file.with_suffix(".parquet"))
    
    logger.info("#TOOL END")
# In any other case, it was not clear which tool to run
else:
    raise AttributeError(f"[{dt.now().isocalendar()}] Either no TOOL_RUN environment variable available, or '{toolname}' is not valid.\n")
