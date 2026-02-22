import { readFileSync } from 'fs';
import { join } from 'path';
import express from 'express';
import venuesRouter from './routes/venues.js';
import usageRouter from './routes/usage.js';

// Load .env manually (no dotenv dependency needed for simple case)
try {
  const envPath = join(import.meta.dirname, '..', '.env');
  const envContent = readFileSync(envPath, 'utf-8');
  for (const line of envContent.split('\n')) {
    const trimmed = line.trim();
    if (!trimmed || trimmed.startsWith('#')) continue;
    const eqIdx = trimmed.indexOf('=');
    if (eqIdx === -1) continue;
    const key = trimmed.slice(0, eqIdx);
    const val = trimmed.slice(eqIdx + 1);
    if (!process.env[key]) process.env[key] = val;
  }
} catch {
  // .env not found, use defaults
}

const app = express();
const PORT = Number(process.env.PORT) || 3456;

app.use('/api/venues', venuesRouter);
app.use('/api/usage', usageRouter);

app.get('/api/health', (_req, res) => {
  res.json({ status: 'ok' });
});

app.listen(PORT, () => {
  console.log(`venue-search-api listening on port ${PORT}`);
});
