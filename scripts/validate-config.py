#!/usr/bin/env python3
"""
Configuration validation script for tech-digest.

Validates sources.json and topics.json against JSON Schema and performs
additional consistency checks.

Usage:
    python3 validate-config.py [--config-dir CONFIG_DIR] [--verbose]
"""

import json
import argparse
import logging
import sys
import os
from pathlib import Path
from typing import Dict, List, Any, Set

try:
    import jsonschema
    from jsonschema import validate, ValidationError
    HAS_JSONSCHEMA = True
except ImportError:
    HAS_JSONSCHEMA = False


def setup_logging(verbose: bool) -> logging.Logger:
    """Setup logging configuration."""
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format='%(asctime)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    return logging.getLogger(__name__)


def load_json_file(file_path: Path) -> Dict[str, Any]:
    """Load and parse JSON file."""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        raise FileNotFoundError(f"Config file not found: {file_path}")
    except json.JSONDecodeError as e:
        raise ValueError(f"Invalid JSON in {file_path}: {e}")


def validate_against_schema(data: Dict[str, Any], schema: Dict[str, Any], 
                          config_type: str) -> bool:
    """Validate data against JSON schema."""
    if not HAS_JSONSCHEMA:
        logging.warning("jsonschema not available, skipping schema validation")
        return True
        
    try:
        # Extract the relevant schema definition
        if config_type == "sources":
            schema_def = {
                "type": "object",
                "required": ["sources"],
                "properties": {
                    "sources": {
                        "type": "array", 
                        "items": schema["definitions"]["source"]
                    }
                }
            }
        elif config_type == "topics":
            schema_def = {
                "type": "object",
                "required": ["topics"],
                "properties": {
                    "topics": {
                        "type": "array",
                        "items": schema["definitions"]["topic"]
                    }
                }
            }
        else:
            raise ValueError(f"Unknown config type: {config_type}")
            
        validate(instance=data, schema=schema_def)
        logging.info(f"✅ {config_type}.json passed schema validation")
        return True
        
    except ValidationError as e:
        logging.error(f"❌ Schema validation failed for {config_type}.json:")
        logging.error(f"   Path: {' -> '.join(str(p) for p in e.absolute_path)}")
        logging.error(f"   Error: {e.message}")
        return False


def validate_sources_consistency(sources_data: Dict[str, Any], 
                               topics_data: Dict[str, Any]) -> bool:
    """Validate consistency between sources and topics."""
    errors = []
    
    # Get valid topic IDs
    valid_topics = {topic["id"] for topic in topics_data["topics"]}
    logging.debug(f"Valid topic IDs: {valid_topics}")
    
    # Check source topic references
    for source in sources_data["sources"]:
        source_id = source.get("id", "unknown")
        source_topics = set(source.get("topics", []))
        
        # Check for invalid topic references
        invalid_topics = source_topics - valid_topics
        if invalid_topics:
            errors.append(f"Source '{source_id}' references invalid topics: {invalid_topics}")
            
        # Check for empty topic lists
        if not source_topics:
            errors.append(f"Source '{source_id}' has no topics assigned")
            
    # Check for duplicate source IDs
    source_ids = [source.get("id") for source in sources_data["sources"]]
    duplicates = {id for id in source_ids if source_ids.count(id) > 1}
    if duplicates:
        errors.append(f"Duplicate source IDs found: {duplicates}")
        
    # Check for duplicate topic IDs
    topic_ids = [topic.get("id") for topic in topics_data["topics"]]
    duplicates = {id for id in topic_ids if topic_ids.count(id) > 1}
    if duplicates:
        errors.append(f"Duplicate topic IDs found: {duplicates}")
        
    if errors:
        logging.error("❌ Consistency validation failed:")
        for error in errors:
            logging.error(f"   {error}")
        return False
    else:
        logging.info("✅ Consistency validation passed")
        return True


def validate_source_types(sources_data: Dict[str, Any]) -> bool:
    """Validate source-type specific requirements."""
    errors = []
    
    for source in sources_data["sources"]:
        source_id = source.get("id", "unknown")
        source_type = source.get("type")
        
        if source_type == "rss":
            if not source.get("url"):
                errors.append(f"RSS source '{source_id}' missing required 'url' field")
        elif source_type == "twitter":
            if not source.get("handle"):
                errors.append(f"Twitter source '{source_id}' missing required 'handle' field")
        elif source_type == "web":
            # Web sources are handled by topics, no specific validation needed
            pass
        else:
            errors.append(f"Source '{source_id}' has invalid type: {source_type}")
            
    if errors:
        logging.error("❌ Source type validation failed:")
        for error in errors:
            logging.error(f"   {error}")
        return False
    else:
        logging.info("✅ Source type validation passed")
        return True


def main():
    """Main validation function."""
    parser = argparse.ArgumentParser(
        description="Validate tech-digest configuration files",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    python3 validate-config.py
    python3 validate-config.py --config-dir workspace/config --verbose
    """
    )
    
    parser.add_argument(
        "--config-dir",
        type=Path,
        default=Path("config/defaults"),
        help="Configuration directory (default: config/defaults)"
    )
    
    parser.add_argument(
        "--verbose", "-v",
        action="store_true", 
        help="Enable verbose logging"
    )
    
    args = parser.parse_args()
    logger = setup_logging(args.verbose)
    
    # File paths
    schema_path = Path("config/schema.json")
    sources_path = args.config_dir / "sources.json"
    topics_path = args.config_dir / "topics.json"
    
    logger.info(f"Validating configuration in: {args.config_dir}")
    
    try:
        # Load schema
        schema = load_json_file(schema_path)
        logger.debug("Loaded schema.json")
        
        # Load configuration files
        sources_data = load_json_file(sources_path)
        logger.debug(f"Loaded {sources_path}")
        
        topics_data = load_json_file(topics_path)
        logger.debug(f"Loaded {topics_path}")
        
        # Perform validations
        all_valid = True
        
        # Schema validation
        all_valid &= validate_against_schema(sources_data, schema, "sources")
        all_valid &= validate_against_schema(topics_data, schema, "topics")
        
        # Consistency validation
        all_valid &= validate_sources_consistency(sources_data, topics_data)
        
        # Source type validation  
        all_valid &= validate_source_types(sources_data)
        
        # Summary
        if all_valid:
            logger.info("🎉 All validations passed!")
            return 0
        else:
            logger.error("💥 Validation failed!")
            return 1
            
    except Exception as e:
        logger.error(f"💥 Validation error: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())