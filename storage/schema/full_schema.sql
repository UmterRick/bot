CREATE TABLE IF NOT EXISTS categories (
	"id" SERIAL NOT NULL,
	"name" varchar(255) NOT NULL,
	CONSTRAINT "category_pk" PRIMARY KEY ("id")
) WITH (
  OIDS=FALSE
);



CREATE TABLE IF NOT EXISTS courses (
	"id" SERIAL NOT NULL UNIQUE,
	"name" varchar(255) NOT NULL,
	"category" INTEGER NOT NULL,
	"trainer" varchar(255) NOT NULL,
	"link" text default '',
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
	"telegram" INTEGER NOT NULL,
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
	"user" integer NOT NULL,
	"group" integer NOT NULL,
	"type" varchar(255) NOT NULL,
	"push" integer,
	CONSTRAINT "user_group_pk" PRIMARY KEY ("user", "group")
) WITH (
  OIDS=FALSE
);




ALTER TABLE "courses" ADD CONSTRAINT "courses_fk0" FOREIGN KEY ("category") REFERENCES "categories"("id") ON UPDATE CASCADE ON DELETE CASCADE ;

ALTER TABLE "groups" ADD CONSTRAINT "groups_fk0" FOREIGN KEY ("course") REFERENCES "courses"("id") ON UPDATE CASCADE ON DELETE CASCADE ;

ALTER TABLE "user_group" ADD CONSTRAINT "user_group_fk0" FOREIGN KEY ("user") REFERENCES "users"("id");

ALTER TABLE "user_group" ADD CONSTRAINT "user_group_fk1" FOREIGN KEY ("group") REFERENCES "groups"("id");


