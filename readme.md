# Processing FAA Sectional Chart GeoTIFFs Scripts

This repository contains scripts to process and reproject VFR sectional chart GeoTIFF files using shapefiles and to process the output as XYZ tiles for web mapping.

## Setup Instructions

### Prerequisites

- Python 3.7 or higher
- `pip` (Python package installer)
- Virtual environment (optional but recommended)

### Installation

1. **Clone the repository or download the scripts**:
   ```bash
   git clone https://github.com/halhawkins/sectional-chart-tiles.git sectiles
   cd sectiles
2. **Load dependencies**:
   ```bash
   pip install -r ./requirements.txt
### Quick Start: Generatate Tiles for Sectional Charts

 1. **Go to [FAA VFR Raster Charts]** (https://www.faa.gov/air_traffic/flight_info/aeronav/digital_products/vfr/)
 2. **Get all current charts for the U.S. and Territories.** This is about 3GB zipped. 
 3. **Extract all the files from the archive into the './rawtiff' folder.**
 4. **Run extract_sectional_charts.py to remove map collars**
      ```bash
      cd ./scripts
      py ./extract_sectional_charts.py
      ```
      This will take a long time. For GeoTiffs this size. This step will remove the map surrounds and save the clipped output in the './clipped' directory. 
      This step will also generate a json file with metadata in the './clipped' directory
 5. **Run reproject_tif.py to convert GeoTiff projection to EPSG:3857 (WGS 84)**
      ```bash
      py ./reproject_tif.py
      ```
    This also takes some time but less than the previous step. The output is saved in the './reprojected' directory. This step ensures that the output will be using the proper projection for web maps. 
 6. **Generate the map tiles**
      ```bash
      py ./make_slippy_tiles
      ```
      This will take the files in the './reprojected' directory and generates map tiles in 'XYZ' format saving the results in a directory './tiles' (./tiles/{z}/{x}/{y}).
      You can also specify zoom levels to generate and the tile size (height=width=tile_size in pixels) on the command line: 
      ```bash
      py ./make_tiles --zoom_start 8 --zoom_end 11 --tile_size 512
      ```
 7. **Copy the tiles to the bucket**
     if you are using AWS S3 to host these tiles, you should use the CLI if possible to copy the files to the bucket. ( --dryrun simulates the command. Remove this before running it for real.)
     ```bash
     aws s3 cp .\ s3://your-bucket-name --dryrun 
     ```
#### Suggestions ####
For the Sectional Chart maps, my recommendation is to render tiles only for zoom levels 5-11 and in the Leaflet TileLayer, set the minNativeZoom and maxNativeZoom to those values respectively. Since there is no visible details at the loweest of these zoom levels anyway, this will avoid a great deal of processing time and decrease the amount of time needed to upload the tiles. Rendering tiles at greater zoom levels would add no additional detail and so would take a great deal of time with no benefit.
### Scripts ###
#### Preparing the Data ####
 1. Download the sectional chart data from https://www.faa.gov/air_traffic/flight_info/aeronav/digital_products/vfr/ . There is an option for downloading the entire set in one zip archive which should save time. In the zip archive(s) there are .tif files which contain the raster data in GeoTIFF format, TFW files, workdfiles, which contains data to place and orient the raster data in geographic space, and finally an .htm file which contains metadata regarding the geographic data in the GeoTIFF. Extract all these files into a source directory. In the ./scripts directory, you can extract all these files into a subdirectory named, 'rawtiff' or you can use another directory but you will pass the path to the script on the command line.
 2. Verify that you have the collection of shapefiles included in the repository in .scripts/shapefiles. There should be four files for each of the raw tif files you extracted. There will be a .dbf, a .prj, a .shp, and a .shx for each sectional map. If you are missing shapefiles, you will not be able to use the script to extract the maps from the surrounds. If there are shapefiles missing, you may need to use QGIS desktop application to create polygon shapefiles to trim the map surrounds. Make sure you get copies for all four files you generate. 
#### Remove the Map Surrounds ####
 1. In the ./scripts directory run the script, extract_sectional_charts.py:
   ```bash
   py ./extract_sectional_charts.py [--source_dir <source directory>] [--target_dir <target directory>]
   ```
   When the process is completed the target directory should have a one tif file for each sectional chart in the source directory but with the border collars removed.
#### Reproject the Clipped GeoTIFFs ####
 1. The GeoTIFFs we use to create the tiles will need to use to correcct projection in order to work correctly for web mapping. You will run the reproject_tif script to accomplish this. By default we use EPSG:3857. If for some reason a different projection is needed, you may pass it as a parameter on the command line:
 ```bash
 py ./reproject_tif.py [--input_dir <source directory>] [--output_dir <target directory>] [--target_crs <EPSG:3857>] [--nodata_value <color index>]
 ```
#### Generate the Map Tiles ####
 1. XYZ tiles, or "slippy tiles" are a widely used method for rendering and displaying maps on the web. This approach involves breaking down a large map into smaller, manageable square tiles that can be loaded and displayed dynamically as the user pans and zooms. Here’s a quick overview of how they work:
  - **Tiling**: The map is divided into square tiles, ours are 512x512 pixels in size but are more often 256x256. Each tile represents a specific geographic area at a particular zoom level.
  - **Zoom Levels**: The map is pre-rendered at multiple zoom levels, where each level increases the map’s detail and doubles the number of tiles required. Zoom level 0 contains a single tile representing the entire world, zoom level 1 has 4 tiles, zoom level 2 has 16 tiles, and so on.
  - **Tile Coordinates**: Each tile is identified by a unique set of coordinates (x, y) and the zoom level (z). The coordinates correspond to the position of the tile within the grid at the given zoom level.
  - **Loading and Display**: As the user navigates the map, only the tiles visible within the viewport are requested and loaded from the server. This ensures efficient use of bandwidth and resources, providing a seamless and responsive user experience.
  - **Caching**: Tiles are often cached on the client side, allowing for quick reloading and reduced server load when the user revisits previously viewed areas.
 2. This step will take the longest by far. If you are planning to run zoom levels 10 or above, make sure you have a few hours for this process to run. For our purposes, we will only render zoom levels 5 through 11. In our Leaflet application, we will set the minNativeZoom to 5 and maxNativeZoom to 11. This will result a in more accurate display at lower zoom levels and reduce the amount of time and storage space required to generate the tiles.
 ```bash
 py ./make_slippy_tiles.py [--start_zoom <zoom>] [--end_zoom <zoom>] [--input_dir <source directory>] [--output_dir <target directory>] [--zoom <zoom level for regeneration>] [--tile_x <tile column for regeneration>] [--tile_y <tile row for regeneration>]
 #to generate all tiles from zoom 5 through 11
 py ./make_slippy_tiles.py
 #to generate all tiles for zoom level 11
 py ./make_slippy_tiles.py --start_zoom 11 --end_zoom 11
 #to regenerate individual tile at zoom 11 column 564 row 126
 py ./make_slippy_tiles.py --zoom 11 --tile_x 564 --tile_y 126
 ```
## Troubleshooting
### Check the results after each step
   #### If a raw tiff fails extract_sectional_charts step
   Chances are the shapefiles aren't named correctly. For example, if the raw file is named 'Dutch Harbor SEC.tif' there should be four files in the shapefiles directory named, 'Dutch Harbor SEC.dbf', 'Dutch Harbor SEC.prj', 'Dutch Harbor SEC.shp' and 'Dutch Harbor SEC.shx'. ( One of the GeoTIFFs from the FAA download seemed to have bad metadata. This was the 'Western Aleutian Islands West SEC.tif' file which resulted in the error, "min() arg is an empty sequence". Fortunately, this area is on the most remote, farthest west group of islands in the United States.)
   **If any of these shape files are missing, you can [use QGIS to generate them](https://arc2qgis.github.io/Basics/exporting_data.html).** Make sure you save the shapefiles in the './shapefiles' directory and named consistantly with the raw tif file.