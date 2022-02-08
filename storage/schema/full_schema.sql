CREATE TABLE IF NOT EXISTS categories (
	"id" SERIAL NOT NULL,
	"name" varchar(255) NOT NULL UNIQUE ,
	CONSTRAINT "category_pk" PRIMARY KEY ("id")
) WITH (
  OIDS=FALSE
);



CREATE TABLE IF NOT EXISTS courses (
	"id" SERIAL NOT NULL UNIQUE,
	"name" varchar(255) NOT NULL UNIQUE ,
	"category" INTEGER NOT NULL,
	"trainer" varchar(255) NOT NULL,
	"link" text default 'google.com',
	"description" TEXT NOT NULL,
	"price" integer NOT NULL,
	CONSTRAINT "courses_pk" PRIMARY KEY ("id", "name")
) WITH (
  OIDS=FALSE
);



CREATE TABLE IF NOT EXISTS groups (
	"id" SERIAL NOT NULL UNIQUE ,
	"stream" INTEGER NOT NULL,
	"day" TEXT NOT NULL,
	"program_day" varchar(40),
	"time" time NOT NULL ,
	"type" BOOLEAN NOT NULL,
	"course" INTEGER NOT NULL,
	"chat" varchar(255),
	CONSTRAINT "groups_pk" PRIMARY KEY ("id")
) WITH (
  OIDS=FALSE
);



CREATE TABLE IF NOT EXISTS users (
	"id" SERIAL NOT NULL UNIQUE ,
	"name" varchar(255) NOT NULL,
	"nickname" varchar(255) NOT NULL,
	"telegram" BIGINT NOT NULL,
	"contact" varchar(40),
	"type" integer NOT NULL,
	"state" TEXT NOT NULL,
	"at_category" INTEGER ,
	"temp_state_1" varchar(255) ,
	"temp_state_2" varchar(255),
	CONSTRAINT "users_pk" PRIMARY KEY ("id")
) WITH (
  OIDS=FALSE
);


CREATE TABLE IF NOT EXISTS user_group (
    "id" SERIAL NOT NULL UNIQUE ,
	"user_id" integer NOT NULL,
	"group_id" integer NOT NULL,
	"type" varchar(255) NOT NULL,
	"push" integer DEFAULT -1,
	CONSTRAINT "user_group_pk" PRIMARY KEY ("user_id", "group_id", "type")
) WITH (
  OIDS=FALSE
);


CREATE TABLE IF NOT EXISTS user_login (

    id         serial
        constraint user_login_pkey
            primary key,
    first_name varchar(100),
    last_name  varchar(100),
    login      varchar(80)
        constraint user_login_login_key
            unique,
    email      varchar(120),
    password   varchar(255)
);


ALTER TABLE "courses" DROP CONSTRAINT IF EXISTS "courses_fk0";
ALTER TABLE "courses" ADD CONSTRAINT  "courses_fk0" FOREIGN KEY ("category") REFERENCES "categories"("id") ON UPDATE CASCADE ON DELETE CASCADE;

ALTER TABLE "groups" DROP CONSTRAINT IF EXISTS "groups_fk0";
ALTER TABLE "groups" ADD CONSTRAINT "groups_fk0" FOREIGN KEY ("course") REFERENCES "courses"("id") ON UPDATE CASCADE ON DELETE CASCADE ;

ALTER TABLE "user_group" DROP CONSTRAINT IF EXISTS "user_group_fk0";
ALTER TABLE "user_group" ADD CONSTRAINT "user_group_fk0" FOREIGN KEY (user_id) REFERENCES "users"("id");

ALTER TABLE "user_group" DROP CONSTRAINT IF EXISTS "user_group_fk1";
ALTER TABLE "user_group" ADD CONSTRAINT "user_group_fk1" FOREIGN KEY (group_id) REFERENCES "groups"("id");


