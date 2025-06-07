import os

script_path = os.path.dirname(os.path.realpath(__file__))

for subdir, dirs, files in os.walk(script_path):
    for dirname in dirs:
        dirpath = subdir + os.sep + dirname

        if dirname.endswith(".bbitem"):
            textureRegions = 0
            if os.path.exists(dirpath + os.sep + "secondary_mask.jpg"):
                textureRegions += 1
            if os.path.exists(dirpath + os.sep + "tertiary_mask.jpg"):
                if textureRegions != 1:
                    raise ValueError("Invalid bbItem '" + dirname + "' - contains a tertiary mask, but no secondary mask.")
                    continue
                textureRegions += 1

            f = open(dirpath + os.sep + "META.json", "w")
            f.write("""{
    "name":             \"""" + dirname.split(".bbitem")[0] + """",
    "textureRegions":   """ + str(textureRegions) + """
}""")
            f.close()

