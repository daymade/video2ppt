import os
import subprocess
from PIL import Image
import pytesseract
import imagehash
from shutil import copy2
import argparse
import glob

def extract_images_from_video(video_path, interval='10'):
    base_name = os.path.splitext(video_path)[0]
    output_dir = f"{base_name}/extracted_images"
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
    command = [
        'ffmpeg',
        '-i', video_path,
        '-vf', f'fps=1/{interval}',
        os.path.join(output_dir, 'img_%05d.png')
    ]
    subprocess.run(command)
    return output_dir

def is_ppt_slide(image_path, white_threshold=200, white_area_threshold=0.5, text_threshold=50):
    image = Image.open(image_path)
    width, height = image.size
    # 可以调整为分析图片的中心区域
    box = (width * 0.1, height * 0.1, width * 0.9, height * 0.9)
    region = image.crop(box)
    pixels = region.getdata()

    # 计算白色像素占比
    n_white = sum(1 for pixel in pixels if all(x > white_threshold for x in pixel))
    n_total = len(pixels)
    white_area_ratio = n_white / n_total

    # 应用OCR来检测文本的存在
    text = pytesseract.image_to_string(region)
    text_length = len(text.replace('\n', '').replace('\r', '').strip())

    # 如果白色区域比例高，或者文本量足够多，认为是PPT幻灯片
    return white_area_ratio > white_area_threshold or text_length > text_threshold


def filter_ppt_images(input_folder, output_folder):
    if not os.path.exists(output_folder):
        os.makedirs(output_folder)
    for image_name in os.listdir(input_folder):
        image_path = os.path.join(input_folder, image_name)
        if os.path.isfile(image_path) and image_path.lower().endswith(('.png', '.jpg', '.jpeg')):
            if is_ppt_slide(image_path):
                print(f"{image_path} is likely a PPT slide")
                copy2(image_path, os.path.join(output_folder, image_name))

def remove_duplicate_images(input_folder, output_folder, similar_threshold):
    if not os.path.exists(output_folder):
        os.makedirs(output_folder)
    image_hashes = {}
    for image_name in os.listdir(input_folder):
        image_path = os.path.join(input_folder, image_name)
        if os.path.isfile(image_path) and image_path.lower().endswith(('.png', '.jpg', '.jpeg')):
            current_image_hash = imagehash.average_hash(Image.open(image_path))
            if not any(are_images_similar(current_image_hash, stored_hash, similar_threshold) for stored_hash in image_hashes.values()):
                image_hashes[image_name] = current_image_hash
                copy2(image_path, os.path.join(output_folder, image_name))
                print(f"Copied unique image {image_name} to {output_folder}")

def are_images_similar(hash1, hash2, threshold=3):
    return abs(hash1 - hash2) < threshold


def main(video_path, interval, similar_threshold):
    # Step 1: Extract images from video
    images_dir = extract_images_from_video(video_path, interval)
    
    # Step 2: Remove duplicate images first
    remove_duplicate_dir = f"{os.path.splitext(video_path)[0]}/remove_duplicate"
    remove_duplicate_images(images_dir, remove_duplicate_dir, similar_threshold)
    
    # Step 3: Filter out PPT slides
    ppt_images_dir = f"{os.path.splitext(video_path)[0]}/ppt"
    filter_ppt_images(remove_duplicate_dir, ppt_images_dir)
    
    # Optional: Clean up temporary images directory
    # shutil.rmtree(images_dir)
    # shutil.rmtree(intermediate_dir)

    print(f"Processed images are saved in: {ppt_images_dir}")

def process_directory(directory, interval_seconds, similar_threshold):
    for video_file in glob.glob(os.path.join(directory, '*.mp4')):
        print(f"Processing video: {video_file}")
        main(video_file, interval_seconds, similar_threshold)

if __name__ == "__main__":
    # 设置命令行参数解析
    parser = argparse.ArgumentParser(description='Extract PPT slides from a video.')
    parser.add_argument('--input_video', type=str, help='Path to the input video file.')
    parser.add_argument('--input_dir', type=str, help='Path to the directory containing video files.')
    parser.add_argument('--interval_seconds', type=int, default=5, help='extract image per [] seconds')
    parser.add_argument('--similar_threshold', type=int, default=5, help='remove duplicated images')
    # similar
    # 解析命令行参数
    args = parser.parse_args()
    
    if args.input_video:
        main(args.input_video, args.interval_seconds, args.similar_threshold)
    elif args.input_dir:
        process_directory(args.input_dir, args.interval_seconds, args.similar_threshold)
    else:
        print("Please specify either --input_video or --input_dir.")