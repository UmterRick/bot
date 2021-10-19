import requests
from bs4 import BeautifulSoup
from utils import read_config
import json

config = read_config('urls.json')
HEADERS = config.get("HEADERS", "")
courses_url = config.get("C_URL", "")


def get_html(url, params=None):
    r = requests.get(url, headers=HEADERS, params=params)
    print('Wrong code status') if r.status_code != 200 else None
    return r


async def get_content(store):
    html = get_html(courses_url)
    soup = BeautifulSoup(html.text, 'html.parser')

    topics = soup.find_all('h2')
    for topic in topics:
        await store.insert('categories', {'name': topic.text})
        titles = topic.find_next('ul').find_all('li')

        for t in titles:
            url = t.find('a').get('href', 'google.com')
            name = str(t.text)
            trainers_collection = name[name.find('(') + 1:name.find(')')].strip().split(',')
            name = name[:name.find('(')]

            for index, trainer in enumerate(trainers_collection):
                if '.' in trainer:
                    delimiter = trainer.find('.')
                    if trainer[delimiter + 1] != ' ':
                        fixed_trainer = trainer[:delimiter + 1] + ' ' + trainer[delimiter + 1:]
                        trainers_collection[index] = fixed_trainer
            course_trainers = json.dumps({'trainers': trainers_collection}, ensure_ascii=False)
            category = await store.select_one('categories', {'name': topic.text}, ('id',))
            course = {
                'name': name,
                'category': category.get('id'),
                'trainer': course_trainers,
                'link': url,
                'description': "-",
                'price': 0
            }
            try:
                await store.insert('courses', course)
            except Exception as ex:
                print(ex)
