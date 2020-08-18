import pika
import os
from typing import Dict, Any, Union

def create_config_from_object(obj: 'Config') -> Dict[str, Any]:
    """Create a config dictionary out of a configuration object.

    Args:
        obj: Config
    """
    config = {}
    for key in dir(obj):
        if key.isupper():
            config[key] = getattr(obj, key)
    return config

class Config:
    """Base config class.
    """
    RABBIT_HOST = os.getenv('RABBIT_HOST', 'localhost')
    RABBIT_PORT = int(os.getenv('RABBIT_PORT', '5672'))
    RABBIT_VHOST = os.getenv('RABBIT_VHOST','mog_test')
    RABBIT_USER =  os.getenv('RABBIT_USER', 'guest')
    RABBIT_PASSWD = os.getenv('RABBIT_PASSWD', '__rabbit_passwd__')
    ELK_USERNAME = os.getenv('ELK_USERNAME', 'genomcore')
    ELK_PASSWORD = os.getenv('ELK_PASSWORD', '__elk_passwd__')
    ELK_URL = os.getenv('ELK_URL', 'https://eacfaaa6ddfc4de7bde9fa49bde616e6.eu-central-1.aws.cloud.es.io:9243')
    QUEUE_TOPIC_UPDATE = os.getenv('QUEUE_TOPIC_UPDATE', 'records-i-u')
    QUEUE_TOPIC_DELETE = os.getenv('QUEUE_TOPIC_DELETE', 'records-d')
class LocalConfig(Config):
    """Local config is the same as defult config in defult class."""

class DevelopmentConfig(Config):
    """Development config."""
    RABBIT_HOST = os.getenv('RABBIT_HOST', '10.2.100.14')
    RABBIT_VHOST = os.getenv('RABBIT_VHOST','mog_dev')
    RABBIT_USER =  os.getenv('RABBIT_USER', 'mogadmin_dev')


class ProductionConfig(Config):
    """Production config."""
    RABBIT_HOST = os.getenv('RABBIT_HOST', '10.235.150.101')
    RABBIT_VHOST = os.getenv('RABBIT_VHOST','mog_prod')
    RABBIT_USER =  os.getenv('RABBIT_USER', 'mogadmin')

configs = {
    'local': LocalConfig,
    'dev': DevelopmentConfig,
    'prod': ProductionConfig
}