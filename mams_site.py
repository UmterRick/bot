import requests
from bs4 import BeautifulSoup
from config import HEADERS, C_URL
from config import DB_NAME


def get_html(url, params=None):
    r = requests.get(url, headers=HEADERS, params=params)
    print('Wrong code status') if r.status_code != 200 else None
    return r

def get_content(html):
    soup = BeautifulSoup(html.text, 'html.parser')
    items = soup.find_all('div', class_='content')
    topics_search = soup.find_all('div', class_='short')
    topics = {}
    counter = 1
    for topic in topics_search:
        topics[counter] = topic.text
        counter += 1
    courseID_dict = {}

    for block_id in range(1,len(topics.keys())+1):
        names = items[block_id-1].find_all('p')
        links = items[block_id-1].find_all('a')
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
                full_id = str(block_id) + str(course_id)
                courseID_dict[full_id] = body
                if body == 'Програма підготовки дітей до школи Календарно-тематичний план':
                    db_add_course(DB_NAME, course_id, body, trainer, '_________', str(block_id), topics[block_id])
                else:
                    db_add_course(DB_NAME, course_id, body, trainer, links[course_id - 1].get('href'), str(block_id), topics[block_id])
                    course_id += 1
    return topics, courseID_dict

