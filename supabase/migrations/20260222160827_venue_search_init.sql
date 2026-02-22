-- Drop all existing Eventos_demo tables
DO $$
DECLARE
  r RECORD;
BEGIN
  FOR r IN (SELECT tablename FROM pg_tables WHERE schemaname = 'public') LOOP
    EXECUTE 'DROP TABLE IF EXISTS public.' || quote_ident(r.tablename) || ' CASCADE';
  END LOOP;
  FOR r IN (SELECT tablename FROM pg_tables WHERE schemaname = 'roles') LOOP
    EXECUTE 'DROP TABLE IF EXISTS roles.' || quote_ident(r.tablename) || ' CASCADE';
  END LOOP;
  FOR r IN (SELECT tablename FROM pg_tables WHERE schemaname = 'admin') LOOP
    EXECUTE 'DROP TABLE IF EXISTS admin.' || quote_ident(r.tablename) || ' CASCADE';
  END LOOP;
END $$;

DROP SCHEMA IF EXISTS roles CASCADE;
DROP SCHEMA IF EXISTS admin CASCADE;

-- Enable pg_trgm for fuzzy text search
CREATE EXTENSION IF NOT EXISTS pg_trgm;

-- venues
CREATE TABLE venues (
  id                TEXT PRIMARY KEY,
  name              TEXT NOT NULL,
  address           TEXT,
  region            TEXT NOT NULL,
  lat               DOUBLE PRECISION,
  lng               DOUBLE PRECISION,
  usage_count       INTEGER DEFAULT 0,
  total_room_count  TEXT,
  practical_info    JSONB
);

CREATE INDEX idx_venues_region ON venues (region);
CREATE INDEX idx_venues_name_trgm ON venues USING gin (name gin_trgm_ops);
CREATE INDEX idx_venues_practical_info ON venues USING gin (practical_info);

-- rooms
CREATE TABLE rooms (
  id                  TEXT PRIMARY KEY,
  venue_id            TEXT NOT NULL REFERENCES venues(id) ON DELETE CASCADE,
  name                TEXT NOT NULL,
  floor               TEXT,
  area_sqm            REAL,
  ceiling_height_m    REAL,
  capacity_theater    INTEGER,
  capacity_school     INTEGER,
  capacity_banquet    INTEGER,
  capacity_standing   INTEGER,
  usage_count         INTEGER DEFAULT 0,
  divisions           JSONB DEFAULT '[]',
  extra               JSONB DEFAULT '{}'
);

CREATE INDEX idx_rooms_venue_id ON rooms (venue_id);
CREATE INDEX idx_rooms_area_sqm ON rooms (area_sqm);
CREATE INDEX idx_rooms_ceiling_height_m ON rooms (ceiling_height_m);
CREATE INDEX idx_rooms_capacity_theater ON rooms (capacity_theater);
CREATE INDEX idx_rooms_capacity_school ON rooms (capacity_school);
CREATE INDEX idx_rooms_capacity_banquet ON rooms (capacity_banquet);
CREATE INDEX idx_rooms_capacity_standing ON rooms (capacity_standing);

-- usage_records
CREATE TABLE usage_records (
  id            TEXT PRIMARY KEY,
  venue_id      TEXT REFERENCES venues(id) ON DELETE SET NULL,
  room_id       TEXT REFERENCES rooms(id) ON DELETE SET NULL,
  hotel_name    TEXT NOT NULL,
  room_name     TEXT NOT NULL,
  seminar_name  TEXT NOT NULL,
  date          DATE,
  year          SMALLINT,
  source_file   TEXT NOT NULL,
  details       JSONB DEFAULT '{}',
  green_rooms   JSONB DEFAULT '[]',
  equipment     TEXT[]
);

CREATE INDEX idx_usage_records_venue_id ON usage_records (venue_id);
CREATE INDEX idx_usage_records_room_id ON usage_records (room_id);
CREATE INDEX idx_usage_records_year ON usage_records (year);

-- RLS: allow public read
ALTER TABLE venues ENABLE ROW LEVEL SECURITY;
ALTER TABLE rooms ENABLE ROW LEVEL SECURITY;
ALTER TABLE usage_records ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Allow public read venues" ON venues FOR SELECT USING (true);
CREATE POLICY "Allow public read rooms" ON rooms FOR SELECT USING (true);
CREATE POLICY "Allow public read usage_records" ON usage_records FOR SELECT USING (true);
