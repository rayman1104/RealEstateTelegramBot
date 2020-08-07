# -*- coding: utf-8 -*-
import json
import logging
from typing import Set

import config
import pika
import threading
from pika.adapters.blocking_connection import BlockingChannel

logger = logging.getLogger("QueueWrapper")


class QueueWrapper:
    params: pika.URLParameters = None
    connection: pika.BlockingConnection = None
    channel: BlockingChannel = None
    publish_channel: BlockingChannel = None
    existing_queues: Set[str] = None
    existing_queues_lock: threading.Lock = None
    consume_thread = None

    @staticmethod
    def init():
        logger.info("Initializing queue manager")
        base = "amqp://{username}:{password}@{host}:{port}"
        QueueWrapper.params = pika.URLParameters(base.format(username=config.rabbit_mq_user,
                                                             password=config.rabbit_mq_pass,
                                                             host=config.rabbit_mq_url,
                                                             port=config.rabbit_mq_port))
        QueueWrapper.connection = pika.BlockingConnection(QueueWrapper.params)
        QueueWrapper.channel = QueueWrapper.connection.channel()
        QueueWrapper.channel.basic_qos(prefetch_count=1)
        QueueWrapper.existing_queues = set()
        QueueWrapper.existing_queues_lock = threading.Lock()

    @staticmethod
    def declare_queue(name):
        with QueueWrapper.existing_queues_lock:
            if name not in QueueWrapper.existing_queues:
                QueueWrapper.channel.queue_declare(queue=name)
                QueueWrapper.existing_queues.add(name)

    @staticmethod
    def subscribe_to_queue(callback, queue, auto_ack=True):
        QueueWrapper.declare_queue(queue)
        QueueWrapper.channel.basic_consume(queue,
                                           callback,
                                           auto_ack=auto_ack)

    @staticmethod
    def send_message(queue: str, message: bytes):
        connection = pika.BlockingConnection(QueueWrapper.params)
        QueueWrapper.publish_channel = connection.channel()
        QueueWrapper.publish_channel.queue_declare(queue=queue)
        logger.info(f"basic_publish: {queue}. {message}")
        QueueWrapper.publish_channel.basic_publish(exchange='',
                                                   routing_key=queue,
                                                   body=message)

    @staticmethod
    def clear_queue(queue, is_publish=False):
        if is_publish and QueueWrapper.publish_channel:
            # QueueWrapper.publish_channel.queue_purge(queue=queue)
            pass
        else:
            QueueWrapper.channel.queue_purge(queue=queue)

    @staticmethod
    def sleep(seconds):
        QueueWrapper.connection.sleep(seconds)

    @staticmethod
    def start_consuming_workaround(channel: BlockingChannel):
        while channel.consumer_tags:
            channel.connection.process_data_events(time_limit=5)

    @staticmethod
    def start(detach=True):
        if detach:
            QueueWrapper.consume_thread = threading.Thread(
                target=lambda: QueueWrapper.start_consuming_workaround(QueueWrapper.channel)
            )
            QueueWrapper.consume_thread.start()
        else:
            QueueWrapper.start_consuming_workaround(QueueWrapper.channel)

    @staticmethod
    def close():
        logger.info("Closing queue manager")
        logger.debug("Stop consuming")
        QueueWrapper.channel.stop_consuming()
        if QueueWrapper.consume_thread:
            logger.debug("Joining consume thread")
            QueueWrapper.consume_thread.join()
        QueueWrapper.channel.close()
        QueueWrapper.connection.close()
        QueueWrapper.channel = None
        QueueWrapper.connection = None


def dump_object(obj: dict):
    return json.dumps(obj, separators=(',', ':'))


def load_object(obj_string: bytes) -> dict:
    if isinstance(obj_string, bytes):
        obj_string = obj_string.decode('utf-8')
    return json.loads(obj_string)
