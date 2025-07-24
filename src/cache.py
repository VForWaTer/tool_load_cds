import os
from pathlib import Path
from datetime import datetime

import duckdb
import pandas as pd


CACHE_DIR = Path(os.environ.get("CACHE_PATH", "/cache"))
CACHE_DIR.mkdir(parents=True, exist_ok=True)
CACHE_PATH = CACHE_DIR / "cache.duckdb"

if not CACHE_PATH.exists():
    with duckdb.connect(CACHE_PATH, read_only=False) as db:
        db.execute("CREATE TABLE models (id INTEGER, model_name TEXT);")
        db.execute("CREATE TABLE variables (id INTEGER, variable_name TEXT);")
        db.execute("CREATE TABLE locations (id INTEGER, longitude REAL, latitude REAL);")
        db.execute("CREATE TABLE scenarios (id INTEGER, scenario_name TEXT);")
        db.execute("CREATE TABLE data (model_id INTEGER, variable_id INTEGER, location_id INTEGER, scenario_id INTEGER, time TIMESTAMP, value REAL);")

def index_model(model_name: str) -> int:
    with duckdb.connect(CACHE_PATH, read_only=False) as db:
        result = db.execute("SELECT id FROM models WHERE model_name = ?", [model_name]).fetchone()
        
        if result is None:
            # Get the next available ID
            max_id_result = db.execute("SELECT COALESCE(MAX(id), 0) FROM models").fetchone()
            model_id = max_id_result[0] + 1
            db.execute("INSERT INTO models (id, model_name) VALUES (?, ?)", [model_id, model_name])
        else:
            model_id = result[0]
            
        return model_id

def index_variable(variable: str) -> int:
    with duckdb.connect(CACHE_PATH, read_only=False) as db:
        result = db.execute("SELECT id FROM variables WHERE variable_name = ?", [variable]).fetchone()
        
        if result is None:
            # Get the next available ID
            max_id_result = db.execute("SELECT COALESCE(MAX(id), 0) FROM variables").fetchone()
            variable_id = max_id_result[0] + 1
            db.execute("INSERT INTO variables (id, variable_name) VALUES (?, ?)", [variable_id, variable])
        else:
            variable_id = result[0]
            
        return variable_id

def index_location(longitude: float, latitude: float) -> int:
    with duckdb.connect(CACHE_PATH, read_only=False) as db:
        result = db.execute("SELECT id FROM locations WHERE longitude = ? AND latitude = ?", [longitude, latitude]).fetchone()
        
        if result is None:
            # Get the next available ID
            max_id_result = db.execute("SELECT COALESCE(MAX(id), 0) FROM locations").fetchone()
            location_id = max_id_result[0] + 1
            db.execute("INSERT INTO locations (id, longitude, latitude) VALUES (?, ?, ?)", [location_id, longitude, latitude])
        else:
            location_id = result[0]
            
        return location_id

def index_scenario(scenario_name: str) -> int:
    with duckdb.connect(CACHE_PATH, read_only=False) as db:
        result = db.execute("SELECT id FROM scenarios WHERE scenario_name = ?", [scenario_name]).fetchone()
        
        if result is None:
            # Get the next available ID
            max_id_result = db.execute("SELECT COALESCE(MAX(id), 0) FROM scenarios").fetchone()
            scenario_id = max_id_result[0] + 1
            db.execute("INSERT INTO scenarios (id, scenario_name) VALUES (?, ?)", [scenario_id, scenario_name])
        else:
            scenario_id = result[0]
            
        return scenario_id

DROP_DATA = """DELETE FROM data WHERE model_id = ? AND variable_id = ? AND location_id = ?
AND scenario_id = ? AND time >= ? AND time <= ?;
"""

def index_data(data: pd.DataFrame, model_name: str, variable: str, longitude: float, latitude: float, scenario: str, model_column: str = 'model'):
    model_id = index_model(model_name)
    variable_id = index_variable(variable)
    location_id = index_location(longitude, latitude)
    scenario_id = index_scenario(scenario)

    # get only relevant rows
    df = data.where(data[model_column] == model_name).dropna(how='all').set_index('time').sort_index(ascending=True)

    first_time = df.index.min()
    last_time = df.index.max()

    # remove any existing data for this model, variable and location
    with duckdb.connect(CACHE_PATH, read_only=False) as db:
        db.execute(DROP_DATA, [model_id, variable_id, location_id, scenario_id, first_time, last_time])
    
    # insert the data
    df.reset_index(inplace=True)
    df['variable_id'] = variable_id
    df['location_id'] = location_id
    df['model_id'] = model_id
    df['scenario_id'] = scenario_id

    with duckdb.connect(CACHE_PATH, read_only=False) as db:
        # Register the dataframe as a temporary table
        db.register('temp_df', df)
        db.execute("INSERT INTO data SELECT model_id, variable_id, location_id, scenario_id, time, value FROM temp_df")

def get_data(model_name: str, variable: str, longitude: float, latitude: float, scenario: str, start_time: datetime, end_time: datetime) -> pd.DataFrame:
    with duckdb.connect(CACHE_PATH, read_only=True) as db:
        data = db.execute("""
        SELECT * FROM data
        WHERE model_id = (SELECT id FROM models WHERE model_name = ?)
        AND variable_id = (SELECT id FROM variables WHERE variable_name = ?)
        AND location_id = (SELECT id FROM locations WHERE longitude = ? AND latitude = ?)
        AND scenario_id = (SELECT id FROM scenarios WHERE scenario_name = ?)
        AND time >= ? AND time <= ?
        ORDER BY time ASC
        """, [model_name, variable, longitude, latitude, scenario, start_time, end_time]).df()

    data.drop(['model_id', 'variable_id', 'location_id', 'scenario_id'], axis=1, inplace=True)
    data.rename(columns=dict(value=variable), inplace=True)
    data.set_index('time', inplace=True)

    return data



