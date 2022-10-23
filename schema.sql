PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS users (
    user_id TEXT PRIMARY KEY NOT NULL UNIQUE,
    username TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS channels (
    channel_id TEXT PRIMARY KEY NOT NULL,
    uploader_id TEXT,
    name TEXT NOT NULL,
    channel_follower_count INTEGER,
    url TEXT NOT NULL UNIQUE,
    FOREIGN KEY(uploader_id) REFERENCES users(user_id) ON DELETE RESTRICT
);

CREATE TABLE IF NOT EXISTS categories (
    name TEXT PRIMARY KEY NOT NULL UNIQUE
);

CREATE TABLE IF NOT EXISTS tags (
    name TEXT PRIMARY KEY NOT NULL UNIQUE
);

CREATE TABLE IF NOT EXISTS video_tags (
    id INTEGER PRIMARY KEY NOT NULL,
    video TEXT NOT NULL,
    tag TEXT NOT NULL,
    FOREIGN KEY(video) REFERENCES videos(video_id) ON DELETE CASCADE,
    FOREIGN KEY(tag) REFERENCES tags(name) ON DELETE CASCADE
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
    FOREIGN KEY(video) REFERENCES videos(video_id) ON DELETE CASCADE,
    FOREIGN KEY(author) REFERENCES users(user_id) ON DELETE CASCADE,
    FOREIGN KEY(parent) REFERENCES comments(comment_id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS videos (
    video_id TEXT PRIMARY KEY NOT NULL UNIQUE,
    title TEXT,
    description TEXT,
    channel TEXT,
    thumbnail BLOB,
    thumbnail_url TEXT,
    duration INTEGER,
    views INTEGER,
    age_limit INTEGER,
    live_status TEXT,
    likes INTEGER,
    dislikes INTEGER,
    rating REAL,
    upload_timestamp INTEGER,
    availability TEXT,
    width INTEGER,
    height INTEGER,
    fps REAL,
    audio_channels INTEGER,
    category TEXT,
    filesize INTEGER,
    archived INTEGER DEFAULT (strftime('%s','now')),
    FOREIGN KEY(category) REFERENCES categories(name) ON DELETE RESTRICT,
    FOREIGN KEY(channel) REFERENCES channels(channel_id) ON DELETE RESTRICT
);

CREATE TABLE IF NOT EXISTS history (
    history_id INTEGER PRIMARY KEY NOT NULL,
    video TEXT,
    watched INTEGER NOT NULL,
    FOREIGN KEY(history_id) REFERENCES videos(video_id)
);

CREATE TABLE IF NOT EXISTS playlists (
    playlist_id TEXT PRIMARY KEY NOT NULL,
    channel TEXT,
    created INTEGER,
    updated INTEGER,
    title TEXT,
    description TEXT,
    visibility TEXT
);

CREATE TABLE IF NOT EXISTS playlist_videos (
    pl INTEGER PRIMARY KEY NOT NULL,
    playlist TEXT NOT NULL,
    video TEXT NOT NULL, -- No foreign key as playlists must remain static
    added INTEGER,
    FOREIGN KEY(playlist) REFERENCES playlists(playlist_id) ON DELETE CASCADE
);



-- Insert youtube's categories
INSERT OR IGNORE INTO categories VALUES ('Film & Animation');
INSERT OR IGNORE INTO categories VALUES ('Autos & Vehicles');
INSERT OR IGNORE INTO categories VALUES ('Music');
INSERT OR IGNORE INTO categories VALUES ('Pets & Animals');
INSERT OR IGNORE INTO categories VALUES ('Sports');
INSERT OR IGNORE INTO categories VALUES ('Travel & Events');
INSERT OR IGNORE INTO categories VALUES ('Gaming');
INSERT OR IGNORE INTO categories VALUES ('People & Blogs');
INSERT OR IGNORE INTO categories VALUES ('Comedy');
INSERT OR IGNORE INTO categories VALUES ('Entertainment');
INSERT OR IGNORE INTO categories VALUES ('News & Politics');
INSERT OR IGNORE INTO categories VALUES ('Howto & Style');
INSERT OR IGNORE INTO categories VALUES ('Education');
INSERT OR IGNORE INTO categories VALUES ('Science & Technology');
INSERT OR IGNORE INTO categories VALUES ('Nonprofits & Activism');
