# **Rendering & Export Layer**

## **Purpose**

This layer takes:

* The **ranked clip list** produced in prior stages
* The **source video file**
* The **timestamped transcript**

and produces **final MP4 clips** with burned-in captions.

This layer performs **no scoring, no segmentation, and no reprocessing decisions.**
It is strictly responsible for **frame-accurate cutting and caption embedding.**

---

## **1. Inputs**

* `video_id`
* `source_video_path`
* `clip_candidates` (list of `{start_time, end_time, clip_id}`)
* `transcript` (WhisperX segments with timestamps)
* `export_selection` (top N + optional manual selection)

---

## **2. Output**

For each clip selected for export:

```
/processed/<video_id>/clips/<clip_id>.mp4
```

Final outputs must:

* Maintain audio/video sync exactly
* Include caption overlay sized appropriately for vertical video consumption
* Match aspect ratio of source or optionally convert to vertical (9:16) if requested

---

## **3. Subtitle Construction**

### 3.1 Subtitle Timing Extraction

For each clip, transcript is filtered to segments that fall within the clip boundaries:

```
clip_transcript = segments where
segment.start_time >= clip.start_time
AND segment.end_time <= clip.end_time
```

### 3.2 Caption Formatting

Subtitle file is generated in `.srt` format.

Example structure:

```
1
00:00:00,000 --> 00:00:01,200
first caption line

2
00:00:01,200 --> 00:00:03,000
second caption line
```

Captions are generated directly from transcript text — no re-alignment is required because WhisperX provides token timestamps.

---

## **4. Clip Extraction (FFmpeg)**

### Command Format (Frame-Accurate)

```
ffmpeg -i <source> \
  -ss <start_time> \
  -to <end_time> \
  -async 1 \
  -c:v libx264 -c:a aac -preset veryfast \
  temp_clip_no_subs.mp4
```

* `-ss` + `-to` ensure precise clipping
* Re-encoding ensures clean cuts regardless of source GOP structure

---

## **5. Subtitle Burn-In (FFmpeg)**

```
ffmpeg -i temp_clip_no_subs.mp4 \
  -vf "subtitles=<clip_subtitle_path>:force_style='Fontsize=32,Outline=2,Shadow=1'" \
  -c:a copy \
  <final_output_path>
```

Caption style attributes are adjustable via environment profile.

---

## **6. Optional Vertical Reframing Mode**

If vertical format requested:

1. Detect primary subject region (face tracking or mobile-safe center crop)
2. Reframe using:

```
-vf "crop=<width>:<height>:<x>:<y>,scale=1080:1920"
```

3. Burn captions **after** reframing.

This mode is only applied when explicitly requested.

---

## **7. Parallel Export Scheduling**

To avoid GPU starvation and disk I/O contention:

* Export jobs run in a queue.
* Max parallel exports configurable (default: 2).
* If cloud arbitration is active during export, limit is reduced to preserve resources.

Example queue logic:

```
if gpu_usage < threshold:
    start next export job
else:
    wait
```

This ensures:

* No stalling
* No dropped frames
* Smooth system performance during batches

---

## **8. Regenerate / Re-Export Rules**

Because timestamps + transcripts are stored:

* **Any clip can be re-exported at any time**
* Subtitle style can be changed without re-scoring
* Output format (wide / square / vertical) can be switched on demand

Rendering requires only:

* `start_time`
* `end_time`
* transcript slice

No inference.
No reprocessing pipeline calls.

---
