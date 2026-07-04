import yaml
import logging

logger = logging.getLogger("ZeroTrust.Agent.Config")

class ConfigManager:
    def __init__(self):
        self.config = {}

    def load(self, filepath: str = "config.yaml"):
        try:
            with open(filepath, 'r') as f:
                self.config = yaml.safe_load(f)
            logger.info(f"Configuration loaded from {filepath}")
        except Exception as e:
            logger.error(f"Failed to load config: {e}")
            self.config = {}

# Singleton instance
config_manager = ConfigManager()
