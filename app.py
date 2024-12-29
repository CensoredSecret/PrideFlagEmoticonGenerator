from flask import Flask, request, jsonify, send_file
from PIL import Image, ImageDraw, ImageOps
import os
from io import BytesIO

app = Flask(__name__)

UPLOAD_FOLDER = "uploads"
PROCESSED_FOLDER = "processed"
TEMPLATES_FOLDER = "templates"

# Ensure folders exist
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(PROCESSED_FOLDER, exist_ok=True)
os.makedirs(TEMPLATES_FOLDER, exist_ok=True)

def apply_heart_clipping(img, heart_base_path):
    """Apply a heart pattern using a base image as a clipping mask."""
    with Image.open(heart_base_path) as heart_base:
        # Ensure the heart base has an alpha channel
        heart_base = heart_base.convert("RGBA")
        
        # Resize the uploaded flag to match the heart base dimensions
        resized_flag = img.resize(heart_base.size, Image.Resampling.LANCZOS)
        
        # Create a mask from the heart base's transparency
        mask = heart_base.getchannel("A")
        
        # Apply the mask to the resized flag
        heart_clipped = Image.new("RGBA", heart_base.size)
        heart_clipped.paste(resized_flag, (0, 0), mask=mask)
        return heart_clipped

@app.route("/combine", methods=["POST"])
def combine_flags():
    if "main_flag" not in request.files or "heart_flag" not in request.files:
        return jsonify({"error": "Both main_flag and heart_flag are required"}), 400

    main_file = request.files["main_flag"]
    heart_file = request.files["heart_flag"]
    template = request.args.get("template", default="heart")

    if main_file.filename == "" or heart_file.filename == "":
        return jsonify({"error": "Both files must be selected"}), 400

    try:
        # Save the original files
        main_file_path = os.path.join(UPLOAD_FOLDER, main_file.filename)
        heart_file_path = os.path.join(UPLOAD_FOLDER, heart_file.filename)
        main_file.save(main_file_path)
        heart_file.save(heart_file_path)

        # Open and resize the main flag image
        with Image.open(main_file_path) as main_img:
            main_img = main_img.resize((36, 21), Image.Resampling.LANCZOS)
            main_final_size = (38, 23)
            main_framed_img = Image.new("RGBA", main_final_size, (255, 255, 255, 0))
            main_framed_img.paste(main_img, (1, 1))

            # Draw the white pixel frame for the main flag
            draw = ImageDraw.Draw(main_framed_img)
            for x in range(0, 38):
                for y in range(0, 23):
                    if (
                        ((x == 0 or x == 37 or y == 0 or y == 22) or ((x == 1 and y == 1) or (x == 36 and y == 1) or (x == 1 and y == 21) or (x == 36 and y == 21))) and  # Edge pixels
                        not ((x == 0 and y == 0) or (x == 37 and y == 0) or (x == 0 and y == 22) or (x == 37 and y == 22))  # Exclude corners
                    ):
                        draw.point((x, y), fill=(255, 255, 255, 255))

            # Open and process the heart flag image
            with Image.open(heart_file_path) as heart_img:
                heart_clipped_img = heart_img.resize((24, 18), Image.Resampling.LANCZOS)

                if template == "heart":
                    heart_base_path = os.path.join(TEMPLATES_FOLDER, "heart_base.png")
                    if not os.path.exists(heart_base_path):
                        return jsonify({"error": "Heart base image not found"}), 404
                    heart_clipped_img = apply_heart_clipping(heart_img, heart_base_path)

                # Overlay the heart flag on the main flag
                combined_img = main_framed_img.copy()
                heart_position = (0, 0)  # Adjust to position the heart
                combined_img.paste(heart_clipped_img, heart_position, mask=heart_clipped_img)

            # Save the combined image
            processed_path = os.path.join(PROCESSED_FOLDER, f"combined_{main_file.filename}")
            combined_img.save(processed_path)

            # Convert the image to a response
            byte_io = BytesIO()
            combined_img.save(byte_io, format="PNG")
            byte_io.seek(0)

        return send_file(byte_io, mimetype="image/png")

    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    app.run(debug=True)
