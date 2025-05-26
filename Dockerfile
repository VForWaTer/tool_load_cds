FROM python:3.12

# Install GDAL and its dependencies
RUN apt-get update && \
    apt-get install -y \
    gdal-bin \
    libgdal-dev \
    python3-gdal \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# install the toolbox runner tools
RUN pip install "json2args[data]>=0.7.0" \
    "cdsapi==0.7.5" \
    "earthkit==0.10.1" \
    "xarray==2025.1.1" \
    "earthengine-api==1.5.8" \
    "gcloud==0.18.3" \
    "h5netcdf==1.6.1"

# create the tool input structure
RUN mkdir /in
COPY ./in /in
RUN mkdir /out
RUN mkdir /src
COPY ./src /src

# copy the citation file - looks funny to make COPY not fail if the file is not there
COPY ./CITATION.cf[f] /src/CITATION.cff

WORKDIR /src
CMD ["python", "run.py"]
