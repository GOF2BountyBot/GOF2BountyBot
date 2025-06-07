import os
import json

script_path = os.path.dirname(os.path.realpath(__file__))

for subdir, dirs, files in os.walk(script_path):
    for dirname in dirs:
        dirpath = subdir + os.sep + dirname
        if dirname.lower().endswith(".bbship"):
            if os.path.isfile(dirpath + os.sep + "secondary_mask.jpg"):
                os.rename(dirpath + os.sep + "secondary_mask.jpg", dirpath + os.sep + "mask1.jpg")
            if os.path.isfile(dirpath + os.sep + "tertiary_mask.jpg"):
                os.rename(dirpath + os.sep + "tertiary_mask.jpg", dirpath + os.sep + "mask2.jpg")
