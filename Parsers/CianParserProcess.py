# -*- coding: utf-8 -*-
from typing import TypedDict, Callable, Optional

import LoggerInit
import config
from Parsers import CianParser
from Queues import QueueWrapper
from Queues.ProducerConsumer.ProducerFactory import ProducerFactory

logger = LoggerInit.init_logging(config.log_parser_file)


class CheckUrlMessage(TypedDict):
    url: str


class ParseUrlMessage(TypedDict):
    url: str
    time: Optional[int]


def check_url_callback(message: CheckUrlMessage, answer_callback: Callable[[any], None]) -> bool:
    url = message['url']
    logger.info("Checking url: {}".format(url))
    result = CianParser.check_url_correct(url)
    answer_callback(result)
    return True


def parse_url_callback(message: ParseUrlMessage, answer_callback: Callable[[any], None]) -> bool:
    url = message['url']
    if 'time' in message.keys():
        time = message['time']
        result = CianParser.get_new_offers(url, time)
    else:
        result = CianParser.get_new_offers(url)
    result = [offer['id'] for offer in result]
    answer_callback(result)
    return True


@LoggerInit.catch_exceptions
def main():
    QueueWrapper.init()
    ProducerFactory.subscribe_producer(config.check_url_req_queue, config.check_url_ans_queue,
                                       check_url_callback)
    ProducerFactory.subscribe_producer(config.parse_url_req_queue, config.parse_url_ans_queue,
                                       parse_url_callback)
    ProducerFactory.subscribe_producer(config.parse_all_moscow_req_queue, config.parse_all_moscow_ans_queue,
                                       parse_url_callback)
    try:
        QueueWrapper.start(detach=False)
    except KeyboardInterrupt:
        QueueWrapper.close()
