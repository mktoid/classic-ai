## Classic.AI

Место 13 из 56 команд-участников

### Запуск на локальной системе

```
$ sudo docker run -v $PWD:/tmp/working -w=/tmp/working -p 8000:8000 -p 9200:9200 --rm -it mktoid/classic
elasticsearch@63365dd1cdff:/tmp/working$ python run.py

```


### Запуск Jupyter Notebook в конкурсном контейнере, чтобы видеть совместимость установленных библиотек
```
jupyter notebook --no-browser --ip="*" --notebook-dir=/tmp/working --allow-root

```

### Пример работы
(https://github.com/sberbank-ai/classic-ai/blob/master/README.md)

При помощи Python 3 и библиотеки [`requests`](http://docs.python-requests.org/en/master/).

```python
>>> import requests
>>> requests.get('http://localhost:8000/ready')
<Response [200]>
>>> resp = requests.post('http://localhost:8000/generate/lermontov', json={'seed': 'регрессия глубокими нейронными сетями'})
>>> resp
<Response [200]>
>>> data = resp.json()
>>> print(data['poem'])
Глубокими нейронными сетями
Летим одни
Вон точно регрессия полукругом
Расходятся огни
```
