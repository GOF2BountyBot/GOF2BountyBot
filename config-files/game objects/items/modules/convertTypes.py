import os
import json

script_path = os.path.dirname(os.path.realpath(__file__))
typesToClassNames = {   "armour":           "armourModule",
                        "booster":          "boosterModule",
                        "cabin":            "cabinModule",
                        "cloak":            "cloakModule",
                        "compressor":       "compressorModule",
                        "gamma shield":     "gammaShieldModule",
                        "mining drill":     "miningDrillModule",
                        "repair beam":      "repairBeamModule",
                        "repair bot":       "repairBotModule",
                        "scanner":          "scannerModule",
                        "shield":           "shieldModule",
                        "spectral filter":  "spectralFilterModule",
                        "thruster":         "thrusterModule",
                        "tractor beam":     "tractorBeamModule",
                        "transfusion beam": "transfusionBeamModule",
                        "weapon mod":       "primaryWeaponModModule",
                        "jump drive":       "jumpDriveModule",
                        "emergency system": "emergencySystemModule",
                        "signature":        "signatureModule",
                        "shield injector":  "shieldInjectorModule",
                        "time extender":    "timeExtenderModule"}

for subdir, dirs, files in os.walk(script_path):
    for dirname in dirs:
        dirpath = subdir + os.sep + dirname
        if dirname.lower().endswith(".bbmodule"):
            with open(dirpath + os.sep + "META.json", "r+") as f:
                moduleData = json.loads(f.read())
                if "type" not in moduleData:
                    raise KeyError("type field missing from module: " + dirpath)
                if moduleData["type"] not in typesToClassNames:
                    raise ValueError("Invalid type field for module: " + dirpath)
                f.seek(0)
                print("converting",moduleData["type"],"to",typesToClassNames[moduleData["type"]])
                moduleData["type"] = typesToClassNames[moduleData["type"]]
                f.write(json.dumps(moduleData, indent=4, sort_keys=True))
                f.truncate()



