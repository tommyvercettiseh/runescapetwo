from actions.click_object import click_object


def click_furnace(bot_id: int = 1):
    return click_object("furnace", bot_id=bot_id)
