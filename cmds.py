import json, csv, sqlite3, colorama

import datetime
from dateutil.parser import *

from yt_dlp import YoutubeDL
from helpers import *

# Open the database

try:
    db = sqlite3.connect("youtube.db")
    with open("schema.sql", "r") as schema:
        db.executescript(schema.read())
except FileNotFoundError as e:
    print("Database schema not found.")


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

        with YoutubeDL({"quiet": True, "getcomments": True}) as ydlp:
            info = ydlp.extract_info(url, download=False)
            if info["extractor"] != "youtube":
                raise ValueError("ERROR: Must be a youtube domain")
            return info


    def print_info(self, url):
        try:
            info = self.get_info(url)
        except ValueError as e: raise e

        print("\nThumbnail: " + info["thumbnail"])
        print(info["title"])
        info["upload_date"] = date_convert(info["upload_date"] )
        print(f"{info['view_count']} views | {info['upload_date']}\n")
        print(f"{info['channel']} | {info['channel_follower_count']} subscribers")
