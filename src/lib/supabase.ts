import { createClient } from '@supabase/supabase-js'

const SUPABASE_URL = import.meta.env.VITE_SUPABASE_URL || 'https://kgaqsazjzrvrzsuiavri.supabase.co'
const SUPABASE_ANON_KEY = import.meta.env.VITE_SUPABASE_ANON_KEY || 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImtnYXFzYXpqenJ2cnpzdWlhdnJpIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NTE3MTUxODksImV4cCI6MjA2NzI5MTE4OX0.U8lmSOsf-x4dlgcVxtGZjyu2VlPgfiNpaQqqn-N0SrE'

export const supabase = createClient(SUPABASE_URL, SUPABASE_ANON_KEY)
