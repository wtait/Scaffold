-- Initialize the database with any required data
-- This file is executed when the PostgreSQL container first starts

-- Create extensions if needed
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- The actual tables will be created by the SQLAlchemy models
-- when the application starts