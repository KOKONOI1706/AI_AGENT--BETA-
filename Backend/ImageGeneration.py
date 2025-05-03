import asyncio
from random import randint
from PIL import Image
import requests
from dotenv import get_key
import os 
from time import sleep
import logging

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def open_images(prompt):
    folder_path = r"Data"
    prompt = prompt.replace(" ", "_")
    
    Files = [f"{prompt}{i}.jpg" for i in range(1,5)]
    
    for jpg_file in Files:
        image_path = os.path.join(folder_path, jpg_file)
        
        try:
            img = Image.open(image_path)
            logging.info(f"Opening image: {image_path}")
            img.show()
            sleep(1)  # Consider using a more robust method to ensure images appear
            
        except IOError as e:
            logging.error(f"Unable to open {image_path}: {e}")
            
API_URL = "https://api-inference.huggingface.co/models/stabilityai/stable-diffusion-xl-base-1.0"
headers = {"Authorization": f"Bearer {get_key('.env', 'HuggingFaceAPIKey')}"}

async def query(payload):
    try:
        response = await asyncio.to_thread(requests.post, API_URL, headers=headers, json=payload)
        response.raise_for_status()  # Will raise an exception for HTTP errors
        return response.content
    except requests.exceptions.RequestException as e:
        logging.error(f"API request failed: {e}")
        return None

async def generate_image(prompt: str):
    tasks = []
    
    for _ in range(4):
        payload = {
            "inputs": f"{prompt}, quality = 4K, sharpness = maximum, Ultra High details, high resolution, seed = {randint(0, 1000000)}",
        }
        task = asyncio.create_task(query(payload))
        tasks.append(task)
        
    image_bytes_list = await asyncio.gather(*tasks)
    
    success_count = 0
    for i, image_bytes in enumerate(image_bytes_list):
        if image_bytes:  # Only process if we got valid image data
            filename = fr"Data\{prompt.replace(' ', '_')}{i + 1}.jpg"
            try:
                with open(filename, "wb") as f:
                    f.write(image_bytes)
                success_count += 1
            except IOError as e:
                logging.error(f"Failed to save image {filename}: {e}")
    
    return success_count

def GenerateImages(prompt: str):
    try:
        success_count = asyncio.run(generate_image(prompt))
        if success_count > 0:
            open_images(prompt)
            return True
        return False
    except Exception as e:
        logging.error(f"Image generation failed: {e}")
        return False

def main():
    data_file = r"Frontend\Files\ImageGeneration.data"
    
    while True:
        try:
            if not os.path.exists(data_file):
                logging.warning(f"Data file not found: {data_file}")
                sleep(2)
                continue
                
            with open(data_file, "r") as f:
                Data = f.read().strip()
            
            # More robust parsing
            parts = Data.split(",", 1)  # Split on first comma only
            if len(parts) != 2:
                logging.error(f"Invalid data format: {Data}")
                sleep(2)
                continue
                
            Prompt, Status = parts[0].strip(), parts[1].strip()
            
            if Status.lower() == "true":
                logging.info(f"Generating images for prompt: {Prompt}")
                success = GenerateImages(prompt=Prompt)
                
                # Update status file
                try:
                    with open(data_file, "w") as f:
                        f.write(f"{Prompt},False")
                    
                    if success:
                        logging.info("Image generation completed successfully")
                    else:
                        logging.warning("Image generation completed with errors")
                        
                    break  # Exit the loop after processing
                except IOError as e:
                    logging.error(f"Failed to update status file: {e}")
            else:
                sleep(1)
        except KeyboardInterrupt:
            logging.info("Process interrupted by user")
            break
        except Exception as e:
            logging.error(f"Unexpected error: {e}")
            sleep(2)  # Sleep longer on errors to avoid rapid looping

if __name__ == "__main__":
    main()