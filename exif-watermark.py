import os
import sys
import exifread
from PIL import Image, ImageDraw, ImageFont, ExifTags

def get_image_metadata(image_path):
    """Extract and return metadata from the specified image."""
    with Image.open(image_path) as img:
        exif_data = img._getexif()

        # Decode the EXIF data into a readable dictionary
        if exif_data is not None:
            exif = {
                ExifTags.TAGS[k]: v
                for k, v in exif_data.items()
                if k in ExifTags.TAGS
            }

            # Extract the metadata we're interested in
            metadata = {
                'ISO': exif.get('ISOSpeedRatings', '??'),
                'F-Value': exif.get('FNumber', (0,0)),  # It's a tuple, e.g., (f, 1)
                'ExposureTime': exif.get('ExposureTime', (0,0)),  # It's a tuple, e.g., (1, 200)
                'Date Taken': exif.get('DateTimeOriginal', 'Unknown'),
                'Device Model': exif.get('Model', 'Unknown'),
                'Device Make': exif.get('Make', 'Unknown'),
                'Lens Model': exif.get('LensModel', 'Unknown'),  # Not all cameras save lens information
                'Focal Length': exif.get('FocalLength', '??'),
            }
            
            # If some values are tuples, convert them to a readable format
            if isinstance(metadata['F-Value'], tuple):
                metadata['F-Value'] = str(metadata['F-Value'][0] / metadata['F-Value'][1])
            
            return metadata
        else:
            print(f"No EXIF metadata found for {image_path}")
            return {}

def create_watermarked_image(input_path, output_path, metadata):
    try:
        # Open the original image
        original = Image.open(input_path)
        
        # Extract the EXIF data from the original image
        exif_data = original.info.get('exif')

        # Determine the watermark template file
        device = metadata['Device Make']
        if 'hasselblad' in device.lower():
            template = 'watermark-hasselblad.png'
        elif 'sony' in device.lower():
            template = 'watermark-sony.png'
        else:
            print(f"No template for {device} of {input_path}!")
            return

        watermark_template_path = os.path.join(os.path.dirname(__file__), template)

        # Open the watermark template
        watermark = Image.open(watermark_template_path)

        # Prepare the watermark text
        font_path = "RobotoMono.ttf"  # make sure this path is correct for your system
        font_size = 60  # adjust as necessary to fit your watermark size
        font = ImageFont.truetype(font_path, font_size)

        # Format the exposure time
        exposure_time = metadata["ExposureTime"]
        if exposure_time:
            exp_numerator, exp_denominator = exposure_time.numerator, exposure_time.denominator
        else:
            exp_numerator, exp_denominator = 0, 0
        
        if exp_denominator == 0:
            exposure = 'Unknown'
        elif exp_numerator == 1:
            exposure = f"{exp_numerator}/{exp_denominator}"
        else:
            exposure = f"{exp_numerator / exp_denominator:.1f}"

        

        # Define the text content
        text = f"{metadata['Device Model']} + {metadata['Lens Model']}  |  " \
            + f"{int(metadata['Focal Length'])}mm, iso{metadata['ISO']}, f/{metadata['F-Value']}, {exposure}s"

        # Create a drawing context on the watermark template (NOT the resized one)
        draw = ImageDraw.Draw(watermark)

        # Calculate text size (width and height)
        _, _, text_width, text_height = draw.textbbox((0,0), text, font=font)

        # # Calculate the x, y coordinates of the text (bottom-right for this example)
        # x = watermark.width - text_width - 70
        # y = watermark.height - text_height - 40

        x = 316
        y = (watermark.height - text_height) / 2

        # Add the text to the watermark template
        draw.text((x, y), text, font=font, fill=(160,160,160,255))

        # Now that the text is applied, resize the watermark to match the original image's width
        base_width = original.width
        watermark_ratio = (base_width / float(watermark.width))
        watermark_size = int((float(watermark.height) * float(watermark_ratio)))
        watermark_resized = watermark.resize((base_width, watermark_size), Image.LANCZOS)

        # Create a new transparent image for the composite (to ensure the alpha channel is calculated correctly)
        transparent = Image.new('RGB', (original.width, original.height + watermark_resized.height))

        # Paste the original image and the watermark (with text) into the transparent composite image
        transparent.paste(original, (0,0))
        transparent.paste(watermark_resized, (0,original.height))

        # Save the final image
        transparent.save(output_path, quality=95, exif=exif_data)

    except Exception as e:
        print(f"An error occurred: {e}")

def main(folder_path):
    for root, dirs, files in os.walk(folder_path):
        for file in files:
            if file.lower().endswith(".jpg"):
                input_path = os.path.join(root, file)

                # Extract metadata from the image
                metadata = get_image_metadata(input_path)

                # Create a watermarked image with the metadata
                create_watermarked_image(input_path, input_path[:-4] + '-sig.jpg', metadata)

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python watermark_script.py <folder_path>")
    else:
        main(sys.argv[1])
