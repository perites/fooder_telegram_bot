import datetime
import requests

from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes
from telegram.constants import ParseMode
from confg import bot_token


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Hi! Use /notifications to get menu notifications")


async def notifications(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_message.chat_id

    try:
        job_removed = {}

        for name in ["cook dinner2", "cook dinner1", "dinner_delivery", "lunch_delivery", "ingr_for_today", "menu_for_today"]:
            job_removed[f"{str(chat_id)} {name}"] = remove_job_if_exists(f"{str(chat_id)} {name}", context)

        job_removed[f"{str(chat_id)}"] = remove_job_if_exists(f"{str(chat_id)}", context)
        context.job_queue.run_daily(general_menu, datetime.time(hour=7, minute=30), chat_id=chat_id, name=str(chat_id))

        text = "You will get notifications "
        if True in job_removed.values():
            text += f" Old one was removed \n{job_removed}"

        await update.effective_message.reply_text(text)

    except Exception as e:
        await update.effective_message.reply_text(f"Something went wrong  : {e}")


async def general_menu(context: ContextTypes.DEFAULT_TYPE):
    job = context.job
    responce = requests.get("https://fooder.onrender.com/api/")
    answer = responce.json()

    if responce.status_code != 200:
        await context.bot.send_message(job.chat_id, text=f"bad api responce: {answer}")
        return

    if answer["weekday"] in ["Saturday", "Sunday"]:
        return

    menu_for_today = f"Сьогодні на обід : {', '.join(answer['lunch'])} \nСьогодні на вечерю : {', '.join(answer['dinner'])}"
    ingr_for_today = "\n".join([f"{ingr['name']} --- {ingr['amount']}" for ingr in answer['ingredients']])
    ingr_for_today = f"Сьогодні знадобиться : \n{ingr_for_today}"

    context.job_queue.run_once(send_message_my, datetime.time(hour=8), data=menu_for_today, chat_id=job.chat_id, name=f"{str(job.chat_id)} menu_for_today")  # hour -2
    context.job_queue.run_once(send_message_my, datetime.time(hour=8), data=ingr_for_today, chat_id=job.chat_id, name=f"{str(job.chat_id)} ingr_for_today")  # hour -2

    if answer["deliverys"].get("lunch_delivery"):
        data = f"Замовити з <a href='{answer['deliverys']['lunch_delivery']['link']}'>{answer['deliverys']['lunch_delivery']['delivery_name']}</a>"
        context.job_queue.run_once(send_message_my, datetime.time(hour=10), data=data, chat_id=job.chat_id, name=f"{str(job.chat_id)} lunch_delivery")  # hour -2

    if answer["deliverys"].get("dinner_delivery"):
        data = f"Замовити з <a href='{answer['deliverys']['dinner_delivery']['link']}'>{answer['deliverys']['dinner_delivery']['delivery_name']}</a>"
        context.job_queue.run_once(send_message_my, datetime.time(hour=15), data=data, chat_id=job.chat_id, name=f"{str(job.chat_id)} lunch_delivery")  # hour -2

    if answer["weekday"] in ["Monday", "Friday", "Wednesday"]:
        data = "Нагадування готувати вечерю!"
        context.job_queue.run_once(send_message_my, datetime.time(hour=12), data=data, chat_id=job.chat_id, name=f"{str(job.chat_id)} cook dinner1")  # hour -2
        context.job_queue.run_once(send_message_my, datetime.time(hour=15), data=data, chat_id=job.chat_id, name=f"{str(job.chat_id)} cook dinner2")  # hour -2

    elif answer["weekday"] in ["Tuesday", "Thursday"]:
        data = "Нагадування приготувати обід!"
        context.job_queue.run_once(send_message_my, datetime.time(hour=9, minute=30), data=data, chat_id=job.chat_id, name=f"{str(job.chat_id)} lunch_delivery")  # hour -2


async def send_message_my(context: ContextTypes.DEFAULT_TYPE):
    job = context.job
    await context.bot.send_message(job.chat_id, text=job.data, parse_mode=ParseMode.HTML)


def remove_job_if_exists(name: str, context: ContextTypes.DEFAULT_TYPE):
    current_jobs = context.job_queue.get_jobs_by_name(name)
    if not current_jobs:
        return False
    for job in current_jobs:
        job.schedule_removal()
    return True


def main():
    application = Application.builder().token(bot_token).build()

    application.add_handler(CommandHandler(["start", "help"], start))
    application.add_handler(CommandHandler("notifications", notifications))

    application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
