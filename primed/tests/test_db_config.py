# test_db_settings.py
import pytest
from django.db import connection
from django.conf import settings

@pytest.mark.django_db
def test_character_set_and_storage_engine():
    with connection.cursor() as cursor:
        if settings.DATABASES['default']['ENGINE'] == 'django.db.backends.mysql':
            # For MariaDB/MySQL
            cursor.execute("SHOW VARIABLES LIKE 'character_set_server';")
            charset = cursor.fetchone()
            print(f"Character set: {charset[1]}")
            
            cursor.execute("SHOW VARIABLES LIKE 'collation_server';")
            collation = cursor.fetchone()
            print(f"Collation: {collation[1]}")
            
            cursor.execute("SHOW TABLE STATUS;")
            tables = cursor.fetchall()
            for table in tables:
                print(f"Table: {table[0]}, Engine: {table[1]}")
                assert table[1] == 'InnoDB'

            assert charset[1] == 'utf8mb4'
            assert collation[1] == 'utf8mb4_general_ci'

        elif settings.DATABASES['default']['ENGINE'] == 'django.db.backends.sqlite3':
            # For SQLite
            cursor.execute("PRAGMA encoding;")
            charset = cursor.fetchone()
            print(f"Character set: {charset[0]}")
            
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
            tables = cursor.fetchall()
            for table in tables:
                print(f"Table: {table[0]}, Engine: SQLite")

            # SQLite always uses UTF-8 encoding
            assert charset[0].lower() == 'utf-8'
