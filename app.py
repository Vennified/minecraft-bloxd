import os
import shutil
import zipfile
import tempfile
import time
import logging
import io
from flask import Flask, request, redirect, url_for, render_template, flash, send_file
from werkzeug.utils import secure_filename
from PIL import Image
from zipfile import ZipFile

# Set up logging to print to console
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger()

app = Flask(__name__)
app.secret_key = '4S$eJ7dL3pR9t8yU2i1o'

BASE_FOLDER = os.environ.get('BASE_FOLDER', 'base_pack')
UPLOAD_FOLDER = tempfile.mkdtemp()  
ALLOWED_EXTENSIONS = {'zip', 'jar'}
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# Extraction
def extract_if_archive(resource_pack):
    if resource_pack.endswith(".zip") or resource_pack.endswith(".jar"):
        with zipfile.ZipFile(resource_pack, 'r') as zip_ref:
            extracted_folder = os.path.splitext(resource_pack)[0]
            zip_ref.extractall(extracted_folder)
        logger.info(f"Extracted {resource_pack} to {extracted_folder}")
        return extracted_folder
    return resource_pack

# Locate blocks folder
def get_blocks_folder(pack_folder):
    for root, dirs, files in os.walk(pack_folder):
        if 'blocks' in dirs:
            blocks_folder = os.path.join(root, 'blocks')
            logger.info(f"Found blocks folder at {blocks_folder}")
            return blocks_folder
        if 'block' in dirs:
            blocks_folder = os.path.join(root, 'block')
            logger.info(f"Found block folder at {blocks_folder}")
            return blocks_folder
    raise FileNotFoundError("Blocks folder not found in the resource pack.")

# Resize images to 32x32
def resize_images_to_32x(blocks_folder):
    dirt_image_path = os.path.join(blocks_folder, "dirt.png")

    if not os.path.exists(dirt_image_path):
        raise FileNotFoundError("dirt.png not found in blocks folder, cannot determine resource pack resolution.")

    with Image.open(dirt_image_path) as dirt_img:
        width, height = dirt_img.size
        logger.info(f"dirt.png dimensions: {width}x{height}")

        if width > 32 and height > 32:
            logger.info("Resource pack is larger than 32x, resizing images.")
            for filename in os.listdir(blocks_folder):
                if filename.endswith(".png"):
                    img_path = os.path.join(blocks_folder, filename)
                    with Image.open(img_path) as img:
                        img_width, img_height = img.size
                        if img_width > 32 and img_height > 32:
                            img_resized = img.resize((32, 32), Image.NEAREST)
                            img_resized.save(img_path)
                            logger.info(f"Resized {filename} from {img_width}x{img_height} to 32x32.")
                        else:
                            logger.info(f"{filename} is {img_width}x{img_height}, no need to resize.")
        else:
            logger.info("Resource pack is 32x or lower, no resizing necessary.")

# Rename images
def rename_images(blocks_folder, rename_map, temp_folder):
    for old_name, new_name in rename_map.items():
        old_path = os.path.join(blocks_folder, f"{old_name}.png")
        new_path_temp = os.path.join(temp_folder, f"{new_name}.png")
        if os.path.exists(old_path):
            shutil.copy2(old_path, new_path_temp)
            logger.info(f"Renamed {old_name}.png to {new_name}.png and moved to temp folder")
        else:
            logger.info(f"Image {old_name}.png not found for renaming")

# Copy overridden images
def copy_overridden_images(blocks_folder, temp_folder, override_list):
    for item in override_list:
        item_path = os.path.join(blocks_folder, f"{item}.png")
        if os.path.exists(item_path):
            shutil.copy2(item_path, os.path.join(temp_folder, f"{item}.png"))
            logger.info(f"Copied overridden {item}.png to temp folder")
        else:
            logger.info(f"Override image {item}.png not found")

# Copy base pack
def copy_base_pack(base_folder):
    base_folder_path = os.path.abspath(base_folder)

    if not os.path.exists(base_folder_path):
        logger.error(f"Base pack folder '{base_folder_path}' does not exist.")
        raise FileNotFoundError(f"Base pack folder '{base_folder_path}' does not exist.")

    timestamp = time.strftime("%Y%m%d_%H%M%S")
    temp_base_folder_copy = tempfile.mkdtemp(dir='/tmp')

    base_folder_name = os.path.basename(base_folder_path)
    base_folder_copy = os.path.join(temp_base_folder_copy, f"{base_folder_name}_copy_{timestamp}")
    
    shutil.copytree(base_folder_path, base_folder_copy)

    logger.info(f"Copied base folder to {base_folder_copy}")
    return base_folder_copy

# Zip base pack
def zip_base_pack(base_folder_copy):
    parent_folder_name = "Converted Texture Pack"  # Define the parent folder name
    zip_filename = os.path.join(UPLOAD_FOLDER, f"{parent_folder_name}.zip")  # Save in uploads (/tmp)
    
    logger.info(f"Creating zip file at {zip_filename}")  # Log this for debugging

    try:
        with zipfile.ZipFile(zip_filename, 'w', zipfile.ZIP_DEFLATED) as zipf:
            for root, dirs, files in os.walk(base_folder_copy):
                for file in files:
                    file_path = os.path.join(root, file)
                    
                    # Compute the archive name by adding the parent folder
                    rel_path_in_base = os.path.relpath(file_path, base_folder_copy)
                    arcname = os.path.join(parent_folder_name, rel_path_in_base)
                    
                    # Write the file into the zip with the new archive name
                    zipf.write(file_path, arcname)
        
        logger.info(f"Zipped {base_folder_copy} to {zip_filename} with parent folder '{parent_folder_name}'")
        logger.info(f"Zip file exists? {os.path.exists(zip_filename)}")  # Check if the file exists after creation
        
    except Exception as e:
        logger.error(f"Error zipping folder {base_folder_copy}: {str(e)}")
        raise
    return zip_filename

# Copy images to base folder
def copy_to_base_folder(temp_folder, base_folder_copy):
    textures_folder = os.path.join(base_folder_copy, "textures")
    os.makedirs(textures_folder, exist_ok=True)

    for item in os.listdir(temp_folder):
        if item.endswith(".png"):
            shutil.copy2(os.path.join(temp_folder, item), os.path.join(textures_folder, item))
            logger.info(f"Copied {item} to {textures_folder}, replacing if it already exists")

# Cleanup temp folder
def cleanup_temp_folder(temp_folder):
    shutil.rmtree(temp_folder)
    logger.info(f"Cleaned up temporary folder at {temp_folder}")

# File upload route
@app.route('/', methods=['GET', 'POST'])
def upload_file():
    if request.method == 'POST':
        if 'file' not in request.files:
            flash('No file part')
            return redirect(request.url)
        
        file = request.files['file']
        if file.filename == '':
            flash('No selected file')
            return redirect(request.url)
        
        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            file.save(filepath)
            
            resource_pack_folder = extract_if_archive(filepath)
            blocks_folder = get_blocks_folder(resource_pack_folder)

            try:
                resize_images_to_32x(blocks_folder)
            except Exception as e:
                flash(f"Error resizing images: {str(e)}")
                return redirect(request.url)

            rename_map = {
                # Your renaming logic here
            }
            temp_folder = tempfile.mkdtemp()

            try:
                rename_images(blocks_folder, rename_map, temp_folder)
                
                override_list = [
                    # Your override images here
                ]
                copy_overridden_images(blocks_folder, temp_folder, override_list)

                base_folder_copy = copy_base_pack(BASE_FOLDER)
                copy_to_base_folder(temp_folder, base_folder_copy)

                # Create the zip file using the zip_base_pack function
                zip_filename = zip_base_pack(base_folder_copy)

                # Return a download button to the user
                return render_template('download.html', filename=zip_filename)

            except Exception as e:
                flash(f"An error occurred during processing: {str(e)}")
                return redirect(request.url)

    return render_template('index.html')

# Download file route
@app.route('/download/<filename>', methods=['GET'])
def download_file(filename):
    file_path = os.path.join(UPLOAD_FOLDER, filename)
    
    logger.info(f"Attempting to download file: {file_path}")

    if os.path.exists(file_path):
        logger.info(f"File found: {file_path}")
        response = send_file(file_path, as_attachment=True)
        
        try:
            cleanup_temp_folder(UPLOAD_FOLDER)
            logger.info(f"Cleaned up temporary folder after download: {UPLOAD_FOLDER}")
        except Exception as e:
            logger.error(f"Error during cleanup: {str(e)}")
        
        return response
    else:
        logger.error(f"File '{filename}' not found at {file_path}.")
        flash(f"File '{filename}' not found.")
        return redirect(url_for('upload_file'))


# Helper function to zip the modified base folder
def zip_base_pack(base_folder):
    zip_filename = os.path.join(app.config['UPLOAD_FOLDER'], "Converted_Texture_Pack.zip")
    with ZipFile(zip_filename, 'w') as zipf:
        for root, dirs, files in os.walk(base_folder):
            for file in files:
                file_path = os.path.join(root, file)
                rel_path_in_base = os.path.relpath(file_path, base_folder)
                zipf.write(file_path, rel_path_in_base)
    return zip_filename

if __name__ == '__main__':
    debug_mode = os.environ.get('FLASK_DEBUG', 'false').lower() == 'true'
    app.run(debug=debug_mode)