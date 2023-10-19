import os
import sys
import exifread
import blend_modes
import numpy
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
        original = Image.open(input_path).convert('RGBA')

        sig_ratio = 0.15
        signature = Image.open('sig.png')
        sig_width = int(original.width * sig_ratio)
        sig_height = int(signature.height * sig_width / signature.width)
        signature = signature.resize((sig_width, sig_height), Image.LANCZOS)

        padding = int(original.width * 0.01)

        watermark = Image.new('RGBA', (original.width, original.height))
        watermark.paste(signature, (padding, original.height - sig_height - padding))
        
        # Extract the EXIF data from the original image
        exif_data = original.info.get('exif')

        # Prepare the watermark text
        font_path = "RobotoMono.ttf"  # make sure this path is correct for your system
        font_size = int(60 * original.width / 5120)  # adjust as necessary to fit your watermark size
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

        # Calculate the x, y coordinates of the text (bottom-right for this example)
        x = watermark.width - text_width - int(font_size / 5)
        y = watermark.height - text_height - int(font_size / 5)

        # Add the text to the watermark template
        draw.text((x, y), text, font=font, fill=(128,128,128,128))

        bg = numpy.array(original).astype(float)
        fg = numpy.array(watermark).astype(float)
        blended = blend_modes.addition(bg, fg, 0.6)
        output = Image.fromarray(numpy.uint8(blended)).convert('RGB')

        # Save the final image
        output.save(output_path, quality=95, exif=exif_data)

    except Exception as e:
        print(f"An error occurred: {e}")

def main(folder_path):
    for root, dirs, files in os.walk(folder_path):
        for file in files:
            if file.lower().endswith(".jpg") and not file.endswith("-sig.jpg"):
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
