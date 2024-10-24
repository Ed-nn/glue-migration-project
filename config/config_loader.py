import os
import yaml
from typing import Dict, Any
import string

class ConfigLoader:
    def __init__(self, env_name: str = "dev"):
        self.env_name = env_name
        self.config_dir = os.path.dirname(os.path.abspath(__file__))
        
        # Load configurations
        self.s3_paths = self._load_yaml("s3_paths.yml")
        self.glue_config = self._load_yaml("glue_config.yml")
        self.env_config = self._load_yaml(f"environments/{env_name}.yml")
        
        # Resolve variable references
        self._resolve_variables()

    def _load_yaml(self, file_name: str) -> Dict[str, Any]:
        file_path = os.path.join(self.config_dir, file_name)
        with open(file_path, 'r') as f:
            return yaml.safe_load(f)

    def _resolve_variables(self):
        template = string.Template(str(self.env_config))
        resolved = template.safe_substitute(self.env_config)
        self.env_config = yaml.safe_load(resolved)

    def get_resource_name(self, resource_type: str) -> str:
        prefix = self.env_config['resource_naming']['prefix']
        separator = self.env_config['resource_naming']['separator']
        return f"{prefix}{separator}{resource_type}"

    def get_s3_path(self, category: str, entity: str = None) -> str:
        base_path = self.s3_paths[category]['base']
        if entity:
            return self.s3_paths[category]['entities'][entity]['path']
        return base_path

    def get_glue_config(self) -> Dict[str, Any]:
        return {
            **self.glue_config['job_defaults'],
            **{
                'workers': self.env_config['glue']['workers'],
                'timeout_minutes': self.env_config['glue']['timeout_minutes'],
                'max_retries': self.env_config['glue']['max_retries']
            }
        }
