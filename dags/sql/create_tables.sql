create table if not exists f_reviews (
    review_id serial primary key,
    itunes_id varchar not null,
    podcast_id varchar not null,
    title varchar,
    content varchar,
    rating float,
    author_id varchar,
    created_at timestamp
);

create table if not exists d_podcasts (
    itunes_id varchar not null primary key,
    podcast_id varchar not null,
    -- from s_podcasts_kaggle
    slug varchar,
    title varchar,
    -- from s_podcasts_itunes
    artist_name varchar not null,
    price float,
    genres varchar [],
    primary_genre varchar,
    explicitness varchar,
    advisory_rating varchar,
    track_count integer,
    country varchar,
    release_date timestamp
);

create table if not exists s_reviews (
    review_id serial primary key,
    podcast_id varchar not null,
    title varchar,
    content varchar,
    rating float,
    author_id varchar,
    created_at timestamp
);

create table if not exists s_categories (
    podcast_id varchar not null,
    category varchar
);

create table if not exists s_podcasts_kaggle (
    podcast_id varchar not null,
    itunes_id varchar not null,
    slug varchar,
    itunes_url varchar,
    title varchar
);

create table if not exists s_podcasts_itunes (
    metadata_staging_id serial primary key,
    metadata jsonb not null
);
