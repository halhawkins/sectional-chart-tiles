# import os
# import argparse
# import logging
# import rasterio
# from rasterio.warp import transform_bounds
# import mercantile
# from PIL import Image
# import numpy as np
# from tqdm import tqdm

# # Setup logging
# logging.basicConfig(filename='tiling.log', level=logging.INFO, 
#                     format='%(asctime)s %(levelname)s:%(message)s')

# def create_tiles(input_folder, output_folder, zoom_start, zoom_end, tile_size):
#     for filename in tqdm(os.listdir(input_folder), desc='Processing GeoTIFFs'):
#         if filename.endswith('.tif'):
#             raster_path = os.path.join(input_folder, filename)
#             try:
#                 with rasterio.open(raster_path) as src:
#                     bounds = src.bounds
#                     dst_crs = src.crs.to_string()
                    
#                     # Get the bounds in the destination CRS
#                     dst_bounds = transform_bounds(src.crs, 'EPSG:4326', *bounds)

#                     # Generate tiles
#                     for zoom in range(zoom_start, zoom_end + 1):
#                         tiles = list(mercantile.tiles(*dst_bounds, zoom))
#                         for tile in tqdm(tiles, desc=f'Zoom level {zoom}', leave=False):
#                             process_tile(src, tile, output_folder, dst_crs, tile_size, zoom)
#                 logging.info(f'Successfully generated tiles for: {raster_path}')
#             except Exception as e:
#                 logging.error(f'Error generating tiles for {raster_path}: {e}')

# def process_tile(src, tile, output_folder, dst_crs, tile_size, zoom):
#     tile_bounds = mercantile.bounds(tile)
#     dst_transform = rasterio.transform.from_bounds(*tile_bounds, tile_size, tile_size)
#     dst_meta = src.meta.copy()
#     dst_meta.update({
#         'driver': 'GTiff',
#         'height': tile_size,
#         'width': tile_size,
#         'transform': dst_transform,
#         'crs': dst_crs
#     })
    
#     window = rasterio.windows.from_bounds(*tile_bounds, transform=src.transform)
#     tile_data = src.read(window=window, out_shape=(src.count, tile_size, tile_size), resampling=rasterio.enums.Resampling.nearest)

#     # Check if the read data is empty or nodata
#     if tile_data.size == 0 or np.all(tile_data == src.nodata):
#         logging.warning(f'Empty or nodata tile: {tile.z}/{tile.x}/{tile.y}')
#         return

#     # Normalize and convert to uint8 for PNG output
#     if tile_data.dtype != np.uint8:
#         tile_data = ((tile_data - tile_data.min()) / (tile_data.max() - tile_data.min()) * 255).astype(np.uint8)

#     # Save the tile as PNG
#     tile_img = np.transpose(tile_data, axes=[1, 2, 0])  # Transpose to (height, width, bands)
#     tile_img = Image.fromarray(tile_img)
    
#     tile_folder = os.path.join(output_folder, str(zoom), str(tile.x))
#     os.makedirs(tile_folder, exist_ok=True)
#     tile_path = os.path.join(tile_folder, f'{tile.y}.png')
#     tile_img.save(tile_path)
    
#     # Log the tile creation
#     logging.info(f'Saved tile {zoom}/{tile.x}/{tile.y}.png')

# def main():
#     parser = argparse.ArgumentParser(description='Generate XYZ tiles from GeoTIFF files.')
#     parser.add_argument('--input_folder', type=str, default='./reprojected/', help='Input folder containing GeoTIFF files.')
#     parser.add_argument('--output_folder', type=str, default='./tiles/', help='Output folder to save the tiles.')
#     parser.add_argument('--zoom_start', type=int, default=0, help='Start zoom level.')
#     parser.add_argument('--zoom_end', type=int, default=10, help='End zoom level.')
#     parser.add_argument('--tile_size', type=int, default=512, help='Size of the output tiles.')

#     args = parser.parse_args()

#     # Ensure output folder exists
#     os.makedirs(args.output_folder, exist_ok=True)

#     # Generate tiles
#     create_tiles(args.input_folder, args.output_folder, args.zoom_start, args.zoom_end, args.tile_size)

# if __name__ == '__main__':
#     main()
import os
import argparse
import logging
import rasterio
from rasterio.warp import reproject, Resampling, calculate_default_transform
from rasterio.transform import from_bounds, array_bounds
import mercantile
from PIL import Image
import numpy as np
from tqdm import tqdm

# Setup logging
logging.basicConfig(filename='tiling.log', level=logging.INFO, 
                    format='%(asctime)s %(levelname)s:%(message)s')

def reproject_geotiff_to_tile(src, tile_bounds, dst_transform, dst_crs, tile_size, tile_bands):
    transform, width, height = calculate_default_transform(
        src.crs, dst_crs, src.width, src.height, *src.bounds)
    
    window = rasterio.windows.from_bounds(*tile_bounds, transform=src.transform)
    
    dest = np.zeros((tile_bands, tile_size, tile_size), dtype=np.uint8)
    
    for i in range(1, min(src.count, tile_bands) + 1):
        reproject(
            source=rasterio.band(src, i),
            destination=dest[i - 1],
            src_transform=src.transform,
            src_crs=src.crs,
            dst_transform=dst_transform,
            dst_crs=dst_crs,
            resampling=Resampling.nearest,
            src_window=window,
            dst_window=window)
    
    return dest

def create_tiles(input_folder, output_folder, zoom_start, zoom_end, tile_size, tile_bands):
    print(f'zoom = {zoom_start}-{zoom_end}')
    # Loop through zoom levels
    for zoom in range(zoom_start, zoom_end + 1):
        logging.info(f'Processing zoom level {zoom}')
        # Determine bounds for the current zoom level
        tiles = list(mercantile.tiles(-180, -85.0511, 180, 85.0511, zoom))
        
        # Process each tile
        for tile in tqdm(tiles, desc=f'Zoom level {zoom}'):
            tile_bounds = mercantile.bounds(tile)
            dst_transform = from_bounds(*tile_bounds, tile_size, tile_size)
            
            tile_data = np.zeros((tile_bands, tile_size, tile_size), dtype=np.uint8)
            tile_filled = False

            for filename in os.listdir(input_folder):
                if filename.endswith('.tif'):
                    raster_path = os.path.join(input_folder, filename)
                    try:
                        with rasterio.open(raster_path) as src:
                            src_bounds = array_bounds(src.height, src.width, src.transform)
                            if (
                                tile_bounds.west < src_bounds[2] and tile_bounds.east > src_bounds[0] and
                                tile_bounds.south < src_bounds[3] and tile_bounds.north > src_bounds[1]
                            ):
                                data = reproject_geotiff_to_tile(src, tile_bounds, dst_transform, 'EPSG:3857', tile_size, tile_bands)
                                tile_data = np.maximum(tile_data, data)  # Merge the data
                                tile_filled = True
                    except Exception as e:
                        logging.error(f'Error processing {raster_path}: {e}')

            if tile_filled:
                save_tile(tile_data, output_folder, zoom, tile.x, tile.y)

def save_tile(tile_data, output_folder, zoom, x, y):
    # Normalize and convert to uint8 for PNG output
    if tile_data.dtype != np.uint8:
        tile_data = ((tile_data - tile_data.min()) / (tile_data.max() - tile_data.min()) * 255).astype(np.uint8)

    # Save the tile as PNG
    tile_img = np.transpose(tile_data, axes=[1, 2, 0])  # Transpose to (height, width, bands)
    tile_img = Image.fromarray(tile_img)
    
    tile_folder = os.path.join(output_folder, str(zoom), str(x))
    os.makedirs(tile_folder, exist_ok=True)
    tile_path = os.path.join(tile_folder, f'{y}.png')
    tile_img.save(tile_path)

    # Log the tile creation
    logging.info(f'Saved tile {zoom}/{x}/{y}.png')

def main():
    parser = argparse.ArgumentParser(description='Generate XYZ tiles from GeoTIFF files.')
    parser.add_argument('--input_folder', type=str, default='./reprojected/', help='Input folder containing GeoTIFF files.')
    parser.add_argument('--output_folder', type=str, default='./tiles/', help='Output folder to save the tiles.')
    parser.add_argument('--zoom_start', type=int, default=3, help='Start zoom level.')
    parser.add_argument('--zoom_end', type=int, default=10, help='End zoom level.')
    parser.add_argument('--tile_size', type=int, default=512, help='Size of the output tiles.')
    parser.add_argument('--tile_bands', type=int, default=3, help='Number of bands in the output tiles.')

    args = parser.parse_args()

    # Ensure output folder exists
    os.makedirs(args.output_folder, exist_ok=True)

    # Generate tiles
    create_tiles(args.input_folder, args.output_folder, args.zoom_start, args.zoom_end, args.tile_size, args.tile_bands)

if __name__ == '__main__':
    main()
