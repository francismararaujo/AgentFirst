import cv2
import numpy as np
import svgwrite
import sys

def convert_to_svg(image_path, svg_path):
    img = cv2.imread(image_path, cv2.IMREAD_UNCHANGED)
    if img is None:
        print(f"Failed to load {image_path}")
        return
        
    print(f"Image shape: {img.shape}")
    
    # If it has alpha channel, we could use that as the mask, or if it's RGB, we check for high intensity.
    # The image is white foreground on black background.
    if len(img.shape) == 3 and img.shape[2] == 4:
        # has alpha
        b,g,r,a = cv2.split(img)
        # Using alpha might be enough if bg is transparent, but let's just use grayscale intensity
        gray = cv2.cvtColor(img, cv2.COLOR_BGRA2GRAY)
    else:
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        
    _, thresh = cv2.threshold(gray, 128, 255, cv2.THRESH_BINARY)
    contours, hierarchy = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    
    # Wait, RETR_EXTERNAL only gets outer. Some parts of the logo might have inner holes?
    # No, the geometric shape has separate islands. Let's use RETR_TREE just in case.
    contours, hierarchy = cv2.findContours(thresh, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)
    
    h, w = thresh.shape
    dwg = svgwrite.Drawing(svg_path, size=(w, h), profile='tiny')
    
    # Draw all contours. We might need to handle holes but using simple path with EVENODD or just drawing 
    # cv2 contours as individual paths.
    
    for i, c in enumerate(contours):
        if len(c) < 3:
            continue
        
        # Check if it's a hole or an outline
        # hierarchy[0][i] = [Next, Previous, First_Child, Parent]
        parent = hierarchy[0][i][3]
        
        # We can just write them all, but holes need inverse fill or we use a single big path with fill-rule="evenodd"
        
    # Build a single path for all contours
    d_path = ""
    for c in contours:
        if len(c) < 3:
            continue
        d_path += "M " + str(c[0][0][0]) + "," + str(c[0][0][1]) + " "
        for i in range(1, len(c)):
            d_path += "L " + str(c[i][0][0]) + "," + str(c[i][0][1]) + " "
        d_path += "Z "
        
    dwg.add(dwg.path(d=d_path, fill='white', fill_rule='evenodd'))
    # Try scaling
    dwg.save()
    print(f"Saved {svg_path}")

convert_to_svg("logo-white.png", "logo.svg")
