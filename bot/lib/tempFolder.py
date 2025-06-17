import os, shutil
from bot.cfg import cfg

class TempFolder:
    """A scoped temporary folder.

    ```py
    with TempFolder("path/myFolder") as folder:
        with open(os.path.join(folder.folderPath, "myFile.txt"), "w") as f:
            f.write("hello world")
    ```
    This code will create a folder at the path `{cfg.paths.tempRenders}/path/myFolder`, create `{cfg.paths.tempRenders}/path/myFolder/myFile.txt`, and write to it.
    Then, the `with` will exit scope, and the entire `{cfg.paths.tempRenders}/path/myFolder` directory will be deleted (but not `{cfg.paths.tempRenders}/path`), including its contents.
    """
    def __init__(self, folderName: str) -> None:
        self.folderName = folderName

    
    @property
    def folderPath(self): return os.path.join(cfg.paths.tempRenders, self.folderName)


    def __enter__(self):
        os.makedirs(self.folderPath, exist_ok=True)
        return self


    def __exit__(self, cls, value, traceback):
        try:
            shutil.rmtree(self.folderPath)
        except ValueError:
            pass
        return False