import sys, os, json, csv, sqlite3, requests, time, yt_dlp, datetime, logging
from dateutil.parser import *
import utils

# Initialize logging
logging.basicConfig(
    level=logging.DEBUG,
    format="[%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler("debug.log"),
        logging.StreamHandler(sys.stdout)
    ])


def dict_factory(cursor, row):
    columns = [col[0] for col in cursor.description]
    return {key: value for key, value in zip(columns, row)}

try:
    # Open the database
    db = sqlite3.connect("youtube.db")
    db.row_factory = dict_factory
    with open("schema.sql", "r") as schema:
        db.executescript(schema.read())
except FileNotFoundError as e:
    print("Database schema not found.")

# Read configuration or write defaults
with open("configs.json", "a+") as config_file:
    try:
        config_file.seek(0)
        configs = json.loads(config_file.read())
        if configs.keys() != utils.CONFIGS_DEFAULT.keys():
            raise json.JSONDecodeError("Invalid keys")

        for key in utils.CONFIGS_DEFAULT:
            if not isinstance(configs[key], type(utils.CONFIGS_DEFAULT[key])):
                raise ValueError(f"Invalid value datatype for {key}")

    except (json.JSONDecodeError, ValueError) as e:
        configs = None

    if not configs:
        configs = utils.CONFIGS_DEFAULT
        config_file.seek(0)
        config_file.truncate()
        config_file.write(json.dumps(utils.CONFIGS_DEFAULT))


options = {
    "quiet": True,
    "logger": utils.YtLogger(),
    "extract_flat":"in_playlist"
}


# Global run command
def run(cmd_class, args):
    if not args: return cmd_class.default()

    cmd = args.pop(0).lower()
    invalid_attr = f'Invalid sub-command: "{cmd}"'
    cmd = getattr(cmd_class, cmd, AttributeError(invalid_attr))

    if callable(cmd):
        if cmd.__name__ != "default": return cmd(args)
        raise AttributeError(invalid_attr)
    elif type(cmd) == Exception: raise cmd
    return cmd


# https://www.youtube.com/watch?v=qOgldkETcxk
class Archive:
    def __init__(self):
        self.help = "TODO"

    def default(self):
        raise Exception(f"Missing method")

    def __get_video(self, id):
        utils.is_video(id)

        logging.info("Extracting data")
        with yt_dlp.YoutubeDL({"getcomments":configs["comments"]} | options) as ydlp:
            try:
                info = ydlp.extract_info(id, download=False)
            except yt_dlp.utils.DownloadError as e:
                logging.info("Searching the Wayback machine")
            else: return info

        for i in range(3):
            try:
                # Attempt to get video from the wayback machine
                info = ydlp.extract_info(f"{utils.WAYBACK}{utils.YOUTUBE}watch?v={id}", download=False)
                info["availability"] = "recovered"
                return info
            except yt_dlp.utils.DownloadError as e:
                logging.info(f"Retrying, {2-i} attempts left")
                utils.time.sleep(2)

        logging.warning("Failed recovering video")


    def __refine_metadata(self, info):
        # Download thumbnail
        info["thumbnail_url"] = info.get("thumbnail").split("?")[0]
        if configs["thumbnails"]:
            logging.info("Downloading video thumbnail")
            try:
                thumbnail = requests.get(info["thumbnail_url"])
                thumbnail.raise_for_status()
                if not thumbnail.content: raise
                info["thumbnail"] = thumbnail.content
            except requests.RequestException:
                logging.warn("Failed downloading thumbnail")
                info["thumbnail"] = None
        else: info["thumbnail"] = None

        try:
            # Get video rating
            ryd = requests.get(f"{utils.RYD_API}Votes?videoId={info['id']}", timeout=0.3).json()
            if not ryd.get("id"): raise requests.RequestException("Failed getting ratings")
        except requests.RequestException as e:
            logging.error(e)
            ryd = {}

        if info.get("description") == utils.DEFAULT_DESC: info["description"] = ""
        info["age_limit"] = info.get("age_limit")
        info["live_status"] = info.get("live_status")
        info["fps"] = info.get("fps")
        info["audio_channels"] = info.get("audio_channels")
        info["filesize"] = info.pop("filesize_approx") if info.get("filesize_approx") else None
        info["upload_date"] = parse(info["upload_date"]) if info.get("upload_date") else None
        info["category"] = info["categories"][0] if info.get("categories") else None
        info["likes"] = (ryd.get("likes") or info.get("like_count"))
        info["dislikes"] = ryd.get("dislikes")
        info["views"] = (ryd.get("viewCount") or info.get("view_count"))
        info["rating"] = ryd.get("rating")
        info["comments"] = info.get("comments")
        info["channel_follower_count"] = info.get("channel_follower_count")
        return info


    def video(self, video_id):
        if not video_id: raise ValueError("Missing video ID")
        video_id, cur = video_id[0], db.cursor()
        if exists := cur.execute("SELECT video_id, availability FROM videos WHERE video_id == ?",(video_id,)).fetchone():
            if exists["availability"] != "lost":
                logging.info("Video already archived, skipping.")
                return

            # Re-attempt to archive if a video is lost
            logging.info("Video previously archived but lost, attempting recovery")

        v = self.__get_video(video_id)
        if not v:
            cur.execute("INSERT OR IGNORE INTO videos (video_id, availability) VALUES (?,?)", (video_id, "lost"))
            db.commit()
            return

        # Prepare metadata for archival
        v = self.__refine_metadata(v)

        # Attempt to insert user, channel and category (if youtube decides to add new ones)
        cur.execute("INSERT OR IGNORE INTO categories VALUES(?)", (v.get("category"),))
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
            logging.error(f"Integrity Error: {e}")
            # Update video info
            # TODO: PUT THIS GARBAGE IN THE UPDATE METHOD WHEN ITS DONE
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
        for c in v.get("comments") or []:
            # Check if user is in the database
            if not cur.execute("SELECT 1 FROM users WHERE user_id == ?", (c["author_id"],)).fetchone():
                cur.execute("INSERT INTO users VALUES(?,?)", (c["author_id"], c["author"]))

            if c["parent"] == "root": c["parent"] = None
            cur.execute("INSERT INTO comments VALUES (?,?,?,?,?,?,?,?,?)", (
                c["id"], v["id"], c["author_id"], c["text"], c["like_count"],
                c["is_favorited"], c["author_is_uploader"], c["parent"], c["timestamp"]
            ))

        # Add video tags
        for tag in v.get("tags") or []:
            cur.execute("INSERT OR IGNORE INTO tags VALUES(?)", (tag,))
            cur.execute("INSERT OR IGNORE INTO video_tags(video, tag) VALUES(?,?)", (video_id, tag))

        # Commit new video
        db.commit()

        # Print video archival status
        if exists and exists["availability"] == "lost":
            msg = "Lost video somehow recovered!"
        elif v.get("availability") == "recovered":
            msg = "Video successfully recovered and archived"
        else: msg = "Video successfully archived"
        logging.info(msg)


    def dump(self, args):
        if not args: raise TypeError("Dump what ?")
        if args[0].lower() == "thumbnails":
            # Create thumbnails folder
            if not os.path.exists("thumbnails"):
                os.mkdir("thumbnails")

            dumped = 0
            for video in db.execute("SELECT video_id, thumbnail, thumbnail_url FROM videos").fetchall():
                if not video["thumbnail"]: continue
                thumbnail_path = f"thumbnails/{video['video_id']}.{video['thumbnail_url'].split('.')[-1]}"

                if os.path.exists(thumbnail_path): continue
                with open(thumbnail_path, "wb") as thumb_file:
                    thumb_file.write(video["thumbnail"])
                    dumped += 1

            if dumped != 0:
                print(utils.color("Thumbnails successfully dumped!", "green", True))
            else:
                print(utils.color("There are no thumbnails in the database.", "yellow"))

    # https://www.youtube.com/playlist?list=PLJOKxKrh9kD2zNxOC1oYZxcLbwHA7v50J
    def playlist(self, args):
        if not args: raise ValueError("What playlist ?")
        args = " ".join(args)

        # Check if the arguments are an ID or a filepath
        if args.split(".")[-1] == "csv":
            try:
                # Get playlist from file
                with open(args, "rt", newline="") as pl_file:
                    playlist = list(csv.DictReader(pl_file, delimiter=','))[0]
                    # Reset file stream position
                    pl_file.seek(0)

                    playlist["Videos"] = list(csv.reader(pl_file, delimiter=','))[4:-1]
            except FileNotFoundError:
                raise FileNotFoundError("Playlist file not found")
            except csv.Error as e:
                raise csv.Error(f"The CSV reader appears illiterate: {e}")
        else:
            # Get playlist from yt-dlp
            logging.info("Extracting playlist info")
            with yt_dlp.YoutubeDL({"quiet":True} | options) as ydlp:
                try:
                    info = ydlp.extract_info(f"{utils.YOUTUBE}playlist?list={args}", download=False)
                except yt_dlp.utils.DownloadError as e: return

            for i in range(len(info.get("entries") or [])):
                info["entries"][i] = [info["entries"][i]["id"], None]

            playlist = {
                "Playlist ID": info.get("id"),
                "Channel ID": info.get("channel_id"),
                "Time Created": None,
                "Time Updated": info.get("modified_date"),
                "Title": info.get("title"),
                "Description": info.get("description"),
                "Visibility": info.get("availability"),
                "Videos": info.get("entries")
            }

        # Parse timestamps into a datetime object
        if playlist.get("Time Updated"): parse(playlist["Time Updated"]).timestamp()
        if playlist.get("Time Created"): parse(playlist["Time Created"]).timestamp()
        id, cur = playlist["Playlist ID"], db.cursor()

        # Check if the playlist already exists in the database
        if cur.execute("SELECT 1 FROM playlists WHERE playlist_id == ?", (id,)).fetchone():
            print(f"Playlist already exists, Overwrite it ? {utils.color('(THIS CANNOT BE REVERTED)', 'red')}")
            utils.user_confirm()

        # Overwrite playlist if it already exists
        cur.execute("DELETE FROM playlists WHERE playlist_id == ?", (id,))
        cur.execute("INSERT INTO playlists VALUES(?,?,?,?,?,?,?)", (id,
            playlist["Channel ID"], playlist["Time Created"],
            playlist["Time Updated"], playlist["Title"],
            playlist["Description"], playlist["Visibility"])
        )

        # Save videos
        time_started = utils.time.perf_counter()
        for i, video in enumerate(playlist["Videos"]):
            utils.step_format(i+1, len(playlist["Videos"]), time_started)
            # Parse timestamp
            if video[1]: video[1] = parse(video[1]).timestamp()

            # remove spaces from video ID and parse timestamp
            video = [video[0].replace(" ", ""), video[1]]
            try:
                self.video([video[0]])
                cur.execute("INSERT INTO playlist_videos(playlist, video, added) VALUES(?,?,?)", (
                    playlist["Playlist ID"], video[0], video[1]))
            except sqlite3.IntegrityError as e:
                logging.error(f"Integrity Error: {e}")
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
        # Validate video IDs
        if thing == "video":
            utils.is_video(id)

        title = db.execute(f"SELECT title FROM {thing}s WHERE {thing}_id == ?", (id,)).fetchone()
        if title:
            title = title["title"]
            # Confirm user wants to delete the thing
            print(f"Delete {thing} <{title}> ? {utils.color('(THIS CANNOT BE REVERTED)', 'red')}")
            utils.user_confirm()
            print()

            db.execute(f"DELETE FROM {thing}s WHERE {thing}_id == ?", (id,))
            db.commit()
            print(utils.color(f"Successfully deleted {thing} <{id}>", "green", True))
        else: logging.error(f"{thing.capitalize()} not found")


    def video(self, video_id):
        if not video_id: raise ValueError("Missing video ID")
        else: self.__unarchive("video", video_id[0])

    def playlist(self, playlist_id):
        if not playlist_id: raise ValueError("Missing playlist ID")
        else: self.__unarchive("playlist", playlist_id[0])



class Config:
    def __init__(self):
        self.help = "TODO"

    def default(self):
        for key in configs:
            key_value = utils.color(configs[key],"green" if configs[key] else "red", bright=True)
            print(f"{key}: {key_value.lower()}")

    def get(self, args):
        if not args: raise ValueError("Get what ?")
        if len(args) < 2: raise ValueError("True or False ?")

        if args[0] not in configs:
            raise ValueError(f"Configuration {args[0]} does not exist")

        args[1] = args[1].lower()
        if args[1] == "true":
            configs[args[0]] = True
        elif args[1] == "false":
            configs[args[0]] = False
        else: raise ValueError("True or false ?")

        with open("configs.json", "w") as config_file:
            config_file.write(json.dumps(configs))

        logging.info(f"Get {args[0]} set to <False>")
