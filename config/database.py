"""
Database Configuration Module

This module provides a connection pool management system for PostgreSQL database
connections. It implements a thread-safe connection pooling mechanism to efficiently
handle multiple database connections while maintaining performance and resource usage.
"""

import logging
from psycopg2 import pool
from psycopg2.extras import DictCursor
from contextlib import contextmanager
import os
from dotenv import load_dotenv

# Load database configuration from environment variables
load_dotenv()

class DatabaseConfig:
    """
    Database configuration and connection pool management class.
    
    This class manages PostgreSQL database connections using a connection pool
    to optimize resource usage and improve performance. It provides methods
    for obtaining and returning connections, as well as a context manager
    for safe database operations.
    
    Attributes:
        DB_HOST (str): Database host address from environment
        DB_NAME (str): Database name from environment
        DB_USER (str): Database username from environment
        DB_PASSWORD (str): Database password from environment
        MIN_CONNECTIONS (int): Minimum number of connections in the pool
        MAX_CONNECTIONS (int): Maximum number of connections in the pool
    """
    
    # Database credentials loaded from environment variables
    DB_HOST = os.getenv('DB_HOST')
    DB_NAME = os.getenv('DB_NAME')
    DB_USER = os.getenv('DB_USER')
    DB_PASSWORD = os.getenv('DB_PASSWORD')
    
    # Connection pool configuration
    MIN_CONNECTIONS = 1      # Minimum connections to maintain in the pool
    MAX_CONNECTIONS = 15     # Maximum connections allowed in the pool
    
    _pool = None            # Connection pool instance
    
    @classmethod
    def init_pool(cls):
        """
        Initialize the database connection pool.
        
        Creates a new connection pool if one doesn't exist, using the configured
        credentials and connection limits. Raises an exception if initialization fails.
        
        Raises:
            Exception: If pool initialization fails
        """
        if cls._pool is None:
            try:
                cls._pool = pool.SimpleConnectionPool(
                    cls.MIN_CONNECTIONS,
                    cls.MAX_CONNECTIONS,
                    host=cls.DB_HOST,
                    dbname=cls.DB_NAME,
                    user=cls.DB_USER,
                    password=cls.DB_PASSWORD
                )
                logging.info("Database connection pool initialized successfully")
            except Exception as e:
                logging.error(f"Error initializing connection pool: {e}")
                raise
    
    @classmethod
    def get_connection(cls):
        """
        Get a connection from the pool.
        
        Initializes the pool if it doesn't exist and returns a connection.
        
        Returns:
            connection: A PostgreSQL database connection from the pool
        """
        if cls._pool is None:
            cls.init_pool()
        return cls._pool.getconn()
    
    @classmethod
    def return_connection(cls, conn):
        """
        Return a connection back to the pool.
        
        Args:
            conn: The PostgreSQL connection to return to the pool
        """
        if cls._pool is not None:
            cls._pool.putconn(conn)
    
    @classmethod
    @contextmanager
    def get_cursor(cls, cursor_factory=DictCursor):
        """
        Context manager for safe database operations.
        
        Provides a cursor for database operations with automatic connection
        management and error handling. Handles commits and rollbacks automatically.
        
        Args:
            cursor_factory: The cursor factory to use (defaults to DictCursor)
        
        Yields:
            cursor: A database cursor for executing queries
            
        Raises:
            Exception: If any database operation fails
        """
        conn = None
        cursor = None
        try:
            conn = cls.get_connection()
            cursor = conn.cursor(cursor_factory=cursor_factory)
            yield cursor
            conn.commit()
        except Exception as e:
            if conn:
                conn.rollback()
            logging.error(f"Error during database operation: {e}")
            raise
        finally:
            if cursor:
                cursor.close()
            if conn:
                cls.return_connection(conn)
