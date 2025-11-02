# **Clip Analysis & Scoring Pipeline**

## **Purpose**

This document defines the pipeline responsible for identifying clip-worthy moments within a video. It specifies how transcripts, semantic segmentation, visual context scoring, micro-emphasis reinforcement, and cloud fallback work together to produce a ranked list of candidate clips for export.

This pipeline **does not** handle storage, file management, or final clip rendering. Those are defined elsewhere.

---

## **1. Inputs**

* **Source Video File** (`.mp4` or `.mov`)
* **WhisperX Timestamped Transcript** (generated in Doc 1 stage)

  * Structure: list of segments containing `{start, end, text}`
* **Model Access:**

  * **Gemma (HF, Local)** – text segmentation
  * **Qwen2-VL (Local via Ollama)** – visual-intent scoring
  * **Qwen3-VL (Cloud via Ollama)** – fallback arbitration

---

## **2. Output**

A ranked list of **Clip Candidate Objects**, structured as:

```
{
  video_id,
  start_time,
  end_time,
  transcript_text,
  text_score,
  vision_score_local,
  audio_emphasis_score,
  facial_emphasis_score,
  final_score,
  escalated_to_cloud (true/false)
}
```

This object is passed forward to the rendering/export stage.

---

## **3. Semantic Segmentation (Text-First Clip Detection)**

**Model:** Gemma (HF Local)

The transcript is segmented into candidate clips based on meaning continuity.

Procedure:

1. Input transcript into Gemma with prompt to identify meaningful idea boundaries.
2. Gemma returns segment boundaries (`start_time`, `end_time`) and a semantic relevance score.
3. These segments form the **initial clip candidate list**.

**Output:**
List of semantic segments with:

```
start_time, end_time, text_score
```

---

## **4. Visual Intent Scoring (Local VLM Scoring)**

**Model:** Qwen2-VL (Local, Ollama)

For each semantic segment:

1. Sample a small number of frames across the segment (e.g., 3–7 evenly spaced).
2. Pass these frames + matching transcript slice to Qwen2-VL.
3. Qwen2-VL evaluates:

   * emotional intensity
   * gesture relevance
   * speaker intent clarity
   * visual storytelling strength

Produces:

```
vision_score_local ∈ [0, 1]
```

This catches meaningful tone shifts missed by text-only segmentation.

---

## **5. Confidence Evaluation**

Combine:

```
base_confidence = weighted(text_score, vision_score_local)
```

If `base_confidence` is **clearly high or clearly low**, accept or reject segment immediately.

If **confidence falls in an ambiguous range** (e.g., 0.40–0.65), proceed to Micro-Emphasis Layer.

---

## **6. Micro-Emphasis Layer (Low-Cost Reinforcement Scoring)**

This layer uses **signals we already have**, so it adds minimal compute overhead.

### Signals Used:

1. **Audio Prosody Spike Score**

   * Measures loudness, pitch shift, and tempo acceleration.
   * Produces `audio_emphasis_score ∈ [0, 1]`.

2. **Facial Micro-Movement Score**

   * Uses the *same sampled frames* from the Qwen2 step.
   * Detects eyebrow/eye/mouth motion deltas frame-to-frame.
   * Produces `facial_emphasis_score ∈ [0, 1]`.

### Reinforcement Logic:

```
micro_emphasis = max(audio_emphasis_score, facial_emphasis_score)
```

If `micro_emphasis` raises confidence above acceptance threshold:
→ **Clip is accepted.**
No cloud call needed.

If confidence remains ambiguous:
→ Escalate to cloud arbitration.

---

## **7. Cloud Arbitration (High-Confidence Resolution Stage)**

**Model:** Qwen3-VL (Cloud via Ollama)

Only executed **for ambiguous segments after micro-emphasis**.

Procedure:

1. Generate a **downsampled segment preview**:

   * Extract ~1–3 seconds around the center of the segment using FFmpeg (`-ss` + `-t`)
   * Resolution optionally reduced (e.g., 320p) to reduce cloud payload.
2. Send preview frames + transcript text to **Qwen3-VL**.
3. Model returns a **final certainty score**.

```
final_score = weighted(text_score, vision_score_local, micro_emphasis, vision_score_cloud)
```

Mark:

```
escalated_to_cloud = true
```

If still low confidence → clip is discarded.

---

## **8. Final Ranking**

All accepted clips are sorted by:

```
final_score DESC
```

Top N (usually N=3) are marked for *auto-export*.
The rest remain available for manual selection.

---

## **9. Performance Principles**

* **Only compute heavy operations when needed.**
* **Cloud is used only to resolve ambiguity.**
* **No step repeats work already done at a previous stage.**
* **No clip is rejected on a single weak signal.**

This ensures:

* Maximum recall of valuable moments
* Minimal unneeded computation expense
* Consistent scoring even across varied content types

---

