CREATE TABLE IF NOT EXISTS courses (
        id	INTEGER NOT NULL AUTO_INCREMENT,
        hash_name TEXT NOT NULL,
        category_id INTEGER NOT NULL,
        name   VARCHAR(255) NOT NULL,
        trainer	VARCHAR(255) NOT NULL,
        description	TEXT,
        price	INTEGER NOT NULL DEFAULT 0,
        category_name VARCHAR(45) NOT NULL,
        hash_category VARCHAR(50) NOT NULL,
        PRIMARY KEY(category_id, id)