## Setup
```bash
docker build --tag telegram_realty_base -f Docker/Dockerfiles/Dockerfile .
cp config.py.example config.py
```

## Start
```bash
docker-compose up -d rabbit && sleep 10 && docker-compose up --build main
```

## Description
#### parser
* Listens to events from several input queues (`check_url_req`, `parse_url_req`, `parse_all_moscow_req`).
* Parses CIAN on events from those queues and sends result to corresponding output queues
(`check_url_ans`, `parse_url_ans`, `parse_all_moscow_ans`).

#### all_moscow
* For every link in `config.links_to_parse` sends parse requests to `parse_all_moscow_req`
and gets response from `parse_all_moscow_ans`.<br>
  Message: `{'url': str, 'time': int}`.
* Sends events to `new_offers_queue`. For each user it filters links they need and
sends new offers via this queue.<br>
  Message: `{'uid': int, 'offers': List[int]}`.

#### updates_manager
* For every link in `config.links_to_parse` sends parse requests to `parse_url_req`
  and gets response from `parse_url_ans`.<br>
  Takes into account only flats that were added in last 2 hours (`config.cian_min_timeout`).
    Message: `{'url': str, 'time': int}`.
* Sends events to `new_offers_queue`. For each user it filters links they need and
sends new offers via this queue.<br>
  Message: `{'uid': int, 'offers': List[int]}`.

#### main
* Processes Telegram events via State machine.
* For every link from user sends check url requests to `check_url_req`
    and gets response from `check_url_ans`.<br>
  msg_id: `{'uid': int, 'url': str, 'tag': str}`, request: `{'url': str}`
* Listens to `new_offers` queue.
