"""
Configuration module for the OpportunityMailer application.
Handles loading and validating configuration settings.
"""
import os
import json
import logging
from typing import Dict, Any, Optional

from dotenv import load_dotenv

# Configure logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Load environment variables from .env file
load_dotenv()


class Config:
    """
    Configuration manager for the OpportunityMailer application.
    Handles loading and validating configuration settings.
    """
    
    def __init__(self, config_file: Optional[str] = None):
        """
        Initialize the configuration manager.
        
        Args:
            config_file: Path to a JSON configuration file (optional)
        """
        # Default configuration
        self.config = {
            "aws": {
                "region": os.getenv("AWS_REGION", "us-east-1"),
                "ses": {
                    "default_sender_email": os.getenv("DEFAULT_SENDER_EMAIL", ""),
                    "max_emails_per_day": int(os.getenv("MAX_EMAILS_PER_DAY", "50")),
                    "rate_limit": int(os.getenv("RATE_LIMIT", "10"))  # emails per second
                },
                "lambda": {
                    "timeout": int(os.getenv("LAMBDA_TIMEOUT", "30")),
                    "memory_size": int(os.getenv("LAMBDA_MEMORY_SIZE", "128"))
                },
                "s3": {
                    "bucket_name": os.getenv("S3_BUCKET_NAME", ""),
                    "template_prefix": os.getenv("S3_TEMPLATE_PREFIX", "templates/")
                }
            },
            "email": {
                "template_storage": os.getenv("TEMPLATE_STORAGE", "local"),  # 'local' or 's3'
                "default_template": os.getenv("DEFAULT_TEMPLATE", "job_application"),
                "max_retries": int(os.getenv("MAX_RETRIES", "3")),
                "retry_delay": int(os.getenv("RETRY_DELAY", "5"))  # seconds
            },
            "app": {
                "debug": os.getenv("DEBUG", "False").lower() == "true",
                "log_level": os.getenv("LOG_LEVEL", "INFO"),
                "version": "1.0.0"
            }
        }
        
        # Load configuration from file if provided
        if config_file:
            self._load_from_file(config_file)
        
        # Validate configuration
        self._validate_config()
    
    def _load_from_file(self, config_file: str) -> None:
        """
        Loads configuration from a JSON file.
        
        Args:
            config_file: Path to a JSON configuration file
            
        Raises:
            ValueError: If the file cannot be loaded
        """
        try:
            if os.path.exists(config_file):
                with open(config_file, 'r') as f:
                    file_config = json.load(f)
                
                # Merge with default configuration
                self._merge_config(self.config, file_config)
            else:
                logger.warning(f"Configuration file not found: {config_file}")
        except Exception as e:
            logger.error(f"Error loading configuration file: {str(e)}")
            raise ValueError(f"Error loading configuration file: {str(e)}")
    
    def _merge_config(self, target: Dict[str, Any], source: Dict[str, Any]) -> None:
        """
        Recursively merges source dictionary into target dictionary.
        
        Args:
            target: Target dictionary to merge into
            source: Source dictionary to merge from
        """
        for key, value in source.items():
            if key in target and isinstance(target[key], dict) and isinstance(value, dict):
                self._merge_config(target[key], value)
            else:
                target[key] = value
    
    def _validate_config(self) -> None:
        """
        Validates the configuration.
        
        Raises:
            ValueError: If the configuration is invalid
        """
        # Check required AWS settings when using AWS services
        if self.config["email"]["template_storage"] == "s3":
            if not self.config["aws"]["s3"]["bucket_name"]:
                raise ValueError("S3 bucket name is required when template_storage is 's3'")
        
        # Check SES settings
        if not self.config["aws"]["ses"]["default_sender_email"]:
            logger.warning("Default sender email is not configured")
        
        # Set log level
        log_level = getattr(logging, self.config["app"]["log_level"].upper(), None)
        if log_level:
            logger.setLevel(log_level)
        else:
            logger.warning(f"Invalid log level: {self.config['app']['log_level']}, using INFO")
            logger.setLevel(logging.INFO)
    
    def get(self, key: str, default: Any = None) -> Any:
        """
        Gets a configuration value by key.
        
        Args:
            key: Dot-separated key path (e.g., 'aws.region')
            default: Default value to return if key is not found
            
        Returns:
            Configuration value or default
        """
        keys = key.split('.')
        value = self.config
        
        try:
            for k in keys:
                value = value[k]
            return value
        except (KeyError, TypeError):
            return default
    
    def set(self, key: str, value: Any) -> None:
        """
        Sets a configuration value by key.
        
        Args:
            key: Dot-separated key path (e.g., 'aws.region')
            value: Value to set
            
        Raises:
            ValueError: If the key path is invalid
        """
        keys = key.split('.')
        config = self.config
        
        # Navigate to the parent of the target key
        for k in keys[:-1]:
            if k not in config:
                config[k] = {}
            elif not isinstance(config[k], dict):
                raise ValueError(f"Cannot set key '{key}': '{k}' is not a dictionary")
            
            config = config[k]
        
        # Set the value
        config[keys[-1]] = value
    
    def save(self, config_file: str) -> bool:
        """
        Saves the configuration to a JSON file.
        
        Args:
            config_file: Path to save the configuration file
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Create directory if it doesn't exist
            os.makedirs(os.path.dirname(os.path.abspath(config_file)), exist_ok=True)
            
            with open(config_file, 'w') as f:
                json.dump(self.config, f, indent=2)
            
            return True
        except Exception as e:
            logger.error(f"Error saving configuration: {str(e)}")
            return False
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Returns the configuration as a dictionary.
        
        Returns:
            Configuration dictionary
        """
        return self.config
