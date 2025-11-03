# Protocol-Driven Prompt Management: A Guide for vid-clip-ai

**Author:** Manus AI  
**Date:** November 3, 2025  
**Project:** vid-clip-ai - Prompt Engineering Architecture

---

## 1. The Problem: Prompts as Fragile Strings

As you correctly identified, your system's success hinges on the quality of your prompts. Currently, your agent stubs imply that prompts will be simple, hard-coded strings inside the agent logic. This approach is common, but it is fragile and creates significant long-term problems:

*   **No Versioning:** How do you track which version of a prompt was used for a specific video? How do you roll back a bad prompt change?
*   **No Validation:** What happens if a developer accidentally deletes a crucial part of the prompt string? The model will produce garbage output with no clear error.
*   **No Reusability:** The same prompt logic might be needed for different models or agents, leading to duplicated, inconsistent strings.
*   **Difficult to A/B Test:** How can you safely test a new prompt on 10% of users without a complex and risky series of `if/else` statements in your core agent logic?
*   **No Separation of Concerns:** Your core agent logic becomes cluttered with prompt text, mixing application code with model instructions.

This is the opposite of the clean, governed architecture you've built. It introduces chaos into an otherwise orderly system.

---

## 2. The Solution: A Protocol-Driven Prompt System

We can solve this by treating prompts not as simple strings, but as structured, versioned, and validated assets, managed by a clear protocol. This approach brings the same governance you applied to your pipeline to your prompt engineering.

This system will have three core components:

1.  **The Prompt Registry:** A centralized, version-controlled library of prompt templates stored in a structured format (YAML files).
2.  **The Prompt Protocol:** A data validation layer (using Pydantic) that defines the required inputs and outputs for each prompt, ensuring data integrity.
3.  **The Prompt Provider:** A service responsible for retrieving, validating, and formatting the correct prompt version for an agent.

### Architectural Diagram

```mermaid
flowchart TD
    subgraph AgentExecution [Agent Execution]
        A[Agent: e.g., TextScoringAgent] --> B{PromptProvider.get("text_scoring_v1")};
    end

    subgraph PromptManagement [Prompt Management System]
        B --> C{1. Retrieve YAML from Registry};
        C --> D[prompts/text_scoring/v1.yaml];
        C --> E{2. Validate Inputs against Protocol};
        E --> F[protocols/prompt_protocols.py];
        E --> G{3. Format Prompt String};
        G --> H{4. Validate Output Schema};
        H --> F;
    end

    B --> I[Formatted & Validated Prompt Object];
    A --> J[LLM];
    I --> J;
    J --> K[LLM Response];
    K --> H;
```

---

## 3. Implementation Guide

Here is a step-by-step guide to implementing this system in your `vid-clip-ai` repository.

### Step 1: Create the Prompt Registry

First, we create a centralized directory to store our prompt templates as YAML files. This makes them easy to read, edit, and version control with Git.

**Create the following directory structure:**

```
src/
├── prompts/
│   ├── __init__.py
│   ├── text_scoring/
│   │   ├── v1.yaml
│   │   └── v2.yaml
│   └── vision_scoring/
│       └── v1.yaml
└── ...
```

**Example: `src/prompts/text_scoring/v1.yaml`**

```yaml
# prompts/text_scoring/v1.yaml

name: "text_scoring"
version: 1
description: "Identifies engaging moments in a transcript for clip generation."

# Defines the variables this prompt template requires.
input_variables:
  - "transcript_text"

# Defines the JSON schema the LLM is expected to return.
output_schema:
  type: "object"
  properties:
    segments:
      type: "array"
      items:
        type: "object"
        properties:
          start_time: { type: "number", description: "Start time of the segment in seconds." }
          end_time: { type: "number", description: "End time of the segment in seconds." }
          score: { type: "number", description: "Relevance score from 0.0 to 1.0." }
          reason: { type: "string", description: "A brief explanation for the score." }
        required: ["start_time", "end_time", "score", "reason"]

# The prompt template itself.
template: |
  You are an expert at identifying viral-worthy moments in video transcripts.
  Analyze the following transcript and identify segments that are:
  1. Self-contained (complete thoughts, no missing context)
  2. Emotionally engaging (surprise, excitement, controversy, insight)
  3. Shareable (interesting to a broad audience, not niche)
  4. Clear and concise (30-90 seconds ideal)

  Transcript:
  ---
  {{transcript_text}}
  ---

  Respond with a JSON object matching the following schema:
  ```json
  {{output_schema}}
  ```
```

### Step 2: Define the Prompt Protocol with Pydantic

Next, we create the data contracts that enforce the structure of our prompts and their outputs. This ensures that a prompt cannot be used if it doesn't receive the right inputs, and the system will raise an error if the LLM's output doesn't match the expected schema.

**Create a new file: `src/protocols/prompt_protocols.py`**

```python
# protocols/prompt_protocols.py

from pydantic import BaseModel, Field
from typing import List, Dict, Any

# --- Output Schemas ---

class TextSegment(BaseModel):
    start_time: float = Field(..., description="Start time of the segment in seconds.")
    end_time: float = Field(..., description="End time of the segment in seconds.")
    score: float = Field(..., ge=0.0, le=1.0, description="Relevance score from 0.0 to 1.0.")
    reason: str = Field(..., description="A brief explanation for the score.")

class TextScoringOutput(BaseModel):
    segments: List[TextSegment]


class VisionScoringOutput(BaseModel):
    vision_score: float = Field(..., ge=0.0, le=1.0)
    key_visual_elements: List[str]
    reason: str

# --- Prompt Protocol Definition ---

class Prompt(BaseModel):
    """A validated and structured representation of a prompt."""
    name: str
    version: int
    description: str
    template: str
    input_variables: List[str]
    output_protocol: BaseModel # Pydantic model for output validation

    def format(self, **kwargs) -> str:
        """Format the prompt template with validated inputs."""
        if not all(key in kwargs for key in self.input_variables):
            raise ValueError(f"Missing input variables. Required: {self.input_variables}")
        return self.template.format(**kwargs)

    def parse_output(self, output_text: str) -> Dict[str, Any]:
        """Parse and validate the LLM's output against the protocol."""
        # Basic JSON cleaning can be added here
        try:
            data = json.loads(output_text)
            return self.output_protocol.model_validate(data).model_dump()
        except Exception as e:
            # Here you can add retry logic or error logging
            raise ValueError(f"Failed to validate LLM output: {e}") from e

```

### Step 3: Create the Prompt Provider

This service acts as the central point of access. It loads the YAML files, validates them against our protocol, and provides ready-to-use `Prompt` objects to the agents.

**Create a new file: `src/prompts/provider.py`**

```python
# prompts/provider.py

import yaml
import json
from pathlib import Path
from typing import Dict

from src.protocols.prompt_protocols import Prompt, TextScoringOutput, VisionScoringOutput

# Mapping of prompt names to their output validation protocols
PROTOCOL_MAP = {
    "text_scoring": TextScoringOutput,
    "vision_scoring": VisionScoringOutput,
}

class PromptProvider:
    def __init__(self, registry_path: str = "src/prompts"):
        self._registry_path = Path(registry_path)
        self._cache: Dict[str, Prompt] = {}

    def get(self, prompt_name: str, version: int = 1) -> Prompt:
        """Retrieve, validate, and return a structured Prompt object."""
        cache_key = f"{prompt_name}_v{version}"
        if cache_key in self._cache:
            return self._cache[cache_key]

        # 1. Load from YAML file
        file_path = self._registry_path / prompt_name / f"v{version}.yaml"
        if not file_path.exists():
            raise FileNotFoundError(f"Prompt {cache_key} not found at {file_path}")

        with open(file_path, 'r') as f:
            data = yaml.safe_load(f)

        # 2. Get the corresponding output protocol
        output_protocol = PROTOCOL_MAP.get(prompt_name)
        if not output_protocol:
            raise ValueError(f"No output protocol defined for prompt '{prompt_name}'")

        # 3. Inject the JSON schema of the protocol into the template
        output_schema_json = json.dumps(output_protocol.model_json_schema(), indent=2)
        data['template'] = data['template'].replace('{{output_schema}}', output_schema_json)

        # 4. Create and validate the Prompt object
        prompt = Prompt(
            name=data['name'],
            version=data['version'],
            description=data['description'],
            template=data['template'],
            input_variables=data['input_variables'],
            output_protocol=output_protocol()
        )

        self._cache[cache_key] = prompt
        return prompt

# Singleton instance for easy access
prompt_provider = PromptProvider()
```

### Step 4: Update an Agent to Use the System

Finally, let's refactor the `TextScoringAgent` to use our new protocol-driven system. Notice how the agent logic becomes cleaner and is completely decoupled from the prompt text.

**Refactor `src/agents/text_scoring.py`:**

```python
# agents/text_scoring.py

from typing import Dict, Any
from .base_agent import BaseAgent
from src.prompts.provider import prompt_provider

class TextScoringAgent(BaseAgent):
    def __init__(self, config: Dict[str, Any] = None):
        super().__init__(config)
        self.model_name = config.get('gemma_model', 'gemma3:3b')
        self.device = config.get('device', 'cuda')
        # The agent now requests a specific version of a prompt
        self.prompt_version = config.get('prompt_version', 1)

    def execute(self, context: Dict[str, Any]) -> Dict[str, Any]:
        self.logger.info(f"Executing text scoring with prompt v{self.prompt_version}")

        # 1. Get the validated prompt object from the provider
        try:
            prompt = prompt_provider.get("text_scoring", version=self.prompt_version)
        except (FileNotFoundError, ValueError) as e:
            self.logger.error(f"Failed to load prompt: {e}")
            return {"success": False, "error": str(e)}

        # 2. Format the prompt with validated inputs
        transcript_text = context.get("transcript_text", "")
        formatted_prompt = prompt.format(transcript_text=transcript_text)

        # 3. Call the LLM (mock implementation)
        # llm_output_str = self._call_gemma(formatted_prompt)
        # For this example, we'll use a mock response:
        mock_llm_output = '''
        {
            "segments": [
                {
                    "start_time": 10.5,
                    "end_time": 45.2,
                    "score": 0.85,
                    "reason": "This segment contains a clear, insightful point about AI."
                }
            ]
        }
        '''

        # 4. Parse and validate the output using the prompt's protocol
        try:
            validated_output = prompt.parse_output(mock_llm_output)
            self.logger.info(f"Successfully parsed and validated {len(validated_output['segments'])} segments.")
            return {"success": True, "segments": validated_output['segments']}
        except ValueError as e:
            self.logger.error(f"LLM output failed validation: {e}")
            return {"success": False, "error": "LLM output validation failed."}

    def _call_gemma(self, prompt_text: str) -> str:
        # Your actual LLM call logic would go here
        pass
```

---

## 4. Benefits of This Protocol-Driven Approach

By implementing this system, you gain immense control and reliability, directly addressing the initial problems:

*   **✅ Governance & Structure:** Prompts are no longer magic strings but structured, versioned, and validated assets. This aligns perfectly with your system's philosophy.
*   **✅ Robustness:** The Pydantic protocol layer ensures that both the data going into the prompt and the data coming out of the LLM are correct. Bad data in or out will raise an immediate, traceable error.
*   **✅ Versioning & A/B Testing:** Changing `prompt_version` in the agent's config is all that's needed to switch to a new prompt. You can easily deploy agents with different versions to test performance.
*   **✅ Separation of Concerns:** Agent logic is clean. It requests a prompt, provides data, and gets validated output. It doesn't care about the prompt's text, format, or version.
*   **✅ Centralized Management:** Your `src/prompts/` directory becomes the single source of truth for all prompts, making them easy to find, review, and manage.

This protocol-driven architecture is the key to making your prompt engineering **reliable, scalable, and maintainable**. It transforms prompts from a liability into a governed, strategic asset. It is the embodiment of the principle: **"In structure, there is freedom."**