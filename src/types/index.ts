export type Region = '東京' | '大阪' | '名古屋' | '福岡' | '京都' | '横浜' | '神戸' | '札幌' | '仙台' | '千葉';

export interface Capacity {
  theater?: number;
  school?: number;
  banquet?: number;
  standing?: number;
  max?: number;
}

export interface Division {
  name: string;
  areaSqm?: number;
  ceilingHeightM?: number;
  capacity: Capacity;
}

export interface Room {
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

export interface PracticalInfo {
  loadingDockSize?: string;
  loadingRoute?: string;
  waitingRoom?: string;
  catering?: string;
  priceGuide?: string;
  wifi?: string;
  avEquipment?: string;
  nearestStation?: string;
  contactPhone?: string;
  parking?: string;
  venuePageUrl?: string;
  floorPlanUrl?: string;
  brochureUrl?: string;
}

export interface Hotel {
  id: string;
  name: string;
  address: string;
  region: Region;
  totalRoomCount?: string;
  rooms: Room[];
  practicalInfo?: PracticalInfo;
  lat?: number;
  lng?: number;
  usageCount?: number;
}

export interface GreenRoom {
  name: string;
  areaSqm?: number;
  purpose: string;
}

export interface UsageRecord {
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
  greenRooms?: GreenRoom[];
  equipment?: string[];
  usageHours?: string;
  attendeeEstimate?: number;
  sourceFile: string;
}

export type CapacityType = 'theater' | 'school' | 'banquet' | 'standing';

export interface FilterState {
  keyword: string;
  regions: Region[];
  areaMin?: number;
  areaMax?: number;
  ceilingMin?: number;
  ceilingMax?: number;
  capacityMin?: number;
  capacityMax?: number;
  capacityType: CapacityType;
  hasDivisions: boolean | null;
  hasUsageRecords: boolean | null;
}
