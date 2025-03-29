# Pull any base image that includes python3
FROM python:3.12

# install the toolbox runner tools
RUN pip install "json2args[data]>=0.7.0" \
    "cdsapi==0.7.5" \
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
