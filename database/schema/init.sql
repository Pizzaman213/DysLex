-- DysLex AI Initial Database Schema
-- PostgreSQL

-- Enable UUID extension
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Users table
CREATE TABLE IF NOT EXISTS users (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    email VARCHAR(255) UNIQUE NOT NULL,
    name VARCHAR(255) NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Error profiles (adaptive brain)
CREATE TABLE IF NOT EXISTS error_profiles (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID UNIQUE REFERENCES users(id) ON DELETE CASCADE,
    overall_score INTEGER DEFAULT 50,
    patterns JSONB DEFAULT '[]'::jsonb,
    confusion_pairs JSONB DEFAULT '[]'::jsonb,
    achievements JSONB DEFAULT '[]'::jsonb,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Error logs for passive learning
CREATE TABLE IF NOT EXISTS error_logs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    original_text TEXT NOT NULL,
    corrected_text TEXT NOT NULL,
    error_type VARCHAR(50) NOT NULL,
    context TEXT,
    confidence FLOAT DEFAULT 0.0,
    was_accepted BOOLEAN,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Language-specific confusion pairs
CREATE TABLE IF NOT EXISTS confusion_pairs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    language VARCHAR(10) NOT NULL,
    word1 VARCHAR(100) NOT NULL,
    word2 VARCHAR(100) NOT NULL,
    category VARCHAR(50) NOT NULL,
    frequency INTEGER DEFAULT 0
);

-- Known error patterns
CREATE TABLE IF NOT EXISTS error_patterns (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name VARCHAR(100) NOT NULL,
    description TEXT NOT NULL,
    category VARCHAR(50) NOT NULL,
    examples JSONB DEFAULT '[]'::jsonb
);

-- User progress tracking
CREATE TABLE IF NOT EXISTS user_progress (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    date DATE NOT NULL,
    words_written INTEGER DEFAULT 0,
    corrections_made INTEGER DEFAULT 0,
    accuracy_score FLOAT DEFAULT 0.0,
    UNIQUE(user_id, date)
);

-- Indexes
CREATE INDEX idx_error_logs_user_id ON error_logs(user_id);
CREATE INDEX idx_error_logs_created_at ON error_logs(created_at);
CREATE INDEX idx_confusion_pairs_language ON confusion_pairs(language);
CREATE INDEX idx_user_progress_user_date ON user_progress(user_id, date);

-- Updated_at trigger function
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Apply trigger to tables with updated_at
CREATE TRIGGER update_users_updated_at
    BEFORE UPDATE ON users
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_error_profiles_updated_at
    BEFORE UPDATE ON error_profiles
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();
