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
from flask import Flask, request, redirect, url_for, render_template, flash, send_file, jsonify, stream_with_context, Response
from werkzeug.utils import secure_filename
from PIL import Image

logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
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


def delete_unnecessary_content(pack_folder):
    
    static_paths = [
        "pack.png",
        "pack.mcmeta",
        "assets/minecraft/atlases",
        "assets/minecraft/blockstates",
        "assets/minecraft/font",
        "assets/minecraft/lang",
        "assets/minecraft/models",
        "assets/minecraft/optifine",
        "assets/minecraft/particles",
        "assets/minecraft/shaders",
        "assets/minecraft/texts",
        "assets/minecraft/textures/colormap",
        "assets/minecraft/textures/effect",
        "assets/minecraft/textures/entity",
        "assets/minecraft/textures/environment",
        "assets/minecraft/textures/font",
        "assets/minecraft/textures/gui",
        "assets/minecraft/textures/item",
        "assets/minecraft/textures/map",
        "assets/minecraft/textures/misc",
        "assets/minecraft/textures/mod_effect",
        "assets/minecraft/textures/models",
        "assets/minecraft/textures/painting",
        "assets/minecraft/textures/particle",
        "assets/minecraft/textures/trims",

        # Static paths (Bedrock packs)
        "animation_controllers",
        "animations",
        "attachables",
        "cameras",
        "entity",
        "fogs",
        "font",
        "models",
        "particles",
        "render_controllers",
        "sounds",
        "texts",
        "ui",
        ".gitignore",
        "biomes_client.json",
        "blocks.json",
        "pack_icon.png"
        "manifest.json",
        "README.md",
        "sounds.json",
        "splashes.json",
        "atlases",
        "textures/colormap",
        "textures/entity",
        "textures/environment",
        "textures/gui",
        "textures/items",
        "textures/map",
        "textures/misc",
        "textures/models",
        "textures/painting",
        "textures/particle",
        "textures/persona_thumbnails",
        "textures/trims",
        "textures/ui",
        "textures/flame_atlas.png",
        "textures/flipbook_textures.json",
        "textures/forcefield_atlas.png",
        "textures/item_texture.json",
        "textures/terrain_texture.json"
    ]
    
    for static_path in static_paths:
        full_path = os.path.normpath(os.path.join(pack_folder, static_path))
        
        if os.path.exists(full_path):
            try:
                if os.path.isfile(full_path):
                    os.remove(full_path)
                    logger.info(f"Deleted file: {full_path}")
                elif os.path.isdir(full_path):
                    shutil.rmtree(full_path)
                    logger.info(f"Deleted directory: {full_path}")
            except Exception as e:
                logger.error(f"Error deleting {full_path}: {str(e)}")
        else:
            logger.info(f"Not found: {full_path}")
    
    for root, dirs, files in os.walk(pack_folder, topdown=False):
        for dir in dirs:
            try:
                dir_path = os.path.join(root, dir)
                if not os.listdir(dir_path):
                    os.rmdir(dir_path)
                    logger.info(f"Deleted empty directory: {dir_path}")
            except Exception as e:
                logger.error(f"Error deleting empty directory {dir_path}: {str(e)}")
    
    logger.info("Finished deleting specified content")

def extract_if_archive_cloudinary(file_url, public_id):
    logger.info(f"Starting extraction process for file: {file_url}")
    temp_dir = tempfile.mkdtemp()
    local_zip_path = os.path.join(temp_dir, f"{public_id}.zip")
    
    try:
        os.makedirs(os.path.dirname(local_zip_path), exist_ok=True)
        response = requests.get(file_url)
        response.raise_for_status()  # Raises an HTTPError for bad responses
        
        with open(local_zip_path, 'wb') as f:
            f.write(response.content)
        logger.info(f"Downloaded zip file to: {local_zip_path}")
        
        extracted_folder = os.path.splitext(local_zip_path)[0]
        with zipfile.ZipFile(local_zip_path, 'r') as zip_ref:
            zip_ref.extractall(extracted_folder)
        logger.info(f"Extracted {local_zip_path} to {extracted_folder}")

        delete_unnecessary_content(extracted_folder)

        return extracted_folder
    except requests.exceptions.RequestException as e:
        logger.error(f"Error downloading file: {str(e)}")
    except zipfile.BadZipFile:
        logger.error(f"Error: The file is not a zip file or is corrupted")
    except Exception as e:
        logger.error(f"Unexpected error during extraction: {str(e)}")
    
    return None

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
    temp_dir = tempfile.mkdtemp()
    zip_filename = os.path.join(temp_dir, f"{parent_folder_name}.zip")
    
    try:
        with zipfile.ZipFile(zip_filename, 'w', zipfile.ZIP_DEFLATED) as zipf:
            for root, dirs, files in os.walk(base_folder_copy):
                for file in files:
                    file_path = os.path.join(root, file)
                    rel_path_in_base = os.path.relpath(file_path, base_folder_copy)
                    arcname = os.path.join(parent_folder_name, rel_path_in_base)
                    zipf.write(file_path, arcname)
        
        logger.info(f"Zipped {base_folder_copy} to {zip_filename}")
        
        # Upload to Cloudinary
        result = cloudinary.uploader.upload(zip_filename, 
                                            resource_type="raw", 
                                            folder="processed_packs/",
                                            use_filename=True,
                                            unique_filename=False)
        
        return result['secure_url'], zip_filename
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
            return jsonify({"error": "No file part"}), 400
        file = request.files['file']
        if file.filename == '':
            return jsonify({"error": "No selected file"}), 400
        if file and allowed_file(file.filename):
            try:
                filename = secure_filename(file.filename)
                temp_dir = tempfile.mkdtemp()
                local_zip_path = os.path.join(temp_dir, filename)
                
                file.save(local_zip_path)
                logger.info(f"File saved locally at: {local_zip_path}")

                extracted_folder = os.path.splitext(local_zip_path)[0]
                with zipfile.ZipFile(local_zip_path, 'r') as zip_ref:
                    zip_ref.extractall(extracted_folder)
                logger.info(f"Extracted {local_zip_path} to {extracted_folder}")

                logger.info(f"Deleting unnecessary content from {extracted_folder}")
                delete_unnecessary_content(extracted_folder)

                blocks_folder = get_blocks_folder(extracted_folder)

                resize_images_to_32x(blocks_folder)

                rename_map = {
                    
                }
                temp_folder = rename_images(blocks_folder, rename_map)

                override_list = [
                    
                ]
                copy_overridden_images(blocks_folder, temp_folder, override_list)

                base_folder_copy = copy_base_pack(BASE_FOLDER)

                copy_to_base_folder(temp_folder, base_folder_copy)

                parent_folder_name = "Converted_Texture_Pack"
                final_zip_filename = os.path.join(temp_dir, f"{parent_folder_name}.zip")
                with zipfile.ZipFile(final_zip_filename, 'w', zipfile.ZIP_DEFLATED) as zipf:
                    for root, dirs, files in os.walk(base_folder_copy):
                        for file in files:
                            file_path = os.path.join(root, file)
                            rel_path_in_base = os.path.relpath(file_path, base_folder_copy)
                            arcname = os.path.join(parent_folder_name, rel_path_in_base)
                            zipf.write(file_path, arcname)
                logger.info(f"Zipped modified content to: {final_zip_filename}")

                result = cloudinary.uploader.upload(final_zip_filename, 
                                                    resource_type="raw", 
                                                    folder="processed_packs/",
                                                    use_filename=True,
                                                    unique_filename=False)
                cloudinary_url = result['secure_url']
                logger.info(f"Zipped content uploaded to Cloudinary: {cloudinary_url}")

                app.config['TEMP_FILES'] = getattr(app.config, 'TEMP_FILES', {})
                temp_id = os.path.basename(final_zip_filename)
                app.config['TEMP_FILES'][temp_id] = final_zip_filename

                return jsonify({
                    "message": "File processed successfully",
                    "download_url": cloudinary_url  
                })
            except Exception as e:
                logger.error(f"An error occurred during processing: {str(e)}")
                return jsonify({"error": str(e)}), 500
    
    return render_template('index.html')


@app.route('/download/<filename>', methods=['GET'])
def download_file(filename):
    try:
        temp_files = app.config.get('TEMP_FILES', {})
        if filename in temp_files:
            return send_file(temp_files[filename], as_attachment=True, download_name=f"{filename}.zip")
        else:

            return redirect(filename)
    except Exception as e:
        logger.error(f"Error in download_file: {str(e)}")
        return jsonify({"error": str(e)}), 404
    
@app.route('/')
def index():
    return render_template('index.html')

if __name__ == '__main__':
    debug_mode = os.environ.get('FLASK_DEBUG', 'false').lower() == 'true'
    app.run(debug=debug_mode)