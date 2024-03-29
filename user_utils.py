from storage.db_utils import DataStore, StoreError
from utils import set_logger
import json
logger = set_logger('utils')
USER_TYPE = {
    0: 'Гість',
    1: 'Адміністратор📒',
    2: 'Тренер',
    3: 'Учень'
}


async def update_state(chat, state, store: DataStore):
    try:
        await store.update('users', {'telegram': chat}, {'state': str(state.state)})
        return True
    except StoreError as err:
        logger.info(f"| Cannot update state | {err}")


async def get_trainers(store):
    trainers = await store.select('courses', None, columns=('trainer',))
    all_trainers = list()
    for row in trainers:
        names = json.loads(row['trainer'])
        all_trainers += names.get('trainer', [])

    return sorted(list(set(all_trainers)))
