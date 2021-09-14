import requests
from bs4 import BeautifulSoup
# from configs import DB_NAME
from utils import read_config
import json


config = read_config('urls.json')
HEADERS = config.get("HEADERS", "")
C_URL = config.get("C_URL", "")


def get_html(url, params=None):
    r = requests.get(url, headers=HEADERS, params=params)
    print('Wrong code status') if r.status_code != 200 else None
    return r


async def get_content(store):
    html = get_html(C_URL)
    soup = BeautifulSoup(html.text, 'html.parser')

    items = soup.find_all('div', class_='content')
    topics_search = soup.find_all('div', class_='short')

    blocks = await store.select('categories', None, ('name',))
    courses = await store.select('courses', None, {'name'})
    courses = list(course['name'] for course in courses)
    for num, topic in enumerate(topics_search):
        if len(blocks) != len(topics_search):
            try:
                if topic.text not in blocks:
                    await store.insert('categories', {'name': topic.text})
            except Exception as ex:
                print(ex)
        parsed_courses = list()
        records = list(p for p in items[num].find_all('p') if str(p.text).startswith('ᐅ'))
        for i in records:
            title = i.text
            link = i.find('a')
            pare = (title, link)
            if link and link.has_attr('href'):
                link = link['href']
                pare = (title, link)
            parsed_courses.append(pare)
        for title, link in parsed_courses:
            if str(title).startswith('ᐅ'):
                title_clear = str(title).replace('ᐅ ', '')
                if '(' in title_clear:
                    name = title_clear[0:title_clear.find('(')]
                    trainer = title_clear[title_clear.find('(') + 1:title_clear.find(')')]
                    names = list()
                    for tr_name in trainer.split(','):
                        if '.' in tr_name:
                            delimiter = tr_name.find('.')
                            if tr_name[delimiter+1] != ' ':
                                tr_name = tr_name[:delimiter+1] + ' ' + tr_name[delimiter+1:]

                        names.append(tr_name)
                    trainer = {'trainer': names}
                    trainer = json.dumps(trainer, ensure_ascii=False)

                else:
                    name = title_clear[0:title_clear.find('👉')]
                    trainer = None
                if name not in courses:
                    category = await store.select_one('categories', {'name': topic.text}, ('id',))
                    course = {
                        'name': name,
                        'category': category.get('id'),
                        'trainer': trainer,
                        'link': link,
                        'description': "-",
                        'price': 0
                    }
                    try:
                        await store.insert('courses', course)
                    except Exception as ex:
                        print(ex)


