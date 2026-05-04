# -*- coding: utf-8 -*-
from functools import partial


def build_library_menu(app, lib_card, caller):
    file_type = getattr(lib_card, 'file_type', 'video')
    items = [
        {
            'viewclass': 'OneLineListItem',
            'text': 'Play',
            'on_release': partial(app._library_menu_action, lib_card, 'play'),
        },
        {
            'viewclass': 'OneLineListItem',
            'text': 'Move to Vault',
            'on_release': partial(app._library_menu_action, lib_card, 'vault'),
        },
        {
            'viewclass': 'OneLineListItem',
            'text': 'Details',
            'on_release': partial(app._library_menu_action, lib_card, 'details'),
        },
        {
            'viewclass': 'OneLineListItem',
            'text': 'Delete',
            'on_release': partial(app._library_menu_action, lib_card, 'delete'),
        },
    ]
    if file_type == 'audio':
        items.insert(2, {
            'viewclass': 'OneLineListItem',
            'text': 'Trim',
            'on_release': partial(app._library_menu_action, lib_card, 'trim'),
        })

    return items
