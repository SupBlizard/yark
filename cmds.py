import json, csv, sqlite3, colorama
from yt_dlp import YoutubeDL
from helpers import *

# Open the database
db = sqlite3.connect("youtube.db")


# Global run command
def run(cmd_class, args):
    if not args:
        return cmd_class.default()

    cmd = args.pop(0).lower()
    invalid_attr = f'Invalid attribute "{cmd}"'
    cmd = getattr(cmd_class, cmd, Exception(invalid_attr))

    if callable(cmd):
        if cmd.__name__ != "default":
            return cmd(args)
        else:
            raise Exception(invalid_attr)
    elif type(cmd) == Exception:
        raise cmd
    else:
        return cmd



# https://www.youtube.com/watch?v=qOgldkETcxk
class Archive:
    def __init__(self):
        self.help = "TODO"

    def default(self):
        raise Exception(f"Missing method")


class Media:
    def __init__(self):
        self.help = "TODO"

    def default(self):
        raise Exception(f"Missing method")

    def get_info(self, url):
        if not url or not url[0]:
            raise ValueError("Missing url")
        else: url = url[0]

        with YoutubeDL({"quiet": True}) as ydlp:
            info = ydlp.extract_info(url, download=False)
            return info
