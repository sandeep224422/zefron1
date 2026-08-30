# ==============================================================================
# radio.py - Live Radio
# ==============================================================================
# Opens a paginated station picker and streams the selected station directly in
# the current voice chat.  Radio is intentionally available to every member;
# only playback controls remain admin/authorized-user restricted.
# ==============================================================================

from pyrogram import enums, errors, filters, types

from ZefronMusic import app, config, db, lang, logger, queue, tune
from ZefronMusic.helpers import Track, buttons


# Public streams.  Keep the callback key short; the full URL never goes into
# Telegram callback data.
RADIO_STATIONS = {
    # Page 1: Bollywood, ordered from new to old.
    "bollywood_new": {"label": "New Bolly", "url": "https://drive.uber.radio/uber/bollywoodnow/icecast.audio"},
    "bollywood_2010s": {"label": "2010s ", "url": "https://drive.uber.radio/uber/bollywood2010s/icecast.audio"},
    "hindi_2000s": {"label": "2000s Bolly", "url": "https://drive.uber.radio/uber/bollywood2000s/icecast.audio"},
    "radio_bollywood_hits": {"label": "Hits Bolly", "url": "https://stream.zeno.fm/143d7gty24zuv"},
    "hindi_90s": {"label": "90s Bolly", "url": "https://stream.zeno.fm/rm4i9pdex3cuv"},
    "bollywood_classics": {"label": "Retro Bolly", "url": "https://stream.zeno.fm/6n6ewddtad0uv"},

    # Page 2: new Haryanvi first, then two old Haryanvi choices.
    "haryanvi_kasoot": {"label": "New Haryanvi", "url": "https://azuracast.radiokasoot.com/radio/8000/listen"},
    "haryanvi_khas": {"label": "Hr Hits", "url": "https://puma.streemlion.com:4130/stream"},
    "haryanvi_maharani": {"label": "Hr Mix", "url": "https://streamasiacdn.atc-labs.com/radiomaharani.aac"},
    "haryanvi_desi": {"label": "Hr Fresh", "url": "https://stream.zeno.fm/0r0xa792kwzuv"},
    "haryanvi_old": {"label": "Old Hr", "url": "https://stream.zeno.fm/7yhq985hnxhvv"},
    "haryanvi_gold": {"label": "Hr Gold", "url": "https://stream.zeno.fm/yz0ncx9gha0uv"},

    # Page 3: new Punjabi first, then two old Punjabi choices.
    "punjabi_bol": {"label": "New Punjabi", "url": "https://bolpunjabi-ekamsoftware.radioca.st/stream"},
    "punjabi_britasia": {"label": "Punj Hits", "url": "https://s4.radio.co/sfefce156f/listen"},
    "punjabi_risham": {"label": "Punj Mix", "url": "https://stream.zeno.fm/4pd041xv1a0uv"},
    "punjabi_desi": {"label": "Punj Fresh", "url": "https://stream.zenolive.com/4mbfcn4mf24tv"},
    "punjabi_old": {"label": "Old Punj", "url": "https://gurbanikirtan.radioca.st/start.mp3"},
    "punjabi_gold": {"label": "Punj Gold", "url": "https://live.sgpc.net:8443/;stream.mp3"},

    # Remaining nonstop Indian regional streams.
    "bengali": {"label": "Bengali", "url": "https://audio.streamcast.xyz/listen/radiogoongoon/radio.mp3"},
    "tamil": {"label": "Tamil", "url": "https://psrlive2.listenon.in/80?station=tamil80shitsradio"},
    "telugu": {"label": "Telugu", "url": "https://air.pc.cdn.bitgravity.com/air/live/pbaudio032/playlist.m3u8"},
    "marathi": {"label": "Marathi", "url": "https://airhlspush.pc.cdn.bitgravity.com/httppush/hlspbaudio008/hlspbaudio008_Auto.m3u8"},
    "bhojpuri": {"label": "Bhojpuri", "url": "https://stream.zeno.fm/yz0ncx9gha0uv"},
    "kannada": {"label": "Kannada", "url": "https://stream.zeno.fm/68snnbug8rhvv"},
    "hindi_gold": {"label": "Hindi Gold", "url": "https://azuracast.vibesounds.in:8010/radio.mp3"},
    "vividh_bharati": {"label": "Vividh", "url": "https://air.pc.cdn.bitgravity.com/air/live/pbaudio001/playlist.m3u8"},
    "malayalam": {"label": "Malayalam", "url": "https://stream.zeno.fm/9x1sw687nf9uv"},
    "odia": {"label": "Odia", "url": "https://stream.zeno.fm/x1q3r3qdxy8uv"},
    "assamese": {"label": "Assamese", "url": "https://internetradio.gupshupradio.com:8080/?type=mp3"},
    "nepali": {"label": "Nepali", "url": "https://radio-broadcast.ekantipur.com/stream"},
    "urdu": {"label": "Urdu", "url": "https://samaakhi107-itelservices.radioca.st/stream"},
    "tamil_panpalai": {"label": "Panpalai", "url": "https://tamilpanpalai.radioca.st/ind"},
    "tamil_90s": {"label": "Tamil90s", "url": "https://stream.zeno.fm/tqnws2eafwzuv.aac"},
    "kannada_amr": {"label": "AMR", "url": "https://stream.zenolive.com/7g8axtgtsg0uv"},
    "radio_city_kannada": {"label": "CityKannada", "url": "https://playerservices.streamtheworld.com/api/livestream-redirect/RADIO_SUNO_MELODY_S06.mp3"},
    "bhojpuri_kesari": {"label": "Kesari", "url": "https://stream.zeno.fm/7yhq985hnxhvv"},
    "bhojpuri_sneh": {"label": "Sneh", "url": "https://stream.zeno.fm/zqyhigwwo5mvv"},
    "bengali_a2z": {"label": "A2Z", "url": "https://listen.radioking.com/radio/1743/stream/125"},
    "bengali_mellow": {"label": "Mellow", "url": "https://radio.mellowbangla.com/stream"},
    "raagam": {"label": "Raagam", "url": "https://airhlspush.pc.cdn.bitgravity.com/httppush/hlspbaudioragam/hlspbaudioragam_Auto.m3u8"},
}


def _radio_text(lang_dict) -> str:
    return lang_dict["radio_menu"]


async def _answer_callback(
    query: types.CallbackQuery, text: str = None, show_alert: bool = False
) -> None:
    """Answer a callback without failing when Telegram has expired its query ID."""
    try:
        if text:
            await query.answer(text, show_alert=show_alert)
        else:
            await query.answer()
    except errors.QueryIdInvalid:
        logger.debug("Ignoring expired radio callback query.")


async def _ensure_assistant(chat_id: int) -> bool:
    """Make sure the selected assistant can resolve and join this group."""
    client = await db.get_client(chat_id)
    if not client:
        return False

    try:
        member = await app.get_chat_member(chat_id, client.id)
        if member.status in (
            enums.ChatMemberStatus.BANNED,
            enums.ChatMemberStatus.RESTRICTED,
        ):
            await app.unban_chat_member(chat_id, client.id)
    except errors.UserNotParticipant:
        try:
            chat = await app.get_chat(chat_id)
            invite_link = (
                f"https://t.me/{chat.username}"
                if chat.username
                else chat.invite_link
            )
            if not invite_link:
                invite_link = await app.export_chat_invite_link(chat_id)
            try:
                await client.join_chat(invite_link)
            except errors.InviteRequestSent:
                await app.approve_chat_join_request(chat_id, client.id)
        except errors.UserAlreadyParticipant:
            pass
        except Exception as exc:
            logger.warning("Could not join assistant to radio chat %s: %s", chat_id, exc)
            return False
    except Exception as exc:
        logger.warning("Could not verify assistant in radio chat %s: %s", chat_id, exc)
        return False

    try:
        await client.resolve_peer(chat_id)
        return True
    except Exception as exc:
        logger.warning("Could not resolve radio chat %s: %s", chat_id, exc)
        return False


async def _show_radio_menu(query: types.CallbackQuery, page: int) -> None:
    markup = buttons.radio_markup(RADIO_STATIONS, page)
    try:
        await query.edit_message_caption(
            caption=_radio_text(query.lang),
            reply_markup=markup,
        )
    except Exception:
        await query.edit_message_text(
            text=_radio_text(query.lang),
            reply_markup=markup,
        )


@app.on_message(filters.command("radio") & filters.group & ~app.bl_users)
@lang.language()
async def radio_command(_, message: types.Message):
    if not message.from_user:
        return

    try:
        await message.delete()
    except Exception:
        pass

    try:
        await message.reply_photo(
            photo=config.RADIO_IMG,
            caption=_radio_text(message.lang),
            reply_markup=buttons.radio_markup(RADIO_STATIONS),
            quote=False,
        )
    except Exception:
        # Keep /radio usable when Telegram cannot fetch the configured image.
        await message.reply_text(
            text=_radio_text(message.lang),
            reply_markup=buttons.radio_markup(RADIO_STATIONS),
            quote=False,
        )


@app.on_callback_query(filters.regex(r"^radio(?::|$)") & ~app.bl_users)
@lang.language()
async def radio_callback(_, query: types.CallbackQuery):
    if not query.from_user or not query.message:
        return

    data = query.data.split(":")
    action = data[1] if len(data) > 1 else ""

    if action == "close":
        await _answer_callback(query)
        try:
            await query.message.delete()
        except Exception:
            pass
        return

    if action == "page":
        await _answer_callback(query)
        try:
            page = int(data[2])
        except (IndexError, ValueError):
            page = 0
        return await _show_radio_menu(query, page)

    station = RADIO_STATIONS.get(action)
    if not station:
        await _answer_callback(
            query, "❌ This station is no longer available.", show_alert=True
        )
        return

    chat_id = query.message.chat.id
    if query.message.chat.type != enums.ChatType.SUPERGROUP:
        await _answer_callback(
            query,
            query.lang["play_chat_invalid"].replace("ᴛʜɪꜱ ʙᴏᴛ", "ᴛʜɪꜱ ꜰᴇᴀᴛᴜʀᴇ"),
            show_alert=True,
        )
        return

    if len(queue.get_queue(chat_id)) >= config.QUEUE_LIMIT:
        await _answer_callback(
            query,
            query.lang["play_queue_full"].format(config.QUEUE_LIMIT),
            show_alert=True,
        )
        return

    await _answer_callback(query, "📻 Connecting to the radio station...")

    if not await db.get_call(chat_id) and not await _ensure_assistant(chat_id):
        return await query.message.reply_text(query.lang["radio_assistant_error"])

    track = Track(
        id=action,
        channel_name="Live Radio",
        duration="LIVE",
        duration_sec=0,
        title=station["label"],
        url=station["url"],
        file_path=station["url"],
        thumbnail=config.RADIO_IMG,
        user=query.from_user.mention,
        is_live=True,
    )

    position = queue.add(chat_id, track)
    try:
        await query.message.delete()
    except Exception:
        pass

    if await db.get_call(chat_id) or position > 0:
        await app.send_message(
            chat_id,
            query.lang["radio_queued"].format(station["label"], position),
        )
        return

    status = await app.send_message(
        chat_id,
        query.lang["radio_connecting"].format(station["label"]),
    )
    try:
        await tune.play_media(chat_id=chat_id, message=status, media=track)
    except Exception as exc:
        logger.error("Radio playback failed in %s: %s", chat_id, exc, exc_info=True)
        queue.clear(chat_id)
        try:
            await status.edit_text(query.lang["radio_error"])
        except Exception:
            pass
