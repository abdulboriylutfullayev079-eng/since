-- 6 tables for Supabase PostgreSQL:
CREATE TABLE IF NOT EXISTS users (
    user_id BIGINT PRIMARY KEY,
    username TEXT,
    timezone TEXT DEFAULT 'UTC',
    is_premium BOOLEAN DEFAULT FALSE,
    total_donated INT DEFAULT 0,
    status TEXT DEFAULT 'active' CHECK (status IN ('active', 'muted', 'deleted')),
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS countdowns (
    id SERIAL PRIMARY KEY,
    user_id BIGINT REFERENCES users(user_id) ON DELETE CASCADE,
    title TEXT,
    target_date DATE,
    frequency INT,
    notify_hour INT CHECK (notify_hour >= 0 AND notify_hour <= 23),
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS habits (
    id SERIAL PRIMARY KEY,
    user_id BIGINT REFERENCES users(user_id) ON DELETE CASCADE,
    title TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS habit_logs (
    id SERIAL PRIMARY KEY,
    habit_id INT REFERENCES habits(id) ON DELETE CASCADE,
    date DATE,
    status TEXT CHECK (status IN ('green', 'red')),
    UNIQUE(habit_id, date)
);

CREATE TABLE IF NOT EXISTS transactions (
    id SERIAL PRIMARY KEY,
    user_id BIGINT REFERENCES users(user_id) ON DELETE CASCADE,
    amount INT,
    telegram_charge_id TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS broadcasts (
    id SERIAL PRIMARY KEY,
    admin_chat_id BIGINT,
    message_chat_id BIGINT,
    message_id INT,
    total_users INT,
    sent INT DEFAULT 0,
    failed INT DEFAULT 0,
    offset_count INT DEFAULT 0,
    status TEXT DEFAULT 'pending' CHECK (status IN ('pending', 'in_progress', 'completed')),
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_countdowns_user_id ON countdowns(user_id);
CREATE INDEX IF NOT EXISTS idx_habits_user_id ON habits(user_id);
CREATE INDEX IF NOT EXISTS idx_habit_logs_habit_id_date ON habit_logs(habit_id, date);
CREATE INDEX IF NOT EXISTS idx_users_total_donated ON users(total_donated DESC);
CREATE INDEX IF NOT EXISTS idx_transactions_user_id ON transactions(user_id);
