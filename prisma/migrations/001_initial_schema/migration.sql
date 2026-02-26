CREATE EXTENSION IF NOT EXISTS pgcrypto;

CREATE TYPE role AS ENUM ('admin', 'manager', 'staff');
CREATE TYPE notification_preference AS ENUM ('in_app', 'in_app_email');
CREATE TYPE availability_type AS ENUM ('recurring', 'exception');

CREATE TABLE users (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  name VARCHAR(255) NOT NULL,
  email VARCHAR(255) NOT NULL UNIQUE,
  password_hash VARCHAR(255) NOT NULL,
  role role NOT NULL,
  home_timezone VARCHAR(100) NOT NULL DEFAULT 'America/New_York',
  desired_hours_per_week INTEGER NOT NULL DEFAULT 40,
  hourly_rate DECIMAL(8, 2),
  notification_pref notification_preference NOT NULL DEFAULT 'in_app',
  is_active BOOLEAN NOT NULL DEFAULT TRUE,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_users_role ON users(role);
CREATE INDEX idx_users_active ON users(is_active) WHERE is_active = TRUE;

CREATE TABLE locations (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  name VARCHAR(255) NOT NULL,
  address TEXT,
  iana_timezone VARCHAR(100) NOT NULL,
  is_active BOOLEAN NOT NULL DEFAULT TRUE,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE skills (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  name VARCHAR(100) NOT NULL UNIQUE
);

CREATE TABLE user_skills (
  user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  skill_id UUID NOT NULL REFERENCES skills(id) ON DELETE CASCADE,
  PRIMARY KEY (user_id, skill_id)
);

CREATE INDEX idx_user_skills_skill ON user_skills(skill_id);

CREATE TABLE user_location_certifications (
  user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  location_id UUID NOT NULL REFERENCES locations(id) ON DELETE CASCADE,
  certified_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  revoked_at TIMESTAMPTZ,
  revoked_by UUID REFERENCES users(id),
  PRIMARY KEY (user_id, location_id)
);

CREATE UNIQUE INDEX idx_active_cert_per_user_location
  ON user_location_certifications(user_id, location_id)
  WHERE revoked_at IS NULL;
CREATE INDEX idx_cert_by_location
  ON user_location_certifications(location_id)
  WHERE revoked_at IS NULL;

CREATE TABLE manager_location_assignments (
  manager_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  location_id UUID NOT NULL REFERENCES locations(id) ON DELETE CASCADE,
  assigned_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  PRIMARY KEY (manager_id, location_id)
);

CREATE INDEX idx_manager_locations ON manager_location_assignments(manager_id);

CREATE TABLE availability (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  avail_type availability_type NOT NULL,
  day_of_week SMALLINT CHECK (day_of_week BETWEEN 0 AND 6),
  specific_date DATE,
  start_clock VARCHAR(5),
  end_clock VARCHAR(5),
  is_available BOOLEAN NOT NULL DEFAULT TRUE,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  CONSTRAINT chk_avail_type CHECK (
    (avail_type = 'recurring' AND day_of_week IS NOT NULL AND specific_date IS NULL)
    OR
    (avail_type = 'exception' AND specific_date IS NOT NULL AND day_of_week IS NULL)
  )
);

CREATE INDEX idx_avail_user_type ON availability(user_id, avail_type);
CREATE INDEX idx_avail_exception ON availability(user_id, specific_date)
  WHERE avail_type = 'exception';
