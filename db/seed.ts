/**
 * Seed script: venues.json + usage-records.json → PostgreSQL
 * Run: npx tsx db/seed.ts
 */
import { readFileSync } from 'fs';
import { join } from 'path';
import pg from 'pg';

const DATABASE_URL = process.env.DATABASE_URL || 'postgresql://localhost:5432/venue_search';
const pool = new pg.Pool({ connectionString: DATABASE_URL });

interface Capacity {
  theater?: number;
  school?: number;
  banquet?: number;
  standing?: number;
  max?: number;
}

interface Division {
  name: string;
  areaSqm?: number;
  ceilingHeightM?: number;
  capacity: Capacity;
}

interface Room {
  id: string;
  name: string;
  floor?: string;
  areaSqm?: number;
  ceilingHeightM?: number;
  capacity: Capacity;
  divisions: Division[];
  equipment?: string;
  features?: string;
  loadingDock?: string;
  usageCount?: number;
  typicalSeatCount?: number;
  typicalUse?: string;
}

interface Hotel {
  id: string;
  name: string;
  address: string;
  region: string;
  totalRoomCount?: string;
  rooms: Room[];
  practicalInfo?: Record<string, unknown>;
  lat?: number;
  lng?: number;
  usageCount?: number;
}

interface UsageRecord {
  id: string;
  hotelName: string;
  hotelId?: string;
  roomName: string;
  roomId?: string;
  floor?: string;
  seminarName: string;
  date?: string;
  year?: number;
  seatCount?: number;
  areaSqm?: number;
  ceilingHeightM?: number;
  greenRooms?: { name: string; areaSqm?: number; purpose: string }[];
  equipment?: string[];
  usageHours?: string;
  attendeeEstimate?: number;
  sourceFile: string;
}

function normalizeDate(dateStr: string | undefined): string | null {
  if (!dateStr) return null;
  // 全角数字→半角に正規化
  const normalized = dateStr.replace(/[０-９]/g, (ch) =>
    String.fromCharCode(ch.charCodeAt(0) - 0xFEE0)
  );
  // YYYY-MM-DD 形式かチェック
  if (/^\d{4}-\d{2}-\d{2}$/.test(normalized)) return normalized;
  return null;
}

async function seed() {
  const root = join(import.meta.dirname, '..', 'public', 'data');
  const venues: Hotel[] = JSON.parse(readFileSync(join(root, 'venues.json'), 'utf-8'));
  const usageRecords: UsageRecord[] = JSON.parse(readFileSync(join(root, 'usage-records.json'), 'utf-8'));

  const client = await pool.connect();
  try {
    await client.query('BEGIN');

    // Clear existing data
    await client.query('DELETE FROM usage_records');
    await client.query('DELETE FROM rooms');
    await client.query('DELETE FROM venues');

    // Insert venues
    for (const v of venues) {
      await client.query(
        `INSERT INTO venues (id, name, address, region, lat, lng, usage_count, total_room_count, practical_info)
         VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)`,
        [
          v.id,
          v.name,
          v.address || null,
          v.region,
          v.lat ?? null,
          v.lng ?? null,
          v.usageCount ?? 0,
          v.totalRoomCount ?? null,
          v.practicalInfo ? JSON.stringify(v.practicalInfo) : null,
        ]
      );

      // Insert rooms for this venue
      for (const r of v.rooms) {
        const extra: Record<string, unknown> = {};
        if (r.equipment) extra.equipment = r.equipment;
        if (r.features) extra.features = r.features;
        if (r.loadingDock) extra.loadingDock = r.loadingDock;
        if (r.typicalSeatCount != null) extra.typicalSeatCount = r.typicalSeatCount;
        if (r.typicalUse) extra.typicalUse = r.typicalUse;

        await client.query(
          `INSERT INTO rooms (id, venue_id, name, floor, area_sqm, ceiling_height_m,
            capacity_theater, capacity_school, capacity_banquet, capacity_standing,
            usage_count, divisions, extra)
           VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13)`,
          [
            r.id,
            v.id,
            r.name,
            r.floor ?? null,
            r.areaSqm ?? null,
            r.ceilingHeightM ?? null,
            r.capacity.theater ?? null,
            r.capacity.school ?? null,
            r.capacity.banquet ?? null,
            r.capacity.standing ?? null,
            r.usageCount ?? 0,
            JSON.stringify(r.divisions),
            JSON.stringify(extra),
          ]
        );
      }
    }

    // Insert usage records
    for (const u of usageRecords) {
      const details: Record<string, unknown> = {};
      if (u.seatCount != null) details.seatCount = u.seatCount;
      if (u.areaSqm != null) details.areaSqm = u.areaSqm;
      if (u.ceilingHeightM != null) details.ceilingHeightM = u.ceilingHeightM;
      if (u.attendeeEstimate != null) details.attendeeEstimate = u.attendeeEstimate;
      if (u.usageHours) details.usageHours = u.usageHours;
      if (u.floor) details.floor = u.floor;

      const dateStr = normalizeDate(u.date);

      await client.query(
        `INSERT INTO usage_records (id, venue_id, room_id, hotel_name, room_name, seminar_name,
          date, year, source_file, details, green_rooms, equipment)
         VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12)`,
        [
          u.id,
          u.hotelId ?? null,
          u.roomId ?? null,
          u.hotelName,
          u.roomName,
          u.seminarName,
          dateStr,
          u.year ?? null,
          u.sourceFile,
          JSON.stringify(details),
          JSON.stringify(u.greenRooms ?? []),
          u.equipment ?? null,
        ]
      );
    }

    await client.query('COMMIT');

    // Verify counts
    const venueCount = await client.query('SELECT count(*) FROM venues');
    const roomCount = await client.query('SELECT count(*) FROM rooms');
    const usageCount = await client.query('SELECT count(*) FROM usage_records');
    console.log(`Seeded: ${venueCount.rows[0].count} venues, ${roomCount.rows[0].count} rooms, ${usageCount.rows[0].count} usage records`);
  } catch (err) {
    await client.query('ROLLBACK');
    throw err;
  } finally {
    client.release();
    await pool.end();
  }
}

seed().catch((err) => {
  console.error('Seed failed:', err);
  process.exit(1);
});
