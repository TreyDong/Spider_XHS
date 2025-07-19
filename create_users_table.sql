-- auto-generated definition
create table users
(
    user_id                 varchar(100) not null
        primary key,
    nickname                varchar(200),
    avatar                  varchar(500),
    created_at              timestamp default CURRENT_TIMESTAMP,
    updated_at              timestamp default CURRENT_TIMESTAMP,
    fans_count              integer   default 0,
    likes_collections_count integer   default 0,
    notes_count             integer   default 0,
    location                varchar(255),
    description             text
);

alter table users
    owner to postgres;

