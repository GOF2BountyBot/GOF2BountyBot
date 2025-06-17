import os
import json

script_path = os.path.dirname(os.path.realpath(__file__))

for subdir, dirs, files in os.walk(script_path):
    for dirname in dirs:
        dirpath = subdir + os.sep + dirname
        if dirname.lower().endswith(".bbship"):
            shipData = {}
            with open(dirpath + os.sep + "META.json", "r") as f:
                shipData = json.loads(f.read())
            shipData["model"] = input("Model for " + shipData["name"] + ": ")
            shipData["skinnable"] = True
            with open(dirpath + os.sep + "META.json", "w") as f:
                f.write(json.dumps(shipData, indent=4, sort_keys=True))
