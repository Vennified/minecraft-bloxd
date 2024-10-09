import os
import shutil
import zipfile
import tempfile
import time
import logging
import cloudinary
import cloudinary.uploader
import cloudinary.api
import requests
from flask import Flask, request, redirect, url_for, render_template, flash, send_file, jsonify
from werkzeug.utils import secure_filename
from PIL import Image

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)
app.secret_key = '4S$eJ7dL3pR9t8yU2i1o'

cloudinary.config(
    cloud_name='dmlqwwxpi',
    api_key='421642484339792',
    api_secret='G02yp4PpcEaXQIa062k_IxlUurw'
)

BASE_FOLDER = os.environ.get('BASE_FOLDER', 'base_pack')
UPLOAD_FOLDER = tempfile.mkdtemp()
ALLOWED_EXTENSIONS = {'zip', 'jar'}
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def extract_if_archive_cloudinary(file_url, public_id):
    temp_dir = tempfile.mkdtemp()
    local_zip_path = os.path.join(temp_dir, f"{public_id}.zip")
    os.makedirs(os.path.dirname(local_zip_path), exist_ok=True)
    response = requests.get(file_url)
    with open(local_zip_path, 'wb') as f:
        f.write(response.content)
    extracted_folder = os.path.splitext(local_zip_path)[0]
    with zipfile.ZipFile(local_zip_path, 'r') as zip_ref:
        zip_ref.extractall(extracted_folder)
    logger.info(f"Extracted {local_zip_path} to {extracted_folder}")
    return extracted_folder

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
    logger.error("Blocks folder not found in the resource pack.")
    raise FileNotFoundError("Blocks folder not found in the resource pack.")

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
                    logger.info(f"Skipping non-PNG file: {filename}")
        else:
            logger.info("Resource pack is 32x or lower, no resizing necessary.")

def rename_images(blocks_folder, rename_map):
    temp_folder = tempfile.mkdtemp()
    for old_name, new_name in rename_map.items():
        old_path = os.path.join(blocks_folder, f"{old_name}.png")
        new_path_temp = os.path.join(temp_folder, f"{new_name}.png")
        if os.path.exists(old_path):
            shutil.copy2(old_path, new_path_temp)
            logger.info(f"Renamed {old_name}.png to {new_name}.png and moved to temp folder")
        else:
            logger.info(f"Image {old_name}.png not found for renaming")
    return temp_folder

def copy_overridden_images(blocks_folder, temp_folder, override_list):
    for item in override_list:
        item_path = os.path.join(blocks_folder, f"{item}.png")
        if os.path.exists(item_path):
            shutil.copy2(item_path, os.path.join(temp_folder, f"{item}.png"))
            logger.info(f"Copied overridden {item}.png to temp folder")
        else:
            logger.info(f"Override image {item}.png not found")

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

def zip_base_pack(base_folder_copy, public_id):
    parent_folder_name = "Converted Texture Pack"
    zip_filename = os.path.join(app.config['UPLOAD_FOLDER'], f"{parent_folder_name}.zip")
    try:
        with zipfile.ZipFile(zip_filename, 'w', zipfile.ZIP_DEFLATED) as zipf:
            for root, dirs, files in os.walk(base_folder_copy):
                for file in files:
                    file_path = os.path.join(root, file)
                    rel_path_in_base = os.path.relpath(file_path, base_folder_copy)
                    arcname = os.path.join(parent_folder_name, rel_path_in_base)
                    zipf.write(file_path, arcname)
        logger.info(f"Zipped {base_folder_copy} to {zip_filename}")
        result = cloudinary.uploader.upload(zip_filename, resource_type="raw", folder="processed_packs/")
        return result['secure_url']
    except Exception as e:
        logger.error(f"Error zipping folder {base_folder_copy}: {str(e)}")
        raise

def copy_to_base_folder(temp_folder, base_folder_copy):
    textures_folder = os.path.join(base_folder_copy, "textures")
    os.makedirs(textures_folder, exist_ok=True)
    for item in os.listdir(temp_folder):
        if item.endswith(".png"):
            shutil.copy2(os.path.join(temp_folder, item), os.path.join(textures_folder, item))
            logger.info(f"Copied {item} to {textures_folder}, replacing if it already exists")

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
            try:
                filename = secure_filename(file.filename)
                result = cloudinary.uploader.upload(file, folder="uploads/", resource_type="raw")
                file_url = result['secure_url']
                public_id = result['public_id']
                
                resource_pack_folder = extract_if_archive_cloudinary(file_url, public_id)
                blocks_folder = get_blocks_folder(resource_pack_folder)
                
                resize_images_to_32x(blocks_folder)
                
                rename_map = {
                    
                }
                temp_folder = rename_images(blocks_folder, rename_map)
                
                override_list = [
                    
                ]
                copy_overridden_images(blocks_folder, temp_folder, override_list)
                
                base_folder_copy = copy_base_pack(BASE_FOLDER)
                copy_to_base_folder(temp_folder, base_folder_copy)
                
                cloudinary_url = zip_base_pack(base_folder_copy, public_id)

                return jsonify({
                "message": "File processed successfully",
                "download_url": url_for('download_file', filename=os.path.basename(cloudinary_url), _external=True)
            })
                
            except Exception as e:
                logger.error(f"An error occurred during processing: {str(e)}")
                return jsonify({"error": str(e)}), 500
    return render_template('index.html')

@app.route('/download/<path:filename>', methods=['GET'])
def download_file(filename):
    try:
        # Check if the file exists in the UPLOAD_FOLDER
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], os.path.basename(filename))
        if os.path.exists(file_path):
            return send_file(file_path, as_attachment=True)
        else:
            # If not in UPLOAD_FOLDER, assume it's a Cloudinary URL
            return redirect(filename)
    except Exception as e:
        logger.error(f"Error in download_file: {str(e)}")
        return jsonify({"error": str(e)}), 404


if __name__ == '__main__':
    debug_mode = os.environ.get('FLASK_DEBUG', 'false').lower() == 'true'
    app.run(debug=debug_mode)