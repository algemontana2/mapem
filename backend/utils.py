
# File: utils.py
# Created: 2025-04-06 16:00:50
# Edited by: King
# Last Edited: 2025-04-06 16:00:50
# Description: Utility functions like name normalization, fuzzy matching, etc.

# utils.py
# utils.py
import re
from fuzzywuzzy import fuzz
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from backend import config


def normalize_name(name):
    """Lowercase and strip whitespace."""
    return name.strip().lower()

def calculate_name_similarity(name1, name2):
    """Calculate fuzzy matching score between two names."""
    name1_norm = normalize_name(name1)
    name2_norm = normalize_name(name2)
    return fuzz.ratio(name1.strip().lower(), name2.strip().lower())

def calculate_match_score(individual1, individual2):
    """
    Calculate a match score based on name similarity and other factors.
    For now, we use name similarity; later you can add birth date proximity, shared locations, etc.
    """
    score = 0
    if hasattr(individual1, 'name') and hasattr(individual2, 'name'):
        score += calculate_name_similarity(individual1.name, individual2.name)
    return score

# Additional utility functions (e.g., tag processing from tags.py, check_names.py, etc.) can be added here.

import psycopg2
from backend import config

def get_db_connection():
    db_uri = (
        f"postgresql+psycopg://{config.DB_USER}:{config.DB_PASSWORD or ''}"
        f"@{config.DB_HOST}:{config.DB_PORT}/{config.DB_NAME}"
    )
    engine = create_engine(db_uri)
    Session = sessionmaker(bind=engine)
    return Session()


def normalize_location_name(name):
    return re.sub(r'\W+', '_', name.strip().lower())
