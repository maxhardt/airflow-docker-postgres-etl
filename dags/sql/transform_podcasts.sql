insert into d_podcasts (
    itunes_id,
    podcast_id,
    slug,
    title,
    artist_name,
    price,
    genres,
    primary_genre,
    explicitness,
    advisory_rating,
    track_count,
    country,
    release_date
) select
    i.metadata->>'collectionId' as itunes_id,
    k.podcast_id as podcast_id,
    k.slug as slug,
    k.title as title,
    i.metadata->>'artistName' as artist_name,
    cast(i.metadata->>'collectionPrice' as float) as price,
    string_to_array(replace(replace(i.metadata->>'genres', '[', ''), ']',''), ',') as genres,
    i.metadata->>'primaryGenreName' as primary_genre,
    i.metadata->>'collectionExplicitness' as explicitness,
    i.metadata->>'contentAdvisoryRating' as advisory_rating,
    cast(i.metadata->>'trackCount' as integer) as track_count,
    i.metadata->>'country' as country,
    cast(i.metadata->>'releaseDate' as timestamp) as release_date
    from s_podcasts_itunes as i
    left join s_podcasts_kaggle as k
    on i.metadata->>'collectionId' = k.itunes_id
    where i.metadata->>'collectionId' is not null
