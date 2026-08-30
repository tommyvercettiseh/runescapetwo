from actions.click_object import click_object


def click_bank(bot_id: int = 1):
    return click_object("bank", bot_id=bot_id)
