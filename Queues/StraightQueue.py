# -*- coding: utf-8 -*-
from pika import spec
from pika.adapters.blocking_connection import BlockingChannel

from Queues import dump_object, load_object, QueueWrapper


class StraightQueue:
    @staticmethod
    def get_sender(queue_name: str):
        def write_msg(request: dict):
            packed: bytes = dump_object(request)
            QueueWrapper.send_message(queue_name, packed)

        return write_msg

    @staticmethod
    def subscribe_getter(queue_name, callback):
        def req_callback(ch: BlockingChannel, method: spec.Basic.Deliver, _: spec.BasicProperties, body: bytes):
            body = load_object(body)
            ack = callback(body)
            if ack is None:
                ack = True
            if ack:
                ch.basic_ack(delivery_tag=method.delivery_tag)
            else:
                ch.basic_nack(delivery_tag=method.delivery_tag)

        QueueWrapper.subscribe_to_queue(callback=req_callback,
                                        queue=queue_name,
                                        auto_ack=False)
