import collections
import hashlib

import mysql.connector
import requests
from bs4 import BeautifulSoup

from configs import *


def get_html(url, params=None):
    r = requests.get(url, headers=HEADERS, params=params)
    print('Wrong code status') if r.status_code != 200 else None
    return r


TABLES = dict()

TABLES['courses'] = ('''
        CREATE TABLE IF NOT EXISTS courses (
        id	INTEGER NOT NULL AUTO_INCREMENT,
        hash_name TEXT NOT NULL,
        category_id INTEGER NOT NULL ,
        name   TEXT NOT NULL,
        teacher	TEXT NOT NULL,
        description	TEXT,
        price	INTEGER NOT NULL DEFAULT 0,
        category_name VARCHAR(45) NOT NULL,
        hash_category VARCHAR(50) NOT NULL,
        PRIMARY KEY(category_id, id)
        )ENGINE = MYISAM;''')
TABLES['groups'] = ('''  
            CREATE TABLE IF NOT EXISTS groups (
              id INT(11) NOT NULL AUTO_INCREMENT,
              daytime TEXT NOT NULL,
              offline INT(11) NULL DEFAULT NULL,
              course_hash VARCHAR(256) NOT NULL,
              telegram_chat VARCHAR(256),

              PRIMARY KEY (id)
              )ENGINE = InnoDB;
            ''')
TABLES['group_trigger'] = ('''
                CREATE
                TRIGGER update_group AFTER UPDATE 
                ON courses
                FOR EACH ROW 
                    BEGIN
                       UPDATE groups SET category_id = NEW.category_id WHERE category_id = OLD.category_id;
                       UPDATE groups SET course_id = NEW.id WHERE course_id = OLD.id;
                    END;
            ''')
TABLES['users'] = ('''
        CREATE TABLE  IF NOT EXISTS users (
            id INTEGER NOT NULL PRIMARY KEY AUTO_INCREMENT,
            telegram_id VARCHAR(45) NOT NULL UNIQUE,
            name TEXT NOT NULL,
            nickname VARCHAR(45),
            user_type VARCHAR(45) DEFAULT 'non_type',
            group_id VARCHAR(45) DEFAULT '',
            enroll VARCHAR(45) DEFAULT '',
            trainer_group VARCHAR(45) DEFAULT '',
            contacts VARCHAR(45) DEFAULT 'empty_number',
            user_state VARCHAR(45) NOT NULL,
            temp TEXT,
            temp_2 TEXT,
            viewing_category VARCHAR(100)            
            );  
            ''')
TABLES['notifications'] = ('''
        CREATE TABLE IF NOT EXISTS notifications (
        id INTEGER NOT NULL PRIMARY KEY AUTO_INCREMENT,
        group_id INTEGER NOT NULL,
        datetime VARCHAR(45) NOT NULL,
        status VARCHAR(45) NOT NULL DEFAULT 'wait');
        ''')
TABLES['logging'] = ('''
        CREATE TABLE IF NOT EXISTS logging (
        id INTEGER NOT NULL PRIMARY KEY AUTO_INCREMENT,
        log_type TEXT NOT NULL,
        telegram_id TEXT NOT NULL,
        user_name TEXT NOT NULL, 
        log_content TEXT NOT NULL, 
        log_time DATETIME NOT NULL)
                    ''')


def get_content(html_, flag=None):
    topics = dict()
    hash_dict = dict()
    courses_id = dict()
    try:
        soup = BeautifulSoup(html_.text, 'html.parser')
        items = soup.find_all('div', class_='content')
        topics_search = soup.find_all('div', class_='short')
        counter = 1
        for topic in topics_search:
            topics[counter] = topic.text
            counter += 1

        for block_id in range(1, len(topics.keys()) + 1):
            names = items[block_id - 1].find_all('p')
            links = items[block_id - 1].find_all('a')
            course_id = 1
            for name in names:
                if str(name.text).startswith('ᐅ'):
                    name = str(name.text).replace('ᐅ ', '')
                    if '(' in name:
                        body = name[0:name.find('(')]
                        trainer = name[name.find('(') + 1:name.find(')')]
                    else:
                        body = name[0:name.find('👉')]
                        trainer = '----'
                    hashed_name = hashlib.md5(body.strip().encode())
                    hashed_category = hashlib.md5(topics[block_id].strip().encode())
                    hash_dict[hashed_name.hexdigest()] = body
                    if flag == 'write':
                        DataBase().addCourse(
                            hashed_name.hexdigest(),
                            block_id,
                            body,
                            trainer,
                            links[course_id - 1].get('href'),
                            topics[block_id],
                            str(hashed_category.hexdigest()))
                    course_id += 1
        if flag == 'topics':
            return topics
        elif flag == 'courses_id':
            return courses_id
        elif flag == 'hash_dict':
            return hash_dict
        else:
            return 0
    except TypeError:
        print('GetContent type error')


html = requests.get(C_URL, headers=HEADERS)


class DataBase:

    def __init__(self):
        self.name = DB_NAME
        try:

            self.db = mysql.connector.connect(
                host=host,
                port=port,
                user=db_user,
                passwd=db_passwd,
                database=self.name)
            self.cursor = self.db.cursor()
            print('database exists')
        except mysql.connector.Error:
            print('creating database')
            self.db = mysql.connector.connect(
                host=host,
                user=db_user,
                password=db_passwd
            )
            self.cursor = self.db.cursor()
            self.cursor.execute(f"CREATE DATABASE {self.name}")

    def connect(self):
        self.db = mysql.connector.connect(
            host=host,
            port=port,
            user=db_user,
            passwd=db_passwd,
            database=self.name)
        self.cursor = self.db.cursor()
        return self.db

    def close(self):
        if self.db.is_connected():
            self.cursor.close()
            self.db.close()

    def createTables(self):
        try:
            for table_name in TABLES:
                table_description = TABLES[table_name]
                try:
                    self.cursor.execute(table_description)
                    print(f"INFO: Creating table {table_name}: ", end='\n')
                except mysql.connector.Error as err:
                    print(f'ERR: Creating table {table_name}:', err.msg)
        except ValueError:
            PrintException()
        finally:
            self.db.commit()

    def checkTables(self):
        self.cursor = self.db.cursor()
        now_tables = list()
        static_tables = ['courses', 'groups', 'notifications', 'users', 'logging']
        command = f"SHOW TABLES FROM {self.name};"
        self.cursor.execute(command)
        result = self.cursor.fetchall()
        for table in result:
            now_tables.append(table[0])
        if collections.Counter(now_tables) == collections.Counter(static_tables):
            flag = True
        else:
            print(f'Table {list(set(static_tables) - set(now_tables))} is NOT FOUND')
            flag = False

        return flag
#fnsdcsd,
    def saveLog(self, chat_id, user_name, log_type, log_content):
        try:
            self.cursor = self.db.cursor()

            log_time = datetime.now().strftime('%y/%m/%d %H:%M:%S')
            command = "INSERT INTO logging (log_type, telegram_id, user_name, log_content, log_time) " \
                      f"VALUES('{log_type}', '{chat_id}', '{user_name}', ('{log_content}'), '{log_time}');"
            self.cursor.execute(command)
            self.db.commit()
        except mysql.connector.Error as err:
            print(f'Save_log err:', err.msg)

    def addCourse(self, hash_name: str, category_id, course_name, course_trainer, course_description, category_name,
                  hash_category):
        # hash_name, category_id, name , teacher,   description,   price,    category_name,    hash_category

        new_course = ('''INSERT INTO courses
                (hash_name, category_id, name, teacher, description, category_name, hash_category )
                VALUES (%s, %s, %s, %s, %s, %s, %s);
                ''')
        course_data = (
            hash_name, category_id, course_name, course_trainer, course_description, category_name, hash_category)
        try:
            self.cursor = self.db.cursor()

            self.cursor.execute(new_course, course_data)
            self.db.commit()
        except mysql.connector.Error as err:
            print(f'DataBase.addCourse() err:', err.msg)

    def update(self):
        update_flag = False
        hash_list = list()
        fresh_hash = list()

        try:
            new_hash = get_content(html, 'hash_dict')
            self.cursor = self.db.cursor()

            self.cursor.execute('select hash_name from courses')
            records = self.cursor.fetchall()
            for item in records:
                hash_list.append(item[0])
            for key in new_hash.keys():
                fresh_hash.append(key)
            if len(hash_list) == len(fresh_hash):
                if collections.Counter(hash_list) == collections.Counter(fresh_hash):
                    print('INFO: There is no need to update')
                else:
                    print(f'WARN: DataBase is updating from site, find new unresolved course hash')
                    update_flag = True
            else:
                update_flag = True
                print(f'WARN: DataBase is updating from site, find new unresolved course hash')

            if update_flag:
                try:
                    print('trunc')
                    self.cursor.execute('TRUNCATE `courses`')
                    self.db.commit()
                except mysql.connector.Error as err:
                    print(err)
                get_content(html, 'write')

            del records, hash_list, fresh_hash, new_hash
        except:
            self.connect()
            PrintException()

    def get_trainers(self, category=None):
        trainers = dict()

        command_0 = f'SELECT hash_name, teacher, name, description, category_name FROM courses where category_id = {category}'
        command_1 = f'SELECT hash_name, teacher, name, description, category_name FROM courses'
        command_2 = f'SELECT id FROM groups WHERE course_hash = %s'
        self.cursor = self.db.cursor()
        if category is None:
            self.cursor.execute(command_1)
        else:
            self.cursor.execute(command_0)

        records = self.cursor.fetchall()

        for row in records:
            temp = list()

            self.cursor.execute(command_2, (row[0],))
            groups = self.cursor.fetchall()
            names = row[1].split(',')

            if len(groups) > 0:
                for group in groups:
                    temp.append(group[0])
                groups = temp
                print('groups = ', groups)
            else:
                print('groups = ', groups)

            if len(names) > 1:
                for name in names:

                    name = str(name).strip()
                    if trainers.get(name) is None:
                        trainers[name] = {row[0]: {'name': row[2], 'groups': groups}}
                    else:
                        trainers[name].update({row[0]: {'name': row[2], 'groups': groups}})

            else:
                name = str(names[0]).strip()
                if trainers.get(name) is None:
                    trainers[name] = {row[0]: {'name': row[2], 'groups': groups}}
                else:
                    trainers[name].update(
                        {row[0]: {'name': row[2], 'groups': groups}})  # for row in records:  hash_name, teacher

        try:
            None
        except mysql.connector.Error as err:
            print(f'DataBase.get_trainers err:', err.msg)
        except:
            PrintException()
        finally:
            self.db.commit()
            return trainers

    def getTopics(self):
        topics = dict()
        command = 'SELECT category_name, hash_category FROM courses'
        try:
            self.cursor = self.db.cursor()
            self.cursor.execute(command)
            records = self.cursor.fetchall()
            for row in records:
                topics[row[0]] = row[1]
        except mysql.connector.Error as err:
            print(f'ERROR DataBase.getTopics(): {err}')
        except:
            PrintException()
        return topics

    def getCourses(self, category=None, course=None):
        command1 = 'SELECT * FROM courses '
        command2 = f"SELECT * FROM courses where (`hash_category` = '{category}');"
        command3 = f"SELECT * FROM courses where (`hash_name` = '{course}');"

        courses = dict()
        try:
            self.cursor = self.db.cursor()
            if category is not None:
                self.cursor.execute(command2)
            elif course is not None:
                self.cursor.execute(command3)
            else:
                self.cursor.execute(command1)

            records = self.cursor.fetchall()
            for row in records:
                courses[row[1]] = {
                    'name': row[3],
                    'trainer': row[4],
                    'link': row[5],
                    'category': row[7],

                }
        except mysql.connector.Error as err:
            print(f'ERROR DataBase.getCourses(): {err}')
        except:
            PrintException()

        return courses

    def getLog(self):
        log = dict()
        command = 'SELECT * from logging'
        command_2 = 'truncate logging'
        try:
            self.cursor = self.db.cursor()
            self.cursor.execute(command)
            records = self.cursor.fetchall()
            for row in records:
                log[row[0]] = {
                    'type': row[1],
                    'user_id': row[2],
                    'user_name': row[3],
                    'content': row[4],
                    'time': row[5]
                }
            self.cursor.execute(command_2)
            self.db.commit()
            return log
        except mysql.connector.Error as err:
            print(f'ERROR DataBase.getLog(): {err}')


class Group:
    def __init__(self):
        self.name = DB_NAME
        try:
            self.db = mysql.connector.connect(
                host=host,
                port=port,
                user=db_user,
                passwd=db_passwd,
                database=self.name)
            self.cursor = self.db.cursor()
            self.group = 0
            self.group_chat = 0
        except mysql.connector.Error:
            self.db = mysql.connector.connect(
                host=host,
                user=db_user,
                password=db_passwd
            )
            self.cursor = self.db.cursor()
            self.cursor.execute(f"CREATE DATABASE {self.name}")

    def connect(self):
        self.db = mysql.connector.connect(
            host=host,
            port=port,
            user=db_user,
            passwd=db_passwd,
            database=self.name)
        self.cursor = self.db.cursor()
        return self.db

    def close(self):
        if self.db.is_connected():
            self.db.close()
            self.cursor.close()

    def read(self, arg=None):

        groups = dict()
        command = ''
        command_1 = f'select * from groups where id = {arg}'
        command_2 = f"select * from groups where (`course_hash` = '{arg}');"
        command_3 = f"select * from groups"
        try:
            try:
                if arg is not None:
                    arg = int(arg)
                    command = command_1
            except ValueError:
                if arg is not None:
                    command = command_2
            finally:
                if arg is None:
                    command = command_3
            self.cursor = self.db.cursor()
            self.cursor.execute(command)
            records = self.cursor.fetchall()
            for row in records:
                groups[row[0]] = {
                    'daytime': row[1],
                    'offline': row[2],
                    'course_hash': row[3],
                    'chat': row[4]
                }
        except mysql.connector.Error as err:
            print("ERROR Groups.read() ", err)
        return groups

    def toCourse(self, course):
        groups = dict()
        command = f"select * from groups where (`course_hash` = '{course}');"
        try:
            self.cursor = self.db.cursor()
            self.cursor.execute(command)
            records = self.cursor.fetchall()
            for row in records:
                groups[row[0]] = {
                    'daytime': row[1],
                    'offline': row[2],
                    'course_hash': row[3]
                }
        except mysql.connector.Error as err:
            print(f'ERROR Group.toCourse(): {err}')

        finally:
            return groups

    def add(self, daytime, type_, course_hash):
        command_1 = f"insert into groups (daytime ,offline, course_hash) values (%s, %s, %s)"
        try:
            self.cursor = self.db.cursor()
            self.cursor.execute(command_1, (daytime, type_, course_hash,))
            self.db.commit()

        except mysql.connector.Error as err:
            print('ERROR Group.add(): ', err.msg)

    def edit(self, group_id, new_type, new_daytime):
        command = f"update groups set daytime = '{new_daytime}', offline = {new_type} where id = {group_id}"
        try:
            self.cursor = self.db.cursor()
            self.cursor.execute(command)
            self.db.commit()
        except mysql.connector.Error as err:
            print(f'ERROR Group.edit() :', err)

    def delete(self, g_id):
        start = time.time()
        command_1 = f'delete from groups where id = {g_id}'
        command_2 = 'select telegram_id, group_id from users'
        command_3 = 'select telegram_id, enroll from users'
        command_4 = 'select telegram_id, trainer_group from users'

        try:
            try:
                self.cursor = self.db.cursor()
                self.cursor.execute(command_1)
            except mysql.connector.Error as err:
                print(f'ERROR Group.delete() command_1 : {err}')
            try:
                self.cursor.execute(command_2)
                records = self.cursor.fetchall()
                for row in records:
                    groups = str_to_list(row[1])
                    if g_id in groups:
                        groups.remove(g_id)
                    if len(groups) == 0:
                        new_groups = ''
                    else:
                        new_groups = str(groups)[1:-1]
                    User.tempVar(User(), row[0], 'group_id', new_groups)
            except mysql.connector.Error as err:
                print(f'ERROR Group.delete() command_2 : {err}')

            try:
                self.cursor.execute(command_3)
                records = self.cursor.fetchall()
                for row in records:
                    enrolls = str_to_list(row[1])
                    if g_id in enrolls:
                        enrolls.remove(g_id)
                    if len(enrolls) == 0:
                        new_enrolls = ''
                    else:
                        new_enrolls = str(enrolls)[1:-1]
                    User.tempVar(User(), row[0], 'enroll', new_enrolls)
            except mysql.connector.Error as err:
                print(f'ERROR Group.delete() command_3 : {err}')
            try:
                self.cursor.execute(command_4)
                records = self.cursor.fetchall()
                for row in records:
                    trainer_group = str_to_list(row[1])
                    if g_id in trainer_group:
                        trainer_group.remove(g_id)
                    if len(trainer_group) == 0:
                        new_trainer_group = ''
                    else:
                        new_trainer_group = str(trainer_group)[1:-1]
                    User.tempVar(User(), row[0], 'trainer_group', new_trainer_group)
            except mysql.connector.Error as err:
                print(f'ERROR Group.delete() command_4 : {err}')
        except:
            PrintException()
        finally:
            self.db.commit()
            print(f'Group was deleted in {round((time.time() - start) * 1000, 2)} ms')

    def getStudents(self, group_id):
        users = list()
        names = dict()
        command_1 = 'select telegram_id, group_id from users'
        command_2 = 'select name from users where telegram_id = %s'
        try:
            group_id = int(group_id)
        except:
            group_id = -1
            print('Group ID must be an integer or could be transform to that')
            return
        try:
            self.cursor = self.db.cursor()
            self.cursor.execute(command_1)
            records = self.cursor.fetchall()
            for row in records:
                groups = str_to_list(row[1])
                users.append(row[0]) if group_id in groups else None
            print(users)
        except mysql.connector.Error as err:
            print(f'ERROR Group.getStudents() 1: {err}')
        except:
            PrintException()
            users = list()
        try:
            for user in users:
                self.cursor.execute(command_2, (user,))
                record = self.cursor.fetchone()
                names[user] = record[0]
        except mysql.connector.Error as err:
            print(f'ERROR Group.getStudents() 2: {err}')
        except:
            PrintException()
            names = dict()
        finally:
            return names

    def removeStudent(self, telegram_id, group_id):
        command = f'select group_id from users where telegram_id = {telegram_id}'
        try:
            self.cursor = self.db.cursor()
            self.cursor.execute(command)
            record = self.cursor.fetchone()
            groups = str_to_list(record[0])
            groups.remove(int(group_id))
            User.tempVar(User(), telegram_id, 'group_id', str(groups)[1:-1])
            self.db.commit()
        except mysql.connector.Error as err:
            print(f'ERROR Group.removeStudent() :', err)

    def accEnroll(self, telegram_id, enroll_id):
        result = '[]'

        command_1 = f'select enroll from users where telegram_id = {telegram_id}'
        command_2 = f'select group_id from users where telegram_id = {telegram_id}'
        command_3 = f'update users set enroll = %s, group_id = %s where telegram_id = {telegram_id}'
        try:
            enroll_id = int(enroll_id)
            self.cursor = self.db.cursor()
            self.cursor.execute(command_1)
            now_enrolls = self.cursor.fetchone()[0]
            now_enrolls = str_to_list(now_enrolls)
            print('now_e', now_enrolls)
            if enroll_id in now_enrolls:
                now_enrolls.remove(enroll_id)
                result = str(now_enrolls)
            else:
                print('ERROR Group.accEnroll(): enroll ID not found in user line ')
                return False
            if len(now_enrolls) == 0:
                result = '[]'
            print('new_e', result)
            self.cursor.execute(command_2)
            now_groups = self.cursor.fetchone()[0]
            now_groups = str_to_list(now_groups)
            print('now_g', now_groups)
            if len(now_groups) == 0:
                new_groups = str(enroll_id)
            elif enroll_id in now_groups:
                print('WARNING in Group.accEnroll(): catch duplicate')
            else:
                now_groups.append(enroll_id)
                new_groups = str(now_groups)
            print('new_g', new_groups)
            print('e', result, '\ng:', new_groups)
            self.cursor.execute(command_3, (result, new_groups,))
            self.db.commit()

        except TypeError:
            print('TYPE ERROR Group,accEnroll()')
        except:
            PrintException()

    def delEnroll(self, telegram_id, enroll_id):
        command = f'select enroll from users where telegram_id = {telegram_id}'
        try:
            self.cursor = self.db.cursor()
            self.cursor.execute(command)
            record = self.cursor.fetchone()[0]
            enrolls = str_to_list(record)
            if enroll_id in enrolls:
                enrolls.remove(enroll_id)
                User.tempVar(User(), telegram_id, 'enroll', str(enrolls)[1:-1])
            else:
                print(f'WARN Group.delEnroll() no such id in user enroll: {telegram_id} : {enroll_id}')
                pass
        except mysql.connector.Error as err:
            print('ERROR Group.delEnroll(): ', err)
        except ValueError:
            PrintException()
        finally:
            self.db.commit()

    def tempVar(self, group_id, column, value=None):
        try:

            if value is None:
                command = f"select {column} from groups WHERE id = {group_id}"
            else:
                command = f"UPDATE groups SET {column} = '{str(value)}' WHERE id = {group_id}"

            try:
                self.cursor = self.db.cursor(buffered=True)
                self.cursor.execute(command)
                self.db.commit()
                if value is None:
                    row = self.cursor.fetchone()
                    return row
            except mysql.connector.Error as err:
                print('ERROR Groups.temp_var(): ', err)
        except:
            PrintException()


class Notification:
    def __init__(self):
        self.name = DB_NAME
        try:
            self.db = mysql.connector.connect(
                host=host,
                port=port,
                user=db_user,
                passwd=db_passwd,
                database=self.name)
            self.cursor = self.db.cursor()
        except mysql.connector.Error:
            self.db = mysql.connector.connect(
                host=host,
                user=db_user,
                password=db_passwd
            )
            self.cursor = self.db.cursor()
            self.cursor.execute(f"CREATE DATABASE {self.name}")

    def connect(self):
        self.db = mysql.connector.connect(
            host=host,
            port=port,
            user=db_user,
            passwd=db_passwd,
            database=self.name)
        self.cursor = self.db.cursor()
        return self.db

    def close(self):
        if self.db.is_connected():
            self.db.close()
            self.cursor.close()

    def read(self):
        notes = dict()
        command = 'select * from notifications'
        try:
            self.cursor = self.db.cursor()
            self.cursor.execute(command)
            records = self.cursor.fetchall()
            for row in records:
                notes[row[0]] = {
                    'group': int(row[1]),
                    'datetime': row[2],
                    'status': row[3]
                }
        except mysql.connector.Error as err:
            print('ERROR Notification.read():', err)
            notes = dict()
        except:
            PrintException()
            notes = dict()
        finally:
            return notes

    def add(self, group_id, time_):
        command = 'insert into notifications(group_id, datetime,status) VALUES (%s,%s,%s)'
        try:
            self.cursor = self.db.cursor()
            self.cursor.execute(command, (group_id, time_, 'wait'))
            self.db.commit()
        except mysql.connector.Error as err:
            print('ERROR Notification.add():', err)

    def delete(self, note_id):
        command = f'delete from notifications where `id` = {note_id}'
        try:
            self.cursor = self.db.cursor()
            self.cursor.execute(command)
            self.db.commit()
        except mysql.connector.Error as err:
            print('ERROR Notification.delete():', err)

    def switch(self, note_id):
        command_1 = f'select status from notifications where `id` = {note_id}'
        command_2 = f'update notifications set status = %s where `id` = {note_id}'
        try:
            self.cursor = self.db.cursor()
            self.cursor.execute(command_1)
            status = self.cursor.fetchone()[0]
            if status == 'wait':
                change_to = 'sended'
            elif status == 'sended':
                change_to = 'wait'
            else:
                change_to = status
            self.cursor.execute(command_2, (change_to,))
            self.db.commit()
        except mysql.connector.Error as err:
            print('ERROR Notification.switch():', err)


class User:
    def __init__(self):
        self.name = DB_NAME
        try:
            self.db = mysql.connector.connect(
                host=host,
                port=port,
                user=db_user,
                passwd=db_passwd,
                database=self.name)
            self.cursor = self.db.cursor()
        except mysql.connector.Error:
            self.db = mysql.connector.connect(
                host=host,
                user=db_user,
                password=db_passwd
            )
            self.cursor = self.db.cursor()
            self.cursor.execute(f"CREATE DATABASE {self.name}")

    def connect(self):
        self.db = mysql.connector.connect(
            host=host,
            port=port,
            user=db_user,
            passwd=db_passwd,
            database=self.name)
        self.cursor = self.db.cursor()

        return self.db

    def close(self):
        if self.db.is_connected():
            self.db.close()
            self.cursor.close()
            return True

    def add(self, message, cur_state):
        command = "INSERT INTO users  (telegram_id, name, nickname, user_state) VALUES (%s, %s, %s, %s);"
        try:
            if str(message.chat.id).startswith('-'):
                user_info = (message.chat.id, message.chat.full_name, message.chat.username, cur_state,)
            else:
                user_info = (message.chat.id, message.from_user.full_name, message.from_user.username, cur_state,)
            self.cursor = self.db.cursor()
            self.cursor.execute(command, user_info)
            self.db.commit()

        except mysql.connector.Error as err:
            if err.errno == 1062:
                log = f'{message.chat.id}:{message.from_user.full_name}(@{message.from_user.username}) перезашел в бота'
                DataBase.saveLog(DataBase(), message.chat.id, message.from_user.full_name, 'WARN', log)
            else:
                print(f'ERR: User, add user error: {err}')
                DataBase.saveLog(DataBase(), message.chat.id, message.from_user.full_name, 'ERR',
                                 f'Add User error: {err}')
        except:
            PrintException()

    def delete(self, telegram_id):
        command = f'delete from users where `telegram_id` = {telegram_id}'
        try:
            self.cursor = self.db.cursor()
            self.cursor.execute(command)
            self.db.commit()
            return True
        except mysql.connector.Error as err:
            print('ERROR User.delete()', err)

    def updateState(self, telegram_id, new_state):
        command = 'UPDATE users SET user_state = %s WHERE(telegram_ID = %s);'
        try:
            self.cursor = self.db.cursor()

            self.cursor.execute(command, (str(new_state), telegram_id,))

            self.db.commit()
        except mysql.connector.Error as err:

            print(f'ERR: User, updateState error: {err}')
            print('ERROR INFO', err.msg, err.args, err.sqlstate)
        except:
            PrintException()

    def getState(self, telegram_id):

        command = 'select user_state from users WHERE telegram_id = %s;'
        try:
            self.cursor = self.db.cursor()

            self.cursor.execute(command, (telegram_id,))
            row = self.cursor.fetchone()
            if row[0] is None:
                return -1
            else:
                return row[0]
        except mysql.connector.Error as err:
            print(f'ERR: User, get State error: {err}')
            print('ERROR INFO', err.args, err.sqlstate)

            return -1
        except TypeError:
            PrintException()
            return -1

    def read(self, telegram_id=None):
        users = dict()
        user_info = dict()

        if telegram_id is None:
            command = 'SELECT * FROM users'
        else:
            command = f'SELECT * FROM users WHERE telegram_id = {telegram_id}'

        try:
            self.cursor = self.db.cursor()

            self.cursor.execute(command)
            records = self.cursor.fetchall()
            for row in records:
                user_info = dict()
                groups = str_to_list(row[5])
                enrolls = str_to_list(row[6])
                trainer_groups = str_to_list(row[7])

                user_info['name'] = row[2]
                user_info['nickname'] = row[3]
                user_info['type'] = row[4]
                user_info['groups'] = groups
                user_info['enrolls'] = enrolls
                user_info['trainer_group'] = trainer_groups
                user_info['contact'] = row[8]
                user_info['state'] = row[9]
                user_info['temp'] = row[10]

                users[row[1]] = user_info
        except mysql.connector.Error as err:
            print("ERR: User.read(): Reading data from MySQL table", err)
        except:
            PrintException()
        finally:
            if telegram_id is None:
                return users
            else:
                return user_info

    def tempVar(self, telegram_id, column, value=None):
        try:

            if value is None:
                command = f"select {column} from users WHERE telegram_id = {telegram_id}"
            else:
                command = f"UPDATE users SET {column} = '{str(value)}' WHERE telegram_id = {telegram_id}"

            try:
                self.cursor = self.db.cursor(buffered=True)
                self.cursor.execute(command)
                self.db.commit()
                if value is None:
                    row = self.cursor.fetchone()
                    return row
            except mysql.connector.Error as err:
                print('User.temp_var(): ERROR: ', err.msg)
        except:
            PrintException()

    def getSpecialChat(self, user_type):
        command = f"select * from users where (`user_type` = %s)"
        user_info = dict()
        chats = dict()
        try:
            self.cursor = self.db.cursor()
            self.cursor.execute(command, (user_type,))
            records = self.cursor.fetchall()
            for row in records:
                user_info['name'] = row[2]
                user_info['nickname'] = row[3]
                user_info['type'] = row[4]

                user_info['contact'] = row[8]
                user_info['state'] = row[9]
                user_info['temp'] = row[10]

                chats[row[1]] = user_info

        except mysql.connector.Error as err:
            print("ERR: User.getSpecialChat(): Reading data from MySQL table", err)
        except:
            PrintException()

        finally:
            return chats

