from aiogram import types

from project.keyboards.inline.cancel import cancel_button


async def edit_wallets(wallets, state):
    wallets_buttons = []
    for wallet in wallets:
        wallets_buttons.append(types.InlineKeyboardButton(text=wallet.wallet_number,
                                                          callback_data=f"wallet-number_{wallet.wallet_number}"))
    cansel_b = await cancel_button(state)
    wallets_buttons.append(cansel_b)
    # keyboard = types.InlineKeyboardMarkup(inline_keyboard=[wallets_buttons])
    return wallets_buttons
