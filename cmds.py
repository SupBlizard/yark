import os, json, csv, sqlite3, colorama, requests, time

import datetime
from dateutil.parser import *

from yt_dlp import YoutubeDL
from helpers import *


VIDEO_ID_LENGTH = 11
PLAYLIST_ID_LENGTH = 34
RYD_API = "https://returnyoutubedislikeapi.com/"


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

    def video(self, video_id):
        v = Media.get_info(self, video_id)
        cur = db.cursor()

        # Check if uploader exists in the database
        if not cur.execute("SELECT 1 FROM users WHERE user_id == ?", (v["uploader_id"],)).fetchone():
            cur.execute("INSERT INTO users VALUES(?,?)", (v["uploader_id"], v["uploader"]))
        # Check if channel exists in the database
        if not cur.execute("SELECT 1 FROM channels WHERE channel_id == ?", (v["channel_id"],)).fetchone():
            cur.execute("INSERT INTO channels VALUES(?,?,?,?,?)", (
                v["channel_id"], v["uploader_id"], v["channel"],
                v["channel_follower_count"], v["channel_url"]
            ))

        # Commit new rows
        db.commit()

        timeout = 1
        while timeout != 0:
            timeout -= 1

            try:
                # Download thumbnail
                thumbnail = requests.get(v["thumbnail"])
                thumbnail.raise_for_status()

                # Get dislike count and rating
                ryd = requests.get(f"{RYD_API}Votes?videoId={v['id']}&likeCount={v['like_count']}")
                ryd.raise_for_status()
                ryd = ryd.json()
                timeout = 0
            except (requests.ConnectionError, requests.Timeout) as e:
                timeout = 5
                time.sleep(3)
            except:
                raise e


        # Add video
        cur.execute("INSERT INTO videos VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)", (
            v["id"], v["fulltitle"], v["description"], v["channel_id"], thumbnail.content,
            v["duration"], v["duration_string"], v["view_count"], v["age_limit"], v["webpage_url"],
            v["live_status"], ryd["likes"], ryd["dislikes"], ryd["rating"], v["upload_date"],
            v["availability"], v["width"], v["height"], v["fps"], v["audio_channels"]
        ))

        # Add comments
        for c in v["comments"]:
            # Check if user is in the database
            if not cur.execute("SELECT 1 FROM users WHERE user_id == ?", (c["author_id"],)).fetchone():
                cur.execute("INSERT INTO users VALUES(?,?)", (c["author_id"], c["author"]))

            if c["parent"] == "root": c["parent"] = None
            cur.execute("INSERT INTO comments VALUES (?,?,?,?,?,?,?,?,?)", (
                c["id"], v["id"], c["author_id"], c["text"], c["like_count"],
                c["is_favorited"], c["author_is_uploader"], c["parent"], c["timestamp"]
            ))

        # Commit new video
        db.commit()


    def dump(self, args):
        if len(args) < 1 or not args[0]:
            raise TypeError("Dump what ?")

        if args[0].lower() == "thumbnails":
            if not os.path.exists("thumbnails"):
                os.mkdir("thumbnails")

            videos = db.execute("SELECT video_id, thumbnail FROM videos").fetchall()

            for video in videos:
                thumbnail_path = f"thumbnails/{video[0]}.webp"
                if os.path.exists(thumbnail_path): continue

                with open(thumbnail_path, "wb") as thumb_file:
                    thumb_file.write(video[1])

    def playlist(self, args):
        pass

    def history(self, args):
        pass



class Media:
    def __init__(self):
        self.help = "TODO"

    def default(self):
        raise Exception(f"Missing method")

    def get_info(self, video_id):
        if not video_id or not video_id[0]:
            raise ValueError("Missing url")
        elif len(video_id[0]) != VIDEO_ID_LENGTH:
            raise ValueError("Invalid video ID")
        else: video_id = video_id[0]

        with YoutubeDL({"quiet": True, "getcomments": True}) as ydlp:
            info = ydlp.extract_info(video_id, download=False)
            if info["extractor"] != "youtube":
                raise ValueError("ERROR: Must be a youtube domain")
            return info

    def print_info(self, video_id):
        try:
            info = self.get_info(video_id)
        except ValueError as e: raise e

        print("\nThumbnail: " + info["thumbnail"])
        print(info["title"])
        info["upload_date"] = date_convert(info["upload_date"] )
        print(f"{info['view_count']} views | {info['upload_date']}\n")
        print(f"{info['channel']} | {info['channel_follower_count']} subscribers")
