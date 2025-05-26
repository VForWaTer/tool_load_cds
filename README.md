# tool_load_cds

[![Docker Image CI](https://github.com/VForWaTer/tool_load_cds/actions/workflows/docker-image.yml/badge.svg)](https://github.com/VForWaTer/tool_load_cds/actions/workflows/docker-image.yml)
[![DOI](https://zenodo.org/badge/558416591.svg)](https://zenodo.org/badge/latestdoi/558416591)

A containerized Python tool for downloading climate data from the Copernicus Climate Data Store (CDS) and Google Earth Engine (GEE). This tool follows the [Tool Specification](https://vforwater.github.io/tool-specs/) for reusable research software using Docker.

## Features

- Download ERA5 climate data (precipitation, evaporation, temperature)
- Download CMIP6 climate projections
- Support for multiple backends:
  - Copernicus Climate Data Store (CDS)
  - Google Earth Engine (GEE)
- Output in both CSV and Parquet formats
- Point-based data extraction

## How to build the image?

You can build the image from within the root of this repo by
```
docker build -t tool_load_cds .
```

Use any tag you like. If you want to run and manage the container with [toolbox-runner](https://github.com/hydrocode-de/tool-runner)
they should be prefixed by `tbr_` to be recognized. 

Alternatively, the contained `.github/workflows/docker-image.yml` will build the image for you 
on new releases on Github. You need to change the target repository in the aforementioned yaml.

## How to run?

This tool installs the json2args python package to parse the parameters in the `/in/inputs.json`. This assumes that
the files are not renamed and not moved and there is actually only one tool in the container. For any other case, the environment variables
`PARAM_FILE` can be used to specify a new location for the `inputs.json` and `TOOL_RUN` can be used to specify the tool to be executed.

### Authentication

#### For CDS backend:
You need to provide authentication for the Copernicus Climate Data Store. You have two options:
1. Mount your `.cdsapirc` file to `/root/.cdsapirc` in the container
2. Pass your CDS API key via the `cds_api_key` parameter (not recommended for production use)

#### For Earth Engine backend:
You need to mount your Google Cloud service account JSON file to `/root/service-account.json` in the container. The service account must have Earth Engine API enabled and the project must be registered with Earth Engine.

### Example Usage

To invoke the docker container directly run something similar to:
```
docker run --rm -it \
  -v /path/to/local/in:/in \
  -v /path/to/local/out:/out \
  -v /path/to/.cdsapirc:/root/.cdsapirc \
  -e TOOL_RUN=download_era5_series \
  tool_load_cds
```

With the [toolbox runner](https://github.com/hydrocode-de/tool-runner), this is simplified:

```python
from toolbox_runner import list_tools
tools = list_tools() # dict with tool names as keys

download_era5 = tools.get('download_era5_series')
download_era5.run(
    result_path='./', 
    longitude=8.4, 
    latitude=49.0, 
    variable="precipitation", 
    start_date="2020-01-01", 
    end_date="2020-12-31",
    backend="cds"
)
```

The example above will create a temporary file structure to be mounted into the container and then create a `.tar.gz` on termination of all 
inputs, outputs, specifications and some metadata, including the image sha256 used to create the output in the current working directory.

## Available Tools

### download_era5_series
Downloads ERA5 climate data for a specific location and time period.

Parameters:
- `longitude`: The longitude of the area of interest
- `latitude`: The latitude of the area of interest
- `variable`: The climate variable to download (precipitation, evaporation, temperature)
- `start_date`: The start date of the series (default: 2010-01-01)
- `end_date`: The end date of the series (optional, defaults to current date)
- `cds_api_key`: The CDS API key (optional, see authentication section)
- `backend`: The backend to use (cds or earthengine, default: cds)

### download_cmip6_series
Downloads CMIP6 climate projections for a specific location and time period.

Parameters:
- `longitude`: The longitude of the area of interest
- `latitude`: The latitude of the area of interest
- `variable`: The climate variable to download (precipitation, temperature)
- `start_date`: The start date of the series (default: 2025-01-01)
- `end_date`: The end date of the series (default: 2050-12-31)
- `model`: The GCM model to use (default: "EC-Earth3")
- `scenario`: The scenario to use (ssp245, ssp585, default: "ssp585")

## Output

The tool saves the downloaded data in two formats:
1. CSV file: `/out/{prefix}{variable}.csv`
2. Parquet file: `/out/{prefix}{variable}.parquet`

Where `{prefix}` is either "era5_" or "cmip6_{model}_{scenario}_" depending on the tool used.

