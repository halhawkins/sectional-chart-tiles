import os
import rasterio
from rasterio.warp import calculate_default_transform, reproject, Resampling
import logging
from tqdm import tqdm
from multiprocessing import Pool, cpu_count

# Setup logging
logging.basicConfig(filename='reprojecting.log', level=logging.INFO, 
                    format='%(asctime)s %(levelname)s:%(message)s')

def reproject_raster(input_path, output_path, target_crs, nodata_value=None):
    try:
        with rasterio.open(input_path) as src:
            transform, width, height = calculate_default_transform(
                src.crs, target_crs, src.width, src.height, *src.bounds)
            kwargs = src.meta.copy()
            kwargs.update({
                'crs': target_crs,
                'transform': transform,
                'width': width,
                'height': height,
                'nodata': nodata_value
            })

            with rasterio.open(output_path, 'w', **kwargs) as dst:
                for i in tqdm(range(1, src.count + 1), desc=f'Reprojecting {os.path.basename(input_path)}', leave=False):
                    reproject(
                        source=rasterio.band(src, i),
                        destination=rasterio.band(dst, i),
                        src_transform=src.transform,
                        src_crs=src.crs,
                        dst_transform=transform,
                        dst_crs=target_crs,
                        resampling=Resampling.bilinear,
                        dst_nodata=nodata_value)
        logging.info(f'Successfully reprojected: {input_path}')
    except Exception as e:
        logging.error(f'Error reprojecting {input_path}: {e}')

def process_file(args):
    input_path, output_path, target_crs, nodata_value = args
    reproject_raster(input_path, output_path, target_crs, nodata_value)

# Paths
input_folder = './clipped/'
output_folder = './reprojected/'

# Target CRS (example: EPSG:4326 for WGS84)
target_crs = 'EPSG:3857'

# Nodata value (example: 0 for black, or any other value that makes sense for your data)
nodata_value = 0

# Ensure output folder exists
os.makedirs(output_folder, exist_ok=True)

# Process each GeoTIFF in the input folder
tiff_files = [filename for filename in os.listdir(input_folder) if filename.endswith('.tif')]

# Prepare arguments for multiprocessing
args = [(os.path.join(input_folder, filename), os.path.join(output_folder, filename), target_crs, nodata_value) for filename in tiff_files]

# Use multiprocessing to process files concurrently
if __name__ == '__main__':
    with Pool(cpu_count()) as pool:
        list(tqdm(pool.imap(process_file, args), total=len(args), desc='Reprojecting GeoTIFFs'))
