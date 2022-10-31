import sys, os, json, csv, sqlite3, requests, time, yt_dlp, datetime, logging
from dateutil.parser import *
import urllib.parse


import utils
from .configs import options, configs

# Initialize database
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
    logging.critical("Database schema not found.")
    sys.exit()

# https://www.youtube.com/watch?v=qOgldkETcxk
class Archive:
    """Archive command:

    This command is used to archive stuff into a database.

    video: archive video [video id]
      Archive the metadata of a single video.
      This method requires a youtube video ID.

    playlist: archive playlist [playlist id / filepath]
      Archive every video in a playlist.
      This method accepts youtube playlist IDs and
      Google takout playlist CSVs.

    history: archive history [filepath]
      Archive every video from a watch history JSON file
      (from Google takeout). This method requires a
      filepath to said history file.

    dump: archive dump thumbnails
      A sub-command used to dump things to disk.
      It is only used for dumping thumbnails and it's
      very likely this will be removed from this command
      at some point in the future.
    """
    def help(self, args): return self.__doc__
    def default(self): return self.__doc__

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
        info["thumbnail_url"] = info.get("thumbnail")
        if configs["thumbnails"] and info["thumbnail_url"]:
            logging.info("Downloading video thumbnail")
            try:
                thumbnail = requests.get(info["thumbnail_url"].split("?")[0])
                thumbnail.raise_for_status()
                if not thumbnail.content: raise
                info["thumbnail"] = thumbnail.content
            except requests.RequestException:
                logging.warn("Failed downloading thumbnail")
                info["thumbnail"] = None
        else: info["thumbnail"] = None

        try:
            # Get video rating
            ryd = requests.get(f"{utils.RYD_API}Votes?videoId={info['id']}", timeout=1).json()
            if not ryd.get("id"): raise requests.RequestException("Failed getting ratings")
        except requests.RequestException as e:
            logging.error(e)
            ryd = {}

        if info.get("description") == utils.DEFAULT_DESC: info["description"] = ""
        info["age_limit"] = info.get("age_limit")
        info["live_status"] = info.get("live_status")
        info["fps"] = info.get("fps")
        info["width"] = info.get("width")
        info["audio_channels"] = info.get("audio_channels")
        info["filesize"] = info.pop("filesize_approx") if info.get("filesize_approx") else None
        info["upload_date"] = parse(info["upload_date"]).timestamp() if info.get("upload_date") else None
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
                print("Video already archived, skipping.")
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

        # Insert user and channel
        cur.execute("INSERT OR IGNORE INTO users VALUES(?,?)", (
            v.get("uploader_id"), (v.get("uploader") or v.get("channel") or v.get("uploader_id"))
        ))
        cur.execute("INSERT OR IGNORE INTO channels VALUES(?,?,?,?,?)", (
            v.get("channel_id"), v.get("uploader_id"), (v.get("channel") or v.get("uploader") or v.get("uploader_id")),
            v.get("channel_follower_count"), v.get("channel_url")
        ))

        try:
            # Add video
            cur.execute("INSERT INTO videos VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)", (
                v["id"], v["fulltitle"], v["description"], v["channel_id"], v["thumbnail"], v["thumbnail_url"],
                v["duration"], v["views"], v["age_limit"], v["live_status"], v["likes"], v["dislikes"],
                v["rating"], v["upload_date"], v["availability"], v["width"], v["height"], v["fps"],
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
                v["rating"], v["upload_date"], v["availability"], v["width"], v["height"], v["fps"],
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
        print(utils.color(msg, "green", True))


    def dump(self, args):
        if not args: raise TypeError("Dump what ?")
        if args[0].lower() == "thumbnails":
            # Create thumbnails folder
            if not os.path.exists("thumbnails"):
                os.mkdir("thumbnails")

            dumped = 0
            for video in db.execute("SELECT video_id, thumbnail, thumbnail_url FROM videos").fetchall():
                if not video["thumbnail"]: continue
                thumbnail_path = f"thumbnails/{video['video_id']}.{video['thumbnail_url'].split('.')[-1].split('?')[0]}"

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
                logging.error(f"CSV reader error: {e}")
                return
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
        if playlist.get("Time Updated"): playlist["Time Updated"] = parse(playlist["Time Updated"]).timestamp()
        if playlist.get("Time Created"): playlist["Time Created"] = parse(playlist["Time Created"]).timestamp()
        id, cur = playlist["Playlist ID"], db.cursor()

        # Check if the playlist already exists in the database
        if cur.execute("SELECT 1 FROM playlists WHERE playlist_id == ?", (id,)).fetchone():
            print(f"Playlist already exists, Overwrite it ?", end=" ")
            if not utils.user_confirm():
                print("Aborting ...")
                return

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

        db.commit()
        # TODO: print total time taken
        print(utils.color(f"Finished Archiving playlist <{playlist['Title']}> ({playlist['Playlist ID']})", "green", True))


    def history(self, args):
        if not args: raise ValueError("Missing path")
        path = " ".join(args)

        try:
            with open(path, "r", encoding="utf8") as history_file:
                history = json.load(history_file)
        except FileNotFoundError as e:
            raise FileNotFoundError("History file not found")
        except (json.JSONDecodeError, ValueError) as e:
            print(f"{e}, {type(e)}")

        time_started = utils.time.perf_counter()
        unavailable,cur = 0,db.cursor()
        for i, video in enumerate(history):
            utils.step_format(i+1, len(history), time_started)
            if video.get("titleUrl"):
                video["titleUrl"] = video.get("titleUrl").split("\u003d")[1]
            else: unavailable+=1

            try:
                self.video([video.get("titleUrl")])
                data_tuple = (video.get("titleUrl"), parse(video["time"]).timestamp())
                if not cur.execute("SELECT 1 FROM history WHERE video==? AND watched==?", data_tuple).fetchone():
                    cur.execute("INSERT INTO history(video, watched) VALUES(?,?)", data_tuple)
                    db.commit()
                    print(utils.color("Added to history", "green", True))
                else: print("Video already in history.")
            except sqlite3.IntegrityError as e:
                logging.error(f"Integrity Error: {e}")
            except Exception as e:
                print(f"{type(e)}, {e}")

        time_taken = utils.format_time(utils.time.perf_counter()-time_started)
        print(utils.color(f"Finished Archiving history, Time taken: {time_taken['time']} {time_taken['unit']}", "green", True))
        print(f"{unavailable} unavailable")




# https://www.youtube.com/watch?v=gbRe9zGFh6k
class Unarchive:
    """Unarchive command:

    This command is used to DELETE things from the database.

    video: unarchive video [video id]
      Unarchive a single video from the database.
      The video and all data associated with it,
      (like comments and tags) will be deleted.
      requires a video ID.

    playlist: unarchive playlist [playlist id]
      Unarchive a playlist from the database.
      Executing this will remove the playlist from
      database including all references to videos and
      associated timestamps. However, the videos
      themselves will not be deleted. Requires a
      playlist ID.
    """
    def help(self, args): return self.__doc__
    def default(self): return self.__doc__

    def __unarchive(self, thing, id):
        # Validate video IDs
        if thing == "video": utils.is_video(id)

        title = db.execute(f"SELECT title FROM {thing}s WHERE {thing}_id == ?", (id,)).fetchone()
        if title:
            title = title["title"]
            # Confirm user wants to delete the thing
            print(f"Delete {thing} <{title}> ?", end=" ")
            if not utils.user_confirm():
                print("Aborting ...")
                return

            print()

            db.execute(f"DELETE FROM {thing}s WHERE {thing}_id == ?", (id,))
            db.commit()
            print(utils.color(f"Successfully deleted {thing} <{id}>", "green", True))
        else: print(f"{thing.capitalize()} not found")


    def video(self, video_id):
        if not video_id: raise ValueError("Missing video ID")
        else: self.__unarchive("video", video_id[0])

    def playlist(self, playlist_id):
        if not playlist_id: raise ValueError("Missing playlist ID")

        if playlist_id[0] == "*":
            print(f"Delete all playlists ?", end=" ")
            if utils.user_confirm():
                db.executescript(f"DELETE FROM playlists;")
                db.commit()
            else: print("Aborting ...")
        else: self.__unarchive("playlist", playlist_id[0])
