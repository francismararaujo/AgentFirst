import cv2
import numpy as np

def make_transparent_logo(image_path, out_path):
    gray = cv2.imread(image_path, cv2.IMREAD_GRAYSCALE)
    if gray is None:
        print(f"Error loading {image_path}")
        return
        
    print(f"Loaded {image_path}, shape: {gray.shape}")
    
    # Check if the background is white by examining a corner pixel
    if gray[0, 0] > 128:
        # Background is white (e.g. 255), Symbol is black (e.g. 0)
        # We need the alpha to be 255 where symbol is (currently 0), and 0 where bg is (currently 255)
        alpha = 255 - gray
        print("Detected white background. Inverting alpha channel.")
    else:
        # Background is black (0), Symbol is white (255)
        # We need alpha to be 255 where symbol is, 0 where bg is
        alpha = gray
        print("Detected black background. Using standard alpha channel.")

    # Create an RGBA image where RGB is all white (255)
    rgba = np.zeros((gray.shape[0], gray.shape[1], 4), dtype=np.uint8)
    rgba[:, :, 0] = 255 # Blue
    rgba[:, :, 1] = 255 # Green
    rgba[:, :, 2] = 255 # Red
    rgba[:, :, 3] = alpha # Alpha
    
    # Crop out the empty transparent space
    coords = cv2.findNonZero((alpha > 10).astype(np.uint8))
    if coords is not None:
        x, y, w, h = cv2.boundingRect(coords)
        cropped = rgba[y:y+h, x:x+w]
    else:
        cropped = rgba
        
    cv2.imwrite(out_path, cropped)
    print(f"Successfully saved {out_path} with cropped shape: {cropped.shape}")

make_transparent_logo("logo-white.png", "logo-transparent.png")
