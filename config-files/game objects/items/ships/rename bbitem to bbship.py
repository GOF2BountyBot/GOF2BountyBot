import os

script_path = os.path.dirname(os.path.realpath(__file__))

for subdir, dirs, files in os.walk(script_path):
    for dirname in dirs:
        dirpath = subdir + os.sep + dirname

        if dirname.endswith(".bbitem"):
            os.rename(dirpath,dirpath[:-6] + "bbship")