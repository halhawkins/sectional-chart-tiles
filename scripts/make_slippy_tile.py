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
import logging

# Set precision for Decimal calculations
getcontext().prec = 20
target_crs = 'EPSG:4326'

# Configure logging
logging.basicConfig(filename='tiles.log', level=logging.INFO, format='%(asctime)s %(levelname)s:%(message)s')

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
        tile_img = Image.new('RGBA', (512, 512), (0, 0, 0, 0))
        
        for geotiff_path in geotiff_paths:
            with rasterio.open(geotiff_path) as dataset:
                tile_bounds = mercantile.bounds(tile)
                dst_transform = from_bounds(
                    float(Decimal(tile_bounds.west)),
                    float(Decimal(tile_bounds.south)),
                    float(Decimal(tile_bounds.east)),
                    float(Decimal(tile_bounds.north)),
                    512, 512
                )
                
                reprojected_data = np.zeros((dataset.count, 512, 512), dtype=np.uint8)
                # logging.info(f"Dataset {dataset}")
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
                    min_val = np.min(reprojected_band)
                    max_val = np.max(reprojected_band)
                    
                    if min_val != max_val:
                        reprojected_band = ((reprojected_band - min_val) / (max_val - min_val) * 255).astype(np.uint8)
                    else:
                        reprojected_band = np.zeros_like(reprojected_band, dtype=np.uint8)
                    
                    reprojected_data[i] = reprojected_band
                    # logging.info(f"Reprojected band {i} x={tile.x} y={tile.y} {reprojected_band}")
                
                # Check if alpha band is present and valid
                if dataset.count == 4 and not np.all(reprojected_data[3] == 0):
                    reprojected_image = Image.merge("RGBA", [Image.fromarray(reprojected_data[i], 'L') for i in range(4)])
                else:
                    # Create alpha channel based on non-zero values in RGB channels
                    alpha_channel = (np.max(reprojected_data[:3], axis=0) > 0).astype(np.uint8) * 255
                    reprojected_image = Image.merge("RGBA", [Image.fromarray(reprojected_data[i], 'L') for i in range(3)] + [Image.fromarray(alpha_channel, 'L')])
                
                # Create a mask to handle transparency
                mask = Image.fromarray((np.max(reprojected_data[:3], axis=0) > 0).astype(np.uint8) * 255, 'L')
                
                # Merge the reprojected image with the existing tile image
                tile_img.paste(reprojected_image, (0, 0), mask)

        # Debugging: Check tile data before saving
        data = np.array(tile_img)
        alpha_channel = data[:, :, 3]
        # print(f"Tile {tile_path} alpha channel unique values: {np.unique(alpha_channel)}")

        # Check if the entire tile is transparent
        if np.all(alpha_channel == 0):
            logging.info(f"Tile {tile_path} is fully transparent.")
        else:
            tile_img.save(tile_path)
            logging.info(f"Saved tile: {tile_path}")

# Function to regenerate specific tiles or columns
def regenerate_tiles(geotiff_paths, zoom_level, tile_x, tile_y, tiles_dir):
    tile_infos = []
    if tile_y is not None:
        # Regenerate specific tile
        tile = mercantile.Tile(x=tile_x, y=tile_y, z=zoom_level)
        tile_infos.append((geotiff_paths, zoom_level, tile, tiles_dir))
    else:
        # Regenerate entire column
        for tile_y in range(0, 2**zoom_level):
            tile = mercantile.Tile(x=tile_x, y=tile_y, z=zoom_level)
            tile_infos.append((geotiff_paths, zoom_level, tile, tiles_dir))
    
    # Use multiprocessing to process tiles in parallel
    with Pool(cpu_count()) as pool:
        for _ in tqdm(pool.imap_unordered(process_tile, tile_infos), total=len(tile_infos), desc=f'Regenerating tiles at zoom level {zoom_level}, column {tile_x}'):
            pass

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
    parser = argparse.ArgumentParser(description='Generate or regenerate slippy tiles from GeoTIFF files.')
    parser.add_argument('--start_zoom', type=int, default=8, help='Start zoom level (default: 8)')
    parser.add_argument('--end_zoom', type=int, default=11, help='End zoom level (default: 11)')
    parser.add_argument('--input_dir', type=str, default='./reprojected', help='Input directory containing GeoTIFF files (default: ./reprojected)')
    parser.add_argument('--output_dir', type=str, default='./tiles', help='Output directory for generated tiles (default: ./tiles)')
    parser.add_argument('--zoom', type=int, help='Zoom level for regeneration')
    parser.add_argument('--tile_x', type=int, help='Tile column for regeneration')
    parser.add_argument('--tile_y', type=int, help='Tile row for regeneration (optional)')
    args = parser.parse_args()

    # Ensure output directory exists
    os.makedirs(args.output_dir, exist_ok=True)

    # Find all GeoTIFF files in the input directory
    geotiff_paths = find_all_geotiffs(args.input_dir)
    if not geotiff_paths:
        print(f"No GeoTIFF files found in the '{args.input_dir}' directory.")
        return
    
    if args.zoom is not None and args.tile_x is not None:
        # Regenerate specific tiles or columns
        regenerate_tiles(geotiff_paths, args.zoom, args.tile_x, args.tile_y, args.output_dir)
    else:
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
