-- ============================================
-- OCP Platform - Initial Database Schema
-- Phase 1: Core Tables for Text-Based Chatbot
-- ============================================

-- Enable UUID extension
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- ============================================
-- USERS & AUTHENTICATION
-- ============================================

CREATE TABLE users (
    user_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    username VARCHAR(100) NOT NULL UNIQUE,
    email VARCHAR(255) NOT NULL UNIQUE,
    password_hash VARCHAR(255) NOT NULL,
    role VARCHAR(50) NOT NULL DEFAULT 'viewer' CHECK (role IN ('admin', 'developer', 'analyst', 'viewer')),
    is_active BOOLEAN DEFAULT TRUE,
    last_login TIMESTAMP,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_users_email ON users(email);
CREATE INDEX idx_users_role ON users(role);

-- Insert default admin user (password: admin123 - CHANGE IN PRODUCTION!)
INSERT INTO users (username, email, password_hash, role)
VALUES (
    'admin',
    'admin@ocplatform.local',
    '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewY5GyYzS8zH9jkC',  -- bcrypt hash of 'admin123'
    'admin'
);

-- ============================================
-- SESSION MANAGEMENT
-- ============================================

CREATE TABLE sessions (
    session_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    channel_type VARCHAR(20) NOT NULL CHECK (channel_type IN ('voice', 'chat', 'api')),

    -- Caller/User Information
    caller_id VARCHAR(50),
    user_id UUID REFERENCES users(user_id),

    -- Session Metadata
    started_at TIMESTAMP NOT NULL DEFAULT NOW(),
    ended_at TIMESTAMP,
    duration_seconds INTEGER,

    -- State Management
    current_state VARCHAR(100) NOT NULL DEFAULT 'started',
    context JSONB DEFAULT '{}'::jsonb,

    -- Routing Information
    assigned_flow_id UUID,  -- Will reference dialogue_flows later
    assigned_agent_id UUID,

    -- Quality Metrics
    containment_achieved BOOLEAN,
    nlu_avg_confidence DECIMAL(3,2),
    user_satisfaction_score INTEGER CHECK (user_satisfaction_score BETWEEN 1 AND 5),

    -- Audit
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_sessions_started_at ON sessions(started_at DESC);
CREATE INDEX idx_sessions_channel ON sessions(channel_type);
CREATE INDEX idx_sessions_context_gin ON sessions USING gin(context);

-- ============================================
-- CONVERSATION TURNS (TRANSCRIPTS)
-- ============================================

CREATE TABLE conversation_turns (
    turn_id BIGSERIAL PRIMARY KEY,
    session_id UUID NOT NULL REFERENCES sessions(session_id) ON DELETE CASCADE,
    turn_number INTEGER NOT NULL,

    -- Speaker
    speaker VARCHAR(10) NOT NULL CHECK (speaker IN ('user', 'bot', 'agent')),

    -- User Input
    user_input_text TEXT,
    user_input_audio_url VARCHAR(500),
    user_input_language VARCHAR(10) DEFAULT 'en-US',

    -- NLU Results
    detected_intent VARCHAR(100),
    intent_confidence DECIMAL(4,3),
    extracted_entities JSONB DEFAULT '[]'::jsonb,

    -- Bot Response
    bot_response_text TEXT,
    bot_response_audio_url VARCHAR(500),
    bot_action VARCHAR(100),

    -- Timing
    timestamp TIMESTAMP NOT NULL DEFAULT NOW(),
    processing_time_ms INTEGER,

    -- Annotations (for retraining)
    is_correct_intent BOOLEAN,
    corrected_intent VARCHAR(100),
    annotation_notes TEXT,

    UNIQUE(session_id, turn_number)
);

CREATE INDEX idx_turns_session ON conversation_turns(session_id, turn_number);
CREATE INDEX idx_turns_intent ON conversation_turns(detected_intent);
CREATE INDEX idx_turns_timestamp ON conversation_turns(timestamp DESC);
CREATE INDEX idx_turns_entities_gin ON conversation_turns USING gin(extracted_entities);

-- ============================================
-- DIALOGUE FLOW CONFIGURATION
-- ============================================

CREATE TABLE dialogue_flows (
    flow_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    flow_name VARCHAR(200) NOT NULL UNIQUE,
    description TEXT,

    -- Flow Definition (JSON graph)
    flow_definition JSONB NOT NULL,

    -- Versioning
    version INTEGER NOT NULL DEFAULT 1,
    is_active BOOLEAN DEFAULT FALSE,
    parent_flow_id UUID REFERENCES dialogue_flows(flow_id),

    -- Metadata
    created_by UUID REFERENCES users(user_id),
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    published_at TIMESTAMP,

    -- A/B Testing
    traffic_percentage INTEGER DEFAULT 100 CHECK (traffic_percentage BETWEEN 0 AND 100)
);

CREATE INDEX idx_flows_active ON dialogue_flows(is_active) WHERE is_active = TRUE;
CREATE INDEX idx_flows_name ON dialogue_flows(flow_name);

-- Add foreign key constraint now that dialogue_flows exists
ALTER TABLE sessions
ADD CONSTRAINT fk_sessions_flow
FOREIGN KEY (assigned_flow_id)
REFERENCES dialogue_flows(flow_id);

-- ============================================
-- NLU TRAINING DATA
-- ============================================

CREATE TABLE intents (
    intent_id SERIAL PRIMARY KEY,
    intent_name VARCHAR(100) NOT NULL UNIQUE,
    description TEXT,
    flow_id UUID REFERENCES dialogue_flows(flow_id),
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_intents_name ON intents(intent_name);
CREATE INDEX idx_intents_active ON intents(is_active) WHERE is_active = TRUE;

CREATE TABLE training_examples (
    example_id BIGSERIAL PRIMARY KEY,
    intent_id INTEGER REFERENCES intents(intent_id) ON DELETE CASCADE,
    example_text TEXT NOT NULL,
    language VARCHAR(10) DEFAULT 'en-US',

    -- Annotations
    annotated_entities JSONB DEFAULT '[]'::jsonb,

    -- Provenance
    source VARCHAR(50) DEFAULT 'manual' CHECK (source IN ('manual', 'mined', 'synthetic')),
    added_at TIMESTAMP DEFAULT NOW(),

    UNIQUE(intent_id, example_text, language)
);

CREATE INDEX idx_examples_intent ON training_examples(intent_id);
CREATE INDEX idx_examples_language ON training_examples(language);

-- ============================================
-- EXTERNAL API INTEGRATIONS
-- ============================================

CREATE TABLE integration_configs (
    integration_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    integration_name VARCHAR(100) NOT NULL UNIQUE,
    integration_type VARCHAR(50) NOT NULL CHECK (integration_type IN ('rest_api', 'graphql', 'soap', 'database')),

    -- Connection Details
    base_url VARCHAR(500),
    auth_type VARCHAR(20) CHECK (auth_type IN ('none', 'bearer', 'api_key', 'oauth2', 'basic')),
    credentials JSONB,

    -- Request Mapping
    endpoint_mappings JSONB,

    -- SLA & Rate Limiting
    timeout_ms INTEGER DEFAULT 5000,
    rate_limit_per_minute INTEGER,

    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_integrations_active ON integration_configs(is_active) WHERE is_active = TRUE;

-- ============================================
-- HUMAN AGENTS (for escalation)
-- ============================================

CREATE TABLE human_agents (
    agent_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID REFERENCES users(user_id),
    agent_name VARCHAR(200) NOT NULL,

    -- Skills & Routing
    skill_tags VARCHAR(50)[],
    max_concurrent_sessions INTEGER DEFAULT 5,

    is_online BOOLEAN DEFAULT FALSE,
    current_session_count INTEGER DEFAULT 0 CHECK (current_session_count >= 0),

    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_agents_online ON human_agents(is_online) WHERE is_online = TRUE;

-- Add foreign key now that human_agents exists
ALTER TABLE sessions
ADD CONSTRAINT fk_sessions_agent
FOREIGN KEY (assigned_agent_id)
REFERENCES human_agents(agent_id);

-- ============================================
-- AUDIT LOGS
-- ============================================

CREATE TABLE audit_logs (
    log_id BIGSERIAL PRIMARY KEY,
    user_id UUID REFERENCES users(user_id),
    action VARCHAR(100) NOT NULL,
    resource_type VARCHAR(50),
    resource_id VARCHAR(100),
    details JSONB,
    ip_address INET,
    timestamp TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_audit_timestamp ON audit_logs(timestamp DESC);
CREATE INDEX idx_audit_user ON audit_logs(user_id);
CREATE INDEX idx_audit_action ON audit_logs(action);

-- ============================================
-- TRIGGERS FOR AUTO-UPDATE TIMESTAMPS
-- ============================================

CREATE OR REPLACE FUNCTION update_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER sessions_updated_at BEFORE UPDATE ON sessions
    FOR EACH ROW EXECUTE FUNCTION update_updated_at();

CREATE TRIGGER flows_updated_at BEFORE UPDATE ON dialogue_flows
    FOR EACH ROW EXECUTE FUNCTION update_updated_at();

CREATE TRIGGER users_updated_at BEFORE UPDATE ON users
    FOR EACH ROW EXECUTE FUNCTION update_updated_at();

CREATE TRIGGER integrations_updated_at BEFORE UPDATE ON integration_configs
    FOR EACH ROW EXECUTE FUNCTION update_updated_at();

CREATE TRIGGER agents_updated_at BEFORE UPDATE ON human_agents
    FOR EACH ROW EXECUTE FUNCTION update_updated_at();

-- ============================================
-- TRIGGER TO AUTO-CALCULATE SESSION DURATION
-- ============================================

CREATE OR REPLACE FUNCTION calculate_session_duration()
RETURNS TRIGGER AS $$
BEGIN
    IF NEW.ended_at IS NOT NULL AND NEW.started_at IS NOT NULL THEN
        NEW.duration_seconds = EXTRACT(EPOCH FROM (NEW.ended_at - NEW.started_at))::INTEGER;
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER sessions_duration BEFORE INSERT OR UPDATE ON sessions
    FOR EACH ROW EXECUTE FUNCTION calculate_session_duration();

-- ============================================
-- SEED DATA: Sample Intents for Phase 1
-- ============================================

-- Insert basic intents
INSERT INTO intents (intent_name, description) VALUES
    ('greet', 'User greets the bot'),
    ('goodbye', 'User says goodbye'),
    ('check_balance', 'User wants to check account balance'),
    ('transfer_money', 'User wants to transfer money'),
    ('help', 'User asks for help'),
    ('cancel', 'User wants to cancel the current action'),
    ('out_of_scope', 'User input is not related to supported features');

-- Insert sample training examples
INSERT INTO training_examples (intent_id, example_text) VALUES
    -- Greet
    ((SELECT intent_id FROM intents WHERE intent_name = 'greet'), 'hello'),
    ((SELECT intent_id FROM intents WHERE intent_name = 'greet'), 'hi there'),
    ((SELECT intent_id FROM intents WHERE intent_name = 'greet'), 'good morning'),
    ((SELECT intent_id FROM intents WHERE intent_name = 'greet'), 'hey'),

    -- Goodbye
    ((SELECT intent_id FROM intents WHERE intent_name = 'goodbye'), 'bye'),
    ((SELECT intent_id FROM intents WHERE intent_name = 'goodbye'), 'goodbye'),
    ((SELECT intent_id FROM intents WHERE intent_name = 'goodbye'), 'see you later'),
    ((SELECT intent_id FROM intents WHERE intent_name = 'goodbye'), 'thanks, bye'),

    -- Check Balance
    ((SELECT intent_id FROM intents WHERE intent_name = 'check_balance'), 'what is my balance'),
    ((SELECT intent_id FROM intents WHERE intent_name = 'check_balance'), 'check my account balance'),
    ((SELECT intent_id FROM intents WHERE intent_name = 'check_balance'), 'how much money do I have'),
    ((SELECT intent_id FROM intents WHERE intent_name = 'check_balance'), 'balance inquiry'),

    -- Transfer Money
    ((SELECT intent_id FROM intents WHERE intent_name = 'transfer_money'), 'I want to transfer money'),
    ((SELECT intent_id FROM intents WHERE intent_name = 'transfer_money'), 'send $500 to my savings'),
    ((SELECT intent_id FROM intents WHERE intent_name = 'transfer_money'), 'make a transfer'),

    -- Help
    ((SELECT intent_id FROM intents WHERE intent_name = 'help'), 'help me'),
    ((SELECT intent_id FROM intents WHERE intent_name = 'help'), 'what can you do'),
    ((SELECT intent_id FROM intents WHERE intent_name = 'help'), 'I need assistance'),

    -- Cancel
    ((SELECT intent_id FROM intents WHERE intent_name = 'cancel'), 'cancel'),
    ((SELECT intent_id FROM intents WHERE intent_name = 'cancel'), 'nevermind'),
    ((SELECT intent_id FROM intents WHERE intent_name = 'cancel'), 'stop');

-- ============================================
-- SEED DATA: Sample Dialogue Flow
-- ============================================

INSERT INTO dialogue_flows (flow_name, description, flow_definition, is_active, created_by)
VALUES (
    'Banking Assistant - Basic',
    'Simple banking assistant flow for balance check and transfers',
    '{
        "nodes": [
            {
                "id": "start",
                "type": "greeting",
                "template": "Hello! I''m your banking assistant. How can I help you today?",
                "next": "intent_router"
            },
            {
                "id": "intent_router",
                "type": "intent_classifier",
                "intent_mapping": {
                    "check_balance": "check_balance_flow",
                    "transfer_money": "transfer_flow",
                    "help": "help_node",
                    "goodbye": "goodbye_node"
                },
                "default_next": "fallback"
            },
            {
                "id": "check_balance_flow",
                "type": "response",
                "template": "Your current account balance is $1,234.56. Is there anything else I can help you with?",
                "next": "intent_router"
            },
            {
                "id": "transfer_flow",
                "type": "slot_filler",
                "slot_name": "amount",
                "prompt_template": "How much would you like to transfer?",
                "acknowledgment_template": "Transfer of {amount} initiated successfully!",
                "next_on_filled": "intent_router"
            },
            {
                "id": "help_node",
                "type": "response",
                "template": "I can help you check your balance or transfer money. What would you like to do?",
                "next": "intent_router"
            },
            {
                "id": "goodbye_node",
                "type": "response",
                "template": "Thank you for banking with us. Have a great day!",
                "next": null
            },
            {
                "id": "fallback",
                "type": "response",
                "template": "I''m sorry, I didn''t understand that. I can help you check your balance or transfer money.",
                "next": "intent_router"
            }
        ],
        "global_intents": {
            "cancel": "start",
            "help": "help_node"
        }
    }'::jsonb,
    TRUE,
    (SELECT user_id FROM users WHERE username = 'admin')
);

-- ============================================
-- VIEWS FOR ANALYTICS (Phase 4 prep)
-- ============================================

-- Daily conversation metrics
CREATE OR REPLACE VIEW daily_conversation_metrics AS
SELECT
    DATE(started_at) as conversation_date,
    channel_type,
    COUNT(*) as total_conversations,
    COUNT(*) FILTER (WHERE containment_achieved = TRUE) as contained_conversations,
    ROUND(
        COUNT(*) FILTER (WHERE containment_achieved = TRUE)::numeric /
        NULLIF(COUNT(*), 0) * 100, 2
    ) as containment_rate,
    AVG(duration_seconds) as avg_duration_seconds,
    AVG(nlu_avg_confidence) as avg_nlu_confidence,
    AVG(user_satisfaction_score) as avg_satisfaction
FROM sessions
WHERE started_at IS NOT NULL
GROUP BY DATE(started_at), channel_type
ORDER BY conversation_date DESC;

-- Intent distribution
CREATE OR REPLACE VIEW intent_distribution AS
SELECT
    detected_intent,
    COUNT(*) as occurrence_count,
    AVG(intent_confidence) as avg_confidence,
    COUNT(*) FILTER (WHERE is_correct_intent = FALSE) as misclassified_count
FROM conversation_turns
WHERE detected_intent IS NOT NULL
GROUP BY detected_intent
ORDER BY occurrence_count DESC;

-- ============================================
-- COMPLETION MESSAGE
-- ============================================

DO $$
BEGIN
    RAISE NOTICE '==================================================';
    RAISE NOTICE 'OCP Platform Database Initialized Successfully!';
    RAISE NOTICE '==================================================';
    RAISE NOTICE 'Default Admin Credentials:';
    RAISE NOTICE '  Username: admin';
    RAISE NOTICE '  Password: admin123 (CHANGE IN PRODUCTION!)';
    RAISE NOTICE '';
    RAISE NOTICE 'Sample Data Loaded:';
    RAISE NOTICE '  - 7 intents with training examples';
    RAISE NOTICE '  - 1 active dialogue flow';
    RAISE NOTICE '  - 1 admin user';
    RAISE NOTICE '==================================================';
END $$;
