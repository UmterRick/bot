import pickle
from storage.db_utils import DataStore, StoreError
from utils import set_logger
from sys import _getframe
logger = set_logger('main')
USER_TYPE = {
    0: 'Гість',
    1: 'Адміністратор📒',
    2: 'Тренер',
    3: 'Учень'
}


async def update_state(chat, state, store: DataStore):
    try:
        print(str(state.state))
        await store.update('users', {'telegram': chat}, {'state': str(state.state)})
        return True
    except StoreError as err:
        logger.info(f"{_getframe().f_code.co_name} | Cannot update state | {err}")


async def get_state(chat, store: DataStore):
    try:
        ser_state = await store.select_one('users', {'telegram': chat}, ('state',))
        print(ser_state['state'])
        with open('state.pickle', 'wb') as pickle_file:
            pickle_file.write(b"%x" % ser_state['state'])
        with open('state.pickle', 'rb') as pickle_file:
            state = pickle.load(pickle_file)

        return state
    except StoreError as err:
        logger.error(f"{_getframe().f_code.co_name} | Cannot get state | {err}")
    except pickle.PickleError as err:
        print('PICKLE ERROR', err)
    # except Exception as ex:
    #     logger.error(f"{_getframe().f_code.co_name} | Unexpected exception | {ex}")



