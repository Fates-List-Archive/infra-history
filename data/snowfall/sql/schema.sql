CREATE DATABASE fateslist;
\c fateslist
CREATE EXTENSION "uuid-ossp";

-- Maps a fates snowflake to a platform specific id
CREATE TABLE platform_map (
    fates_id DECIMAL NOT NULL,
    platform_id TEXT NOT NULL
);

CREATE TABLE features (
    id text not null,
    name text not null,
    description text not null,
    viewed_as text not null
);

INSERT INTO features VALUES (
    'custom_prefix',
    'Customizable Prefix',
    'positive',
    'This bot supports changing of its prefix and/or has recently migrated to slash commands'
);
INSERT INTO features VALUES (
    'open_source',
    'Open Source',
    'positive',
    'These bots are open source meaning they can easily be audited and/or potentially self hosted'
);
INSERT INTO features VALUES (
    'slash_commands',
    'Slash Commands',
    'critical',
    'These bots support slash commands'
);
INSERT INTO features VALUES (
    'cryptocurrency',
    'Cryptocurrency (NFTs)',
    'negative',
    'These bots offer services related to cryptocurrency which is considered negative by users'
);

CREATE TABLE bots (
    id BIGINT NOT NULL, -- Used by piccolo, must be equal to bot_id
    username_cached text DEFAULT '',
    bot_id bigint not null unique,
    client_id bigint,
    locks integer[] default '{}',
    votes bigint default 0,
    total_votes bigint default 0,
    guild_count bigint DEFAULT 0,
    last_stats_post timestamptz DEFAULT NOW(),
    user_count bigint DEFAULT 0,
    shard_count bigint DEFAULT 0,
    shards integer[] DEFAULT '{}',
    bot_library text,
    webhook_type integer DEFAULT 1,
    webhook text,
    webhook_secret text,
    site_lang TEXT DEFAULT 'default',
    description text,
    long_description text,
    long_description_parsed text,
    long_description_type integer not null default 0,
    page_style integer not null default 0,
    css text default '',
    prefix text,
    features TEXT[] DEFAULT '{}',
    api_token text unique not null,
    website text,
    discord text,
    state integer not null DEFAULT 1,
    banner_card text,
    banner_page text,
    keep_banner_decor boolean default true,
    created_at timestamptz DEFAULT NOW(),
    invite text,
    invite_amount integer DEFAULT 0,
    github TEXT,
    donate text,
    privacy_policy text,
    nsfw boolean DEFAULT false,
    verifier bigint,
    js_allowed BOOLEAN DEFAULT TRUE,
    system boolean default false,
    uptime_checks_total integer default 0,
    uptime_checks_failed integer default 0,
    di_text text
);

CREATE TABLE resources (
    id uuid primary key DEFAULT uuid_generate_v4(),
    target_id BIGINT NOT NULL,
    target_type integer default 0,
    resource_title TEXT NOT NULL,
    resource_link TEXT NOT NULL,
    resource_description TEXT NOT NULL
);

CREATE TABLE bot_list_tags (
    id TEXT NOT NULL UNIQUE,
    icon TEXT NOT NULL UNIQUE
);

CREATE INDEX bot_list_tags_index ON bot_list_tags (id, icon);

CREATE TABLE bot_tags (
    id SERIAL,
    bot_id BIGINT NOT NULL,
    tag TEXT NOT NULL,
    CONSTRAINT bots_fk FOREIGN KEY (bot_id) REFERENCES bots(bot_id) ON DELETE CASCADE ON UPDATE CASCADE,
    CONSTRAINT tags_fk FOREIGN KEY (tag) REFERENCES bot_list_tags(id) ON DELETE CASCADE ON UPDATE CASCADE
);


CREATE TABLE bot_owner (
    _id SERIAL,
    bot_id BIGINT not null,
    owner BIGINT not null,
    main BOOLEAN DEFAULT false,
    CONSTRAINT bots_fk FOREIGN KEY (bot_id) REFERENCES bots(bot_id) ON DELETE CASCADE ON UPDATE CASCADE
);

CREATE TABLE bot_packs (
   id uuid primary key DEFAULT uuid_generate_v4(),
   icon text,
   banner text,
   created_at timestamptz DEFAULT NOW(),
   owner bigint,
   bots bigint[],
   description text,
   name text
);

CREATE TABLE bot_commands (
   id uuid primary key DEFAULT uuid_generate_v4(),
   bot_id bigint,
   cmd_type integer not null, -- 0 = no, 1 = guild, 2 = global
   cmd_groups text[] default '{Default}',
   cmd_name text not null, -- command name
   vote_locked boolean default false, -- friendly name
   description text, -- command description
   args text[], -- list of arguments
   examples text[], -- examples
   premium_only boolean default false, -- premium status
   notes text[], -- notes on said command
   doc_link text, -- link to documentation of command
   CONSTRAINT bots_fk FOREIGN KEY (bot_id) REFERENCES bots(bot_id) ON DELETE CASCADE ON UPDATE CASCADE
);

CREATE TABLE bot_stats_votes_pm (
   bot_id bigint,
   month integer,
   votes bigint
);

CREATE TABLE reviews (
   id uuid primary key DEFAULT uuid_generate_v4(),
   target_id bigint not null,
   target_type integer default 0,
   user_id bigint not null,
   star_rating numeric(4,2) default 0.0,
   review_text text,
   review_upvotes bigint[] default '{}',
   review_downvotes bigint[] default '{}',
   flagged boolean default false,
   epoch bigint[] default '{}',
   replies uuid[] default '{}',
   reply boolean default false,
   CONSTRAINT users_fk FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE ON UPDATE CASCADE
);

create index review_index on reviews (id, target_id, user_id, review_text, review_upvotes, review_downvotes, epoch, replies, target_type, star_rating, flagged, reply);

CREATE TABLE bot_voters (
    bot_id bigint,
    user_id bigint,
    timestamps timestamptz[] DEFAULT '{NOW()}',
    CONSTRAINT bots_fk FOREIGN KEY (bot_id) REFERENCES bots(bot_id) ON DELETE CASCADE ON UPDATE CASCADE
);

CREATE TABLE users (
    id bigint not null, -- Used by piccolo, must be equal to user_id
    user_id bigint not null unique,
    api_token text,
    vote_epoch timestamptz,
    description text DEFAULT 'This user prefers to be an enigma',
    badges text[],
    username text,
    user_css text not null default '',
    profile_css text not null default '',
    state integer default 0, -- 0 = No Ban, 1 = Global Ban
    coins INTEGER DEFAULT 0,
    js_allowed BOOLEAN DEFAULT false,
    vote_reminders bigint[] not null default '{}',
    vote_reminder_channel bigint,
    staff_verify_code text
);

CREATE TABLE user_bot_logs (
    user_id BIGINT NOT NULL,
    bot_id BIGINT NOT NULL,
    action_time timestamptz NOT NULL DEFAULT NOW(),
    action integer not null, -- 0 = approve
    context text, -- Optional context field
    CONSTRAINT users_fk FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE ON UPDATE CASCADE
);

CREATE TABLE user_reminders (
    user_id BIGINT NOT NULL,
    bot_id BIGINT NOT NULL,
    resolved BOOLEAN DEFAULT false,
    remind_time timestamptz NOT NULL DEFAULT NOW() + interval '8 hours',
    CONSTRAINT users_fk FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE ON UPDATE CASCADE,
    CONSTRAINT bots_fk FOREIGN KEY (bot_id) REFERENCES bots(bot_id) ON DELETE CASCADE ON UPDATE CASCADE
);

CREATE TABLE user_payments (
    user_id bigint NOT NULL,
    token TEXT NOT NULL,
    stripe_id TEXT DEFAULT '',
    livemode BOOLEAN DEFAULT FALSE,
    coins INTEGER NOT NULL,
    paid BOOLEAN DEFAULT FALSE
);

CREATE TABLE bot_api_event (
    bot_id BIGINT, 
    ts timestamptz default now(),
    event INTEGER, 
    context JSONB, 
    id UUID,
    posted integer DEFAULT 0,
    CONSTRAINT bots_fk FOREIGN KEY (bot_id) REFERENCES bots(bot_id) ON DELETE CASCADE ON UPDATE CASCADE
);

CREATE TABLE bot_promotions (
   id uuid primary key DEFAULT uuid_generate_v4(),
   bot_id bigint,
   title text,
   info text,
   css text,
   type integer default 3, -- 1 = announcement, 2 = promo, 3 = generic
   CONSTRAINT bots_fk FOREIGN KEY (bot_id) REFERENCES bots(bot_id) ON DELETE CASCADE ON UPDATE CASCADE
);

CREATE TABLE bot_maint (
   id uuid primary key DEFAULT uuid_generate_v4(),
   bot_id bigint,
   reason text,
   type integer,
   epoch bigint,
   CONSTRAINT bots_fk FOREIGN KEY (bot_id) REFERENCES bots(bot_id) ON DELETE CASCADE ON UPDATE CASCADE
);

CREATE TABLE vanity (
    id SERIAL,
    type integer, -- 1 = bot, 2 = profile, 3 = server
    vanity_url text unique, -- This is the text I wish to match
    redirect bigint unique, -- What does this vanity resolve to
    redirect_text text unique-- For the future
);

CREATE TABLE servers (
    guild_id bigint not null unique,
    owner_id bigint not null default 0,
    name_cached text default 'Unlisted',
    avatar_cached text default 'Unlisted',
    votes bigint default 0,   
    total_votes bigint default 0,
    webhook_type integer DEFAULT 1,
    webhook text,
    webhook_secret text,
    description text,
    user_blacklist text[] default '{}',
    user_whitelist text[] default '{}',
    audit_logs jsonb[] default '{}',
    long_description text default 'No long description set! Set one with /settings longdesc Long description',
    long_description_type integer default 0,
    css text default '',
    api_token text unique,
    website text,
    login_required boolean default false,
    created_at timestamptz default now(),
    invite_amount integer DEFAULT 0,
    invite_url text,
    invite_channel text,
    state int not null default 0,
    nsfw boolean default false,
    banner_card text,
    banner_page text,
    keep_banner_decor boolean default true,
    guild_count bigint default 0,
    tags text[] default '{}',
    deleted boolean default false,
    js_allowed boolean default true,
    flags integer[] default '{}',
    autorole_votes bigint[] default '{}'
);

-- In server tags, owner_guild is the first guild a tag was given to
create table server_tags (id TEXT NOT NULL UNIQUE, name TEXT NOT NULL UNIQUE, iconify_data TEXT NOT NULL, owner_guild BIGINT NOT NULL);

-- ULA
CREATE TABLE bot_list_feature (
	feature_id INTEGER PRIMARY KEY,
	name TEXT NOT NULL UNIQUE,
	iname TEXT NOT NULL UNIQUE, -- Internal Name
	description TEXT,
	positive INTEGER
);

CREATE TABLE bot_list_partners (
	id UUID NOT NULL UNIQUE, 
	mod BIGINT NOT NULL,
	partner BIGINT NOT NULL, 
	publish_channel BIGINT, 
	edit_channel BIGINT NOT NULL UNIQUE,
	type INTEGER NOT NULL,
	invite TEXT NOT NULL, 
	user_count BIGINT NOT NULL,
	target BIGINT NOT NULL UNIQUE,
	site_ad TEXT,
	server_ad TEXT,
	created_at timestamptz default now(),
	js_allowed boolean default true,
	published boolean default false
);

CREATE TABLE bot_list (
	icon TEXT,
	url TEXT NOT NULL UNIQUE,
	api_url TEXT,
	api_docs TEXT,
	discord TEXT,
	description TEXT,
	no_post boolean default false,
	supported_features INTEGER[],
	state INTEGER DEFAULT 0,
	owners BIGINT[] DEFAULT '{}'
);

CREATE TABLE bot_list_feature (
	feature_id INTEGER PRIMARY KEY,
	name TEXT NOT NULL UNIQUE,
	iname TEXT NOT NULL UNIQUE, -- Internal Name
	description TEXT,
	positive INTEGER
);

CREATE TABLE bot_list_api (
	id SERIAL PRIMARY KEY, -- Django'isms and good for us
	url TEXT NOT NULL,
	method INTEGER, -- 1 = GET, 2 = POST, 3 = PATCH, 4 = PUT, 5 = DELETE
	feature INTEGER, -- 1 = Get Bot, 2 = Post Stats
	supported_fields JSONB, -- Supported fields
	api_path TEXT NOT NULL,
	CONSTRAINT url_constraint FOREIGN KEY (url) REFERENCES bot_list(url) ON DELETE CASCADE ON UPDATE CASCADE -- Autoupdate
);

CREATE TABLE manager_staff (user_id BIGINT, user_token TEXT NOT NULL UNIQUE);
