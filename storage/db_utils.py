import psycopg2
from utils import read_config, set_logger
from sys import intern, _getframe
from typing import (Any, Dict, List, Iterable, )

config = read_config('database.json')
logger = set_logger('database')
expected_tables = set(config.pop("expected_tables"))


class DataStore:

    def __init__(self):
        self.conn = psycopg2.connect(**config)
        self.cursor = self.Cursor(self.conn)

    @staticmethod
    def add_value(value):
        if isinstance(value, str):
            if 'SELECT' in value.upper() and 'FROM' in value.upper():
                return value
            return f"'{value}'"
        else:
            return value

    def check_existence(self):
        sql = "SELECT table_name FROM information_schema.tables WHERE table_schema = 'public'"

        with self.cursor as cursor:
            try:
                cursor.execute(sql)
                tables = cursor.fetchall()
                tables = [table[0] for table in tables]
                return (True, tables) if set(tables) == expected_tables else (False, tables)
            except Exception as err:
                logger.info(f"{_getframe().f_code.co_name}: {err}")
                return list()

    def create_tables(self):
        with self.cursor as cursor:
            try:
                cursor.execute(open("storage/schema/full_schema.sql", "r").read())
                logger.info(f"=== Tables created ===")
            except Exception as err:
                logger.info(f"{_getframe().f_code.co_name}: {err}")
                return list()

    async def select(self, table, keyvalues: [Dict[str, Any]], columns: Iterable[str]) -> List[Dict[str, Any]]:
        if keyvalues:
            sql = "SELECT %s FROM %s WHERE %s;" % (
                ", ".join(columns),
                table,
                " AND ".join(f"{k} = {self.add_value(keyvalues[k])}" for k in keyvalues),
            )
            with self.cursor as cursor:
                cursor.execute(sql, list(keyvalues.values()))
                res = self.cursor_to_dict(cursor)
        else:
            sql = "SELECT %s FROM %s" % (", ".join(columns), table)
            with self.cursor as cursor:
                cursor.execute(sql)
                res = self.cursor_to_dict(cursor)

        return res

    async def select_one(self, table: str, keyvalues: Dict[str, Any], retcols: Iterable[str]):
        select_sql = "SELECT %s FROM %s WHERE %s ;" % (
            ", ".join(retcols),
            table,
            " AND ".join(f"{k} = {self.add_value(keyvalues[k])}" for k in keyvalues),
        )
        with self.cursor as cursor:
            cursor.execute(select_sql, list(keyvalues.values()))
            row = cursor.fetchone()

        if not row:
            logger.warning(f"{_getframe().f_code.co_name} | No row found {(table,)})")
            return {}
        if cursor.rowcount > 1:
            logger.error(f"{_getframe().f_code.co_name} | More than one row matched {(table,)})")
            raise StoreError(500, "More than one row matched (%s)" % (table,))
        return dict(zip(retcols, row))

    async def insert(self, table: str, values: Dict[str, Any]) -> bool:
        keys, vals = zip(*values.items())
        sql = "INSERT INTO %s (%s) values (%s);" % (
            table,
            ", ".join(k for k in keys),
            ", ".join("%s" for _ in keys),
        )
        with self.cursor as cursor:
            try:
                cursor.execute(sql, vals)
                logger.info(f"{_getframe().f_code.co_name}: Add new record {vals}")
                return True
            except psycopg2.DatabaseError as err:
                if err.pgcode == '23505':
                    logger.warning(
                        f"{_getframe().f_back.f_code.co_name} --> {_getframe().f_code.co_name}"
                        f" Skip insert cuause 23505 err code ")
                logger.error(
                    f"{_getframe().f_back.f_code.co_name} --> {_getframe().f_code.co_name}: DB Error {err}|  {vals}")
            except Exception as err:
                logger.error(f"{_getframe().f_back.f_code.co_name} --> {_getframe().f_code.co_name}: "
                             f"{err=} |  {vals=}")
                return False

    async def delete(self, table: str, keyvalues: Dict[str, Any]) -> bool:
        sql = "DELETE FROM %s WHERE %s" % (
            table,
            " AND ".join(f"{k} = {self.add_value(keyvalues[k])}" for k in keyvalues),
        )
        with self.cursor as cursor:
            try:
                cursor.execute(sql, list(keyvalues.values()))
                if cursor.rowcount == 0:
                    raise StoreError(404, f'No rows to delete from {table} where {keyvalues}')
                return True
            except Exception as err:
                logger.error(f"{_getframe().f_code.co_name} | {err}")
                return False

    async def update(self, table: str, keyvalues: Dict[str, Any], updatevalues: Dict[str, Any]):
        if keyvalues:
            sql = "UPDATE %s SET %s WHERE %s RETURNING *;" % (
                table,
                ", ".join(f"{k} = {self.add_value(updatevalues[k])}" for k in updatevalues),
                " AND ".join(f"{k} = {self.add_value(keyvalues[k])}" for k in keyvalues),
            )
            with self.cursor as cursor:
                try:
                    cursor.execute(sql, list(keyvalues.values()))
                    return self.cursor_to_dict(cursor)
                except Exception as ex:
                    logger.warning(f'{_getframe().f_back.f_code.co_name} -> {_getframe().f_code.co_name}  '
                                   f'Exception: {ex}')


        else:
            sql = "UPDATE %s SET %s" % (table, ", ".join("%s = ?" % (k,) for k in updatevalues))
            with self.cursor as cursor:
                cursor.execute(sql)
                try:
                    res = self.cursor_to_dict(cursor)
                except AssertionError:
                    logger.warning(f'''{_getframe().f_code.co_name} | Nothing suitable for the conditions: 
                    {" AND ".join(f"{k} = {self.add_value(keyvalues[k])}" for k in keyvalues)}''')

    @staticmethod
    def cursor_to_dict(cursor) -> List[Dict[str, Any]]:
        """Converts a SQL cursor into an list of dicts.

        Args:
            cursor: The DBAPI cursor which has executed a query.
        Returns:
            A list of dicts where the key is the column header.
        """
        assert cursor.description is not None, "cursor.description was None"
        col_headers = [intern(str(column[0])) for column in cursor.description]
        results = [dict(zip(col_headers, row)) for row in cursor]
        return results

    class Cursor:
        def __init__(self, conn):
            self.db = conn

        def __enter__(self):
            self.cursor = self.db.cursor()
            return self.cursor

        def __exit__(self, exc_type, exc_val, exc_tb):
            self.db.commit()
            self.cursor.close()


class StoreError(RuntimeError):
    def __init__(self, code: int, msg: str):
        super().__init__("%d: %s" % (code, msg))
        self.code = int(code)
        self.msg = msg
