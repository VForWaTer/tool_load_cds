from pathlib import Path
import ee


def build_cds_credentials(cds_api_key: str = None):
    credentials_file = Path.home() / ".cdsapirc"

    if credentials_file.exists():
        return
    
    if cds_api_key is None:
        raise ValueError("No CDS API credentials can be created. You need to mount the .cdsapirc to /root/.cdsapirc into the container, or pass cds_api_key (extremely unsafe) for development and local use only.")
    
    credentials_file.write_text(f"url: https://cds.climate.copernicus.eu/api\nkey: {cds_api_key}")
    return

def build_ee_credentials(credentials_path: str | Path = None):
    if credentials_path is None:
        credentials_path = Path("/root/service-account.json")

    if not credentials_path.exists():
        raise ValueError(f"Credentials file not found at {credentials_path}. Right now you need to mount the service-account.json file to /root/service-account.json. It needs the earth engine API activated and the cloud project needs to be registered for Earth Engine.")
    
    credentials = ee.ServiceAccountCredentials(
        email=None,
        key_file=str(credentials_path)
    )

    ee.Initialize(credentials=credentials)
    return