# Video Clip Extraction System (vid-clip-ai)

An automated AI video clipping engine that identifies key moments, scores them for impact, and produces ready-to-share clips with captions. It combines ASR, text scoring, and vision-language analysis to create concise, high-quality highlights from any video with minimal input.

## Overview

This system uses **8 cooperating agents** in a multi-stage pipeline to automatically:
- Transcribe video audio with precise timestamps (WhisperX)
- Identify meaningful clip candidates through semantic analysis (Gemma)
- Evaluate visual salience and emotional intensity (Qwen2-VL)
- Apply micro-emphasis scoring to avoid unnecessary cloud costs
- Arbitrate ambiguous clips with cloud models (Qwen3-VL)
- Combine scores with configurable weights
- Export final clips with burned-in captions (FFmpeg)

### Key Features

✅ **Multi-user architecture** - Each user has isolated directories and processing
✅ **Non-destructive pipeline** - Transcripts stored once, can re-score/re-export anytime
✅ **Cost-optimized** - Cloud models only used for ambiguous segments
✅ **State-based processing** - Resumable pipeline with audit trail
✅ **Portable database** - SQLite → Postgres with no schema changes
✅ **Modular agents** - Each agent has one clear responsibility

## Architecture

### Pipeline Flow

```
File Watcher → Transcription → Text Scoring → Vision Scoring
                                                    ↓
                                            Micro-Emphasis
                                                    ↓
                                         Quality Assurance (if needed)
                                                    ↓
                                            Scoring & Ranking
                                                    ↓
                                               Rendering
```

### Video State Machine

```
INGESTED → TRANSCRIBED → SEGMENTED → SCORED → READY → ARCHIVED
```

Each state transition is logged and validated to ensure pipeline integrity.

### The 8 Agents

1. **File Watcher Agent** - Monitors user directories for new videos
2. **Transcription Agent** - WhisperX for timestamped transcripts
3. **Text Scoring Agent** - Gemma for semantic segmentation
4. **Vision Scoring Agent** - Qwen2-VL for visual evaluation (local)
5. **Micro-Emphasis Agent** - Audio prosody + facial movement analysis
6. **Quality Assurance Agent** - Qwen3-VL cloud arbitration (conditional)
7. **Scoring & Ranking Agent** - Weighted score combination
8. **Rendering Agent** - FFmpeg clip export with captions

See [claude.md](claude.md) for detailed agent specifications.

## Project Structure

```
vid-clip-ai/
├── src/
│   ├── agents/              # 8 pipeline agents
│   │   ├── base_agent.py       # Abstract base class
│   │   ├── file_watcher.py
│   │   ├── transcription.py
│   │   ├── text_scoring.py
│   │   ├── vision_scoring.py
│   │   ├── micro_emphasis.py
│   │   ├── quality_assurance.py
│   │   ├── scoring_ranking.py
│   │   └── rendering.py
│   ├── database/            # Data layer
│   │   ├── models.py           # SQLAlchemy ORM models
│   │   ├── schema.py           # Database initialization
│   │   └── operations.py       # CRUD operations
│   ├── pipeline/            # Orchestration
│   │   ├── context.py          # Execution context
│   │   ├── state_machine.py    # State validation
│   │   └── orchestrator.py     # Agent coordination
│   ├── utils/               # Shared utilities
│   │   ├── file_system.py
│   │   ├── video_utils.py
│   │   └── logging_config.py
│   └── config/              # Configuration
│       └── settings.py
├── tests/
│   ├── unit/                # Unit tests
│   ├── integration/         # Integration tests
│   ├── fixtures/            # Test data
│   └── conftest.py          # Pytest configuration
├── scripts/
│   ├── init_user.py         # Create new user
│   └── setup_db.py          # Initialize database
├── docs/
│   └── dev-specs/           # Detailed specifications
├── requirements.txt
├── pyproject.toml
├── .env.example
└── .gitignore
```

## Installation

### Prerequisites

- Python 3.10+
- FFmpeg installed and in PATH
- CUDA-capable GPU (recommended for local models)
- Ollama running locally (for Qwen2-VL)

### Setup

1. **Clone the repository**
```bash
git clone <repository-url>
cd vid-clip-ai
```

2. **Create virtual environment**
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. **Install dependencies**
```bash
pip install -r requirements.txt
```

4. **Configure environment**
```bash
cp .env.example .env
# Edit .env with your settings
```

5. **Initialize database**
```bash
python scripts/setup_db.py
```

6. **Create admin user**
```bash
python scripts/init_user.py admin ./data
```

This creates the directory structure:
```
./data/admin/
├── incoming/     # Drop videos here
├── processed/    # Active processing
└── archived/     # Long-term storage
```

## Usage

### Basic Workflow

1. **Place video in watched directory**
```bash
cp your_video.mp4 ./data/admin/incoming/
```

2. **Start the pipeline** (implementation pending)
```bash
python -m src.main
```

3. **Find processed clips**
```bash
ls ./data/admin/processed/<video_id>/clips/
```

### Configuration

Edit `.env` to customize:

**Model Settings**
- `WHISPER_MODEL` - WhisperX model size (tiny, base, small, medium, large)
- `GEMMA_MODEL` - Gemma model variant
- `QWEN2_MODEL` - Local Qwen2-VL model
- `QWEN3_MODEL` - Cloud Qwen3-VL model

**Scoring Weights** (must sum to 1.0)
- `SCORE_WEIGHT_TEXT` - Text relevance weight (default: 0.30)
- `SCORE_WEIGHT_VISION` - Visual salience weight (default: 0.30)
- `SCORE_WEIGHT_AUDIO_EMPHASIS` - Audio prosody weight (default: 0.15)
- `SCORE_WEIGHT_FACIAL_EMPHASIS` - Facial movement weight (default: 0.15)
- `SCORE_WEIGHT_CLOUD` - Cloud score weight (default: 0.10)

**Export Settings**
- `TOP_N_AUTO_EXPORT` - Number of top clips to auto-export (default: 3)
- `MAX_PARALLEL_EXPORTS` - Concurrent FFmpeg processes (default: 2)

**Caption Styling**
- `CAPTION_FONTSIZE` - Font size in pixels (default: 32)
- `CAPTION_OUTLINE` - Outline thickness (default: 2)
- `CAPTION_SHADOW` - Shadow intensity (default: 1)

## Database Schema

### Entity Relationship Diagram

```
┌─────────────────────────┐
│   watch_directories     │
├─────────────────────────┤
│ id (PK)                 │
│ user_id                 │
│ directory_path          │
│ is_active               │
│ created_at              │
└─────────────────────────┘
           │
           │ 1      N
           ▼
┌─────────────────────────┐           1      N   ┌────────────────────────┐
│        videos           │─────────────────────▶│       transcript       │
├─────────────────────────┤                       ├────────────────────────┤
│ id (PK)                 │                       │ id (PK)                │
│ file_path               │                       │ video_id (FK)          │
│ title                   │                       │ start_time (sec)       │
│ source_type             │                       │ end_time (sec)         │
│ status                  │                       │ text                   │
│ created_at              │                       └────────────────────────┘
│ user_id                 │
│ watch_directory_id (FK) │
└─────────────────────────┘
           │
           │ 1      N
           ▼
┌─────────────────────────┐
│       segments          │
├─────────────────────────┤
│ id (PK)                 │
│ video_id (FK)           │
│ start_time (sec)        │
│ end_time (sec)          │
│ source                  │  ← 'asr', 'local_vlm', 'cloud_vlm'
└─────────────────────────┘
           │
           │ 1      1
           ▼
┌──────────────────────────┐
│     segment_scores       │
├──────────────────────────┤
│ segment_id (PK, FK)      │
│ text_score               │
│ vision_score             │
│ audio_emphasis_score     │
│ facial_emphasis_score    │
│ cloud_score              │
│ combined_score           │
│ escalated_to_cloud       │
└──────────────────────────┘

           │
           │ videos 1:N
           ▼
┌────────────────────────┐
│    processing_log      │
├────────────────────────┤
│ id (PK)                │
│ video_id (FK)          │
│ step                   │ ← 'ingest', 'transcribe', 'segment', 'score', 'render'
│ status                 │ ← 'ok', 'fail'
│ message                │
│ created_at             │
└────────────────────────┘
```

### Core Tables

**watch_directories** - User directory monitoring
- Tracks which directories are being watched
- Associates directories with user_ids
- Enables multi-user isolation

**videos** - Source video metadata
- File paths and processing state
- User ownership
- State machine status

**transcript** - WhisperX timestamped segments
- Word-level timestamps
- Ground truth for all operations
- Never regenerated

**segments** - Clip candidates
- Start/end timestamps
- Source (text/vision/cloud)
- Many-to-one with videos

**segment_scores** - Multi-model scoring
- text_score, vision_score, cloud_score
- audio_emphasis_score, facial_emphasis_score
- combined_score for ranking
- escalated_to_cloud flag

**processing_log** - Audit trail
- Step-by-step execution history
- Success/failure tracking
- Debugging and resumability

## Development

### Running Tests

```bash
# All tests
pytest

# Unit tests only
pytest tests/unit/

# With coverage
pytest --cov=src tests/
```

### Code Style

```bash
# Format code
black src/ tests/

# Lint
flake8 src/ tests/

# Type checking
mypy src/
```

### Adding a New Agent

1. Create agent class in `src/agents/`
2. Inherit from `BaseAgent`
3. Implement `execute()` method
4. Add to orchestrator in `src/pipeline/orchestrator.py`
5. Add tests in `tests/unit/`

## Design Principles

### No Overlapping Responsibilities
Each agent does ONE thing well. The transcription agent only transcribes. The rendering agent only renders. No agent makes decisions outside its domain.

### Structured I/O
Every agent consumes well-defined inputs and produces well-defined outputs. No magic global state.

### Non-Destructive Processing
The transcript is the ground truth. Everything else can be recomputed. Change scoring weights? Just re-score. Update models? Re-evaluate without re-transcribing.

### Performance Optimized
- Text scoring runs first (fast, cheap)
- Vision scoring uses sampled frames (not full video)
- Micro-emphasis uses existing data (no extra extraction)
- Cloud only used when truly needed

### Database Portability
Schema uses only `INTEGER`, `REAL`, `TEXT`, `TIMESTAMP` - works identically on SQLite and Postgres.

### Resumability
State machine + processing log means you can stop/restart at any point without losing work.

## Roadmap

### Phase 1: Foundation (Current)
- [x] Project structure
- [ ] Database implementation
- [ ] State machine
- [ ] Base agent framework

### Phase 2: Core Pipeline
- [ ] File watcher
- [ ] Transcription agent
- [ ] Text scoring agent
- [ ] Basic rendering

### Phase 3: Advanced Scoring
- [ ] Vision scoring agent
- [ ] Micro-emphasis layer
- [ ] Quality assurance agent
- [ ] Scoring & ranking

### Phase 4: Polish
- [ ] Vertical video reframing
- [ ] Parallel export queue
- [ ] Comprehensive tests
- [ ] Documentation

### Phase 5: Future (Post-MVP)
- [ ] Web UI for user management
- [ ] Real-time progress monitoring
- [ ] Custom model fine-tuning
- [ ] Semantic search over transcripts
- [ ] Cloud storage integration (S3, B2)
- [ ] Postgres migration

## Documentation

- [claude.md](claude.md) - High-level agent overview
- [docs/dev-specs/architecture.md](docs/dev-specs/architecture.md) - System architecture
- [docs/dev-specs/db-schema.md](docs/dev-specs/db-schema.md) - Database design
- [docs/dev-specs/analysis-and-scoring.md](docs/dev-specs/analysis-and-scoring.md) - Scoring pipeline
- [docs/dev-specs/rendering-and-export.md](docs/dev-specs/rendering-and-export.md) - Export system
- [docs/dev-specs/state-and-storage.md](docs/dev-specs/state-and-storage.md) - State management

## License

MIT

## Contributing

This project is in early development. Contributions welcome after core pipeline is stable.
