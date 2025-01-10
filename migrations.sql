-- Create lecture table
CREATE TABLE public.lectures (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES public.users(id),
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT now(),
    updated_at TIMESTAMP WITH TIME ZONE,
    topic TEXT,
    resources TEXT,
    title TEXT,
    status TEXT NOT NULL DEFAULT 'draft',
    voice_id TEXT,
    language TEXT,
    video_url TEXT,
    subtitles_url TEXT,
    thumbnail_url TEXT
);

-- Create scene table
CREATE TABLE public.scenes (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES public.users(id),
    lecture_id UUID NOT NULL REFERENCES public.lecture(id),
    index INTEGER NOT NULL,
    version INTEGER NOT NULL DEFAULT 1,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT now(),
    updated_at TIMESTAMP WITH TIME ZONE,
    description TEXT,
    voiceover TEXT,
    user_prompt TEXT,
    code TEXT,
    audio_url TEXT,
    video_url TEXT
);

-- Create indexes for common queries
CREATE INDEX lecture_user_id_idx ON public.lecture(user_id);
CREATE INDEX scene_user_id_idx ON public.scene(user_id);
CREATE INDEX scene_lecture_id_idx ON public.scene(lecture_id);
CREATE INDEX scene_index_idx ON public.scene(lecture_id, index); 