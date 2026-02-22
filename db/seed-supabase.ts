/**
 * Seed script for Supabase (PostgREST API)
 * Run: npx tsx db/seed-supabase.ts
 */
import { readFileSync } from 'fs';
import { join } from 'path';

const SUPABASE_URL = 'https://kgaqsazjzrvrzsuiavri.supabase.co';
const SERVICE_ROLE_KEY = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImtnYXFzYXpqenJ2cnpzdWlhdnJpIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc1MTcxNTE4OSwiZXhwIjoyMDY3MjkxMTg5fQ.0Uwc6SRzDWe3VTpuQqr8bFW0yTbJkg-VsIG__KyVGq0';

const headers = {
  'apikey': SERVICE_ROLE_KEY,
  'Authorization': `Bearer ${SERVICE_ROLE_KEY}`,
  'Content-Type': 'application/json',
  'Prefer': 'return=minimal',
};

async function post(table: string, rows: unknown[]) {
  // PostgREST has a practical limit per request; batch in chunks of 200
  const CHUNK = 200;
  for (let i = 0; i < rows.length; i += CHUNK) {
    const chunk = rows.slice(i, i + CHUNK);
    const res = await fetch(`${SUPABASE_URL}/rest/v1/${table}`, {
      method: 'POST',
      headers,
      body: JSON.stringify(chunk),
    });
    if (!res.ok) {
      const body = await res.text();
      throw new Error(`POST ${table} [${i}..${i + chunk.length}] failed: ${res.status} ${body}`);
    }
  }
}

interface Capacity { theater?: number; school?: number; banquet?: number; standing?: number; max?: number; }
interface Division { name: string; areaSqm?: number; ceilingHeightM?: number; capacity: Capacity; }
interface Room {
  id: string; name: string; floor?: string; areaSqm?: number; ceilingHeightM?: number;
  capacity: Capacity; divisions: Division[]; equipment?: string; features?: string;
  loadingDock?: string; usageCount?: number; typicalSeatCount?: number; typicalUse?: string;
}
interface Hotel {
  id: string; name: string; address: string; region: string; totalRoomCount?: string;
  rooms: Room[]; practicalInfo?: Record<string, unknown>; lat?: number; lng?: number; usageCount?: number;
}
interface UsageRecord {
  id: string; hotelName: string; hotelId?: string; roomName: string; roomId?: string;
  floor?: string; seminarName: string; date?: string; year?: number; seatCount?: number;
  areaSqm?: number; ceilingHeightM?: number; greenRooms?: { name: string; areaSqm?: number; purpose: string }[];
  equipment?: string[]; usageHours?: string; attendeeEstimate?: number; sourceFile: string;
}

function normalizeDate(dateStr: string | undefined): string | null {
  if (!dateStr) return null;
  const normalized = dateStr.replace(/[０-９]/g, (ch) =>
    String.fromCharCode(ch.charCodeAt(0) - 0xFEE0)
  );
  if (/^\d{4}-\d{2}-\d{2}$/.test(normalized)) return normalized;
  return null;
}

async function seed() {
  const root = join(import.meta.dirname, '..', 'public', 'data');
  const venues: Hotel[] = JSON.parse(readFileSync(join(root, 'venues.json'), 'utf-8'));
  const usageRecords: UsageRecord[] = JSON.parse(readFileSync(join(root, 'usage-records.json'), 'utf-8'));

  // 1. Insert venues
  const venueRows = venues.map(v => ({
    id: v.id,
    name: v.name,
    address: v.address || null,
    region: v.region,
    lat: v.lat ?? null,
    lng: v.lng ?? null,
    usage_count: v.usageCount ?? 0,
    total_room_count: v.totalRoomCount ?? null,
    practical_info: v.practicalInfo ?? null,
  }));
  await post('venues', venueRows);
  console.log(`venues: ${venueRows.length} inserted`);

  // 2. Insert rooms
  const roomRows: Record<string, unknown>[] = [];
  for (const v of venues) {
    for (const r of v.rooms) {
      const extra: Record<string, unknown> = {};
      if (r.equipment) extra.equipment = r.equipment;
      if (r.features) extra.features = r.features;
      if (r.loadingDock) extra.loadingDock = r.loadingDock;
      if (r.typicalSeatCount != null) extra.typicalSeatCount = r.typicalSeatCount;
      if (r.typicalUse) extra.typicalUse = r.typicalUse;

      roomRows.push({
        id: r.id,
        venue_id: v.id,
        name: r.name,
        floor: r.floor ?? null,
        area_sqm: r.areaSqm ?? null,
        ceiling_height_m: r.ceilingHeightM ?? null,
        capacity_theater: r.capacity.theater ?? null,
        capacity_school: r.capacity.school ?? null,
        capacity_banquet: r.capacity.banquet ?? null,
        capacity_standing: r.capacity.standing ?? null,
        usage_count: r.usageCount ?? 0,
        divisions: r.divisions,
        extra,
      });
    }
  }
  await post('rooms', roomRows);
  console.log(`rooms: ${roomRows.length} inserted`);

  // 3. Insert usage records
  const usageRows = usageRecords.map(u => {
    const details: Record<string, unknown> = {};
    if (u.seatCount != null) details.seatCount = u.seatCount;
    if (u.areaSqm != null) details.areaSqm = u.areaSqm;
    if (u.ceilingHeightM != null) details.ceilingHeightM = u.ceilingHeightM;
    if (u.attendeeEstimate != null) details.attendeeEstimate = u.attendeeEstimate;
    if (u.usageHours) details.usageHours = u.usageHours;
    if (u.floor) details.floor = u.floor;

    return {
      id: u.id,
      venue_id: u.hotelId ?? null,
      room_id: u.roomId ?? null,
      hotel_name: u.hotelName,
      room_name: u.roomName,
      seminar_name: u.seminarName,
      date: normalizeDate(u.date),
      year: u.year ?? null,
      source_file: u.sourceFile,
      details,
      green_rooms: u.greenRooms ?? [],
      equipment: u.equipment ?? null,
    };
  });
  await post('usage_records', usageRows);
  console.log(`usage_records: ${usageRows.length} inserted`);

  console.log('Done!');
}

seed().catch((err) => {
  console.error('Seed failed:', err);
  process.exit(1);
});
