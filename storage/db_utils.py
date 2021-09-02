import logging
import psycopg2
from utils import read_config, ROOT_DIR
from sys import intern, _getframe
import logging
from typing import (
    Any,
    Callable,
    Dict,
    Iterable,
    Iterator,
    List,
    Optional,
    Tuple,
    TypeVar,
    cast,
    overload,
)

config = read_config('database.json')
logger = logging.getLogger(__name__)
# Create handlers

c_handler = logging.StreamHandler()
f_handler = logging.FileHandler(ROOT_DIR + '/log/database.log')
c_handler.setLevel(logging.ERROR)
f_handler.setLevel(logging.ERROR)
# Create formatters and add it to handlers
c_format = logging.Formatter('%(name)s - %(levelname)s - %(message)s')
f_format = logging.Formatter('%(asctime)s - %(name)s - %(funcName)s - %(levelname)s - %(message)s')

c_handler.setFormatter(c_format)
f_handler.setFormatter(f_format)
# Add handlers to the logger
logger.addHandler(c_handler)
logger.addHandler(f_handler)


class DataStore:

    def __init__(self):
        self.conn = psycopg2.connect(**config)

    @staticmethod
    def add_value(value):
        if isinstance(value, str):
            return f"'{value}'"
        else:
            return value


    def select(self, table, keyvalues: [Dict[str, Any]], columns: Iterable[str]) -> List[Dict[str, Any]]:
        if keyvalues:
            sql = "SELECT %s FROM %s WHERE %s;" % (
                ", ".join(columns),
                table,
                " AND ".join(f"{k} = {self.add_value(keyvalues[k])}" for k in keyvalues),
            )
            with self.Cursor(self.conn) as cursor:
                cursor.execute(sql, list(keyvalues.values()))
                res = self.cursor_to_dict(cursor)
        else:
            sql = "SELECT %s FROM %s" % (", ".join(columns), table)
            with self.Cursor(self.conn) as cursor:
                cursor.execute(sql)
                res = self.cursor_to_dict(cursor)

        return res

    def insert(self, table: str, values: Dict[str, Any]) -> bool:
        keys, vals = zip(*values.items())
        sql = "INSERT INTO %s (%s) values (%s);" % (
            table,
            ", ".join(k for k in keys),
            ", ".join("%s" for _ in keys),
        )
        with self.Cursor(self.conn) as cursor:
            try:
                logger.info(f"{_getframe().f_code.co_name}: {cursor=} |  {vals}")

                cursor.execute(sql, vals)
                return True
            except psycopg2.DatabaseError as err:
                logger.error(f"{_getframe().f_code.co_name}: {cursor=} | {err}|  {vals}")
            except Exception as err:
                logger.error(f"insert: {type(err)=} | {err=} |  {vals=}")
                return False
        logger.info(f"{_getframe().f_code.co_name}: {cursor=} |  {vals}")

    def delete(self, table: str, keyvalues: Dict[str, Any]) -> bool:
        sql = "DELETE FROM %s WHERE %s" % (
            table,
            " AND ".join(f"{k} = {self.add_value(keyvalues[k])}"  for k in keyvalues),
        )
        with self.Cursor(self.conn) as cursor:
            try:
                cursor.execute(sql, list(keyvalues.values()))

                if cursor.rowcount == 0:
                    raise StoreError(404, f'No rows to delete from {table} where {keyvalues}')
                return True
            except Exception as err:
                logger.error(f"{_getframe().f_code.co_name} | {err}")
                return False

    def update(self, table: str, keyvalues: Dict[str, Any], updatevalues: Dict[str, Any]) -> bool:

        if keyvalues:
            sql = "UPDATE %s SET %s WHERE %s;" % (
                table,
                ", ".join(f"{k} = {self.add_value(updatevalues[k])}" for k in updatevalues),
                " AND ".join(f"{k} = {self.add_value(keyvalues[k])}" for k in keyvalues),
            )
            with self.Cursor(self.conn) as cursor:
                cursor.execute(sql, list(keyvalues.values()))
                try:
                    res = self.cursor_to_dict(cursor)
                except AssertionError:
                    logger.warning(f"{_getframe().f_code.co_name} | Nothing suitable for the conditions ")


        else:
            sql = "UPDATE %s SET %s" % (table, ", ".join("%s = ?" % (k,) for k in updatevalues))
            with self.Cursor(self.conn) as cursor:
                cursor.execute(sql)
                try:
                    res = self.cursor_to_dict(cursor)
                except AssertionError:
                    logger.warning(f"{_getframe().f_code.co_name} | Nothing suitable for the conditions ")

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

        def __exit__(self, exc_class, exc, traceback):
            self.db.commit()
            self.cursor.close()


class StoreError(RuntimeError):
    def __init__(self, code: int, msg: str):
        super().__init__("%d: %s" % (code, msg))

        self.code = int(code)
        self.msg = msg
