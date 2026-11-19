-- Enable pgvector extension for semantic RAG search
CREATE EXTENSION IF NOT EXISTS vector;

-- Projects isolate and categorize papers, datasets, notes, and experiments
-- Categories: 'research' | 'ml' | 'software' | 'teaching'
-- Statuses:   'active'   | 'paused' | 'completed' | 'archived'
CREATE TABLE IF NOT EXISTS projects (
    id SERIAL PRIMARY KEY,
    slug TEXT UNIQUE NOT NULL,
    name TEXT NOT NULL,
    category TEXT NOT NULL DEFAULT 'research',
    status TEXT NOT NULL DEFAULT 'active',
    description TEXT DEFAULT '',
    tags TEXT[] DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_projects_cat_status ON projects(category, status);

-- Shared cross-AI memory notes (Claude, Antigravity, ChatGPT, Qwen, CodeBuddy, etc.)
CREATE TABLE IF NOT EXISTS notes (
    id SERIAL PRIMARY KEY,
    project_slug TEXT NOT NULL REFERENCES projects(slug) ON DELETE CASCADE,
    title TEXT NOT NULL,
    content TEXT NOT NULL,
    author_ai TEXT DEFAULT 'unknown',
    tags TEXT[] DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_notes_project ON notes(project_slug, created_at DESC);

-- Academic papers & ingested documents (with structured Literature Review Matrix columns)
CREATE TABLE IF NOT EXISTS papers (
    id SERIAL PRIMARY KEY,
    project_slug TEXT NOT NULL REFERENCES projects(slug) ON DELETE CASCADE,
    title TEXT NOT NULL,
    authors TEXT DEFAULT '',
    year INT,
    doi TEXT DEFAULT '',
    url TEXT DEFAULT '',
    abstract TEXT DEFAULT '',
    summary TEXT DEFAULT '',
    method TEXT DEFAULT '',
    dataset_used TEXT DEFAULT '',
    key_metrics TEXT DEFAULT '',
    limitations TEXT DEFAULT '',
    storage_key TEXT DEFAULT '',
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_papers_project ON papers(project_slug, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_papers_doi ON papers(doi);

-- Document chunks + vector embeddings (default 768 dims for nomic-embed-text)
CREATE TABLE IF NOT EXISTS chunks (
    id SERIAL PRIMARY KEY,
    paper_id INT NOT NULL REFERENCES papers(id) ON DELETE CASCADE,
    project_slug TEXT NOT NULL REFERENCES projects(slug) ON DELETE CASCADE,
    chunk_index INT NOT NULL,
    content TEXT NOT NULL,
    embedding vector(768),
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_chunks_project ON chunks(project_slug);
CREATE INDEX IF NOT EXISTS idx_chunks_embedding ON chunks USING hnsw (embedding vector_cosine_ops);

-- Dataset Registry across Kaggle, Office PC (Win 11), Mac mini M4, and Oracle Cloud
CREATE TABLE IF NOT EXISTS datasets (
    id SERIAL PRIMARY KEY,
    slug TEXT UNIQUE NOT NULL,
    project_slug TEXT NOT NULL REFERENCES projects(slug) ON DELETE CASCADE,
    name TEXT NOT NULL,
    location TEXT NOT NULL DEFAULT 'kaggle',
    kaggle_ref TEXT DEFAULT '',
    mount_path TEXT DEFAULT '',
    format TEXT DEFAULT 'csv',
    num_samples INT DEFAULT 0,
    num_classes INT DEFAULT 0,
    size_mb DOUBLE PRECISION DEFAULT 0,
    description TEXT DEFAULT '',
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_datasets_project ON datasets(project_slug, location);

-- Registered compute nodes (mac, pc, kaggle)
CREATE TABLE IF NOT EXISTS nodes (
    name TEXT PRIMARY KEY,
    kind TEXT NOT NULL,
    status TEXT DEFAULT 'online',
    capabilities JSONB DEFAULT '{}'::jsonb,
    last_seen TIMESTAMPTZ DEFAULT NOW()
);

-- Experiment registry & distributed job queue (linked to Kaggle datasets)
CREATE TABLE IF NOT EXISTS experiments (
    id TEXT PRIMARY KEY,
    project_slug TEXT NOT NULL REFERENCES projects(slug) ON DELETE CASCADE,
    name TEXT NOT NULL,
    target_node TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'queued',
    dataset_slug TEXT DEFAULT '',
    kaggle_datasets TEXT[] DEFAULT '{}',
    script TEXT NOT NULL DEFAULT '',
    config JSONB DEFAULT '{}'::jsonb,
    metrics JSONB DEFAULT '{}'::jsonb,
    logs TEXT DEFAULT '',
    artifact_url TEXT DEFAULT '',
    created_by TEXT DEFAULT 'ai',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    started_at TIMESTAMPTZ,
    finished_at TIMESTAMPTZ
);

CREATE INDEX IF NOT EXISTS idx_experiments_project ON experiments(project_slug, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_experiments_queue ON experiments(target_node, status, created_at ASC);

-- Seed initial research projects across categories
INSERT INTO projects (slug, name, category, status, description, tags)
VALUES
    ('general', 'General Workspace', 'research', 'active', 'Default shared workspace across all AI clients', ARRAY['general']),
    ('eye_movement', 'Eye Movement Classification', 'research', 'active', 'Eye movement classification using GazeCom, CNN, Multi-Head Attention, and TimesNet', ARRAY['gazecom', 'cnn', 'attention', 'deep-learning']),
    ('network_security', 'Network Intrusion Detection', 'ml', 'active', 'Deep learning and machine learning models for network intrusion detection systems (IDS)', ARRAY['ids', 'cybersecurity', 'ml'])
ON CONFLICT (slug) DO NOTHING;
