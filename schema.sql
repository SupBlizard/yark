PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS users (
    user_id TEXT PRIMARY KEY NOT NULL UNIQUE,
    username TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS channels (
    channel_id TEXT PRIMARY KEY NOT NULL,
    uploader_id TEXT NOT NULL UNIQUE,
    name TEXT NOT NULL,
    channel_follower_count INTEGER NOT NULL,
    url TEXT NOT NULL UNIQUE,
    FOREIGN KEY(uploader_id) REFERENCES users(user_id)
);

CREATE TABLE IF NOT EXISTS categories (
    category_id INTEGER PRIMARY KEY NOT NULL,
    name TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS categories_relations (
    video INTEGER PRIMARY KEY NOT NULL,
    category TEXT NOT NULL,
    FOREIGN KEY(video) REFERENCES video(video_id),
    FOREIGN KEY(category) REFERENCES categories(category_id)
);

CREATE TABLE IF NOT EXISTS tags (
    tag_id INTEGER PRIMARY KEY NOT NULL,
    name TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS tags_relations (
    video TEXT NOT NULL,
    tag INTEGER PRIMARY KEY NOT NULL,
    FOREIGN KEY(video) REFERENCES video(video_id),
    FOREIGN KEY(tag) REFERENCES tag(tag_id)
);

CREATE TABLE IF NOT EXISTS comments (
    comment_id TEXT PRIMARY KEY NOT NULL,
    video TEXT NOT NULL,
    author TEXT NOT NULL,
    content TEXT NOT NULL,
    likes INTEGER NOT NULL,
    is_favorited INTEGER NOT NULL,
    author_is_uploader INTEGER NOT NULL,
    parent TEXT,
    timestamp INTEGER NOT NULL,
    FOREIGN KEY(video) REFERENCES videos(video_id),
    FOREIGN KEY(author) REFERENCES users(user_id),
    FOREIGN KEY(parent) REFERENCES comments(comment_id)
);

CREATE TABLE IF NOT EXISTS videos (
    video_id TEXT PRIMARY KEY NOT NULL UNIQUE,
    title TEXT NOT NULL,
    description TEXT NOT NULL,
    channel TEXT NOT NULL,
    thumbnail BLOB,
    duration INTEGER NOT NULL,
    duration_string TEXT NOT NULL,
    views INTEGER NOT NULL,
    age_limit INTEGER NOT NULL,
    webpage_url TEXT NOT NULL,
    live_status TEXT NOT NULL,
    likes INTEGER,
    dislikes INTEGER,
    rating REAL NOT NULL,
    upload_date INTEGER NOT NULL,
    availability TEXT NOT NULL,
    width INTEGER NOT NULL,
    height INTEGER NOT NULL,
    fps REAL NOT NULL,
    audio_channels INTEGER NOT NULL,
    FOREIGN KEY(channel) REFERENCES channels(channel_id)
);

CREATE TABLE IF NOT EXISTS history (
    history_id INTEGER PRIMARY KEY NOT NULL,
    video TEXT NOT NULL UNIQUE,
    timestamp INTEGER NOT NULL,
    FOREIGN KEY(history_id) REFERENCES videos(video_id)
);

CREATE TABLE IF NOT EXISTS playlist (
    playlist_id TEXT PRIMARY KEY NOT NULL,
    channel TEXT NOT NULL,
    created INTEGER NOT NULL,
    updated INTEGER NOT NULL,
    title TEXT NOT NULL,
    description TEXT,
    visibility TEXT NOT NULL,
    FOREIGN KEY(channel) REFERENCES channels(channel_id)
);



-- Insert youtube's categories
INSERT OR IGNORE INTO categories ('category_id','name') VALUES ('1', 'Film & Animation');
INSERT OR IGNORE INTO categories ('category_id','name') VALUES ('2', 'Autos & Vehicles');
INSERT OR IGNORE INTO categories ('category_id','name') VALUES ('10', 'Music');
INSERT OR IGNORE INTO categories ('category_id','name') VALUES ('15', 'Pets & Animals');
INSERT OR IGNORE INTO categories ('category_id','name') VALUES ('17', 'Sports');
INSERT OR IGNORE INTO categories ('category_id','name') VALUES ('19', 'Travel & Events');
INSERT OR IGNORE INTO categories ('category_id','name') VALUES ('20', 'Gaming');
INSERT OR IGNORE INTO categories ('category_id','name') VALUES ('22', 'People & Blogs');
INSERT OR IGNORE INTO categories ('category_id','name') VALUES ('23', 'Comedy');
INSERT OR IGNORE INTO categories ('category_id','name') VALUES ('24', 'Entertainment');
INSERT OR IGNORE INTO categories ('category_id','name') VALUES ('25', 'News & Politics');
INSERT OR IGNORE INTO categories ('category_id','name') VALUES ('26', 'Howto & Style');
INSERT OR IGNORE INTO categories ('category_id','name') VALUES ('27', 'Education');
INSERT OR IGNORE INTO categories ('category_id','name') VALUES ('28', 'Science & Technology');
INSERT OR IGNORE INTO categories ('category_id','name') VALUES ('29', 'Nonprofits & Activism');
