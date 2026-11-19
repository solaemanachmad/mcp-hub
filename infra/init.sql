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

-- Dynamic Multi-LLM Provider Registry (Qwen, DeepSeek, Baidu, Weixin/Hunyuan, Gemini, OpenAI, OpenRouter, etc.)
CREATE TABLE IF NOT EXISTS llm_providers (
    name TEXT PRIMARY KEY,
    base_url TEXT NOT NULL,
    default_model TEXT NOT NULL,
    embed_model TEXT DEFAULT '',
    api_key_env TEXT NOT NULL,
    enabled BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Shared cross-AI memory notes (Claude, Antigravity, ChatGPT, Qwen, CodeBuddy, WorkBuddy, etc.)
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

-- Document chunks + vector embeddings (default 768 dims)
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

-- Dataset Registry across Kaggle, Office PC (Win 11), and Oracle Cloud
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

-- Registered compute nodes (pc, kaggle)
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

-- Seed initial research projects
INSERT INTO projects (slug, name, category, status, description, tags)
VALUES
    ('general', 'General Workspace', 'research', 'active', 'Default shared workspace across all AI clients', ARRAY['general']),
    ('eye_movement', 'Eye Movement Classification', 'research', 'active', 'Eye movement classification using GazeCom, CNN, Multi-Head Attention, and TimesNet', ARRAY['gazecom', 'cnn', 'attention', 'deep-learning']),
    ('network_security', 'Network Intrusion Detection', 'ml', 'active', 'Deep learning and machine learning models for network intrusion detection systems (IDS)', ARRAY['ids', 'cybersecurity', 'ml'])
ON CONFLICT (slug) DO NOTHING;

-- Seed popular OpenAI-compatible LLM providers (activate any by setting its API key in .env)
INSERT INTO llm_providers (name, base_url, default_model, embed_model, api_key_env)
VALUES
    ('qwen', 'https://dashscope-intl.aliyuncs.com/compatible-mode/v1', 'qwen-plus', 'text-embedding-v3', 'QWEN_API_KEY'),
    ('deepseek', 'https://api.deepseek.com/v1', 'deepseek-chat', '', 'DEEPSEEK_API_KEY'),
    ('baidu', 'https://qianfan.baidubce.com/v2', 'ernie-4.0-8k', 'embedding-v1', 'BAIDU_API_KEY'),
    ('weixin', 'https://api.hunyuan.cloud.tencent.com/v1', 'hunyuan-pro', 'hunyuan-embedding', 'WEIXIN_API_KEY'),
    ('gemini', 'https://generativelanguage.googleapis.com/v1beta/openai', 'gemini-2.5-flash', 'text-embedding-004', 'GEMINI_API_KEY'),
    ('openai', 'https://api.openai.com/v1', 'gpt-4o-mini', 'text-embedding-3-small', 'OPENAI_API_KEY'),
    ('openrouter', 'https://openrouter.ai/api/v1', 'qwen/qwen-2.5-72b-instruct', '', 'OPENROUTER_API_KEY')
ON CONFLICT (name) DO NOTHING;
