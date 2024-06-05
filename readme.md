# GeoTIFF Processing Scripts

This repository contains scripts to process and reproject GeoTIFF files using shapefiles and to process the output as XYZ tiles for web mapping.

## Setup Instructions

### Prerequisites

- Python 3.7 or higher
- `pip` (Python package installer)
- Virtual environment (optional but recommended)

### Installation

1. **Clone the repository or download the scripts**:
   ```bash
   git clone https://github.com/yourusername/yourrepository.git
   cd yourrepository
2. **Load dependencies**:
   ```bash
   pip install rasterio geopandas shapely numpy mercantile Pillow
### Generatate Tiles for Sectional Charts

 1. **Go to [FAA VFR Raster Charts]** (https://www.faa.gov/air_traffic/flight_info/aeronav/digital_products/vfr/)
 2. **Get all current charts for the U.S. and Territories.** This is about 3GB zipped. 
 3. **Extract all the .tif files from the archive into the './rawtiff' folder.**
 4. **Run extract_sectional_charts.py to remove map collars**
      ```bash
      py ./extract_sectional_charts.py
      ```
      This will take a long time. For GeoTiffs this size, expect it to take about 5 to 10 minutes per file. This step will remove the map surrounds and save the clipped output in the './clipped' directory. 
 5. **Run reproject_tif.py to convert GeoTiff projection to EPSG:3857 (WGS 84)**
      ```bash
      py ./reproject_tif.py
      ```
    This also takes some time but less than the previous step. Expect 3 to 5 minutes per file. The output is saved in the './reprojected' directory. This step ensures that the output will be using the proper projection for web maps. 
 6. **Generate the map tiles**
      ```bash
      py ./make_tiles
      ```
      This will take the files in the './reprojected' directory and generates map tiles in 'XYZ' format saving the results in a directory './tiles' (./tiles/{z}/{x}/{y}).
      You can also specify zoom levels to generate and the tile size (height=width=tile_size in pixels) on the command line: 
      ```bash
      py ./make_tiles --zoom_start 1 --zoom_end 18 --tile_size 512
## Troubleshooting
### Check the results after each step
   #### If a raw tiff fails extract_sectional_charts step
   Chances are the shapefiles aren't named correctly. For example, if the raw file is named 'Dutch Harbor SEC.tif' there should be four files in the shapefiles directory named, 'Dutch Harbor SEC.dbf', 'Dutch Harbor SEC.prj', 'Dutch Harbor SEC.shp' and 'Dutch Harbor SEC.shx'. ( One of the GeoTIFFs from the FAA download seemed to have bad metadata. This was the 'Western Aleutian Islands West SEC.tif' file which resulted in the error, "min() arg is an empty sequence". Fortunately, this area is on the most remote, farthest west group of islands in the United States.)
   **If any of these shape files are missing, you can [use QGIS to generate them](https://arc2qgis.github.io/Basics/exporting_data.html).** Make sure you save the shapefiles in the './shapefiles' directory and named consistantly with the raw tif file.