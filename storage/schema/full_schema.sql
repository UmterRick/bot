CREATE TABLE IF NOT EXISTS categories (
	"hash" varchar(255) NOT NULL,
	"name" varchar(255) NOT NULL,
	CONSTRAINT "category_pk" PRIMARY KEY ("hash")
) WITH (
  OIDS=FALSE
);



CREATE TABLE IF NOT EXISTS courses (
	"hash" varchar(255) NOT NULL,
	"name" varchar(255) NOT NULL,
	"category" varchar(255) NOT NULL,
	"trainer" varchar(255) NOT NULL,
	"description" TEXT NOT NULL,
	"price" integer NOT NULL,
	CONSTRAINT "courses_pk" PRIMARY KEY ("hash")
) WITH (
  OIDS=FALSE
);



CREATE TABLE IF NOT EXISTS groups (
	"id" serial NOT NULL,
	"daytime" TEXT NOT NULL,
	"type" BOOLEAN NOT NULL,
	"course" varchar(255) NOT NULL,
	"chat" varchar(255) NOT NULL,
	CONSTRAINT "groups_pk" PRIMARY KEY ("id")
) WITH (
  OIDS=FALSE
);



CREATE TABLE IF NOT EXISTS users (
	"id" serial NOT NULL,
	"name" varchar(255) NOT NULL,
	"nickname" varchar(255) NOT NULL,
	"telegram" varchar(255) NOT NULL,
	"type" integer NOT NULL,
	"state" varchar(255) NOT NULL,
	"at_category" varchar(255) NOT NULL,
	"temp_state_1" varchar(255) NOT NULL,
	"temp_state_2" varchar(255) NOT NULL,
	CONSTRAINT "users_pk" PRIMARY KEY ("id")
) WITH (
  OIDS=FALSE
);




ALTER TABLE "courses" ADD CONSTRAINT "courses_fk0" FOREIGN KEY ("category") REFERENCES "categories"("hash") ON UPDATE CASCADE ON DELETE CASCADE ;

ALTER TABLE "groups" ADD CONSTRAINT "groups_fk0" FOREIGN KEY ("course") REFERENCES "courses"("hash") ON UPDATE CASCADE ON DELETE CASCADE ;

ALTER TABLE "users" ADD CONSTRAINT "users_fk0" FOREIGN KEY ("id") REFERENCES "groups"("id") ON UPDATE CASCADE ON DELETE CASCADE ;




