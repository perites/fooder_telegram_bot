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
        job_removed = remove_job_if_exists(str(chat_id), context)
        # context.job_queue.run_daily(general_menu, datetime.time(hour=8), chat_id=chat_id, name=str(chat_id))  # hour -2
        context.job_queue.run_once(general_menu, 1, chat_id=chat_id, name=str(chat_id))  # hour -2

        text = "You will get notifications "
        if job_removed:
            text += " Old one was removed "
        await update.effective_message.reply_text(text)

    except Exception as e:
        await update.effective_message.reply_text(f"Something went wrong  : {e}")


async def general_menu(context: ContextTypes.DEFAULT_TYPE):
    job = context.job
    responce = requests.get("http://127.0.0.1:5000/api/")
    answer = responce.json()

    if responce.status_code != 200:
        await context.bot.send_message(job.chat_id, text=f"bad api responce: {answer}")
        return

    menu_for_today = f"Сьогодні на обід : {', '.join(answer['lunch'])} \nСьогодні на вечерю : {', '.join(answer['dinner'])}"
    ingr_for_today = "\n".join([f"{ingr['name']} --- {ingr['amount']}" for ingr in answer['ingredients']])
    ingr_for_today = f"Сьогодні знадобиться : \n{ingr_for_today}"
    await context.bot.send_message(job.chat_id, text=menu_for_today)
    await context.bot.send_message(job.chat_id, text=ingr_for_today)

    if answer["deliverys"]["lunch_delivery"]:
        data = f"Замовити з <a href='{answer['deliverys']['lunch_delivery']['link']}'>{answer['deliverys']['lunch_delivery']['delivery_name']}</a>"
        context.job_queue.run_once(send_message_my, datetime.datetime(hour=10), data=data, parse_mode=ParseMode.HTML, chat_id=job.chat_id, name=f"{str(job.chat_id)} lunch_delivery")  # hour -2
        # context.job_queue.run_once(send_message_my, 1, data=data, chat_id=job.chat_id, name=f"{str(job.chat_id)} lunch_delivery")  # hour -2

    if answer["deliverys"]["dinner_delivery"]:
        data = f"Замовити з <a href='{answer['deliverys']['dinner_delivery']['link']}'>{answer['deliverys']['dinner_delivery']['delivery_name']}</a>"
        context.job_queue.run_once(send_message_my, datetime.datetime(hour=15), data=data, parse_mode=ParseMode.HTML, chat_id=job.chat_id, name=f"{str(job.chat_id)} lunch_delivery")  # hour -2
        # context.job_queue.run_once(send_message_my, 2, data=data, chat_id=job.chat_id, name=f"{str(job.chat_id)} dinner_delivery")  # hour -2

    if answer["weekday"] in ["Monday", "Friday", "Wednesday"]:
        data = "Нагадування готувати вечерю!"
        context.job_queue.run_once(send_message_my, datetime.datetime(hour=12), data=data, parse_mode=ParseMode.HTML, chat_id=job.chat_id, name=f"{str(job.chat_id)} cook dinner1")  # hour -2
        context.job_queue.run_once(send_message_my, datetime.datetime(hour=15), data=data, parse_mode=ParseMode.HTML, chat_id=job.chat_id, name=f"{str(job.chat_id)} cook dinner2")  # hour -2

        # context.job_queue.run_once(send_message_my, 4, data=data, chat_id=job.chat_id, name=f"{str(job.chat_id)} cook dinner1")  # hour -2
        # context.job_queue.run_once(send_message_my, 5, data=data, chat_id=job.chat_id, name=f"{str(job.chat_id)} cook dinner2")  # hour -2

    elif answer["weekday"] in ["Tuesday", "Thursday"]:
        data = "Нагадування приготувати обід!"
        context.job_queue.run_once(send_message_my, datetime.datetime(hour=9, minute=30), data=data, parse_mode=ParseMode.HTML, chat_id=job.chat_id, name=f"{str(job.chat_id)} lunch_delivery")  # hour -2
        # context.job_queue.run_once(send_message_my, 3, data=data, chat_id=job.chat_id, name=f"{str(job.chat_id)} cook lunch")  # hour -2


async def send_message_my(context: ContextTypes.DEFAULT_TYPE):
    job = context.job
    await context.bot.send_message(job.chat_id, text=job.data, parse_mode=ParseMode.HTML)


def remove_job_if_exists(name: str, context: ContextTypes.DEFAULT_TYPE) -> bool:
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
