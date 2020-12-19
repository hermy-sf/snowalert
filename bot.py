from telegram import Update
from telegram.ext import Updater, CommandHandler, CallbackContext

from logger import logger

import datetime
from forecast import Forecast

from my_config import TOKEN, PRIVILEGED, checktimes


#==================================================================#

cities = {}
# chats = {
#    chatid: {
#       city1: [ job1, job2, ...]
#       city2: [ ... ] 
#    }
# }
chats = {}

def get_jobnames(name, chat_id):
    return [ "{}_hour{}_{}".format(name, h.hour, str(chat_id)) for h in checktimes ]


def snow_alert(context):
    """Check for snow and send message"""
    job = context.job
    try:
        snow, det = cities[job.context[1]].check_snow_tomorrow()
        if snow:
            context.bot.send_message(job.context[0], text='Snow Alert! {}'.format(det))
    except RuntimeError:
        context.bot.send_message(job.context[0], text="Could not check weather for {}".format(job.context[1]))



def remove_job_if_exists(name, context):
    """Remove job with given name. Returns whether job was removed."""
    current_jobs = context.job_queue.get_jobs_by_name(name)
    if not current_jobs:
        return False
    for job in current_jobs:
        job.schedule_removal()
    return True


def create_forecast(lat, lon):
    try:
        forecast = Forecast(lat, lon)
        return True, forecast
    except RuntimeError:
        return False, None

#===============================================================#


def start(update: Update, context: CallbackContext) -> None:
    update.message.reply_text("""Telegram SnowAlert Bot.
    - Use `/alert <lat> <lon>` to get daily alerts for location
    - Use `/disable <lat> <lon>` to disable an alert by name
    - Use `/weather` to get a short weather forecast for alert locations
    - Use `/snow` to manually check for snow tomorrow on alert locations
    - Use `/list` to list all alerts""")


def list_jobs(update: Update, context: CallbackContext) -> None:
    chat_id = update.message.chat_id
    res = []
    if chat_id == PRIVILEGED:
        res = list(chats.items())
    else:
        if chat_id in chats:
            for j in chats[chat_id].keys():
                res.append(j)

    text = "" if len(res) > 0 else "No Jobs"
    for j in res:
        text+=str(j) + "\n"
    update.message.reply_text(text)


def weather(update: Update, context: CallbackContext) -> None:
    chat_id = update.message.chat_id
    text=""
    if chat_id in chats:
        for city in chats[chat_id]:
            text+="{}".format(cities[city].pretty_forecast())
    text = text if text!="" else "No locations configured"
    update.message.reply_text(text)



def snow(update: Update, context: CallbackContext) -> None:
    chat_id = update.message.chat_id
    text=""
    if chat_id in chats:
        for city in chats[chat_id]:
            try:
                snow, det = cities[city].check_snow_tomorrow()
                if snow:
                    text+=f"{city}: {det}\n"
            except RuntimeError:
                text+="Could not check weather for {}".format(city)
        if len(chats[chat_id].keys()) == 0:
            text="No locations configured"
    else:
        text="No locations configured"
    text = text if text!="" else "No snow tomorrow"
    update.message.reply_text(text)



def set_snow_alert(update: Update, context: CallbackContext) -> None:
    """Add a job to the queue."""
    chat_id = update.message.chat_id
    try:
    #if True:
        lat = float(context.args[0])
        lon = float(context.args[1])
        success, forecast = create_forecast(lat, lon)
        if not success:
            update.message.reply_text("Could not create forecast. Please try again later.")
            return

        exact_lat = forecast.lat
        exact_lon = forecast.lon
        name = "{}_{}".format(exact_lat, exact_lon)
        if name not in cities:
            cities[name] = forecast

        for t, n in zip(checktimes, get_jobnames(name, chat_id)):
            if chat_id in chats and name in chats[chat_id] and n in chats[chat_id][name]:
                update.message.reply_text('Alert already actve. Usage: `/alert <lat> <lon>`')
                return

            context.job_queue.run_daily(snow_alert, t, context=[chat_id, name], name=n)
            if chat_id not in chats:
                chats[chat_id] = { name: [] }
            if name not in chats[chat_id]:
                chats[chat_id][name] = []

            chats[chat_id][name].append(n)

        text="Set snow alerts for {}: {} {}".format(forecast.city, exact_lat, exact_lon)
        update.message.reply_text(text)

    except (IndexError, ValueError):
    #else:
        update.message.reply_text('Usage: `/alert <lat> <lon>`')



def unset(update: Update, context: CallbackContext) -> None:
    """Remove the job if the user changed their mind."""
    chat_id = update.message.chat_id
    text="Removed jobs: "
    try:
        exact_lat = str(context.args[0])
        exact_lon = str(context.args[1])
        name = "{}_{}".format(exact_lat, exact_lon)
        jobs_removed = 0
        for n in get_jobnames(name, chat_id):
            if remove_job_if_exists(n, context):
                jobs_removed+=1
            if chat_id in chats and name in chats[chat_id]:
                chats[chat_id][name].remove(n)
                if len(chats[chat_id][name]) == 0:
                    del chats[chat_id][name]
                if len(chats[chat_id].keys()) == 0:
                    del chats[chat_id]

        text += f"{jobs_removed}"
    except (IndexError, ValueError):
        update.message.reply_text('Usage: `/disable <lat> <lon>`')

    update.message.reply_text(text)


################################################################################

def main():
    """Run bot."""
    # Create the Updater and pass it your bot's token.
    # Make sure to set use_context=True to use the new context based callbacks
    # Post version 12 this will no longer be necessary
    updater = Updater(TOKEN, use_context=True)

    # Get the dispatcher to register handlers
    dispatcher = updater.dispatcher

    # on different commands - answer in Telegram
    dispatcher.add_handler(CommandHandler("alert", set_snow_alert))
    dispatcher.add_handler(CommandHandler("help", start))
    dispatcher.add_handler(CommandHandler("disable", unset))
    dispatcher.add_handler(CommandHandler("weather", weather))
    dispatcher.add_handler(CommandHandler("snow", snow))
    dispatcher.add_handler(CommandHandler("list", list_jobs))

    # Start the Bot
    updater.start_polling()

    # Block until you press Ctrl-C or the process receives SIGINT, SIGTERM or
    # SIGABRT. This should be used most of the time, since start_polling() is
    # non-blocking and will stop the bot gracefully.
    updater.idle()


if __name__ == '__main__':
    main()
