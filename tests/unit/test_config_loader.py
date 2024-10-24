import pytest
from config.config_loader import ConfigLoader

def test_config_loader_initialization():
    # WHEN
    config = ConfigLoader(env_name="dev")
    
    # THEN
    assert config.env_name == "dev"
    assert config.s3_paths is not None
    assert config.glue_config is not None
    assert config.env_config is not None

def test_resource_naming():
    # GIVEN
    config = ConfigLoader(env_name="dev")
    
    # WHEN
    resource_name = config.get_resource_name("test-resource")
    
    # THEN
    assert "dev" in resource_name
    assert "test-resource" in resource_name

def test_s3_path_resolution():
    # GIVEN
    config = ConfigLoader(env_name="dev")
    
    # WHEN
    path = config.get_s3_path("raw", "hired_employees")
    
    # THEN
    assert "raw" in path
    assert "hired_employees" in path
