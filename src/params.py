import datetime
from pydantic import BaseModel


class Params(BaseModel):
    variable: str
    start_date: datetime.datetime
    end_date: datetime.datetime | None = None
    longitude: float
    latitude: float

CDS_ERA5_LAND_VARIABLE_DAILY = {
    "precipitation": "total_precipitation",
    "evaporation": "evaporation",
    "temperature": "2m_temperature",
}

# "ECMWF/ERA5_LAND/DAILY_AGGR"
EE_ERA5_LAND_VARIABLE_DAILY = {
    "precipitation": "total_precipitation_sum",
    "evaporation": "total_evaporation_sum",
    "temperature": "temperature_2m"
}

def map_variable(variable: str, dataset: str, provider: str) -> str:
    if dataset != "era5-daily":
        raise ValueError(f"Dataset {dataset} not supported. Currently only daily ERA5 is supported.")
    
    if provider == "cds":
        mapping = CDS_ERA5_LAND_VARIABLE_DAILY
    elif provider == "earthengine":
        mapping = EE_ERA5_LAND_VARIABLE_DAILY
    else:
        raise ValueError(f"Provider {provider} not supported")

    return mapping.get(variable, variable)

def map_dataset(dataset: str, provider: str) -> str:
    if dataset != "era5-daily":
        raise ValueError(f"Dataset {dataset} not supported. Currently only daily ERA5 is supported.")
    
    if provider == "cds":
        return "derived-era5-single-levels-daily-statistics"
    elif provider == "earthengine":
        return "ECMWF/ERA5_LAND/DAILY_AGGR"
    else:
        raise ValueError(f"Provider {provider} not supported")