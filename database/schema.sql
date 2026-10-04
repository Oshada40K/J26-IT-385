-- IMPORTANT:
-- Shared schema is controlled by the group leader.
-- Component-specific tables should be coordinated with the group leader
-- before being added to this shared schema.

CREATE TABLE IF NOT EXISTS students (
    id SERIAL PRIMARY KEY,
    name VARCHAR(150) NOT NULL,
    email VARCHAR(255) UNIQUE NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
