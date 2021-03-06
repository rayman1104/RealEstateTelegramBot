# -*- coding: utf-8 -*-
import logging

import bot_strings
import config
from Databases import Databases
from Databases.Flats import FlatsDB
from Databases.UserLinks import LinksDBManager
from Databases.Invites import InvitesManager
from .States import StateMachine, StateTags
import TelegramAPI

logger = logging.getLogger('user')
logger.setLevel(logging.DEBUG)


class User:
    db = None

    @staticmethod
    def init():
        User.db = Databases.get_users_db()

    def __init__(self, user_id, callback, delete_user_from_dict_callback):
        # Getting info from db
        self.db_filter = {'id': user_id}
        data = User.db.find_one(self.db_filter)
        if data is None:
            logger.debug("User {} added to DB".format(str(user_id)))
            data = config.default_user.copy()
            data['id'] = user_id
            User.db.insert_one(data)
        else:
            # In case of default user config
            # updates to avoid potential errors
            missed_keys_values = {key: value for key, value in
                                  config.default_user.items()
                                  if key not in data.keys()}
            if len(missed_keys_values) > 0:
                data.update(missed_keys_values)
                User.db.update_one(self.db_filter, {"$set": missed_keys_values})

        logger.debug("User {} {} inited".format(user_id, data))

        # Filling fields
        self.user_id = user_id
        self._authorized = data['auth']
        self.messages_before_ignore_left = data['ignore_left']
        self._updates_duration = data['updates_frequency']
        self._links = list(LinksDBManager.get_user_links(user_id))
        self._max_price = data['max_price']
        self._metro_stations = set(data['metro_stations'])
        self._menu_message = data.get('menu_message_id')

        self.raw_callback = callback
        self.callback = User.UserCallback(self)
        self.delete_callback = delete_user_from_dict_callback
        self.state_machine = StateMachine(self,
                                          StateTags.MAIN if
                                          self._authorized
                                          else StateTags.NONE)

    def delete_user(self):
        logger.debug("Deleting user {}".format(self.user_id))
        LinksDBManager.remove_all_links(self.user_id)
        User.db.remove(self.db_filter)
        self.delete_callback()

    class UserCallback:
        def __init__(self, user):
            self.user = user

        def __call__(self, *args, **kwargs):
            return self.__getattr__('__call__')(*args, **kwargs)

        def __getattr__(self, item):
            var = getattr(self.user.raw_callback, item)
            if callable(var):
                def callback(*args, **kwargs):
                    try:
                        return var(*args, **kwargs)
                    except TelegramAPI.UserBlocked:
                        logger.info("User {} blocked the bot. Deleting.".format(self.user.user_id))
                        self.user.delete_user()
                return callback
            return var

    def get_metro_stations(self):
        return self._metro_stations

    def add_station(self, name):
        self._metro_stations.add(name)
        User.db.update_one(self.db_filter, {'$push': {'metro_stations': name}})

    def remove_station(self, name):
        self._metro_stations.remove(name)
        User.db.update_one(self.db_filter, {'$pull': {'metro_stations': name}})

    def clear_stations(self):
        self._metro_stations = set()
        User.db.update_one(self.db_filter, {'$set': {'metro_stations': []}})

    def clear_all(self):
        self.clear_stations()
        self.remove_links()

    def send_offer_info(self, offer_id):
        offer = FlatsDB.get_flat(offer_id)
        if offer is None:
            self.callback(bot_strings.no_flat_with_id)
            return
        metro = "{} ({})".format(offer['location']['metro']['name'],
                                 offer['location']['metro']['description']) \
            if 'metro' in offer['location'] else "Метро нет"
        sizes_info = ", ".join(offer['sizes'])
        message = bot_strings.base_for_sending_flat.format(metro=metro,
                                                           address=", ".join(offer['location']['address']),
                                                           object=offer['object'], sizes_total=sizes_info,
                                                           floor=offer['floor'], price=offer['price'][0],
                                                           price_info=offer['price'][2], percent=offer['fee'],
                                                           contacts=offer.get('contacts'))

        url = self.callback.inline_url(bot_strings.go_to_flat_by_url_caption,
                                       offer['url'])
        markup = self.callback.inline_keyboard([[url]])
        self.callback(message, inline_markup=markup)

    def new_links_acquired_event(self, updates_ids):
        logger.debug("Sending new offers to user " + str(self.user_id))
        logger.debug(f'updated_ids: {updates_ids}')
        updates = FlatsDB.get_flats(updates_ids)
        received_links = set(User.db.find_one(self.db_filter)['received_links'])
        logger.debug(f'received_links: {received_links}')
        new_links = set()
        required_updates = (x for x in updates if x['id'] not in received_links)
        message = ""
        for update in required_updates:
            logger.debug(f'update: {update}')
            new_links.add(update['id'])
            if 'metro' in update['location']:
                metro = update['location']['metro']
                location = "{} ({})".format(metro['name'], metro['description'])
            else:
                location = " ".join(update['location']['address'][:-2])
            price = update['price'][0]
            message += bot_strings.base_for_sending_preview.format(location=location, price=price,
                                                                   info_cmd=bot_strings.cian_base_cmd.format(
                                                                       id=update['id']),
                                                                   url=update['url']) + '\n'
        self.callback(message, parse_mode='Markdown', disable_web_page_preview=True)
        if len(new_links) > 0:
            User.db.update_one(self.db_filter, {'$push': {'received_links': {'$each': list(new_links)}}})

    def pull_auth_message(self, message):
        self.messages_before_ignore_left -= 1
        if InvitesManager.pull_invite(message):
            return True
        User.db.update_one(self.db_filter, {'$inc': {'ignore_left': -1}})
        return False

    @property
    def max_price(self):
        return self._max_price

    @max_price.setter
    def max_price(self, value):
        self._max_price = value
        User.db.update_one(self.db_filter, {'$set': {'max_price': value}})

    @property
    def updates_duration(self):
        return self._updates_duration

    @updates_duration.setter
    def updates_duration(self, value):
        self._updates_duration = value
        User.db.update_one(self.db_filter, {'$set': {'updates_frequency': value}})

        for link in LinksDBManager.get_user_links(self.user_id):
            LinksDBManager.update_frequency(link['_id'], value)

    @property
    def authorized(self):
        return self._authorized

    @authorized.setter
    def authorized(self, value):
        self._authorized = value
        if value:
            User.db.update_one(self.db_filter, {'$set': {'auth': True}})
        else:
            User.db.update_one(self.db_filter, {'$set': {'auth': False,
                                                         'ignore_left': config.user_messages_before_ignore}})

    @property
    def links(self):
        return self._links

    @staticmethod
    def check_tag_correct(tag):
        return len(tag) < config.max_tag_len

    @property
    def menu_message(self):
        return self._menu_message

    @menu_message.setter
    def menu_message(self, value):
        self._menu_message = value
        User.db.update_one(self.db_filter, {'$set': {'menu_message_id': value}})

    @staticmethod
    def check_time_correct(time):
        return isinstance(time, int) and time >= config.min_time_update_len

    def link_add_callback(self, link, tag, answer):
        if answer:
            self.add_link(link, tag)
            self.callback(bot_strings.add_link_success.format(tag=tag))
        else:
            self.callback(bot_strings.add_link_failed.format(tag=tag))

    def link_add_request(self, link, tag):
        from User.UserManager import UserManager
        UserManager.add_link_checking(self.user_id, link, tag)

    def add_link(self, link, tag):
        logger.debug("Adding link of user " + str(self.user_id) +
                     " to database\n" + link +
                     " with tag " + tag)
        self._links.append(LinksDBManager.add_user_link(self.user_id, link, tag,
                                                        self.updates_duration, 'CIAN'))

    def remove_links(self):
        logger.debug("User {} removing all links".format(self.user_id))
        self._links = []
        LinksDBManager.remove_all_links(self.user_id)

    def set_menu(self, message_text, inline_keyboard, parse_mode=None, invoke=False):
        inline_keyboard = TelegramAPI.MessageFunctionObject.get_inline_keyboard(inline_keyboard)
        if not self.menu_message:
            invoke = True
        if invoke:
            if self.menu_message:
                self.callback.change_message_markup(self.menu_message)
            new_message = self.callback(message_text, inline_markup=inline_keyboard,
                                        parse_mode=parse_mode)
            self.menu_message = new_message['message_id']
        else:
            self.callback.change_text(self.menu_message, message_text, inline_markup=inline_keyboard,
                                      parse_mode=parse_mode)

    def process_message(self, message):
        message_text = message['text']
        if self.messages_before_ignore_left >= 0:
            self.state_machine.process_message(message_text)

    def process_inline_req(self, inline_message):
        if self.messages_before_ignore_left >= 0:
            self.state_machine.process_inline_req(inline_message)

    def process_inline_ans(self, inline_answer):
        if self.messages_before_ignore_left >= 0:
            self.state_machine.process_inline_ans(inline_answer)

    def process_callback(self, callback):
        if self.messages_before_ignore_left >= 0:
            self.state_machine.process_callback(callback)
