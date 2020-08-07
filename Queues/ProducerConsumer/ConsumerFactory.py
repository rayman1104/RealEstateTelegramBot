# -*- coding: utf-8 -*-
from typing import TypedDict, Callable, Optional

from pika import spec
from pika.adapters.blocking_connection import BlockingChannel

from Queues import QueueWrapper, dump_object, load_object


class AnsBody(TypedDict):
    id: dict
    ans: dict


class ConsumerFactory:
    @staticmethod
    def get_consumer(request_queue_name: str, answer_queue_name: str,
                     answer_callback: Callable[[dict, any], Optional[bool]]):
        def raw_answer_callback(ch: BlockingChannel, method: spec.Basic.Deliver, _: spec.BasicProperties, body: bytes):
            body: AnsBody = load_object(body)
            ack = answer_callback(body['id'], body['ans'])
            if ack is None:
                ack = True
            if ack:
                ch.basic_ack(delivery_tag=method.delivery_tag)
            else:
                ch.basic_nack(delivery_tag=method.delivery_tag)

        def write_msg(msg_id: dict, request: dict):
            message = {
                'id': msg_id,
                'req': request
            }
            packed: bytes = dump_object(message)
            QueueWrapper.send_message(request_queue_name, packed)

        QueueWrapper.subscribe_to_queue(callback=raw_answer_callback,
                                        queue=answer_queue_name,
                                        auto_ack=False)
        return write_msg
