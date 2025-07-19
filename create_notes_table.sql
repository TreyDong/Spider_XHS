-- auto-generated definition
create table notes
(
    note_id             varchar(100) not null
        primary key,
    user_id             varchar(100) not null,
    type                varchar(20)  not null,
    title               text         not null,
    liked_count         integer   default 0,
    comments_count      integer   default 0,
    collected_count     integer   default 0,
    shared_count        integer   default 0,
    cover_url           text,
    video_url           text,
    nick_name           text,
    url                 text,
    raw_data            jsonb,
    image_list          jsonb,
    publish_time        timestamp,
    last_update_time    timestamp,
    created_at          timestamp default CURRENT_TIMESTAMP,
    updated_at          timestamp default CURRENT_TIMESTAMP,
    video_text          text,
    video_transfer_flag integer   default 0,
    collection_status   varchar(20),
    collection_error    text
);

alter table notes
    owner to postgres;

create index idx_notes_comments_count
    on notes (user_id asc, comments_count desc);

create index idx_notes_liked_count
    on notes (user_id asc, liked_count desc);

create index idx_notes_publish_time
    on notes (user_id asc, publish_time desc);

create index idx_notes_type
    on notes (user_id, type);

create index idx_notes_user_id
    on notes (user_id);

