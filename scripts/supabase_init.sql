-- FitQuest — run once in Supabase → SQL Editor → Run
-- Creates tables + seeds achievements & reward shop

-- ---------- ENUM types ----------
DO $$ BEGIN CREATE TYPE gender_enum AS ENUM ('male', 'female', 'other');
EXCEPTION WHEN duplicate_object THEN NULL; END $$;

DO $$ BEGIN CREATE TYPE fitness_level_enum AS ENUM ('beginner', 'intermediate', 'advanced');
EXCEPTION WHEN duplicate_object THEN NULL; END $$;

DO $$ BEGIN CREATE TYPE fitness_goal_enum AS ENUM ('lose_weight', 'gain_muscle', 'get_fitter');
EXCEPTION WHEN duplicate_object THEN NULL; END $$;

DO $$ BEGIN CREATE TYPE achievement_condition_type AS ENUM (
  'first_workout', 'total_workouts', 'total_reps', 'total_points', 'streak_days', 'custom'
);
EXCEPTION WHEN duplicate_object THEN NULL; END $$;

DO $$ BEGIN CREATE TYPE friendship_status AS ENUM ('pending', 'accepted', 'blocked');
EXCEPTION WHEN duplicate_object THEN NULL; END $$;

DO $$ BEGIN CREATE TYPE challenge_metric_type AS ENUM ('reps', 'points', 'duration_seconds', 'workouts');
EXCEPTION WHEN duplicate_object THEN NULL; END $$;

DO $$ BEGIN CREATE TYPE exercise_difficulty AS ENUM ('easy', 'medium', 'hard');
EXCEPTION WHEN duplicate_object THEN NULL; END $$;

-- ---------- Tables ----------
CREATE TABLE IF NOT EXISTS users (
  id BIGSERIAL PRIMARY KEY,
  email VARCHAR(255) NOT NULL UNIQUE,
  username VARCHAR(50) NOT NULL UNIQUE,
  password_hash VARCHAR(255) NOT NULL,
  display_name VARCHAR(100),
  avatar_url VARCHAR(255),
  total_points INTEGER DEFAULT 0,
  level INTEGER DEFAULT 1,
  current_streak_days INTEGER DEFAULT 0,
  longest_streak_days INTEGER DEFAULT 0,
  last_active_date DATE,
  gender gender_enum,
  birth_date DATE,
  height_cm NUMERIC(5, 2),
  weight_kg NUMERIC(5, 2),
  target_weight_kg NUMERIC(5, 2),
  fitness_level fitness_level_enum,
  fitness_goal fitness_goal_enum,
  has_completed_onboarding BOOLEAN NOT NULL DEFAULT FALSE,
  created_at TIMESTAMP NOT NULL DEFAULT (NOW() AT TIME ZONE 'utc'),
  updated_at TIMESTAMP NOT NULL DEFAULT (NOW() AT TIME ZONE 'utc')
);

CREATE TABLE IF NOT EXISTS workouts (
  id BIGSERIAL PRIMARY KEY,
  user_id BIGINT NOT NULL REFERENCES users(id),
  title VARCHAR(100),
  workout_date DATE NOT NULL,
  started_at TIMESTAMP NOT NULL DEFAULT (NOW() AT TIME ZONE 'utc'),
  ended_at TIMESTAMP,
  total_duration_seconds INTEGER,
  total_points_earned INTEGER DEFAULT 0,
  calories_estimate INTEGER,
  exercise_id VARCHAR(50),
  difficulty VARCHAR(20),
  preset_id VARCHAR(50),
  target_sets INTEGER,
  target_reps INTEGER,
  total_reps INTEGER DEFAULT 0
);

CREATE TABLE IF NOT EXISTS achievements (
  id SERIAL PRIMARY KEY,
  code VARCHAR(50) NOT NULL UNIQUE,
  name VARCHAR(100) NOT NULL,
  description VARCHAR(255),
  points_reward INTEGER NOT NULL DEFAULT 0,
  condition_type achievement_condition_type NOT NULL,
  condition_value INTEGER NOT NULL DEFAULT 0,
  is_active BOOLEAN NOT NULL DEFAULT TRUE
);

CREATE TABLE IF NOT EXISTS user_achievements (
  id BIGSERIAL PRIMARY KEY,
  user_id BIGINT NOT NULL REFERENCES users(id),
  achievement_id INTEGER NOT NULL REFERENCES achievements(id),
  unlocked_at TIMESTAMP NOT NULL DEFAULT (NOW() AT TIME ZONE 'utc')
);

CREATE TABLE IF NOT EXISTS reward_items (
  id SERIAL PRIMARY KEY,
  code VARCHAR(50) NOT NULL UNIQUE,
  name VARCHAR(120) NOT NULL,
  description VARCHAR(255),
  points_cost INTEGER NOT NULL,
  redeem_message VARCHAR(255),
  is_active BOOLEAN NOT NULL DEFAULT TRUE,
  sort_order INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS reward_shop_settings (
  id INTEGER PRIMARY KEY DEFAULT 1,
  default_redeem_message VARCHAR(255) NOT NULL DEFAULT 'Go to the counter to redeem the reward'
);

INSERT INTO reward_shop_settings (id, default_redeem_message)
VALUES (1, 'Go to the counter to redeem the reward')
ON CONFLICT (id) DO NOTHING;

CREATE TABLE IF NOT EXISTS reward_redemptions (
  id BIGSERIAL PRIMARY KEY,
  user_id BIGINT NOT NULL REFERENCES users(id),
  reward_item_id INTEGER NOT NULL REFERENCES reward_items(id),
  points_spent INTEGER NOT NULL,
  redeemed_at TIMESTAMP NOT NULL DEFAULT (NOW() AT TIME ZONE 'utc')
);

CREATE TABLE IF NOT EXISTS friendships (
  id BIGSERIAL PRIMARY KEY,
  requester_id BIGINT NOT NULL REFERENCES users(id),
  addressee_id BIGINT NOT NULL REFERENCES users(id),
  status friendship_status NOT NULL DEFAULT 'pending',
  created_at TIMESTAMP NOT NULL DEFAULT (NOW() AT TIME ZONE 'utc'),
  updated_at TIMESTAMP NOT NULL DEFAULT (NOW() AT TIME ZONE 'utc')
);

CREATE TABLE IF NOT EXISTS challenges (
  id BIGSERIAL PRIMARY KEY,
  name VARCHAR(100) NOT NULL,
  description VARCHAR(255),
  created_by BIGINT NOT NULL REFERENCES users(id),
  start_date DATE NOT NULL,
  end_date DATE NOT NULL,
  metric_type challenge_metric_type NOT NULL,
  exercise_id VARCHAR(50),
  difficulty VARCHAR(20),
  preset_id VARCHAR(64),
  target_value INTEGER,
  is_active BOOLEAN NOT NULL DEFAULT TRUE,
  created_at TIMESTAMP NOT NULL DEFAULT (NOW() AT TIME ZONE 'utc')
);

CREATE TABLE IF NOT EXISTS challenge_items (
  id BIGSERIAL PRIMARY KEY,
  challenge_id BIGINT NOT NULL REFERENCES challenges(id),
  exercise_id VARCHAR(50) NOT NULL,
  difficulty VARCHAR(20),
  preset_id VARCHAR(64),
  target_value INTEGER NOT NULL DEFAULT 0,
  created_at TIMESTAMP NOT NULL DEFAULT (NOW() AT TIME ZONE 'utc')
);

CREATE TABLE IF NOT EXISTS challenge_participants (
  id BIGSERIAL PRIMARY KEY,
  challenge_id BIGINT NOT NULL REFERENCES challenges(id),
  user_id BIGINT NOT NULL REFERENCES users(id),
  progress_value INTEGER NOT NULL DEFAULT 0,
  rank_cache INTEGER,
  last_updated TIMESTAMP NOT NULL DEFAULT (NOW() AT TIME ZONE 'utc')
);

CREATE TABLE IF NOT EXISTS exercises (
  id SMALLSERIAL PRIMARY KEY,
  code VARCHAR(50) NOT NULL UNIQUE,
  name VARCHAR(100) NOT NULL,
  category VARCHAR(50),
  description VARCHAR(255),
  difficulty_level exercise_difficulty NOT NULL DEFAULT 'easy',
  points_per_rep INTEGER NOT NULL DEFAULT 1,
  points_per_minute INTEGER NOT NULL DEFAULT 1
);

CREATE TABLE IF NOT EXISTS exercise_sessions (
  id BIGSERIAL PRIMARY KEY,
  workout_id BIGINT NOT NULL REFERENCES workouts(id),
  exercise_id SMALLINT NOT NULL REFERENCES exercises(id),
  sequence_order INTEGER NOT NULL DEFAULT 1,
  started_at TIMESTAMP NOT NULL,
  ended_at TIMESTAMP,
  reps_count INTEGER NOT NULL DEFAULT 0,
  duration_seconds INTEGER NOT NULL DEFAULT 0,
  avg_form_score NUMERIC(5, 2),
  max_form_score NUMERIC(5, 2)
);

CREATE TABLE IF NOT EXISTS pose_metrics (
  id BIGSERIAL PRIMARY KEY,
  exercise_session_id BIGINT NOT NULL REFERENCES exercise_sessions(id),
  metric_name VARCHAR(100) NOT NULL,
  metric_value NUMERIC(10, 4),
  metric_json JSONB,
  created_at TIMESTAMP NOT NULL DEFAULT (NOW() AT TIME ZONE 'utc')
);

CREATE TABLE IF NOT EXISTS user_daily_stats (
  id BIGSERIAL PRIMARY KEY,
  user_id BIGINT NOT NULL REFERENCES users(id),
  stat_date DATE NOT NULL,
  total_points INTEGER NOT NULL DEFAULT 0,
  total_workouts INTEGER NOT NULL DEFAULT 0,
  total_reps INTEGER NOT NULL DEFAULT 0,
  total_duration_seconds INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS global_leaderboard (
  user_id BIGINT PRIMARY KEY REFERENCES users(id),
  username VARCHAR(50),
  display_name VARCHAR(100),
  avatar_url VARCHAR(255),
  total_points INTEGER,
  level INTEGER,
  current_streak_days INTEGER,
  longest_streak_days INTEGER
);

-- ---------- Seed: achievements ----------
INSERT INTO achievements (code, name, description, points_reward, condition_type, condition_value, is_active)
VALUES
  ('first_workout', 'First Quest', 'Complete your first workout session.', 50, 'first_workout', 1, TRUE),
  ('workouts_5', 'Regular Athlete', 'Complete 5 workout sessions.', 100, 'total_workouts', 5, TRUE),
  ('workouts_25', 'Quest Grinder', 'Complete 25 workout sessions.', 200, 'total_workouts', 25, TRUE),
  ('reps_100', 'Rep Machine', 'Log 100 total reps across all workouts.', 75, 'total_reps', 100, TRUE),
  ('reps_500', 'Rep Legend', 'Log 500 total reps across all workouts.', 150, 'total_reps', 500, TRUE),
  ('points_500', 'Point Collector', 'Earn 500 total points.', 50, 'total_points', 500, TRUE),
  ('points_1000', 'Point Hunter', 'Earn 1,000 total points.', 100, 'total_points', 1000, TRUE),
  ('streak_3', 'On a Roll', 'Train 3 days in a row.', 75, 'streak_days', 3, TRUE),
  ('streak_7', 'Week Warrior', 'Train 7 days in a row.', 200, 'streak_days', 7, TRUE)
ON CONFLICT (code) DO NOTHING;

-- ---------- Seed: reward shop ----------
INSERT INTO reward_items (code, name, description, points_cost, redeem_message, is_active, sort_order)
VALUES
  ('gym_day_pass', 'Gym Day Pass', 'One full day access to partner gym facilities.', 1000, 'Go to the counter to redeem the reward', TRUE, 1),
  ('treadmill_1hr', '1 hr Treadmill', 'One hour on the treadmill at a partner gym.', 500, 'Go to the counter to redeem the reward', TRUE, 2),
  ('protein_shake', 'Protein Shake', 'Redeem a post-workout protein shake.', 250, 'Go to the counter to redeem the reward', TRUE, 3)
ON CONFLICT (code) DO NOTHING;

-- Backfill redeem_message on existing rows (safe if column was added later)
UPDATE reward_items
SET redeem_message = 'Go to the counter to redeem the reward'
WHERE redeem_message IS NULL OR redeem_message = '';

-- Done. Check Table Editor for: users, achievements, reward_items, reward_redemptions, workouts
