import os

script_path = os.path.dirname(os.path.realpath(__file__))

for subdir, dirs, files in os.walk(script_path):
    for filename in files:
        filepath = subdir + os.sep + filename

        if filepath.endswith(".mtl"):
            f = open(filepath, "r")
            lines = f.readlines()
            f.close()

            workinglines = []
            
            for line in range(len(lines)):
                if not lines[line].startswith("map_Kd"):
                    workinglines.append(lines[line])
            f = open(filepath, "w")
            f.writelines(workinglines)
            f.close()

