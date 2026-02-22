import { Router, type Request, type Response } from 'express';
import { supabase } from '../db.js';

const router = Router();

interface RoomRow {
  id: string;
  name: string;
  floor: string | null;
  area_sqm: number | null;
  ceiling_height_m: number | null;
  capacity_theater: number | null;
  capacity_school: number | null;
  capacity_banquet: number | null;
  capacity_standing: number | null;
  usage_count: number;
  divisions: unknown[];
  extra: Record<string, unknown>;
}

interface VenueRow {
  id: string;
  name: string;
  address: string | null;
  region: string;
  lat: number | null;
  lng: number | null;
  usage_count: number;
  total_room_count: string | null;
  practical_info: Record<string, unknown> | null;
  rooms: RoomRow[];
}

function mapRoom(r: RoomRow) {
  return {
    id: r.id,
    name: r.name,
    floor: r.floor,
    areaSqm: r.area_sqm,
    ceilingHeightM: r.ceiling_height_m,
    capacity: {
      theater: r.capacity_theater,
      school: r.capacity_school,
      banquet: r.capacity_banquet,
      standing: r.capacity_standing,
    },
    divisions: r.divisions,
    equipment: r.extra?.equipment ?? null,
    features: r.extra?.features ?? null,
    loadingDock: r.extra?.loadingDock ?? null,
    usageCount: r.usage_count,
    typicalSeatCount: r.extra?.typicalSeatCount != null ? Number(r.extra.typicalSeatCount) : null,
    typicalUse: r.extra?.typicalUse ?? null,
  };
}

function mapVenue(v: VenueRow) {
  return {
    id: v.id,
    name: v.name,
    address: v.address,
    region: v.region,
    lat: v.lat,
    lng: v.lng,
    usageCount: v.usage_count,
    totalRoomCount: v.total_room_count,
    practicalInfo: v.practical_info,
    rooms: (v.rooms ?? []).map(mapRoom),
  };
}

/**
 * GET /api/venues
 * Returns { venues: Hotel[], total: number }
 */
router.get('/', async (req: Request, res: Response) => {
  try {
    const { data, error } = await supabase
      .from('venues')
      .select('*, rooms(*)')
      .order('name');

    if (error) throw error;

    const venues = (data as VenueRow[]).map(mapVenue);
    res.json({ venues, total: venues.length });
  } catch (err) {
    console.error('GET /api/venues error:', err);
    res.status(500).json({ error: 'Internal server error' });
  }
});

export default router;
