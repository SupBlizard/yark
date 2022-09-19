import os, json, csv, sqlite3, requests, time, yt_dlp, time
import datetime
from dateutil.parser import *
import utils

VIDEO_ID_LENGTH = 11
PLAYLIST_ID_LENGTH = 34
RYD_API = "https://returnyoutubedislikeapi.com/"
WAYBACK = "https://web.archive.org/web/"
YOUTUBE = "https://www.youtube.com/"



# Open the database
try:
    db = sqlite3.connect("youtube.db")
    with open("schema.sql", "r") as schema:
        db.executescript(schema.read())
except FileNotFoundError as e:
    print("Database schema not found.")


options = {
    "quiet": True,
    "logger": utils.Logger()
}

config = {
    "thumbnails": False,
    "comments": False
}


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
        video_id = video_id[0]
        cur = db.cursor()
        exists = cur.execute("SELECT video_id, availability FROM videos WHERE video_id == ?",(video_id,)).fetchone()
        if exists:
            if exists[1] != "lost":
                utils.Logger.info("Video already archived, skipping.", video_id)
                return

            utils.Logger.info("Video previously archived but lost, attempting recovery", video_id)

        # Extract video info
        v = Media.get_info(self, [video_id], simulate=False)
        if not v:
            cur.execute("INSERT OR IGNORE INTO videos (video_id, availability) VALUES (?,?)", (video_id,"lost"))
            db.commit()
            return

        cur.execute("INSERT OR IGNORE INTO users VALUES(?,?)", (v["uploader_id"], v["uploader"]))
        cur.execute("INSERT OR IGNORE INTO channels VALUES(?,?,?,?,?)", (
            v["channel_id"], v["uploader_id"], v["uploader"],
            v["channel_follower_count"], v["channel_url"]
        ))

        if v.get("category"):
            cur.execute("INSERT OR IGNORE INTO categories VALUES(?)", (v.get("category"),))

        # Commit new rows
        db.commit()

        # Add video
        try:
            cur.execute("INSERT INTO videos VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)", (
                v["id"], v["fulltitle"], v["description"], v["channel_id"], v["thumbnail"], v["thumbnail_url"],
                v["duration"], v["views"], v["age_limit"], v["live_status"], v["likes"], v["dislikes"],
                v["rating"], v["upload_date"].timestamp(), v["availability"], v["width"], v["height"], v["fps"],
                v["audio_channels"], v["category"], v["filesize"], None
            ))
        except sqlite3.IntegrityError:
            # Update video info
            cur.execute("""UPDATE videos SET title = ?, description = ?, channel = ?, thumbnail = ?,
                thumbnail_url = ?, duration = ?, views = ?, age_limit = ?, live_status = ?, likes = ?,
                dislikes = ?, rating = ?, upload_timestamp = ?, availability = ?, width = ?, height = ?,
                fps = ?, audio_channels = ?, category = ?, filesize = ? WHERE video_id == ?""", (
                v["fulltitle"], v["description"], v["channel_id"], v["thumbnail"], v["thumbnail_url"],
                v["duration"], v["views"], v["age_limit"], v["live_status"], v["likes"], v["dislikes"],
                v["rating"], v["upload_date"].timestamp(), v["availability"], v["width"], v["height"], v["fps"],
                v["audio_channels"], v["category"], v["filesize"], v["id"]
            ))

        # Add comments
        if v.get("comments"):
            for c in v.get("comments"):
                # Check if user is in the database
                if not cur.execute("SELECT 1 FROM users WHERE user_id == ?", (c["author_id"],)).fetchone():
                    cur.execute("INSERT INTO users VALUES(?,?)", (c["author_id"], c["author"]))

                if c["parent"] == "root": c["parent"] = None
                cur.execute("INSERT INTO comments VALUES (?,?,?,?,?,?,?,?,?)", (
                    c["id"], v["id"], c["author_id"], c["text"], c["like_count"],
                    c["is_favorited"], c["author_is_uploader"], c["parent"], c["timestamp"]
                ))

        # Add video tags
        if v.get("tags"):
            for tag in v.get("tags"):
                cur.execute("INSERT OR IGNORE INTO tags VALUES(?)", (tag,))
                cur.execute("INSERT OR IGNORE INTO video_tags(video, tag) VALUES(?,?)", (v["id"], tag))

        # Commit new video
        db.commit()
        if exists and exists[1] == "lost":
            utils.Logger.info("Lost video somehow recovered!", video_id)
        else: utils.Logger.info("Video successfully archived", video_id)


    def dump(self, args):
        if len(args) < 1 or not args[0]:
            raise TypeError("Dump what ?")

        if args[0].lower() == "thumbnails":
            if not os.path.exists("thumbnails"):
                os.mkdir("thumbnails")

            dumped = 0
            for video in db.execute("SELECT video_id, thumbnail, thumbnail_url FROM videos").fetchall():
                if not video[1]: continue
                thumbnail_path = f"thumbnails/{video[0]}.{video[2].split('.')[-1]}"
                if os.path.exists(thumbnail_path): continue

                with open(thumbnail_path, "wb") as thumb_file:
                    thumb_file.write(video[1])
                    dumped += 1

            if dumped != 0:
                print("Thumbnails successfully dumped!")
            else:
                print("There are no thumbnails in the database.")


    def playlist(self, path):
        if not path or not path[0]:
            raise ValueError("Missing path")
        else: path = " ".join(path)

        try:
            with open(path, "rt", newline="") as pl_file:
                playlist = list(csv.DictReader(pl_file, delimiter=','))[0]
                # Reset file stream position
                pl_file.seek(0)

                playlist["Videos"] = list(csv.reader(pl_file, delimiter=','))[4:-1]
        except FileNotFoundError:
            raise FileNotFoundError("Playlist file not found")
        except csv.Error as e:
            print("ERROR: The CSV reader appears illiterate.", e)
        except Exception as e:
            print(e)

        # Store playlist
        db.execute("INSERT OR IGNORE INTO playlists VALUES(?,?,?,?,?,?,?)", (playlist["Playlist ID"],
            playlist["Channel ID"], parse(playlist["Time Created"]).timestamp(),
            parse(playlist["Time Updated"]).timestamp(), playlist["Title"],
            playlist["Description"], playlist["Visibility"])
        )

        # Save videos
        for video in playlist["Videos"]:
            # remove spaces
            video = [video[0].replace(" ", ""), parse(video[1]).timestamp()]
            try:
                self.video([video[0]])
                db.execute("""INSERT INTO playlist_videos(playlist, video, added)
                VALUES(?,?,?)""", (playlist["Playlist ID"], video[0], video[1]))
            except sqlite3.IntegrityError:
                continue

        print("Finished Archiving playlist !")



    def history(self, args):
        pass



class Media:
    def __init__(self):
        self.help = "TODO"

    def default(self):
        raise Exception(f"Missing method")

    def get_info(self, video_id, simulate=True):
        if not video_id or not video_id[0]:
            raise ValueError("Missing url")
        elif len(video_id[0]) != VIDEO_ID_LENGTH:
            raise ValueError("Invalid video ID")
        else: video_id = video_id[0]

        utils.Logger.info("Extracting data", video_id)
        with yt_dlp.YoutubeDL({"getcomments":config["comments"]} | options) as ydlp:
            try:
                info = ydlp.extract_info(video_id, download=False)
            except yt_dlp.utils.DownloadError as e:
                # Attempt to get video from the wayback machine
                utils.Logger.info("Searching the Wayback machine", video_id)

                attempts = 3
                while True:
                    try:
                        info = ydlp.extract_info(f"{WAYBACK}{YOUTUBE}watch?v={video_id}", download=False)
                        info["availability"] = "recovered"
                        break
                    except yt_dlp.utils.DownloadError as e:
                        attempts -= 1
                        if attempts < 1:
                            print(utils.err_format("Failed recovering video"))
                            return
                        utils.Logger.info(f"Retrying, {attempts} left", video_id)
                    time.sleep(2)



        if info["extractor"] == "youtube" or info["extractor"] == "web.archive:youtube":
            # Download thumbnail
            info["thumbnail_url"] = info["thumbnail"]
            if config["thumbnails"]:
                thumbnail = requests.get(info["thumbnail"])
                print(thumbnail)
                info["thumbnail"] = thumbnail.content
                thumbnail.raise_for_status()
            else: info["thumbnail"] = None

            if info.get("like_count"):
                info.pop("like_count")
            if info.get("view_count"):
                info.pop("view_count")
            if info.get("description") == utils.DEFAULT_DESC:
                info["description"] = ""
            if not info.get("age_limit"):
                info["age_limit"] = 0;
            if not info.get("live_status"):
                info["live_status"] = None
            if not info.get("fps"):
                info["fps"] = None
            if not info.get("audio_channels"):
                info["audio_channels"] = None
            if not info.get("filesize_approx"):
                info["filesize"] = None
            else:
                info["filesize"] = info.get("filesize_approx")
                info.pop("filesize_approx")
            if not info.get("categories"):
                info["category"] = None
            else: info["category"] = info["categories"][0]
            if info.get("upload_date"):
                info["upload_date"] = parse(info.get("upload_date"))
            else: info["upload_date"] = None

            # Get video rating
            ryd = requests.get(f"{RYD_API}Votes?videoId={info['id']}").json()
            info["likes"] = ryd.get("likes")
            info["dislikes"] = ryd.get("dislikes")
            info["views"] = ryd.get("viewCount")
            info["rating"] = ryd.get("rating")
            info["comments"] = info.get("comments")
            info["channel_follower_count"] = info.get("channel_follower_count")
        else:
            utils.Logger.error()
            return

        if not simulate:
            return info


    def print_info(self, video_id):
        info = self.get_info(video_id, False)
        if not info: return

        print("\nThumbnail: " + info["thumbnail_url"])
        print(info["title"])
        print(f"{info['views']} views | {info['upload_date']} | {info['likes']} likes  {info['dislikes']} dislikes\n")
        print(f"{info['uploader']} | {info['channel_follower_count']} subscribers")
        print("-----------------------------------------------------------------")
        print(info["description"])
