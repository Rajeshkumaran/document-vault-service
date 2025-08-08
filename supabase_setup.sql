-- Create documents table in Supabase
-- Run this SQL in your Supabase SQL editor

CREATE TABLE IF NOT EXISTS public.documents (
    id BIGSERIAL PRIMARY KEY,
    filename VARCHAR(255) NOT NULL,
    original_filename VARCHAR(255) NOT NULL,
    content_type VARCHAR(100) NOT NULL,
    file_size INTEGER NOT NULL,
    file_path VARCHAR(500) NOT NULL,
    storage_path VARCHAR(500),
    description TEXT,
    tags JSONB,
    is_active BOOLEAN NOT NULL DEFAULT true,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT timezone('utc'::text, now()) NOT NULL,
    updated_at TIMESTAMP WITH TIME ZONE
);

-- Create indexes for better performance
CREATE INDEX IF NOT EXISTS idx_documents_is_active ON public.documents(is_active);
CREATE INDEX IF NOT EXISTS idx_documents_created_at ON public.documents(created_at);
CREATE INDEX IF NOT EXISTS idx_documents_filename ON public.documents(original_filename);
CREATE INDEX IF NOT EXISTS idx_documents_tags ON public.documents USING GIN(tags);

-- Enable Row Level Security (RLS)
ALTER TABLE public.documents ENABLE ROW LEVEL SECURITY;

-- Create a policy that allows all operations for authenticated users
-- You can modify this based on your security requirements
CREATE POLICY "Enable all operations for authenticated users" ON public.documents
    FOR ALL USING (auth.role() = 'authenticated');

-- Create a policy for anonymous users (if needed)
-- CREATE POLICY "Enable read access for anonymous users" ON public.documents
--     FOR SELECT USING (is_active = true);

-- Create storage bucket for documents
-- Run this in the Supabase Storage section
-- INSERT INTO storage.buckets (id, name, public) VALUES ('documents', 'documents', false);

-- Create storage policy for documents bucket
-- CREATE POLICY "Enable upload for authenticated users" ON storage.objects
--     FOR INSERT WITH CHECK (bucket_id = 'documents' AND auth.role() = 'authenticated');

-- CREATE POLICY "Enable download for authenticated users" ON storage.objects
--     FOR SELECT USING (bucket_id = 'documents' AND auth.role() = 'authenticated');

-- CREATE POLICY "Enable delete for authenticated users" ON storage.objects
--     FOR DELETE USING (bucket_id = 'documents' AND auth.role() = 'authenticated');
