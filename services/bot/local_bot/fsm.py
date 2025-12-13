from typing import Any, Dict
from aiogram import Bot
from services.bot.local_bot.storage import user_states, save_user_states


def _st(uid: str) -> Dict[str, Any]:
    return user_states.setdefault(uid, {})


def _save():
    save_user_states()


class FSM:
    def __init__(self, uid: str):
        self.uid = uid

    def get(self):
        return _st(self.uid)

    def set(self, **kwargs):
        st = _st(self.uid)
        st.update(kwargs)
        _save()

    def clear(self):
        user_states[self.uid] = {}
        _save()

    def add_prompt(self, msg_id: int):
        st = _st(self.uid)
        st.setdefault("prompts", []).append(msg_id)
        _save()

    async def clear_prompts(self, bot: Bot, chat_id: int):
        st = _st(self.uid)
        for mid in st.get("prompts", []):
            try:
                await bot.delete_message(chat_id, mid)
            except:
                pass
        st["prompts"] = []
        _save()

    async def show_menu(self, bot: Bot, chat_id: int, text: str, kb):
        st = _st(self.uid)
        old_menu_id = st.get("menu_id")

        if old_menu_id:
            try:
                await bot.delete_message(chat_id, old_menu_id)
            except:
                pass

        try:
            await bot.edit_message_reply_markup(chat_id, chat_id, reply_markup=None)
        except:
            pass

        msg = await bot.send_message(chat_id, text, reply_markup=kb)
        st["menu_id"] = msg.message_id
        _save()

    async def final(self, bot: Bot, chat_id: int, text: str):
        await bot.send_message(chat_id, text)


def fsm(uid: str) -> FSM:
    return FSM(uid)
