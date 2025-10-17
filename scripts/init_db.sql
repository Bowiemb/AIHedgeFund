-- Initial database setup for AIHedgeFund

-- Enable extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pg_trgm";  -- For text search

-- Create enums (will also be created by Alembic, but good to have here)
DO $$ BEGIN
    CREATE TYPE processing_status_enum AS ENUM ('pending', 'processing', 'completed', 'failed');
EXCEPTION
    WHEN duplicate_object THEN null;
END $$;

DO $$ BEGIN
    CREATE TYPE statement_type_enum AS ENUM ('income', 'balance', 'cashflow', 'equity');
EXCEPTION
    WHEN duplicate_object THEN null;
END $$;

DO $$ BEGIN
    CREATE TYPE put_call_enum AS ENUM ('put', 'call', 'both', 'none');
EXCEPTION
    WHEN duplicate_object THEN null;
END $$;

DO $$ BEGIN
    CREATE TYPE user_role_enum AS ENUM ('user', 'admin', 'internal');
EXCEPTION
    WHEN duplicate_object THEN null;
END $$;

DO $$ BEGIN
    CREATE TYPE subscription_status_enum AS ENUM ('active', 'canceled', 'past_due', 'paused');
EXCEPTION
    WHEN duplicate_object THEN null;
END $$;

DO $$ BEGIN
    CREATE TYPE account_type_enum AS ENUM ('paper', 'live');
EXCEPTION
    WHEN duplicate_object THEN null;
END $$;

DO $$ BEGIN
    CREATE TYPE order_side_enum AS ENUM ('buy', 'sell');
EXCEPTION
    WHEN duplicate_object THEN null;
END $$;

DO $$ BEGIN
    CREATE TYPE order_type_enum AS ENUM ('market', 'limit', 'stop', 'stop_limit');
EXCEPTION
    WHEN duplicate_object THEN null;
END $$;

DO $$ BEGIN
    CREATE TYPE order_status_enum AS ENUM ('pending', 'submitted', 'filled', 'partially_filled', 'canceled', 'rejected');
EXCEPTION
    WHEN duplicate_object THEN null;
END $$;

-- Seed default plans
INSERT INTO plans (id, name, display_name, description, price_monthly, requests_per_day, rows_per_response, is_active)
VALUES
    (uuid_generate_v4(), 'free', 'Free', 'Basic access to SEC data API', 0, 100, 100, true),
    (uuid_generate_v4(), 'pro', 'Pro', 'Full API access with higher limits', 99, 10000, 1000, true),
    (uuid_generate_v4(), 'enterprise', 'Enterprise', 'Unlimited access with SLA', 999, 1000000, 100000, true)
ON CONFLICT (name) DO NOTHING;
