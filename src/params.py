import datetime
from pydantic import BaseModel


class Params(BaseModel):
    variable: str
    start_date: datetime.datetime
    end_date: datetime.datetime | None = None
    longitude: float
    latitude: float

class ParamsCMIP6(Params):
    model: str
    scenario: str

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

EE_CMIP6_VARIABLE = {
    "precipitation": "pr",
    "evaporation": "NaN",
    "temperature": "tas"
}

EE_CMIP6_MODELS = ["ACCESS-CM2", "ACCESS-ESM1-5", "BCC-CSM2-MR", "CESM2", "CESM2-WACCM", "CMCC-CM2-SR5", "CMCC-ESM2", "CNRM-CM6-1", "CNRM-ESM2-1", "CanESM5", "EC-Earth3", "EC-Earth3-Veg-LR", "FGOALS-g3", "GFDL-CM4", "GFDL-ESM4", "GISS-E2-1-G", "HadGEM3-GC31-LL", "HadGEM3-GC31-MM", "IITM-ESM", "INM-CM4-8", "INM-CM5-0", "IPSL-CM6A-LR", "KACE-1-0-G", "KIOST-ESM", "MIROC-ES2L", "MIROC6", "MPI-ESM1-2-HR", "MPI-ESM1-2-LR", "MRI-ESM2-0", "NESM3", "NorESM2-LM", "NorESM2-MM", "TaiESM1", "UKESM1-0-LL"]
EE_CMIP6_MODELS_SHORT = ["ACCESS-CM2",  "MPI-ESM1-2-HR", "EC-Earth3", "FGOALS-g3", "GISS-E2-1-G", "IPSL-CM6A-LR"]

def map_variable(variable: str, dataset: str, provider: str) -> str:
    if dataset == "era5-daily":    
        if provider == "cds":
            mapping = CDS_ERA5_LAND_VARIABLE_DAILY
        elif provider == "earthengine":
            mapping = EE_ERA5_LAND_VARIABLE_DAILY
        else:
            raise ValueError(f"Provider {provider} not supported")
    elif dataset == "cmip6":
        if provider == "earthengine":
            mapping = EE_CMIP6_VARIABLE
        else:
            raise ValueError(f"Provider {provider} not supported")
    else:
        raise ValueError(f"Dataset {dataset} not supported")

    variable_name = mapping.get(variable, variable)
    if variable_name == "NaN":
        raise RuntimeError(f"Variable {variable} not supported for dataset {dataset} and provider {provider}.")
    return variable_name

def map_dataset(dataset: str, provider: str) -> str:
    if dataset == "era5-daily":    
        if provider == "cds":
            return "derived-era5-single-levels-daily-statistics"
        elif provider == "earthengine":
            return "ECMWF/ERA5_LAND/DAILY_AGGR"
        else:
            raise ValueError(f"Provider {provider} not supported")
    elif dataset == "cmip6":
        if provider == "earthengine":
            return "NASA/GDDP-CMIP6"
        elif provider == "cds":
            raise NotImplementedError("CDS downlaod for CMIP6 is currently not implemented. We are working on it!")
        else:
            raise ValueError(f"Provider {provider} not supported")
    else:
        raise ValueError(f"Dataset {dataset} not supported")