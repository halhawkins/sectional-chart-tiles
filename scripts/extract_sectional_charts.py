# import os
# import rasterio
# from rasterio.mask import mask
# from shapely.geometry import box
# import geopandas as gpd
# import numpy as np
# import logging
# from tqdm import tqdm
# import json
# from datetime import datetime, timedelta
# from bs4 import BeautifulSoup
# from colorama import Fore, Style, init
# import argparse

# # Author: Hal Hawkins harold.hawkins@truweathersolutions.com

# # Setup logging
# logging.basicConfig(filename='processing.log', level=logging.INFO, 
#                     format='%(asctime)s %(levelname)s:%(message)s')

# # Initialize colorama
# init()

# def get_latest_date_from_html(directory):
#     latest_date = None
#     latest_file = None

#     for filename in os.listdir(directory):
#         if filename.endswith('.htm'):
#             filepath = os.path.join(directory, filename)
#             try:
#                 with open(filepath, 'r', encoding='utf-8') as file:
#                     soup = BeautifulSoup(file, 'html.parser')
#                     meta_tag = soup.find('meta', {'name': 'dc.date'})
#                     if meta_tag:
#                         date_str = meta_tag['content']
#                         file_date = datetime.strptime(date_str, '%Y%m%d')

#                         if not latest_date or file_date > latest_date:
#                             latest_date = file_date
#                             latest_file = filename
#             except Exception as e:
#                 logging.warning(f"Failed to parse date for {filename}: {e}")

#     if latest_date:
#         return latest_file, latest_date
#     return None, None

# def process_geotiff(raster_path, shapefile_path, output_path, nodata_value=0):
#     try:
#         # Load the shapefile
#         shapes = gpd.read_file(shapefile_path)
#         shapefile_crs = shapes.crs

#         with rasterio.open(raster_path) as src:
#             # print(f'Source CRS {src.crs}...')
#             # Reproject shapefile to raster CRS if they don't match
#             if shapefile_crs != src.crs:
#                 shapes = shapes.to_crs(src.crs)
            
#             # Extract geometry in GeoJSON format
#             geometry = [shape['geometry'] for shape in shapes.__geo_interface__['features']]

#             # Clip the raster using the geometry
#             out_img, out_transform = mask(src, shapes=geometry, crop=True, nodata=nodata_value)
            
#             # Apply colormap if present
#             if src.colorinterp[0] == rasterio.enums.ColorInterp.palette:
#                 colormap = src.colormap(1)
#                 out_img_rgb = apply_colormap(out_img[0], colormap)  # out_img[0] as out_img is 3D array

#                 # Ensure nodata value is applied
#                 out_img_rgb[out_img[0] == nodata_value] = [0, 0, 0, 0]  # Set RGBA to transparent
                
#                 # Update metadata for the new clipped raster
#                 out_meta = src.meta.copy()
#                 out_meta.update({
#                     "driver": "GTiff",
#                     "height": out_img_rgb.shape[0],
#                     "width": out_img_rgb.shape[1],
#                     "count": 4,  # RGBA image
#                     "dtype": 'uint8',
#                     "transform": out_transform,
#                     "compress": src.tags(ns='IMAGE_STRUCTURE').get('COMPRESSION', 'LZW'),  # Use same compression as input or default to LZW
#                     "nodata": nodata_value
#                 })
                
#                 # Save the clipped raster to a new file
#                 with rasterio.open(output_path, 'w', **out_meta) as dest:
#                     dest.write(out_img_rgb.transpose(2, 0, 1))  # Write as (bands, rows, cols)
#             else:
#                 # Ensure nodata value is applied
#                 for band in range(out_img.shape[0]):
#                     out_img[band][out_img[band] == nodata_value] = nodata_value
                
#                 # Update metadata for the new clipped raster
#                 out_meta = src.meta.copy()
#                 out_meta.update({
#                     "driver": "GTiff",
#                     "height": out_img.shape[1],
#                     "width": out_img.shape[2],
#                     "transform": out_transform,
#                     "count": src.count,  # Ensure the band count is set correctly
#                     "compress": src.tags(ns='IMAGE_STRUCTURE').get('COMPRESSION', 'LZW'),  # Use same compression as input or default to LZW
#                     "nodata": nodata_value
#                 })
                
#                 # Save the clipped raster to a new file
#                 with rasterio.open(output_path, 'w', **out_meta) as dest:
#                     dest.write(out_img)
#         logging.info(f'Successfully processed: {raster_path}')
#     except Exception as e:
#         logging.error(f'Error processing {raster_path}: {e}')

# # Function to apply a colormap to a single-band image
# def apply_colormap(image, colormap):
#     height, width = image.shape
#     rgba_image = np.zeros((height, width, 4), dtype=np.uint8)  # RGBA image
#     for i in range(height):
#         for j in range(width):
#             rgba = colormap[image[i, j]]
#             rgba_image[i, j] = rgba  # Include alpha channel
#     return rgba_image

# def main():
#     # Argument parser setup
#     parser = argparse.ArgumentParser(description='Process GeoTIFF files with specified zoom levels.')
#     parser.add_argument('--start_zoom', type=int, default=8, help='Start zoom level (default: 8)')
#     parser.add_argument('--end_zoom', type=int, default=11, help='End zoom level (default: 11)')
#     args = parser.parse_args()

#     # Paths
#     input_folder = './rawtiff/'
#     shapefile_folder = './shapefiles/'
#     output_folder = './clipped/'

#     # Ensure output folder exists
#     os.makedirs(output_folder, exist_ok=True)

#     # Get the latest date from HTML metadata files
#     latest_file, latest_date = get_latest_date_from_html(input_folder)

#     if latest_file:
#         latest_iso = latest_date.isoformat() + 'Z'
#         print(f'Latest file: {latest_file}')
#         logging.info(f'Latest file: {latest_file}')

#         # Check if the date is older than or equal to 56 days
#         if (datetime.now() - latest_date).days >= 56:
#             print(Fore.YELLOW + 'Warning: Sectional charts are older than 56 days. Check for new updates at https://www.faa.gov/air_traffic/flight_info/aeronav/digital_products/vfr/' + Style.RESET_ALL)

#         # Initialize metadata
#         update_metadata = {
#             "last_updated": latest_iso,
#             "maps": []
#         }

#         # Process each GeoTIFF in the input folder
#         tiff_files = [filename for filename in os.listdir(input_folder) if filename.endswith('.tif')]

#         for filename in tqdm(tiff_files, desc='Processing GeoTIFFs'):
#             raster_path = os.path.join(input_folder, filename)
#             shapefile_name = filename.replace('.tif', '.shp')
#             shapefile_path = os.path.join(shapefile_folder, shapefile_name)
#             output_path = os.path.join(output_folder, filename)

#             if os.path.exists(shapefile_path):
#                 process_geotiff(raster_path, shapefile_path, output_path)
#                 update_metadata["maps"].append({
#                     "name": filename.replace('.tif', ''),
#                     "last_updated": latest_iso
#                 })
#             else:
#                 logging.warning(f'Shapefile not found for {raster_path}')

#         # Save the update metadata to a JSON file
#         with open(os.path.join(output_folder, 'update_metadata.json'), 'w') as json_file:
#             json.dump(update_metadata, json_file, indent=4)

#         logging.info('Update metadata JSON file created successfully.')
#     else:
#         logging.error('No HTML files with valid dates found in the input folder.')
#         print('No HTML files with valid dates found in the input folder.')

# if __name__ == '__main__':
#     main()
import os
import rasterio
from rasterio.mask import mask
from shapely.geometry import box
import geopandas as gpd
import numpy as np
import logging
from tqdm import tqdm
import json
from datetime import datetime, timedelta
from bs4 import BeautifulSoup
from colorama import Fore, Style, init
import argparse

# Author: Hal Hawkins harold.hawkins@truweathersolutions.com

# Setup logging
logging.basicConfig(filename='processing.log', level=logging.INFO, 
                    format='%(asctime)s %(levelname)s:%(message)s')

# Initialize colorama
init()

def get_latest_date_from_html(directory):
    latest_date = None
    latest_file = None

    for filename in os.listdir(directory):
        if filename.endswith('.htm'):
            filepath = os.path.join(directory, filename)
            try:
                with open(filepath, 'r', encoding='utf-8') as file:
                    soup = BeautifulSoup(file, 'html.parser')
                    meta_tag = soup.find('meta', {'name': 'dc.date'})
                    if meta_tag:
                        date_str = meta_tag['content']
                        file_date = datetime.strptime(date_str, '%Y%m%d')

                        if not latest_date or file_date > latest_date:
                            latest_date = file_date
                            latest_file = filename
            except Exception as e:
                logging.warning(f"Failed to parse date for {filename}: {e}")

    if latest_date:
        return latest_file, latest_date
    return None, None

def process_geotiff(raster_path, shapefile_path, output_path, nodata_value=0):
    try:
        # Load the shapefile
        shapes = gpd.read_file(shapefile_path)
        shapefile_crs = shapes.crs

        with rasterio.open(raster_path) as src:
            # print(f'Source CRS {src.crs}...')
            # Reproject shapefile to raster CRS if they don't match
            if shapefile_crs != src.crs:
                shapes = shapes.to_crs(src.crs)
            
            # Extract geometry in GeoJSON format
            geometry = [shape['geometry'] for shape in shapes.__geo_interface__['features']]

            # Clip the raster using the geometry
            out_img, out_transform = mask(src, shapes=geometry, crop=True, nodata=nodata_value)
            
            # Apply colormap if present
            if src.colorinterp[0] == rasterio.enums.ColorInterp.palette:
                colormap = src.colormap(1)
                out_img_rgb = apply_colormap(out_img[0], colormap)  # out_img[0] as out_img is 3D array

                # Ensure nodata value is applied
                out_img_rgb[out_img[0] == nodata_value] = [0, 0, 0, 0]  # Set RGBA to transparent
                
                # Update metadata for the new clipped raster
                out_meta = src.meta.copy()
                out_meta.update({
                    "driver": "GTiff",
                    "height": out_img_rgb.shape[0],
                    "width": out_img_rgb.shape[1],
                    "count": 4,  # RGBA image
                    "dtype": 'uint8',
                    "transform": out_transform,
                    "compress": src.tags(ns='IMAGE_STRUCTURE').get('COMPRESSION', 'LZW'),  # Use same compression as input or default to LZW
                    "nodata": nodata_value
                })
                
                # Save the clipped raster to a new file
                with rasterio.open(output_path, 'w', **out_meta) as dest:
                    dest.write(out_img_rgb.transpose(2, 0, 1))  # Write as (bands, rows, cols)
            else:
                # Ensure nodata value is applied
                for band in range(out_img.shape[0]):
                    out_img[band][out_img[band] == nodata_value] = nodata_value
                
                # Update metadata for the new clipped raster
                out_meta = src.meta.copy()
                out_meta.update({
                    "driver": "GTiff",
                    "height": out_img.shape[1],
                    "width": out_img.shape[2],
                    "transform": out_transform,
                    "count": src.count,  # Ensure the band count is set correctly
                    "compress": src.tags(ns='IMAGE_STRUCTURE').get('COMPRESSION', 'LZW'),  # Use same compression as input or default to LZW
                    "nodata": nodata_value
                })
                
                # Save the clipped raster to a new file
                with rasterio.open(output_path, 'w', **out_meta) as dest:
                    dest.write(out_img)
        logging.info(f'Successfully processed: {raster_path}')
    except Exception as e:
        logging.error(f'Error processing {raster_path}: {e}')

# Function to apply a colormap to a single-band image
def apply_colormap(image, colormap):
    height, width = image.shape
    rgba_image = np.zeros((height, width, 4), dtype=np.uint8)  # RGBA image
    for i in range(height):
        for j in range(width):
            rgba = colormap[image[i, j]]
            rgba_image[i, j] = rgba  # Include alpha channel
    return rgba_image

def main():
    # Argument parser setup
    parser = argparse.ArgumentParser(description='Extract and process sectional charts from GeoTIFF files.')
    parser.add_argument('--source_dir', type=str, default='./rawtiff', help='Source directory containing GeoTIFF files (default: ./rawtiff)')
    parser.add_argument('--target_dir', type=str, default='./clipped', help='Target directory for processed files (default: ./clipped)')
    args = parser.parse_args()

    # Paths
    input_folder = args.source_dir
    shapefile_folder = './shapefiles/'
    output_folder = args.target_dir

    # Ensure output folder exists
    os.makedirs(output_folder, exist_ok=True)

    # Get the latest date from HTML metadata files
    latest_file, latest_date = get_latest_date_from_html(input_folder)

    if latest_file:
        latest_iso = latest_date.isoformat() + 'Z'
        print(f'Latest file: {latest_file}')
        logging.info(f'Latest file: {latest_file}')

        # Check if the date is older than or equal to 56 days
        if (datetime.now() - latest_date).days >= 56:
            print(Fore.YELLOW + 'Warning: Sectional charts are older than 56 days. Check for new updates at https://www.faa.gov/air_traffic/flight_info/aeronav/digital_products/vfr/' + Style.RESET_ALL)

        # Initialize metadata
        update_metadata = {
            "last_updated": latest_iso,
            "maps": []
        }

        # Process each GeoTIFF in the input folder
        tiff_files = [filename for filename in os.listdir(input_folder) if filename.endswith('.tif')]

        for filename in tqdm(tiff_files, desc='Processing GeoTIFFs'):
            raster_path = os.path.join(input_folder, filename)
            shapefile_name = filename.replace('.tif', '.shp')
            shapefile_path = os.path.join(shapefile_folder, shapefile_name)
            output_path = os.path.join(output_folder, filename)

            if os.path.exists(shapefile_path):
                process_geotiff(raster_path, shapefile_path, output_path)
                update_metadata["maps"].append({
                    "name": filename.replace('.tif', ''),
                    "last_updated": latest_iso
                })
            else:
                logging.warning(f'Shapefile not found for {raster_path}')

        # Save the update metadata to a JSON file
        with open(os.path.join(output_folder, 'update_metadata.json'), 'w') as json_file:
            json.dump(update_metadata, json_file, indent=4)

        logging.info('Update metadata JSON file created successfully.')
    else:
        logging.error('No HTML files with valid dates found in the input folder.')
        print('No HTML files with valid dates found in the input folder.')

if __name__ == '__main__':
    main()
