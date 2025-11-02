# Video Clip Extraction System
---
This system uses multiple cooperating agents, each responsible for a distinct part of the video processing pipeline.
The agents do not overlap responsibilities. Each operates on structured inputs and produces structured outputs.

---

## **1. Audio Transcription Agent (Whisper)**

**Role:** Convert audio into timestamped text.
**Input:** Raw video file
**Output:** Transcript lines (`start_time`, `end_time`, `text`)
**Notes:**

* Accuracy and timestamp alignment are critical.
* Output is stored immediately in the database.

---

## **2. Text Scoring Agent (Gemma Local)**

**Role:** Identify speech-based clip candidates from the transcript.
**Input:** Transcript
**Output:** Candidate segments + **text_score**
**Criteria:**

* Relevance
* Emotional intensity
* Topic shifts
  **Notes:**
* Fast and cheap → runs first.
* Produces many potential clips.

---

## **3. Vision Scoring Agent (Qwen2-VL via Ollama Local)**

**Role:** Evaluate visual salience of each candidate segment.
**Input:** Video segment reference (timestamps, + low-res frame sample)
**Output:** **vision_score**
**Checks for:**

* Facial expressions
* Gestures
* Scene changes
* Visual emphasis
  **Notes:**
* Enhances segments where visuals matter.

---

## **4. Quality Assurance Agent (Qwen3-VL via Ollama Cloud, Conditional)**

**Role:** Re-evaluate **low-confidence** segments only.
**Trigger Condition:**
`combined_score < threshold` **OR** segment lacks clear action/speech signal
**Input:** Small clipped segment (not entire video)
**Output:** **cloud_score**
**Notes:**

* Used sparingly to save cost.

---

## **5. Scoring & Ranking Agent**

**Role:** Combine multiple scores into final ranking.
**Formula (example):**
`combined_score = (text_score * 0.5) + (vision_score * 0.4) + (cloud_score * 0.1)`
**Output:** Sorted list of clips (best → worst)

---

## **6. Rendering Agent (FFmpeg)**

**Role:** Generate finished clips with captions.
**Inputs:**

* Original video
* Segment timestamps
* Transcript text for overlay
  **Output:** `.mp4` clips ready to share
  **Notes:**
* No resizing or stylistic decisions are automated yet — just functional output.

---

## **7. File Watcher Agent**

**Role:** Detect new videos and trigger the pipeline automatically.
**Input:** New file dropped into watched directory
**Output:** Pipeline execution start
**Notes:**

* Allows full hands-off automation.

---

## **8. Database Logging Agent**

**Role:** Track pipeline steps, statuses, timestamps.
**Purpose:**

* Resumability
* Debugging
* Audit trail
  **Stores:**
* transcripts
* segments
* scores
* processing logs

---

## **Pipeline Flow Overview**

```
File added → Whisper → Transcript
              ↓
         Gemma → Text candidates
              ↓
        Qwen2 → Visual scoring
              ↓
   Qwen3 (only if needed)
              ↓
       Combined scoring
              ↓
      Top clips exported
```

