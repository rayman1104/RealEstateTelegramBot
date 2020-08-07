# -*- coding: utf-8 -*-
from typing import TypedDict, Callable

from pika import spec
from pika.adapters.blocking_connection import BlockingChannel

from Queues import QueueWrapper, dump_object, load_object


class ReqBody(TypedDict):
    id: int
    req: dict


class ProducerFactory:
    @staticmethod
    def subscribe_producer(
            request_queue_name: str,
            answer_queue_name: str,
            request_callback: Callable[[dict, Callable[[any], None]], bool]
    ):
        def answer_callback(msg_id: int, answer) -> None:
            total_answer = {
                'id': msg_id,
                'ans': answer,
            }
            QueueWrapper.send_message(answer_queue_name, dump_object(total_answer))

        def req_callback(ch: BlockingChannel, method: spec.Basic.Deliver, _: spec.BasicProperties, body: bytes):
            body: ReqBody = load_object(body)
            ack = request_callback(body['req'], lambda answer: answer_callback(body['id'], answer))
            if ack is None:
                ack = True
            if ack:
                ch.basic_ack(delivery_tag=method.delivery_tag)
            else:
                ch.basic_nack(delivery_tag=method.delivery_tag)

        QueueWrapper.subscribe_to_queue(callback=req_callback,
                                        queue=request_queue_name,
                                        auto_ack=False)


