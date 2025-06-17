import os
from BB.bbConfig.bbData import builtInShipData
import json

script_path = os.path.dirname(os.path.realpath(__file__))

for shipName in builtInShipData:
    if shipName in ["Cronus", "Phantom XT"]:
        continue

    shipData = builtInShipData[shipName]
    shipDir = script_path + os.sep + "items" + os.sep + "ships" + os.sep + shipData["manufacturer"].title() + os.sep + shipName + ".bbship" + os.sep
    if not os.path.exists(shipDir):
        shipDir = script_path + os.sep + "items" + os.sep + "ships" + os.sep + "Most Wanted" + os.sep + shipName + ".bbship" + os.sep
        if not os.path.exists(shipDir):
            shipDir = script_path + os.sep + "items" + os.sep + "ships" + os.sep + "Kaamo" + os.sep + shipName + ".bbship" + os.sep
            if not os.path.exists(shipDir):
                raise ValueError("bbItem not found: " + shipDir)

    textureRegions = 0
    if os.path.exists(shipDir + "secondary_mask.jpg"):
        textureRegions += 1
    if os.path.exists(shipDir + "tertiary_mask.jpg"):
        if textureRegions != 1:
            raise ValueError("Invalid bbItem '" + shipName + "' - contains a tertiary mask, but no secondary mask.")
            continue
        textureRegions += 1

    shipData["textureRegions"] = textureRegions

    with open(shipDir + "META.json", "w") as f:
        f.write(json.dumps(shipData, indent=4, sort_keys=True))


# script_path = os.path.dirname(os.path.realpath(__file__))

# for subdir, dirs, files in os.walk(script_path):
#     for dirname in dirs:
#         dirpath = subdir + os.sep + dirname

#         if dirname.endswith(".bbitem"):
#             textureRegions = 0
#             if os.path.exists(dirpath + os.sep + "secondary_mask.jpg"):
#                 textureRegions += 1
#             if os.path.exists(dirpath + os.sep + "tertiary_mask.jpg"):
#                 if textureRegions != 1:
#                     raise ValueError("Invalid bbItem '" + dirname + "' - contains a tertiary mask, but no secondary mask.")
#                     continue
#                 textureRegions += 1

#             f = open(dirpath + os.sep + "META.json", "w")
#             f.write("""{
#     "name":             \"""" + dirname.split(".bbitem")[0] + """",
#     "textureRegions":   """ + str(textureRegions) + """
# }""")
#             f.close()

