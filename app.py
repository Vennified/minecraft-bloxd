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
from flask import Flask, request, redirect, url_for, render_template, flash
from werkzeug.utils import secure_filename
from PIL import Image

# Set up logging
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
                    "acacia_log": "log_plum",
            "acacia_planks": "planks_plum",
            "acacia_sapling": "plum_sapling",
            "birch_log": "log_aspen",
            "birch_planks": "planks_aspen",
            "birch_sapling": "aspen_sapling",
            "cherry_log": "log_cherry",
            "cherry_planks": "planks_cherry",
            "dark_oak_log": "cedar_log",
            "dark_oak_planks": "planks_cedar",
            "dark_oak_sapling": "cedar_sapling",
            "jungle_log": "log_elm",
            "jungle_planks": "planks_elm",
            "jungle_sapling": "elm_sapling",
            "mangrove_log": "log_palm",
            "mangrove_planks": "planks_palm",
            "mangrove_propagule": "palm_sapling",
            "spruce_log": "log_pine",
            "spruce_planks": "planks_pine",
            "spruce_sapling": "pine_sapling",
            "oak_log": "log_maple",
            "oak_planks": "planks_maple",
            "oak_sapling": "maple_sapling",
            "stripped_acacia_log": "stripped_plum_log",
            "stripped_birch_log": "stripped_aspen_log",
            "stripped_dark_oak_log": "stripped_cedar_log",
            "stripped_jungle_log": "stripped_elm_log",
            "stripped_mangrove_log": "stripped_palm_log",
            "stripped_oak_log": "stripped_maple_log",
            "stripped_spruce_log": "stripped_pine_log",
            "polished_andesite": "stone_andesite_smooth",
            "andesite": "stone_andesite",
            "polished_diorite": "stone_diorite_smooth",
            "diorite": "stone_diorite",
            "polished_granite": "stone_granite_smooth",
            "granite": "stone_granite",
            "prismarine_bricks": "green_bricks",
            "dark_prismarine": "dark_green_bricks",
            "red_sandstone_bottom": "red_sandstone",
            "sandstone_bottom": "sandstone_normal",
            "rooted_dirt": "rocky_dirt",
            "mossy_stone_bricks": "stonebrick_mossy",
            "smooth_stone_slab_side": "slab_smooth_stone_side",
            "cobblestone_mossy": "mossy_cobblestone",
            "chiseled_stone_bricks": "stonebrick_carved",
            "cobblestone": "messy_stone",
            "cracked_stone_bricks": "stonebrick_cracked",
            "stone_bricks": "stonebrick",
            "end_stone": "yellowstone",
            "nether_bricks": "nether_brick",
            "bricks": "brick",
            "chiseled_quartz_block": "quartz_block_chiseled",
            "netherite_block": "moonstone_block",
            "ancient_debris_side": "moonstone_ore",
            "jack_o_lantern": "pumpkin_face_on",
            "melon_side": "watermelon_side",
            "melon_top": "watermelon_top",
            "redstone_lamp": "redstone_lamp_off",
            "smithing_table_front": "artisan_table_side",
            "smithing_table_top": "artisan_table_top",
            "tnt_side": "moonstone_explosive_side",
            "tnt_top": "moonstone_explosive_top",
            "sweet_berry_bush_stage0": "berry_bush_stage0",
            "sweet_berry_bush_stage1": "berry_bush_stage1",
            "sweet_berry_bush_stage3": "berry_bush_stage2",
            "terracotta": "hardened_clay",
            "black_terracotta": "hardened_clay_stained_black",
            "blue_terracotta": "hardened_clay_stained_blue",
            "brown_terracotta": "hardened_clay_stained_brown",
            "cyan_terracotta": "hardened_clay_stained_cyan",
            "gray_terracotta": "hardened_clay_stained_gray",
            "green_terracotta": "hardened_clay_stained_green",
            "light_blue_terracotta": "hardened_clay_stained_light_blue",
            "lime_terracotta": "hardened_clay_stained_lime",
            "magenta_terracotta": "hardened_clay_stained_magenta",
            "orange_terracotta": "hardened_clay_stained_orange",
            "pink_terracotta": "hardened_clay_stained_pink",
            "purple_terracotta": "hardened_clay_stained_purple",
            "red_terracotta": "hardened_clay_stained_red",
            "silver_terracotta": "hardened_clay_stained_silver",
            "white_terracotta": "hardened_clay_stained_white",
            "yellow_terracotta": "hardened_clay_stained_yellow",
            "yellow_wool": "wool_colored_yellow",
            "blue_wool": "wool_colored_blue",
            "brown_wool": "wool_colored_brown",
            "cyan_wool": "wool_colored_cyan",
            "gray_wool": "wool_colored_gray",
            "green_wool": "wool_colored_green",
            "light_blue_wool": "wool_colored_light_blue",
            "light_grey_wool": "wool_colored_light_grey",
            "lime_wool": "wool_colored_lime",
            "magenta_wool": "wool_colored_magenta",
            "orange_wool": "wool_colored_orange",
            "pink_wool": "wool_colored_pink",
            "purple_wool": "wool_colored_purple",
            "red_wool": "wool_colored_red",
            "silver_wool": "wool_colored_silver",
            "white_wool": "wool_colored_white",
            "black_wool": "wool_colored_black",
            "concrete_black": "black_concrete",
            "concrete_blue": "blue_concrete",
            "concrete_brown": "brown_concrete",
            "concrete_cyan": "cyan_concrete",
            "concrete_gray": "gray_concrete",
            "concrete_green": "green_concrete",
            "concrete_light_blue": "light_blue_concrete",
            "concrete_lime": "lime_concrete",
            "concrete_magenta": "magenta_concrete",
            "concrete_orange": "orange_concrete",
            "concrete_pink": "pink_concrete",
            "concrete_purple": "purple_concrete",
            "concrete_red": "red_concrete",
            "concrete_silver": "silver_concrete",
            "concrete_white": "white_concrete",
            "concrete_yellow": "yellow_concrete",
            "dirt_podzol_top": "podzol_top",
            "dirt_with_roots": "rocky_dirt",
            "ender_chest_front": "moonstone_chest_front",
            "ender_chest_side": "moonstone_chest_side",
            "ender_chest_top": "moonstone_chest_top",
            "farmland_dry": "farmland",
            "flower_allium": "allium",
            "flower_blue_orchid": "blue_orchid",
            "flower_cornflower": "cornflower",
            "flower_dandelion": "dandelion",
            "flower_lily_of_the_valley": "lily_of_the_valley",
            "flower_oxeye_daisy": "oxeye_daisy",
            "flower_tulip_orange": "orange_tulip",
            "flower_tulip_pink": "pink_tulip",
            "flower_tulip_red": "red_tulip",
            "flower_tulip_white": "white_tulip",
            "flower_wither_rose": "wither_rose",
            "glazed_terracotta_black": "black_glazed_terracotta",
            "glazed_terracotta_blue": "blue_glazed_terracotta",
            "glazed_terracotta_brown": "brown_glazed_terracotta",
            "glazed_terracotta_cyan": "cyan_glazed_terracotta",
            "glazed_terracotta_gray": "gray_glazed_terracotta",
            "glazed_terracotta_green": "green_glazed_terracotta",
            "glazed_terracotta_light_blue": "light_blue_glazed_terracotta",
            "glazed_terracotta_lime": "lime_glazed_terracotta",
            "glazed_terracotta_magenta": "magenta_glazed_terracotta",
            "glazed_terracotta_orange": "orange_glazed_terracotta",
            "glazed_terracotta_pink": "pink_glazed_terracotta",
            "glazed_terracotta_purple": "purple_glazed_terracotta",
            "glazed_terracotta_red": "red_glazed_terracotta",
            "glazed_terracotta_silver": "silver_glazed_terracotta",
            "glazed_terracotta_white": "white_glazed_terracotta",
            "glazed_terracotta_yellow": "yellow_glazed_terracotta",
            "log_acacia": "log_plum",
            "log_birch": "log_aspen",
            "log_dark_oak": "log_cedar",
            "log_spruce": "log_pine",
            "log_oak": "log_maple",
            "log_mangrove": "log_palm",
            "log_jungle": "log_elm",
            "mushroom_block_skin_brown": "brown_mushroom_block",
            "mushroom_block_skin_red": "red_mushroom_block",
            "mushroom_block_skin_stem": "mushroom_stem",
            "mushroom_brown": "brown_mushroom",
            "mushroom_red": "red_mushroom",
            "planks_acacia": "planks_plum",
            "planks_big_oak": "planks_cedar",
            "planks_birch": "planks_aspen",
            "planks_jungle": "planks_elm",
            "planks_oak": "planks_maple",
            "planks_spruce": "planks_pine",
            "prismarine_dark": "dark_green_bricks",
            "pumpkin_face_off": "carved_pumpkin",
            "red_sandstone_carved": "chiseled_red_sandstone",
            "red_sandstone_smooth": "cut_red_sandstone",
            "sandstone_carved": "chiseled_sandstone",
            "sandstone_smooth": "cut_sandstone",
            "sapling_acacia": "plum_sapling",
            "sapling_birch": "aspen_sapling",
            "sapling_jungle": "elm_sapling",
            "sapling_oak": "maple_sapling",
            "sapling_spruce": "pine_sapling",
            "sapling_roofed_oak": "cedar_sapling",
            "stone_slab_side": "slab_stone_side",
            "stripped_cherry_log_side": "stripped_cherry_log",
            "stripped_mangrove_log_side": "stripped_palm_log",
            "web": "cobweb",
            "wheat_stage_0": "wheat_stage0",
            "wheat_stage_1": "wheat_stage1",
            "wheat_stage_2": "wheat_stage2",
            "wheat_stage_3": "wheat_stage3",
            "wheat_stage_4": "wheat_stage4",
            "wheat_stage_5": "wheat_stage5",
            "wheat_stage_6": "wheat_stage6",
            "wheat_stage_7": "wheat_stage7",
            "wool_colored_silver": "wool_colored_light_grey",
            "birch_planks": "slab_aspen_side",
            "planks_birch": "slab_aspen_side",
            "bricks": "slab_brick_side",
            "brick": "slab_brick_side",
            "dark_oak_planks": "slab_cedar_side",
            "planks_dark_oak": "slab_cedar_side",
            "cherry_planks": "slab_cherry_side",
            "planks_cherry": "slab_cherry_side",
            "chiseled_red_sandstone": "slab_chiseled_red_sandstone_side",
            "red_sandstone_carved": "slab_chiseled_red_sandstone_side",
            "chiseled_sandstone": "slab_chiseled_sandstone_side",
            "sandstone_carved": "slab_chiseled_sandstone_side",
            "cobblestone": "slab_cobblestone_side",
            "cut_red_sandstone": "slab_cut_red_sandstone_side",
            "red_sandstone_smooth": "slab_cut_red_sandstone_side",
            "cut_sandstone": "slab_cut_sandstone_side",
            "sandstone_smooth": "slab_cut_sandstone_side",
            "dirt": "slab_dirt_side",
            "jungle_planks": "slab_elm_side",
            "planks_jungle": "slab_elm_side",
            "oak_planks": "slab_maple_side",
            "planks_oak": "slab_maple_side",
            "mossy_cobblestone": "slab_mossy_cobblestone_side",
            "cobblestone_mossy": "slab_mossy_cobblestone_side",
            "mangrove_planks": "slab_palm_side",
            "planks_mangrove": "slab_palm_side",
            "spruce_planks": "slab_pine_side",
            "planks_spruce": "slab_pine_side",
            "acacia_planks": "slab_plum_side",
            "planks_acacia": "slab_plum_side",
            "red_sandstone_bottom": "slab_red_sandstone_side",
            "sandstone_bottom": "slab_sandstone_normal_side",
            "chiseled_stone_bricks": "slab_stonebrick_carved_side",
            "stonebrick_carved": "slab_stonebrick_carved_side",
            "mossy_stone_bricks": "slab_stonebrick_mossy_side",
            "stonebrick_mossy": "slab_stonebrick_mossy_side",
            "stone_bricks": "slab_stonebrick_side",
            "stonebrick": "slab_stonebrick_side",
            "andesite": "slab_stone_andesite_side",
            "stone_andesite": "slab_stone_andesite_side",
            "polished_andesite": "slab_stone_andesite_smooth_side",
            "stone_andesite_smooth": "slab_stone_andesite_smooth_side",
            "diorite": "slab_stone_diorite_side",
            "stone_diorite": "slab_stone_diorite_side",
            "polished_diorite": "slab_stone_diorite_smooth_side",
            "stone_diorite_smooth": "slab_stone_diorite_smooth_side",
            "granite": "slab_stone_granite_side",
            "stone_granite": "slab_stone_granite_side",
            "polished_granite": "slab_stone_granite_smooth_side",
            "stone_granite_smooth": "slab_stone_granite_smooth_side",
            "stone": "slab_stone_side",
            "aspen_door": "door_birch",
            "aspen_door": "birch_door",
            "cedar_door": "door_dark_oak",
            "cedar_door": "dark_oak_door",
            "elm_door": "door_jungle",
            "elm_door": "jungle_door",
            "glistering_watermelon_slice": "melon_speckled",
            "maple_door": "door_oak",
            "maple_door": "oak_door",
            "moonstone": "netherite_ingot",
            "moonstone_orb": "ender_pearl",
            "moonstone_pickaxe": "netherite_pickaxe",
            "palm_door": "door_mangrove",
            "palm_door": "mangrove_door",
            "pine_door": "door_spruce",
            "pine_door": "spruce_door",
            "plum_door": "door_acacia",
            "plum_door": "acacia_door",
            "potion_table": "brewing_stand",
            "watermelon_seeds": "melon_seeds",
            "watermelon_seeds": "seeds_melon",
            "watermelon_slice": "melon",
            "watermelon_slice": "melon_slice",
            "wood_boots": "leather_boots",
            "wood_chestplate": "leather_chestplate",
            "wood_helmet": "leather_helmet",
            "wood_leggings": "leather_leggings",
            "mushroom_soup": "mushroom_stew",
            "book": "book_normal",
            "bucket": "bucket_empty",
            "golden_axe": "gold_axe",
            "golden_boots": "gold_boots",
            "golden_chestplate": "gold_chestplate",
            "golden_helmet": "gold_helmet",
            "golden_hoe": "gold_hoe",
            "golden_leggings": "gold_leggings",
            "golden_pickaxe": "gold_pickaxe",
            "golden_shovel": "gold_shovel",
            "golden_sword": "gold_sword",
            "oak_boat": "boat",
            "pumpkin_seeds": "seeds_pumpkin",
            "water_bucket": "bucket_water",
            "wheat_seeds": "seeds_wheat",
            "wooden_axe": "wood_axe",
            "wooden_hoe": "wood_hoe",
            "wooden_pickaxe": "wood_pickaxe",
            "wooden_shovel": "wood_shovel",
            "wooden_sword": "wood_sword"
                }
                temp_folder = rename_images(blocks_folder, rename_map)
                
                override_list = [
                    "allium",
            "azure_bluet",
            "beacon",
            "bedrock",
            "black_concrete",
            "black_glazed_terracotta",
            "blue_concrete",
            "blue_glazed_terracotta",
            "blue_orchid",
            "brown_concrete",
            "brown_glazed_terracotta",
            "brown_mushroom",
            "brown_mushroom_block",
            "carved_pumpkin",
            "chiseled_red_sandstone",
            "chiseled_sandstone",
            "clay",
            "coal_block",
            "coal_ore",
            "coarse_dirt",
            "cobweb",
            "cornflower",
            "crafting_table_top",
            "cut_red_sandstone",
            "cut_sandstone",
            "cyan_concrete",
            "cyan_glazed_terracotta",
            "dandelion",
            "destroy_stage_0",
            "destroy_stage_1",
            "destroy_stage_2",
            "destroy_stage_3",
            "destroy_stage_4",
            "destroy_stage_5",
            "destroy_stage_6",
            "destroy_stage_7",
            "destroy_stage_8",
            "destroy_stage_9",
            "diamond_block",
            "diamond_ore",
            "dirt",
            "emerald_block",
            "emerald_ore",
            "end_stone",
            "farmland",
            "furnace_front",
            "furnace_side",
            "furnace_top",
            "glass",
            "glowstone",
            "gold_block",
            "gold_ore",
            "gravel",
            "gray_concrete",
            "gray_glazed_terracotta",
            "green_concrete",
            "green_glazed_terracotta",
            "hay_block_side",
            "hay_block_top",
            "ice",
            "iron_block",
            "iron_ore",
            "lapis_block",
            "lapis_ore",
            "light_blue_concrete",
            "light_blue_glazed_terracotta",
            "light_gray_concrete",
            "light_gray_glazed_terracotta",
            "lily_of_the_valley",
            "lime_concrete",
            "lime_glazed_terracotta",
            "magenta_concrete",
            "magenta_glazed_terracotta",
            "mushroom_stem",
            "netherrack",
            "obsidian",
            "orange_concrete",
            "orange_glazed_terracotta",
            "orange_tulip",
            "oxeye_daisy",
            "pink_concrete",
            "pink_glazed_terracotta",
            "pink_tulip",
            "podzol_top",
            "poppy",
            "pumpkin_side",
            "pumpkin_top",
            "purple_concrete",
            "purple_glazed_terracotta",
            "quartz_block_side",
            "redstone_lamp_on",
            "red_concrete",
            "red_glazed_terracotta",
            "red_mushroom",
            "red_mushroom_block",
            "red_tulip",
            "slab_smooth_stone_side",
            "smooth_stone",
            "snow",
            "sponge",
            "stone",
            "wheat_stage0",
            "wheat_stage1",
            "wheat_stage2",
            "wheat_stage3",
            "wheat_stage4",
            "wheat_stage5",
            "wheat_stage6",
            "wheat_stage7",
            "white_concrete",
            "white_glazed_terracotta",
            "white_tulip",
            "wither_rose",
            "yellow_concrete",
            "yellow_glazed_terracotta",
            "brick",
            "chest_front",
            "chest_side",
            "chest_top",
            "hardened_clay",
            "hardened_clay_stained_black",
            "hardened_clay_stained_blue",
            "hardened_clay_stained_brown",
            "hardened_clay_stained_cyan",
            "hardened_clay_stained_gray",
            "hardened_clay_stained_green",
            "hardened_clay_stained_light_blue",
            "hardened_clay_stained_lime",
            "hardened_clay_stained_magenta",
            "hardened_clay_stained_orange",
            "hardened_clay_stained_pink",
            "hardened_clay_stained_purple",
            "hardened_clay_stained_red",
            "hardened_clay_stained_silver",
            "hardened_clay_stained_white",
            "hardened_clay_stained_yellow",
            "nether_brick",
            "pumpkin_face_on",
            "quartz_block_chiseled",
            "stone_andesite",
            "stone_andesite_smooth",
            "stone_diorite",
            "stone_diorite_smooth",
            "stone_granite",
            "stone_granite_smooth",
            "stonebrick",
            "stonebrick_carved",
            "stonebrick_cracked",
            "stonebrick_mossy",
            "wool_colored_black",
            "wool_colored_blue",
            "wool_colored_brown",
            "wool_colored_cyan",
            "wool_colored_gray",
            "wool_colored_green",
            "wool_colored_light_blue",
            "wool_colored_lime",
            "wool_colored_magenta",
            "wool_colored_orange",
            "wool_colored_pink",
            "wool_colored_purple",
            "wool_colored_red",
            "wool_colored_white",
            "wool_colored_yellow",
            "apple",
            "arrow",
            "book",
            "bowl",
            "bread",
            "bucket",
            "coal",
            "diamond",
            "diamond_axe",
            "diamond_boots",
            "diamond_chestplate",
            "diamond_helmet",
            "diamond_hoe",
            "diamond_leggings",
            "diamond_pickaxe",
            "diamond_shovel",
            "diamond_sword",
            "golden_axe",
            "golden_boots",
            "golden_chestplate",
            "golden_helmet",
            "golden_hoe",
            "golden_leggings",
            "golden_pickaxe",
            "golden_shovel",
            "golden_sword",
            "gold_ingot",
            "iron_axe",
            "iron_boots",
            "iron_chestplate",
            "iron_helmet",
            "iron_hoe",
            "iron_ingot",
            "iron_leggings",
            "iron_pickaxe",
            "iron_shovel",
            "iron_sword",
            "oak_boat",
            "pumpkin_pie",
            "pumpkin_seeds",
            "shears",
            "snowball",
            "stick",
            "stone_axe",
            "stone_hoe",
            "stone_pickaxe",
            "stone_shovel",
            "stone_sword",
            "water_bucket",
            "wheat",
            "wheat_seeds",
            "wooden_axe",
            "wooden_hoe",
            "wooden_pickaxe",
            "wooden_shovel",
            "wooden_sword",
            "glistering_melon_slice"
                ]
                copy_overridden_images(blocks_folder, temp_folder, override_list)
                
                base_folder_copy = copy_base_pack(BASE_FOLDER)
                copy_to_base_folder(temp_folder, base_folder_copy)
                
                cloudinary_url = zip_base_pack(base_folder_copy, public_id)
                
                return render_template('download.html', filename=cloudinary_url)
            except Exception as e:
                logger.error(f"An error occurred during processing: {str(e)}")
                flash(f"An error occurred during processing: {str(e)}")
                return redirect(request.url)
    return render_template('index.html')

@app.route('/download/<path:filename>', methods=['GET'])
def download_file(filename):
    return redirect(filename)  # Direct redirect to Cloudinary URL

if __name__ == '__main__':
    debug_mode = os.environ.get('FLASK_DEBUG', 'false').lower() == 'true'
    app.run(debug=debug_mode)