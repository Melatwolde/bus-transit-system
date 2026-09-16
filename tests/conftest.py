import pytest
import os
import tempfile
from pathlib import Path

# Set up test database before any modules load
@pytest.fixture(autouse=True, scope="session")
def setup_test_database():
    fd, path = tempfile.mkstemp(suffix=".db", prefix="bus_transit_test_")
    os.close(fd)
    os.environ["DB_PATH"] = path
    
    # Initialize the test DB
    from src.database import init_database
    init_database()
    
    yield path
    
    # Teardown
    if os.path.exists(path):
        os.remove(path)

@pytest.fixture(autouse=True)
def clean_database():
    from src.database import get_connection
    connection = get_connection()
    # Delete all data from tables
    connection.execute("DELETE FROM tickets")
    connection.execute("DELETE FROM users")
    connection.commit()
    connection.close()
