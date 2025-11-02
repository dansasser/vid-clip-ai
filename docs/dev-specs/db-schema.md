## Core Concepts

Your system tracks:

1. A **Video**
2. The **Segments** (candidate clips) extracted from the video
3. The **Transcript lines** aligned to timestamps
4. The **Model scoring** used to determine “clip quality”
5. Processing state so the pipeline knows what is done

That’s it. Five tables.

---

## Schema (Portable SQL)

```sql
CREATE TABLE videos (
    id INTEGER PRIMARY KEY,
    file_path TEXT NOT NULL,               -- Path on disk or URL
    title TEXT,
    source_type TEXT,                      -- 'local', 'youtube', 'gdrive', etc.
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    status TEXT DEFAULT 'pending'          -- 'pending', 'processing', 'done', 'archived'
);
```

```sql
CREATE TABLE transcript (
    id INTEGER PRIMARY KEY,
    video_id INTEGER NOT NULL,
    start_time REAL NOT NULL,              -- seconds
    end_time REAL NOT NULL,
    text TEXT NOT NULL,
    FOREIGN KEY (video_id) REFERENCES videos(id)
);
```

```sql
CREATE TABLE segments (
    id INTEGER PRIMARY KEY,
    video_id INTEGER NOT NULL,
    start_time REAL NOT NULL,
    end_time REAL NOT NULL,
    source TEXT NOT NULL,                  -- 'asr', 'local_vlm', 'cloud_vlm'
    FOREIGN KEY (video_id) REFERENCES videos(id)
);
```

```sql
CREATE TABLE segment_scores (
    segment_id INTEGER PRIMARY KEY,
    text_score REAL,                       -- Score from Gemma: "how interesting is what was said"
    vision_score REAL,                     -- Score from Qwen2: "how visually eventful"
    cloud_score REAL,                      -- Score from Qwen3 if needed
    combined_score REAL,                   -- Weighted score used to pick the top clips
    FOREIGN KEY (segment_id) REFERENCES segments(id)
);
```

```sql
CREATE TABLE processing_log (
    id INTEGER PRIMARY KEY,
    video_id INTEGER NOT NULL,
    step TEXT NOT NULL,                    -- 'download', 'transcribe', 'segment', 'score', 'render'
    status TEXT NOT NULL,                  -- 'ok', 'fail'
    message TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (video_id) REFERENCES videos(id)
);
```

---

## Why this schema is good

### Database portability

Every field is:

* INTEGER
* REAL
* TEXT
* TIMESTAMP

These types map **directly** to Postgres without change.

### Scoring flexibility

If later you add:

* emotional tone detector
* excitement detection
* speaker ID
* faces-on-screen classifier

You just add **columns to `segment_scores`**.
No refactor needed.

### Clip regeneration

Since clips are defined by:
`video.file_path + segment.start_time + segment.end_time`

You can always:

* re-render a clip
* change caption styling
* upscale later
* re-score everything with new models

### Nothing is lost

This schema is **non-destructive**.
You can always re-run or improve your logic without reprocessing the original video.

---

## Later scaling path (future, no action now)

When the app blows up:

* Move from SQLite → Postgres (no schema change)
* Add Qdrant / Weaviate for semantic search (parallel, no replacement)
* Store videos in S3 or Backblaze B2 instead of local disk

No rewrites. Just plug-ins.

---
