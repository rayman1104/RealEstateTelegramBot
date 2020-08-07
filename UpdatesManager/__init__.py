# -*- coding: utf-8 -*-
import threading
import logging

import time
from typing import List, Callable, Dict

import config
from Databases.UserLinks import LinksDBManager
from Queues.ProducerConsumer.ConsumerFactory import ConsumerFactory
from Queues.StraightQueue import StraightQueue

logger = logging.getLogger("UpdatesManager")
logger.setLevel(logging.DEBUG)


class UpdatesManager:
    link_update_request_function: Callable[[dict, any], None] = None
    links_send_function: Callable[[dict], None] = None

    @staticmethod
    def link_updated_result(info: dict, new_links: List[int]) -> None:
        message = {
            'uid': info['uid'],
            'offers': new_links,
        }
        UpdatesManager.links_send_function(message)

    @staticmethod
    def worker():
        while True:
            left_time = LinksDBManager.get_left_time_before_new_link_arrival()
            if left_time > 0:
                logger.debug("Waiting {} seconds for new links to come".format(left_time))
                time.sleep(left_time)

            for link in LinksDBManager.get_expired_links():
                logger.debug("Parsing offers for user " + str(link['id']))
                timeout = max(config.cian_min_timeout, link['frequency'] * 60)
                UpdatesManager.link_update_request_function({'uid': link['id']},
                                                            {'url': link['url'], 'time': timeout})

    @staticmethod
    def init_manager():
        logger.info("Initializing updates manager")

        UpdatesManager.link_update_request_function = ConsumerFactory.get_consumer(
            config.parse_url_req_queue,
            config.parse_url_ans_queue,
            UpdatesManager.link_updated_result)

        UpdatesManager.links_send_function = StraightQueue.get_sender(config.new_offers_queue)
