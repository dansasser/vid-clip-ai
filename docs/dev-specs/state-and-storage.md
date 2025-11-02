# **State, Storage, and Reprocessing Logic**

## **Purpose**

This component ensures that all information derived from a video — transcripts, clip segments, scoring values, and ranking results — is persistently stored so the pipeline does not repeat work. It also enables clips to be re-ranked, re-scored, or re-exported at any time, without reprocessing the source video.

The storage layer creates a **stable reference** between:

* The source video
* The transcript
* The clip candidate list
* The scoring results
* Exported clips (optional artifacts)

---

## **1. Video Lifecycle State Machine**

```
INGESTED → TRANSCRIBED → SEGMENTED → SCORED → READY → ARCHIVED
```

| State           | Definition                                                                    |
| --------------- | ----------------------------------------------------------------------------- |
| **INGESTED**    | Video detected and registered into system state.                              |
| **TRANSCRIBED** | WhisperX transcript stored and indexed by timestamps.                         |
| **SEGMENTED**   | Gemma meaning-based clip boundaries computed and stored.                      |
| **SCORED**      | Clip candidates evaluated by Qwen2-VL, Micro-Emphasis, and optional Qwen3-VL. |
| **READY**       | Ranked clip list available for export.                                        |
| **ARCHIVED**    | Video moved out of watch path; metadata remains accessible.                   |

State transitions occur in order and are recorded persistently.

---

## **2. Persistent Data Requirements**

All stored data is keyed by a `video_id`.
The format of `video_id` is implementation-defined (UUID, filename hash, etc.).
Only the requirement is **stability** across runs.

### **2.1 Transcript**

* Full WhisperX transcript with timestamps.
* Stored once per video.
* Used as reference for future clip export and re-scoring.

### **2.2 Clip Candidate Records**

For each detected semantic segment:

* `clip_id`
* `video_id`
* `start_time`
* `end_time`

### **2.3 Scoring Records**

For each clip:

* `text_score` (Gemma)
* `vision_score_local` (Qwen2-VL)
* `audio_emphasis_score`
* `facial_emphasis_score`
* `vision_score_cloud` (only if escalated)
* `final_score`
* `escalated_to_cloud` (boolean)

### **2.4 Ranking Record**

* List of clip_ids sorted by `final_score`
* Top N clips flagged for auto-export

---

## **3. File System Organization**

```
/incoming/               ← watched ingestion directory
/processed/<video_id>/   ← contains processed source + derived outputs
/archive/<video_id>/     ← optional long-term storage
```

* Source video is moved from `/incoming` to `/processed/<video_id>/` after transcription.
* Archiving moves `/processed/<video_id>/` to `/archive/<video_id>/`.

The system maintains one authoritative path for each video.

---

## **4. Reprocessing Rules**

Reprocessing must **not** repeat work unnecessarily.
The following rules apply:

| Action                        | Requires Re-Transcription? | Requires Re-Segmentation? | Requires Re-Scoring?                   |
| ----------------------------- | -------------------------- | ------------------------- | -------------------------------------- |
| Changing clip ranking weights | No                         | No                        | Yes (re-score only)                    |
| Updating local VLM            | No                         | No                        | Yes (vision_score_local re-evaluation) |
| Updating cloud VLM            | No                         | No                        | Only ambiguous clips are re-escalated  |
| Changing caption style        | No                         | No                        | No (re-export only)                    |

The transcript remains the **ground truth anchor** for the lifetime of the video.

---

## **5. Clip Export Triggers**

When state transitions to **READY**:

* Top N clips (default = 3) are automatically rendered.
* All clips remain available for manual export later.
* Re-export uses stored timestamps + transcript alignment directly.

No inference is repeated during export.

---

