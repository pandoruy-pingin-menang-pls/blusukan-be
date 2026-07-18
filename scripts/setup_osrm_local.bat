@echo off
echo ====================================================
echo Blusukan OSRM Local Setup (Windows)
echo ====================================================
echo.

if not exist "osrm_data" (
    echo Creating osrm_data directory...
    mkdir osrm_data
)

cd osrm_data

if not exist "java-latest.osm.pbf" (
    echo Downloading Java Map from Geofabrik (This may take a while)...
    curl -L -o java-latest.osm.pbf https://download.geofabrik.de/asia/indonesia/java-latest.osm.pbf
) else (
    echo Map file java-latest.osm.pbf already exists. Skipping download.
)

cd ..

echo.
echo Running OSRM Extract (Processing foot routing graph)...
docker run -t -v "%cd%\osrm_data:/data" ghcr.io/project-osrm/osrm-backend osrm-extract -p /opt/foot.lua /data/java-latest.osm.pbf

echo.
echo Running OSRM Partition...
docker run -t -v "%cd%\osrm_data:/data" ghcr.io/project-osrm/osrm-backend osrm-partition /data/java-latest.osrm

echo.
echo Running OSRM Customize...
docker run -t -v "%cd%\osrm_data:/data" ghcr.io/project-osrm/osrm-backend osrm-customize /data/java-latest.osrm

echo.
echo ====================================================
echo Setup Complete! 
echo You can now start the server by running:
echo docker-compose up -d osrm
echo ====================================================
pause
