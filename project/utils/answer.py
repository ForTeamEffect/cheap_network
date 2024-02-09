import contextlib
# from typing import assert_never,
try:
    from typing import NoReturn
except Exception as e:
    print(e)
from aiogram import types, Bot
from aiogram.exceptions import TelegramAPIError
from aiogram.types import InputMediaVideo, InputMediaPhoto, InputMediaDocument, InputMediaAudio, \
    Message, InlineKeyboardMarkup, ReplyKeyboardMarkup, ReplyKeyboardRemove
from loguru import logger

from project.utils.kwargs import filter_kwargs

def assert_never(x: NoReturn) -> NoReturn:
    raise AssertionError(f"Unhandled type: {type(x).__name__}")


async def answer(
        message: Message = None,
        *,
        chat_id: int = None,
        text: str = None,
        audio: InputMediaAudio = None,
        document: InputMediaDocument = None,
        photo: InputMediaPhoto = None,
        video: InputMediaVideo = None,
        media_group: list[InputMediaAudio | InputMediaDocument | InputMediaPhoto | InputMediaVideo] = None,
        reply_markup: InlineKeyboardMarkup | ReplyKeyboardMarkup | ReplyKeyboardRemove = None,
        retry: bool = True,
        force_delete: bool = False,
        **common_kwargs,
) -> Message | None:
    assert bool(message) ^ bool(chat_id)
    chat_id = chat_id or message.chat.id
    message_id = message.message_id if message else None

    media_group = media_group or []
    media_group.extend(media for media in (audio, document, photo, video) if media)
    assert len(media_group) <= 10

    assert not message_id or message_id and len(media_group) <= 1
    assert not reply_markup or reply_markup and len(media_group) <= 1

    audio_amount = bool(audio) + sum(isinstance(media, InputMediaAudio) for media in media_group)
    assert audio_amount == 0 or audio_amount == len(media_group)

    text = text or ''
    assert media_group or text

    bot = Bot.get_current()

    async def delete():
        nonlocal message_id
        with contextlib.suppress(TelegramAPIError):
            await message.delete()
        message_id = None

    if force_delete:
        await delete()
    elif message:
        prev_media = message.audio or message.document or message.photo or message.video
        if bool(prev_media) != bool(media_group) or isinstance(reply_markup, types.ReplyKeyboardMarkup):
            await delete()

    async def edit() -> Message:
        if media_group:
            media, = media_group
            media.caption = shrink_text(text, 1024)
            return await bot.edit_message_media(
                chat_id=chat_id,
                message_id=message_id,
                media=media,
                reply_markup=reply_markup,
                **filter_kwargs(bot.edit_message_media, **common_kwargs),
            )
        else:
            return await bot.edit_message_text(
                chat_id=chat_id,
                message_id=message_id,
                text=shrink_text(text, 4096),
                reply_markup=reply_markup,
                **filter_kwargs(bot.edit_message_text, **common_kwargs),
            )

    async def send() -> Message:
        if media_group:
            media, *other_media = media_group
            media.caption = shrink_text(text, 1024)
            if reply_markup or not other_media:
                kwargs = dict(
                    chat_id=chat_id,
                    caption=shrink_text(text, 1024),
                    reply_markup=reply_markup,
                )
                match media:
                    case InputMediaAudio():
                        return await bot.send_audio(
                            audio=media.media,
                            **kwargs,
                            **filter_kwargs(bot.send_audio, **common_kwargs),
                        )
                    case InputMediaDocument():
                        return await bot.send_document(
                            document=media.media,
                            **kwargs,
                            **filter_kwargs(bot.send_document, **common_kwargs),
                        )
                    case InputMediaPhoto():
                        return await bot.send_photo(
                            photo=media.media,
                            **kwargs,
                            **filter_kwargs(bot.send_photo, **common_kwargs),
                        )
                    case InputMediaVideo():
                        return await bot.send_video(
                            video=media.media,
                            **kwargs,
                            **filter_kwargs(bot.send_video, **common_kwargs),
                        )
                    case _ as unreachable:
                        assert_never(unreachable)
            else:
                return await bot.send_media_group(
                    chat_id=chat_id,
                    media=media_group,
                    **filter_kwargs(bot.send_media_group, **common_kwargs),
                )
        else:
            return await bot.send_message(
                chat_id=chat_id,
                text=shrink_text(text, 4096),
                reply_markup=reply_markup,
                **filter_kwargs(bot.send_message, **common_kwargs),
            )

    try:
        if message_id:
            return await edit()
        else:
            return await send()
    except TelegramAPIError as e:
        if "message is not modified" in e.message:
            return message
        elif "message can't be edited" in e.message:
            with contextlib.suppress(TelegramAPIError):
                await message.delete()
        else:
            logger.exception(e)

    if retry:
        try:
            return await send()
        except TelegramAPIError as e:
            logger.exception(e)
