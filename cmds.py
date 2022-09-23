import os, json, csv, sqlite3, requests, time, yt_dlp
import datetime
from dateutil.parser import *
import utils


try:
    # Open the database
    db = sqlite3.connect("youtube.db")
    with open("schema.sql", "r") as schema:
        db.executescript(schema.read())
except FileNotFoundError as e:
    print("Database schema not found.")


# Read configuration or write defaults
CONFIGS_DEFAULT = {"thumbnails": True, "comments": True}
with open("configs.json", "a+") as config_file:
    try:
        config_file.seek(0)
        configs = json.loads(config_file.read())
        if configs.keys() != CONFIGS_DEFAULT.keys():
            raise json.JSONDecodeError("Invalid keys")

        for key in CONFIGS_DEFAULT:
            if not isinstance(configs[key], type(CONFIGS_DEFAULT[key])):
                raise ValueError(f"Invalid value datatype for {key}")

    except (json.JSONDecodeError, ValueError) as e:
        configs = None

    if not configs:
        configs = CONFIGS_DEFAULT
        config_file.seek(0)
        config_file.truncate()
        config_file.write(json.dumps(CONFIGS_DEFAULT))


options = {
    "quiet": True,
    "logger": utils.Logger()
}


# Global run command
def run(cmd_class, args):
    if not args:
        return cmd_class.default()

    cmd = args.pop(0).lower()
    invalid_attr = f'Invalid attribute "{cmd}"'
    cmd = getattr(cmd_class, cmd, Exception(invalid_attr))

    if callable(cmd):
        if cmd.__name__ != "default": return cmd(args)
        else: raise Exception(invalid_attr)
    elif type(cmd) == Exception: raise cmd
    else: return cmd


# https://www.youtube.com/watch?v=qOgldkETcxk
class Archive:
    def __init__(self):
        self.help = "TODO"

    def default(self):
        raise Exception(f"Missing method")

    def video(self, video_id):
        video_id, cur = video_id[0], db.cursor()
        exists = cur.execute("SELECT video_id, availability FROM videos WHERE video_id == ?",(video_id,)).fetchone()
        if exists:
            if exists[1] != "lost":
                utils.Logger.info("Video already archived, skipping.", video_id)
                return

            # Re-attempt to archive if a video is lost
            utils.Logger.info("Video previously archived but lost, attempting recovery", video_id)

        # Extract video info
        v = Media.get_info(self, [video_id], simulate=False)
        if not v:
            cur.execute("INSERT OR IGNORE INTO videos (video_id, availability) VALUES (?,?)", (video_id,"lost"))
            db.commit()
            return

        # If youtube decides to add new categories
        cur.execute("INSERT OR IGNORE INTO categories VALUES(?)", (v.get("category"),))
        # Insert user and channel
        cur.execute("INSERT OR IGNORE INTO users VALUES(?,?)", (v.get("uploader_id"), v.get("uploader")))
        cur.execute("INSERT OR IGNORE INTO channels VALUES(?,?,?,?,?)", (
            v.get("channel_id"), v.get("uploader_id"), (v.get("channel") or v.get("uploader")),
            v.get("channel_follower_count"), v.get("channel_url")
        ))

        try:
            # Add video
            cur.execute("INSERT INTO videos VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)", (
                v["id"], v["fulltitle"], v["description"], v["channel_id"], v["thumbnail"], v["thumbnail_url"],
                v["duration"], v["views"], v["age_limit"], v["live_status"], v["likes"], v["dislikes"],
                v["rating"], v["upload_date"].timestamp(), v["availability"], v["width"], v["height"], v["fps"],
                v["audio_channels"], v["category"], v["filesize"], None
            ))
        except sqlite3.IntegrityError as e:
            utils.Logger.error(msg=utils.err_format(f"Integrity Error: {e}", video_id, "sqlite3"))
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
                cur.execute("INSERT OR IGNORE INTO video_tags(video, tag) VALUES(?,?)", (video_id, tag))

        # Commit new video
        db.commit()
        if exists and exists[1] == "lost":
            utils.Logger.info("Lost video somehow recovered!", video_id)
        elif v.get("availability") == "recovered":
            utils.Logger.info("Video successfully recovered and archived", video_id)
        else:
            utils.Logger.info("Video successfully archived", video_id)


    def dump(self, args):
        if not args: raise TypeError("Dump what ?")
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
                print(utils.color("Thumbnails successfully dumped!", "green", True))
            else:
                print(utils.color("There are no thumbnails in the database.", "yellow"))

    # https://www.youtube.com/playlist?list=PLJOKxKrh9kD2zNxOC1oYZxcLbwHA7v50J
    def playlist(self, path):
        if not path:
            raise ValueError("Missing path")
        else: path = " ".join(path)

        try:
            with open(path, "rt", newline="") as pl_file:
                playlist = list(csv.DictReader(pl_file, delimiter=','))[0]
                # Reset file stream position
                pl_file.seek(0)

                playlist["Videos"] = list(csv.reader(pl_file, delimiter=','))[4:-1]
            if len(playlist.get("Playlist ID")) != utils.PLAYLIST_ID_LENGTH:
                raise ValueError("Invalid playlist ID")
        except FileNotFoundError:
            raise FileNotFoundError("Playlist file not found")
        except csv.Error as e:
            raise csv.Error(f"The CSV reader appears illiterate: {e}")

        cur = db.cursor()

        # Clear previous playlist data
        cur.execute("DELETE FROM playlists WHERE playlist_id == ?", (playlist["Playlist ID"],))

        # Store playlist
        cur.execute("INSERT OR IGNORE INTO playlists VALUES(?,?,?,?,?,?,?)", (playlist["Playlist ID"],
            playlist["Channel ID"], parse(playlist["Time Created"]).timestamp(),
            parse(playlist["Time Updated"]).timestamp(), playlist["Title"],
            playlist["Description"], playlist["Visibility"])
        )

        # Save videos
        time_started = utils.time.perf_counter()
        for i, video in enumerate(playlist["Videos"]):
            utils.step_format(i+1, len(playlist["Videos"]), time_started)
            # remove spaces from video ID and parse timestamp
            video = [video[0].replace(" ", ""), parse(video[1]).timestamp()]
            try:
                self.video([video[0]])
                cur.execute("INSERT INTO playlist_videos(playlist, video, added) VALUES(?,?,?)", (
                    playlist["Playlist ID"], video[0], video[1]))
            except sqlite3.IntegrityError as e:
                utils.Logger.error(msg=utils.err_format(f"Integrity Error: {e}", video[0], "sqlite3"))
                continue

        db.commit()
        # TODO: print total time taken
        print(utils.color(f"Finished Archiving playlist <{playlist['Title']}> ({playlist['Playlist ID']})", "green", True))


    def history(self, args):
        # TODO
        pass


# https://www.youtube.com/watch?v=gbRe9zGFh6k
class Unarchive:
    def __init__(self):
        self.help = "TODO"

    def default(self):
        raise Exception(f"Missing method")

    def __unarchive(self, thing, id):
        # Figure out what it is
        if thing == "video" and len(id) != utils.VIDEO_ID_LENGTH:
            raise ValueError("Invalid video ID")
        elif thing == "playlist" and len(id) != utils.PLAYLIST_ID_LENGTH:
            raise ValueError("Invalid playlist ID")

        if title := db.execute(f"SELECT title FROM {thing}s WHERE {thing}_id == ?", (id,)).fetchone():
            # Confirm user wants to delete the thing
            print(f"Delete {thing} <{title[0]}> ? {utils.color('(THIS CANNOT BE REVERTED)', 'red')}")
            if not utils.user_confirm(): return
            print()

            db.execute(f"DELETE FROM {thing}s WHERE {thing}_id == ?", (id,))
            db.commit()
            print(utils.color(f"Successfully deleted {thing} <{id}>", "green", True))
        else: utils.Logger.error(msg=utils.err_format(f"{thing.capitalize()} not found", id, "sqlite3"))


    def video(self, video_id):
        if not video_id:
            raise ValueError("Missing video ID")
        else: self.__unarchive("video", video_id[0])

    def playlist(self, playlist_id):
        if not playlist_id:
            raise ValueError("Missing playlist ID")
        else: self.__unarchive("playlist", playlist_id[0])


class Media:
    def __init__(self):
        self.help = "TODO"

    def default(self):
        raise Exception(f"Missing method")

    def get_info(self, video_id, simulate=True):
        if not video_id:
            raise ValueError("Missing video ID")
        elif len(video_id[0]) != utils.VIDEO_ID_LENGTH:
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
                        info = ydlp.extract_info(f"{utils.WAYBACK}{utils.YOUTUBE}watch?v={video_id}", download=False)
                        info["availability"] = "recovered"
                        break
                    except yt_dlp.utils.DownloadError as e:
                        attempts -= 1
                        if attempts < 1:
                            utils.Logger.info(msg=utils.err_format("Failed recovering video", video_id))
                            return
                        utils.Logger.info(f"Retrying, {attempts} left", video_id)
                    utils.time.sleep(2)



        if info["extractor"] == "youtube" or info["extractor"] == "web.archive:youtube":
            # Download thumbnail
            info["thumbnail_url"] = info["thumbnail"].split("?")[0]
            if config["thumbnails"]:
                utils.Logger.info(f"Downloading video thumbnail", video_id)
                try:
                    thumbnail = requests.get(info["thumbnail_url"])
                    thumbnail.raise_for_status()
                    if not thumbnail.content: raise
                except requests.RequestException:
                    utils.Logger.error(msg=utils.err_format("Failed downloading thumbnail", video_id, "requests"))

            try:
                # Get video rating
                ryd = requests.get(f"{utils.RYD_API}Votes?videoId={video_id}", timeout=0.2).json()
                if not ryd.get("id"): raise requests.RequestException("Failed getting ratings")
            except requests.RequestException as e:
                utils.Logger.error(msg=utils.err_format(e, video_id, "requests"))
                ryd = {}

            if info.get("description") == utils.DEFAULT_DESC: info["description"] = ""
            info["age_limit"] = (info.get("age_limit") or None)
            info["live_status"] = (info.get("live_status") or None)
            info["fps"] = (info.get("fps") or None)
            info["audio_channels"] = (info.get("audio_channels") or None)
            info["filesize"] = info.pop("filesize_approx") if info.get("filesize_approx") else None
            info["upload_date"] = parse(info["upload_date"]) if info.get("upload_date") else None
            info["category"] = info["categories"][0] if info.get("categories") else None

            info["likes"] = (ryd.get("likes") or info.get("like_count"))
            info["dislikes"] = ryd.get("dislikes")
            info["views"] = (ryd.get("viewCount") or info.get("view_count"))
            info["rating"] = ryd.get("rating")

            info["thumbnail"] = (thumbnail.content or None)
            info["comments"] = info.get("comments")
            info["channel_follower_count"] = info.get("channel_follower_count")
        else:
            utils.Logger.error(msg=err_format("Invalid extractor", id=video_id, process="get_info"))
            return

        if not simulate: return info


    def print_info(self, video_id):
        info = self.get_info(video_id, False)
        if not info: return

        print("\nThumbnail: " + info["thumbnail_url"])
        print(info["title"])
        print(f"{info['views']} views | {info['upload_date']} | {info['likes']} likes  {info['dislikes']} dislikes\n")
        print(f"{info['uploader']} | {info['channel_follower_count']} subscribers")
        print("-----------------------------------------------------------------")
        print(info["description"])



class Config:
    def __init__(self):
        self.help = "TODO"

    def default(self):
        print(f"Your configuration: {configs}")

    def get(self, args):
        if not args: raise ValueError("Get what ?")
        if len(args) < 2: raise ValueError("True or False ?")

        if args[0] not in configs:
            raise ValueError(f"Configuration {args[0]} does not exist")

        state = args[1]
        if state == "true":
            configs[args[0]] = True
            utils.Logger.info(f"Get {args[0]} set to <True>")
        elif state == "false":
            configs[args[0]] = False
            utils.Logger.info(f"Get {args[0]} set to <False>")
        else: raise ValueError("True or false ?")

        with open("configs.json", "w") as config_file:
            config_file.write(json.dumps(configs))
