from datetime import datetime, timedelta
import pandas as pd
import ee
from json2args import get_parameter

# Assuming these are correctly set up in your environment
from params import ParamsCMIP6, map_dataset, map_variable, EE_CMIP6_MODELS, EE_CMIP6_MODELS_SHORT
from credentials import build_ee_credentials

# Your GCS bucket name
GCS_BUCKET_NAME = 'camels_plus_cazs'

# Authenticate Earth Engine
build_ee_credentials()
ee.Initialize() # Make sure to initialize EE after credentials are built

# Get parameters from your environment (assuming json2args works as intended)
kwargs = get_parameter(typed=True)

# Define the point of interest
point = ee.Geometry.Point(kwargs.longitude, kwargs.latitude)

# Set date range
start_date = kwargs.start_date
if kwargs.end_date is None:
    end_date = datetime.now()
else:
    end_date = kwargs.end_date

# Map variable name and dataset
variable_name = map_variable(kwargs.variable, "cmip6", "earthengine")
dataset = map_dataset("cmip6", "earthengine")
cmip6 = ee.ImageCollection(dataset)

# Filter the collection by date and scenario
cmip6 = cmip6.filterDate(start_date.strftime("%Y-%m-%d"), end_date.strftime("%Y-%m-%d")) \
             .filter(ee.Filter.eq('scenario', kwargs.scenario))

# Filter by selected models
cmip6 = cmip6.filter(ee.Filter.inList('model', EE_CMIP6_MODELS_SHORT))

print(f"Attempting to extract {kwargs.variable} data for scenario {kwargs.scenario} from {start_date.year} to {end_date.year}...")

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

# --- Attempt Direct Download via getInfo() (for smaller datasets) ---
# This approach can be slow or fail for large datasets due to memory limits
# or Earth Engine's getInfo() limits. For 50 years of daily data for 20 models,
# this will likely be too much for a direct getInfo().

try:
    print("Attempting to fetch data directly (might be slow/fail for large datasets)...")
    data_list = features_to_export.getInfo()['features']

    parsed_data = []
    for f in data_list:
        properties = f['properties']
        parsed_data.append({
            'date': properties['date'],
            'model': properties['model'],
            'value': properties['value']
        })

    # Create a Pandas DataFrame
    df = pd.DataFrame(parsed_data)

    # Pivot the DataFrame to have models as columns
    df_pivot = df.pivot_table(index='date', columns='model', values='value')

    # Rename columns for clarity (e.g., 'tas_GFDL_ESM4')
    df_pivot.columns = [f"{kwargs.variable}_{col.replace('-', '_')}" for col in df_pivot.columns]

    # Reset index to make 'date' a regular column and sort by date
    df_pivot = df_pivot.reset_index()
    df_pivot['date'] = pd.to_datetime(df_pivot['date'])
    df_pivot = df_pivot.sort_values(by='date')

    # Save to CSV locally
    output_filename = f"{kwargs.variable}_{kwargs.scenario}_timeseries_local_download.csv"
    df_pivot.to_csv(output_filename, index=False)
    print(f"Data successfully saved to {output_filename}")

except Exception as e:
    print(f"Direct data fetch failed: {e}")
    print("This usually happens when the dataset is too large to download directly via getInfo().")
    print(f"Proceeding with export to Google Cloud Storage bucket: '{GCS_BUCKET_NAME}'...")

    # --- Fallback to Google Cloud Storage Export (Recommended for large datasets) ---
    # This creates an asynchronous task in Earth Engine that saves the CSV to your GCS bucket.
    # You'll need to download it from GCS afterwards.

    # Selectors ensure only the desired columns are exported
    selectors = ['date', 'model', 'value']

    task = ee.batch.Export.table.toCloudStorage(
        collection=features_to_export,
        description=f'CMIP6_Export_{kwargs.variable}_{kwargs.scenario}',
        bucket=GCS_BUCKET_NAME, # Your specified GCS bucket
        fileNamePrefix=f'{kwargs.variable}_{kwargs.scenario}_daily_timeseries',
        fileFormat='CSV',
        selectors=selectors
    )
    task.start()
    print(f"Earth Engine export task started. Check your Earth Engine Tasks tab (https://code.earthengine.google.com/tasks)")
    print(f"Once complete, your CSV will be available in the '{GCS_BUCKET_NAME}' Google Cloud Storage bucket.")
    print("You will need to manually pivot the data using Pandas/Excel after downloading it from GCS if you want models as columns.")

# Create the feature collection
# features = cmip6.filterDate(
#     start_date.strftime("%Y-%m-%d"),
#     end_date.strftime("%Y-%m-%d")
# ).filterBounds(point).map(get_value)  # Filter to our point of interest
#features = cmip6.map(extract_data)

#    return features
