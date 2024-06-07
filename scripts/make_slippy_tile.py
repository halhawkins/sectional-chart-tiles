# import os
# import numpy as np
# import rasterio
# import mercantile
# from PIL import Image
# from rasterio.warp import reproject, Resampling, transform_bounds
# from rasterio.transform import from_bounds
# from multiprocessing import Pool, cpu_count
# from filelock import FileLock
# from decimal import Decimal, getcontext
# from tqdm import tqdm  # Import tqdm

# # Set precision for Decimal calculations
# getcontext().prec = 20
# target_crs = 'EPSG:4326'

# # Directories
# reprojected_dir = './reprojected'
# tiles_dir = './tiles'

# # Ensure the tiles directory exists
# os.makedirs(tiles_dir, exist_ok=True)

# # Find all GeoTIFF files in the directory
# def find_all_geotiffs(directory):
#     return [os.path.join(directory, file) for file in os.listdir(directory) if file.endswith('.tif') or file.endswith('.tiff')]

# # Function to process a single tile
# def process_tile(tile_info):
#     geotiff_paths, zoom_level, tile = tile_info

#     tile_dir = os.path.join(tiles_dir, str(tile.z), str(tile.x))
#     os.makedirs(tile_dir, exist_ok=True)
#     tile_path = os.path.join(tile_dir, f'{tile.y}.png')
#     lock_path = tile_path + '.lock'
    
#     with FileLock(lock_path):
#         # Initialize an empty image for the tile
#         tile_img = Image.new('RGBA', (512, 512), (0, 0, 0, 0))
        
#         for geotiff_path in geotiff_paths:
#             with rasterio.open(geotiff_path) as dataset:
#                 # Get the tile bounds in EPSG:4326
#                 tile_bounds = mercantile.bounds(tile)
                
#                 # Calculate the affine transform for the dataset to tile conversion
#                 dst_transform = from_bounds(
#                     float(Decimal(tile_bounds.west)),
#                     float(Decimal(tile_bounds.south)),
#                     float(Decimal(tile_bounds.east)),
#                     float(Decimal(tile_bounds.north)),
#                     512, 512
#                 )
                
#                 # Create an empty array for each color channel
#                 reprojected_data = np.zeros((dataset.count, 512, 512), dtype=np.uint8)
                
#                 # Reproject the data to the tile coordinates for each color channel
#                 for i in range(dataset.count):
#                     reprojected_band = np.zeros((512, 512), dtype=np.float32)
#                     reproject(
#                         source=rasterio.band(dataset, i + 1),
#                         destination=reprojected_band,
#                         src_transform=dataset.transform,
#                         src_crs=dataset.crs,
#                         dst_transform=dst_transform,
#                         # dst_crs='EPSG:3857',
#                         dst_crs=target_crs,
#                         resampling=Resampling.bilinear
#                     )
#                     # Normalize the reprojected data to the range [0, 255] for each channel
#                     min_val = np.min(reprojected_band)
#                     max_val = np.max(reprojected_band)
#                     if min_val != max_val:
#                         reprojected_band = ((reprojected_band - min_val) / (max_val - min_val) * 255).astype(np.uint8)
#                     else:
#                         reprojected_band = np.zeros_like(reprojected_band, dtype=np.uint8)
                    
#                     reprojected_data[i] = reprojected_band
                
#                 # Combine the reprojected data into an RGBA image
#                 if dataset.count == 3:
#                     reprojected_image = Image.merge("RGB", [Image.fromarray(reprojected_data[i], 'L') for i in range(3)]).convert('RGBA')
#                 elif dataset.count == 4:
#                     reprojected_image = Image.merge("RGBA", [Image.fromarray(reprojected_data[i], 'L') for i in range(4)])
#                 else:
#                     raise ValueError("Unsupported number of channels")
                
#                 # Create a mask to handle transparency
#                 mask = Image.fromarray((np.max(reprojected_data, axis=0) > 0).astype(np.uint8) * 255, 'L')
                
#                 # Merge the reprojected image with the existing tile image
#                 tile_img.paste(reprojected_image, (0, 0), mask)
        
#         # Save the tile
#         tile_img.save(tile_path)

# # Read the GeoTIFF file and create slippy tiles
# def create_slippy_tiles(geotiff_paths, zoom_level_start=8):
#     for zoom_level in range(zoom_level_start, 11):
#         tile_infos = []
#         processed_tiles = set()
        
#         for geotiff_path in geotiff_paths:
#             with rasterio.open(geotiff_path) as dataset:
#                 # Get the bounds of the dataset
#                 bounds = dataset.bounds
#                 # Transform the GeoTIFF bounds to EPSG:4326
#                 geo_bounds_latlon = transform_bounds(dataset.crs, target_crs, *bounds)
#                 # print(f"GeoTIFF {geotiff_path} bounds in EPSG:4326: {geo_bounds_latlon}")
                
#                 # Get the tiles that intersect with the GeoTIFF bounds at the specified zoom level
#                 tiles = list(mercantile.tiles(
#                     float(Decimal(geo_bounds_latlon[0])),
#                     float(Decimal(geo_bounds_latlon[1])),
#                     float(Decimal(geo_bounds_latlon[2])),
#                     float(Decimal(geo_bounds_latlon[3])),
#                     zoom_level
#                 ))
#                 for tile in tiles:
#                     tile_id = (tile.z, tile.x, tile.y)
#                     if tile_id not in processed_tiles:
#                         tile_infos.append((geotiff_paths, zoom_level, tile))
#                         processed_tiles.add(tile_id)
        
#         # Use multiprocessing to process tiles in parallel
#         with Pool(cpu_count()) as pool:
#             for _ in tqdm(pool.imap_unordered(process_tile, tile_infos), total=len(tile_infos), desc=f'Processing zoom level {zoom_level}'):
#                 pass

# # Main function
# def main():
#     geotiff_paths = find_all_geotiffs(reprojected_dir)
#     if not geotiff_paths:
#         # print("No GeoTIFF files found in the './reprojected' directory.")
#         return
    
#     create_slippy_tiles(geotiff_paths)
#     print("Slippy tiles created.")

# if __name__ == "__main__":
#     main()
import os
import numpy as np
import rasterio
import mercantile
from PIL import Image
from rasterio.warp import reproject, Resampling, transform_bounds
from rasterio.transform import from_bounds
from multiprocessing import Pool, cpu_count
from filelock import FileLock
from decimal import Decimal, getcontext
from tqdm import tqdm
import argparse
import shutil

# Set precision for Decimal calculations
getcontext().prec = 20
target_crs = 'EPSG:4326'

# Find all GeoTIFF files in the directory
def find_all_geotiffs(directory):
    return [os.path.join(directory, file) for file in os.listdir(directory) if file.endswith('.tif') or file.endswith('.tiff')]

# Function to process a single tile
def process_tile(tile_info):
    geotiff_paths, zoom_level, tile, tiles_dir = tile_info

    tile_dir = os.path.join(tiles_dir, str(tile.z), str(tile.x))
    os.makedirs(tile_dir, exist_ok=True)
    tile_path = os.path.join(tile_dir, f'{tile.y}.png')
    lock_path = tile_path + '.lock'
    
    with FileLock(lock_path):
        # Initialize an empty image for the tile
        tile_img = Image.new('RGBA', (512, 512), (0, 0, 0, 0))
        
        for geotiff_path in geotiff_paths:
            with rasterio.open(geotiff_path) as dataset:
                # Get the tile bounds in EPSG:4326
                tile_bounds = mercantile.bounds(tile)
                
                # Calculate the affine transform for the dataset to tile conversion
                dst_transform = from_bounds(
                    float(Decimal(tile_bounds.west)),
                    float(Decimal(tile_bounds.south)),
                    float(Decimal(tile_bounds.east)),
                    float(Decimal(tile_bounds.north)),
                    512, 512
                )
                
                # Create an empty array for each color channel
                reprojected_data = np.zeros((dataset.count, 512, 512), dtype=np.uint8)
                
                # Reproject the data to the tile coordinates for each color channel
                for i in range(dataset.count):
                    reprojected_band = np.zeros((512, 512), dtype=np.float32)
                    reproject(
                        source=rasterio.band(dataset, i + 1),
                        destination=reprojected_band,
                        src_transform=dataset.transform,
                        src_crs=dataset.crs,
                        dst_transform=dst_transform,
                        dst_crs=target_crs,
                        resampling=Resampling.bilinear
                    )
                    # Normalize the reprojected data to the range [0, 255] for each channel
                    min_val = np.min(reprojected_band)
                    max_val = np.max(reprojected_band)
                    if min_val != max_val:
                        reprojected_band = ((reprojected_band - min_val) / (max_val - min_val) * 255).astype(np.uint8)
                    else:
                        reprojected_band = np.zeros_like(reprojected_band, dtype=np.uint8)
                    
                    reprojected_data[i] = reprojected_band
                
                # Combine the reprojected data into an RGBA image
                if dataset.count == 3:
                    reprojected_image = Image.merge("RGB", [Image.fromarray(reprojected_data[i], 'L') for i in range(3)]).convert('RGBA')
                elif dataset.count == 4:
                    reprojected_image = Image.merge("RGBA", [Image.fromarray(reprojected_data[i], 'L') for i in range(4)])
                else:
                    raise ValueError("Unsupported number of channels")
                
                # Create a mask to handle transparency
                mask = Image.fromarray((np.max(reprojected_data, axis=0) > 0).astype(np.uint8) * 255, 'L')
                
                # Merge the reprojected image with the existing tile image
                tile_img.paste(reprojected_image, (0, 0), mask)
        
        # Save the tile
        tile_img.save(tile_path)

# Read the GeoTIFF file and create slippy tiles
def create_slippy_tiles(geotiff_paths, zoom_level_start, zoom_level_end, tiles_dir):
    for zoom_level in range(zoom_level_start, zoom_level_end + 1):
        tile_infos = []
        processed_tiles = set()
        
        for geotiff_path in geotiff_paths:
            with rasterio.open(geotiff_path) as dataset:
                # Get the bounds of the dataset
                bounds = dataset.bounds
                # Transform the GeoTIFF bounds to EPSG:4326
                geo_bounds_latlon = transform_bounds(dataset.crs, target_crs, *bounds)
                
                # Get the tiles that intersect with the GeoTIFF bounds at the specified zoom level
                tiles = list(mercantile.tiles(
                    float(Decimal(geo_bounds_latlon[0])),
                    float(Decimal(geo_bounds_latlon[1])),
                    float(Decimal(geo_bounds_latlon[2])),
                    float(Decimal(geo_bounds_latlon[3])),
                    zoom_level
                ))
                for tile in tiles:
                    tile_id = (tile.z, tile.x, tile.y)
                    if tile_id not in processed_tiles:
                        tile_infos.append((geotiff_paths, zoom_level, tile, tiles_dir))
                        processed_tiles.add(tile_id)
        
        # Use multiprocessing to process tiles in parallel
        with Pool(cpu_count()) as pool:
            for _ in tqdm(pool.imap_unordered(process_tile, tile_infos), total=len(tile_infos), desc=f'Processing zoom level {zoom_level}'):
                pass

# Main function
def main():
    # Argument parser setup
    parser = argparse.ArgumentParser(description='Generate slippy tiles from GeoTIFF files.')
    parser.add_argument('--start_zoom', type=int, default=8, help='Start zoom level (default: 8)')
    parser.add_argument('--end_zoom', type=int, default=11, help='End zoom level (default: 11)')
    parser.add_argument('--input_dir', type=str, default='./reprojected', help='Input directory containing GeoTIFF files (default: ./reprojected)')
    parser.add_argument('--output_dir', type=str, default='./tiles', help='Output directory for generated tiles (default: ./tiles)')
    args = parser.parse_args()

    # Ensure output directory exists
    os.makedirs(args.output_dir, exist_ok=True)

    # Find all GeoTIFF files in the input directory
    geotiff_paths = find_all_geotiffs(args.input_dir)
    if not geotiff_paths:
        print(f"No GeoTIFF files found in the '{args.input_dir}' directory.")
        return
    
    # Create slippy tiles
    create_slippy_tiles(geotiff_paths, args.start_zoom, args.end_zoom, args.output_dir)
    print("Slippy tiles created.")
    
    # Copy JSON file from input directory to output directory
    json_file = os.path.join(args.input_dir, 'update_metadata.json')
    if os.path.exists(json_file):
        shutil.copy(json_file, args.output_dir)
        print("JSON metadata file copied to the output directory.")
    else:
        print("JSON metadata file not found in the input directory.")

if __name__ == "__main__":
    main()
