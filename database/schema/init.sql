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

-- Source column on error_logs (detection source)
ALTER TABLE error_logs ADD COLUMN IF NOT EXISTS source VARCHAR(20) DEFAULT 'passive';

-- Per-user error pattern frequency map
CREATE TABLE IF NOT EXISTS user_error_patterns (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    misspelling VARCHAR(255) NOT NULL,
    correction VARCHAR(255) NOT NULL,
    error_type VARCHAR(50) NOT NULL,
    frequency INTEGER NOT NULL DEFAULT 1,
    improving BOOLEAN NOT NULL DEFAULT FALSE,
    language_code VARCHAR(10) NOT NULL DEFAULT 'en',
    first_seen TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    last_seen TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(user_id, misspelling, correction)
);

-- Per-user word confusion tracking
CREATE TABLE IF NOT EXISTS user_confusion_pairs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    word_a VARCHAR(100) NOT NULL,
    word_b VARCHAR(100) NOT NULL,
    confusion_count INTEGER NOT NULL DEFAULT 1,
    last_confused_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(user_id, word_a, word_b)
);

-- Personal dictionary — words to never flag
CREATE TABLE IF NOT EXISTS personal_dictionary (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    word VARCHAR(255) NOT NULL,
    source VARCHAR(20) NOT NULL DEFAULT 'manual',
    added_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(user_id, word)
);

-- Weekly aggregated progress snapshots
CREATE TABLE IF NOT EXISTS progress_snapshots (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    week_start DATE NOT NULL,
    total_words_written INTEGER NOT NULL DEFAULT 0,
    total_corrections INTEGER NOT NULL DEFAULT 0,
    accuracy_score FLOAT NOT NULL DEFAULT 0.0,
    error_type_breakdown JSONB DEFAULT '{}'::jsonb,
    top_errors JSONB DEFAULT '[]'::jsonb,
    patterns_mastered INTEGER NOT NULL DEFAULT 0,
    new_patterns_detected INTEGER NOT NULL DEFAULT 0,
    UNIQUE(user_id, week_start)
);

-- Indexes
CREATE INDEX idx_error_logs_user_id ON error_logs(user_id);
CREATE INDEX idx_error_logs_created_at ON error_logs(created_at);
CREATE INDEX idx_error_logs_source ON error_logs(source);
CREATE INDEX idx_confusion_pairs_language ON confusion_pairs(language);
CREATE INDEX idx_user_error_patterns_user_id ON user_error_patterns(user_id);
CREATE INDEX idx_user_error_patterns_user_freq ON user_error_patterns(user_id, frequency DESC);
CREATE INDEX idx_user_confusion_pairs_user_id ON user_confusion_pairs(user_id);
CREATE INDEX idx_personal_dictionary_user_id ON personal_dictionary(user_id);
CREATE INDEX idx_progress_snapshots_user_id ON progress_snapshots(user_id);
CREATE INDEX idx_progress_snapshots_user_week ON progress_snapshots(user_id, week_start DESC);

-- Composite indexes for performance
CREATE INDEX IF NOT EXISTS idx_error_logs_user_created ON error_logs(user_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_user_error_patterns_user_type ON user_error_patterns(user_id, error_type);
CREATE INDEX IF NOT EXISTS idx_user_error_patterns_user_lastseen ON user_error_patterns(user_id, last_seen);

-- -------------------------------------------------------------------------
-- Document & Folder persistence (added in migration 005)
-- -------------------------------------------------------------------------

-- Folders table
CREATE TABLE IF NOT EXISTS folders (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    name VARCHAR(255) NOT NULL,
    sort_order INTEGER NOT NULL DEFAULT 0,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Documents table
CREATE TABLE IF NOT EXISTS documents (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    folder_id UUID REFERENCES folders(id) ON DELETE SET NULL,
    title VARCHAR(500) NOT NULL DEFAULT 'Untitled Document',
    content TEXT NOT NULL DEFAULT '',
    mode VARCHAR(20) NOT NULL DEFAULT 'draft',
    sort_order INTEGER NOT NULL DEFAULT 0,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_folders_user_id ON folders(user_id);
CREATE INDEX IF NOT EXISTS idx_documents_user_id ON documents(user_id);
CREATE INDEX IF NOT EXISTS idx_documents_user_folder ON documents(user_id, folder_id);
CREATE INDEX IF NOT EXISTS idx_documents_user_folder_sort ON documents(user_id, folder_id, sort_order);

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

CREATE TRIGGER update_folders_updated_at
    BEFORE UPDATE ON folders
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_documents_updated_at
    BEFORE UPDATE ON documents
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();
