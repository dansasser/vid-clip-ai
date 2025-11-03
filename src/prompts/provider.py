"""
Prompt Provider Service

Central service for loading, validating, and caching prompt templates.
Acts as the single point of access for all agents requesting prompts.

Usage:
    from src.prompts.provider import prompt_provider

    prompt = prompt_provider.get("text_scoring", version=1)
    formatted = prompt.format(transcript_text="...")
    validated_output = prompt.parse_output(llm_response)
"""

import yaml
import json
import logging
from pathlib import Path
from typing import Dict, Optional

from ..protocols.prompt_protocols import Prompt, PROTOCOL_MAP


logger = logging.getLogger(__name__)


class PromptProvider:
    """
    Centralized service for managing prompt templates.

    Responsibilities:
    - Load YAML prompt files from registry
    - Validate prompts against protocols
    - Cache loaded prompts for performance
    - Inject output schemas into templates
    """

    def __init__(self, registry_path: Optional[str] = None):
        """
        Initialize the prompt provider.

        Args:
            registry_path: Path to prompts directory (default: src/prompts)
        """
        if registry_path is None:
            # Default to src/prompts relative to this file
            registry_path = Path(__file__).parent

        self._registry_path = Path(registry_path)
        self._cache: Dict[str, Prompt] = {}

        logger.info(f"PromptProvider initialized with registry: {self._registry_path}")

    def get(self, prompt_name: str, version: int = 1) -> Prompt:
        """
        Retrieve, validate, and return a structured Prompt object.

        Args:
            prompt_name: Name of the prompt (e.g., "text_scoring")
            version: Version number (default: 1)

        Returns:
            Validated Prompt object ready to use

        Raises:
            FileNotFoundError: If prompt file doesn't exist
            ValueError: If prompt validation fails or no protocol is defined
            yaml.YAMLError: If YAML file is malformed
        """
        cache_key = f"{prompt_name}_v{version}"

        # Return from cache if available
        if cache_key in self._cache:
            logger.debug(f"Returning cached prompt: {cache_key}")
            return self._cache[cache_key]

        logger.info(f"Loading prompt: {cache_key}")

        # 1. Load YAML file
        file_path = self._registry_path / prompt_name / f"v{version}.yaml"
        if not file_path.exists():
            raise FileNotFoundError(
                f"Prompt file not found: {file_path}\n"
                f"Expected location: {file_path.absolute()}"
            )

        try:
            with open(file_path, 'r') as f:
                data = yaml.safe_load(f)
        except yaml.YAMLError as e:
            raise yaml.YAMLError(f"Failed to parse YAML file {file_path}: {e}") from e

        # 2. Get the corresponding output protocol
        output_protocol = PROTOCOL_MAP.get(prompt_name)
        if not output_protocol:
            available = ', '.join(PROTOCOL_MAP.keys())
            raise ValueError(
                f"No output protocol defined for prompt '{prompt_name}'.\n"
                f"Available protocols: {available}"
            )

        # 3. Inject the JSON schema of the protocol into the template
        output_schema_json = json.dumps(
            output_protocol.model_json_schema(),
            indent=2
        )

        template = data.get('template', '')
        if '{{output_schema}}' in template:
            template = template.replace('{{output_schema}}', output_schema_json)

        # 4. Create and validate the Prompt object
        try:
            prompt = Prompt(
                name=data['name'],
                version=data['version'],
                description=data['description'],
                template=template,
                input_variables=data['input_variables'],
                output_protocol=output_protocol
            )
        except KeyError as e:
            raise ValueError(
                f"Prompt YAML missing required field: {e}\n"
                f"Required fields: name, version, description, template, input_variables"
            ) from e
        except Exception as e:
            raise ValueError(f"Failed to create Prompt object: {e}") from e

        # 5. Cache and return
        self._cache[cache_key] = prompt
        logger.info(f"Successfully loaded and cached prompt: {cache_key}")

        return prompt

    def clear_cache(self) -> None:
        """Clear the prompt cache (useful for testing or reloading)."""
        self._cache.clear()
        logger.info("Prompt cache cleared")

    def list_available_prompts(self) -> Dict[str, list]:
        """
        List all available prompts in the registry.

        Returns:
            Dictionary mapping prompt names to lists of available versions
        """
        available = {}

        for prompt_dir in self._registry_path.iterdir():
            if prompt_dir.is_dir() and not prompt_dir.name.startswith('_'):
                versions = []
                for yaml_file in prompt_dir.glob('v*.yaml'):
                    # Extract version number from filename (v1.yaml -> 1)
                    try:
                        version = int(yaml_file.stem[1:])
                        versions.append(version)
                    except ValueError:
                        continue

                if versions:
                    available[prompt_dir.name] = sorted(versions)

        return available


# Singleton instance for easy access throughout the application
prompt_provider = PromptProvider()
