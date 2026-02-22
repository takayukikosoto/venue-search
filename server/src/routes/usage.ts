import { Router, type Request, type Response } from 'express';
import { supabase } from '../db.js';

const router = Router();

interface UsageRow {
  id: string;
  venue_id: string | null;
  room_id: string | null;
  hotel_name: string;
  room_name: string;
  seminar_name: string;
  date: string | null;
  year: number | null;
  source_file: string;
  details: Record<string, unknown>;
  green_rooms: unknown[];
  equipment: string[] | null;
}

function mapUsage(u: UsageRow) {
  return {
    id: u.id,
    hotelName: u.hotel_name,
    hotelId: u.venue_id,
    roomName: u.room_name,
    roomId: u.room_id,
    seminarName: u.seminar_name,
    date: u.date,
    year: u.year,
    sourceFile: u.source_file,
    floor: u.details?.floor ?? null,
    seatCount: u.details?.seatCount != null ? Number(u.details.seatCount) : null,
    areaSqm: u.details?.areaSqm != null ? Number(u.details.areaSqm) : null,
    ceilingHeightM: u.details?.ceilingHeightM != null ? Number(u.details.ceilingHeightM) : null,
    attendeeEstimate: u.details?.attendeeEstimate != null ? Number(u.details.attendeeEstimate) : null,
    usageHours: u.details?.usageHours ?? null,
    greenRooms: u.green_rooms,
    equipment: u.equipment,
  };
}

/**
 * GET /api/usage
 * Returns UsageRecord[]
 */
router.get('/', async (req: Request, res: Response) => {
  try {
    const { venueId, roomId } = req.query;

    let query = supabase
      .from('usage_records')
      .select('*')
      .order('date', { ascending: false, nullsFirst: false });

    if (venueId) query = query.eq('venue_id', venueId as string);
    if (roomId) query = query.eq('room_id', roomId as string);

    const { data, error } = await query;
    if (error) throw error;

    res.json((data as UsageRow[]).map(mapUsage));
  } catch (err) {
    console.error('GET /api/usage error:', err);
    res.status(500).json({ error: 'Internal server error' });
  }
});

export default router;
