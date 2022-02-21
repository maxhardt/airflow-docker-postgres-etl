insert into f_reviews (
    itunes_id,
    podcast_id,
    title,
    content,
    rating,
    author_id,
    created_at
) select
    p.itunes_id,
    r.podcast_id,
    r.title,
    r.content,
    r.rating,
    r.author_id,
    r.created_at
    from s_reviews as r
    left join s_podcasts_kaggle as p
    on r.podcast_id = p.podcast_id
    where p.itunes_id is not null
