from telethon import TelegramClient, functions, types, events
import time
import datetime
from config import API_ID, API_HASH, BOT_TOKEN, OWNER_ID

# Console text colors
F = '\033[1;32m'
Z = '\033[1;31m'

# Initialize the client
client = TelegramClient('bot_session', API_ID, API_HASH).start(bot_token=BOT_TOKEN)

# Member add limit variables
member_add_limit = 50
added_members_count = 0
start_time = datetime.datetime.now()

# Helper function to check if the user is the owner
def is_owner(event):
    return event.sender_id == OWNER_ID

# Reset the member add counter every 24 hours
def reset_member_add_counter():
    global added_members_count, start_time
    while True:
        now = datetime.datetime.now()
        if (now - start_time).days >= 1:
            added_members_count = 0
            start_time = now
        time.sleep(3600)  # Check every hour

# Start the reset counter in the background
import threading
threading.Thread(target=reset_member_add_counter, daemon=True).start()

# Ping Command
@client.on(events.NewMessage(pattern='/ping'))
async def ping(event):
    if is_owner(event):
        await event.respond('Pong! Bot is active.')
    else:
        await event.respond(Z + "You are not authorized to use this command.")

# Member Transfer Function
async def transfer_members(event, source_group, target_group):
    global added_members_count
    try:
        entity = await client.get_entity(source_group)
        all_participants = await client.get_participants(entity)

        for participant in all_participants:
            if added_members_count >= member_add_limit:
                await event.respond(Z + "Daily member add limit reached.")
                break

            try:
                await client(functions.channels.InviteToChannelRequest(
                    channel=target_group,
                    users=[types.InputUser(
                        user_id=participant.id,
                        access_hash=participant.access_hash
                    )]
                ))
                added_members_count += 1
                await event.respond(F + "Member {} was successfully moved to the channel".format(participant.first_name))
                time.sleep(1)  # Reduced sleep time to avoid rapid requests
            except Exception as e:
                await event.respond(Z + "\nError moving member {} to channel: {}".format(participant.first_name, str(e)))
    except Exception as e:
        await event.respond(Z + "Failed to transfer members: {}".format(str(e)))

# Active Member Transfer Function
async def transfer_active_members(event, source_group, target_group, days_active):
    global added_members_count
    try:
        entity = await client.get_entity(source_group)
        all_participants = await client.get_participants(entity)

        now = datetime.datetime.now()
        active_cutoff = now - datetime.timedelta(days=days_active)

        for participant in all_participants:
            if added_members_count >= member_add_limit:
                await event.respond(Z + "Daily member add limit reached.")
                break

            if participant.status and hasattr(participant.status, 'was_online'):
                last_seen = participant.status.was_online
                if last_seen and last_seen > active_cutoff:
                    try:
                        await client(functions.channels.InviteToChannelRequest(
                            channel=target_group,
                            users=[types.InputUser(
                                user_id=participant.id,
                                access_hash=participant.access_hash
                            )]
                        ))
                        added_members_count += 1
                        await event.respond(F + "Active member {} was successfully moved to the channel".format(participant.first_name))
                        time.sleep(1)  # Reduced sleep time to avoid rapid requests
                    except Exception as e:
                        await event.respond(Z + "\nError moving active member {} to channel: {}".format(participant.first_name, str(e)))
    except Exception as e:
        await event.respond(Z + "Failed to transfer active members: {}".format(str(e)))

# Member Add Function
async def add_member(event, target_group, user_id):
    global added_members_count
    if added_members_count >= member_add_limit:
        await event.respond(Z + "Daily member add limit reached.")
        return

    try:
        await client(functions.channels.InviteToChannelRequest(
            channel=target_group,
            users=[types.InputUser(
                user_id=user_id,
                access_hash=0  # Use 0 if access_hash is unknown
            )]
        ))
        added_members_count += 1
        await event.respond(F + "Member with ID {} was successfully added to the channel".format(user_id))
    except Exception as e:
        await event.respond(Z + "Failed to add member: {}".format(str(e)))

# Member Remove Function
async def remove_member(event, target_group, user_id):
    try:
        await client(functions.channels.EditBannedRequest(
            channel=target_group,
            user_id=user_id,
            banned_rights=types.ChatBannedRights(until_date=None, view_messages=True)
        ))
        await event.respond(F + "Member with ID {} was successfully removed from the channel".format(user_id))
    except Exception as e:
        await event.respond(Z + "Failed to remove member: {}".format(str(e)))

# Channel Statistics Function
async def get_channel_stats(event):
    try:
        channel_link = event.pattern_match.group(1)
        cha = await client.get_entity(channel_link)
        full_chat = await client(functions.channels.GetFullChannelRequest(cha)).full_chat
        participants_count = full_chat.participants_count
        description = full_chat.about
        title = full_chat.chat.title
        await event.respond(F + "Channel Title: {}\nMembers: {}\nDescription: {}".format(title, participants_count, description))
    except Exception as e:
        await event.respond(Z + "Failed to retrieve channel stats: {}".format(str(e)))

# Command Handlers
@client.on(events.NewMessage(pattern='/transfer (.+) (.+)'))
async def transfer(event):
    if is_owner(event):
        source_group, target_group = event.pattern_match.group(1), event.pattern_match.group(2)
        await transfer_members(event, source_group, target_group)
    else:
        await event.respond(Z + "You are not authorized to use this command.")

@client.on(events.NewMessage(pattern='/transfer_active (.+) (.+) (.+)'))
async def transfer_active(event):
    if is_owner(event):
        source_group, target_group, days_active = event.pattern_match.group(1), event.pattern_match.group(2), int(event.pattern_match.group(3))
        await transfer_active_members(event, source_group, target_group, days_active)
    else:
        await event.respond(Z + "You are not authorized to use this command.")

@client.on(events.NewMessage(pattern='/addmember (.+) (.+)'))
async def add(event):
    if is_owner(event):
        target_group, user_id = event.pattern_match.group(1), int(event.pattern_match.group(2))
        await add_member(event, target_group, user_id)
    else:
        await event.respond(Z + "You are not authorized to use this command.")

@client.on(events.NewMessage(pattern='/removemember (.+) (.+)'))
async def remove(event):
    if is_owner(event):
        target_group, user_id = event.pattern_match.group(1), int(event.pattern_match.group(2))
        await remove_member(event, target_group, user_id)
    else:
        await event.respond(Z + "You are not authorized to use this command.")

@client.on(events.NewMessage(pattern='/stats (.+)'))
async def stats(event):
    if is_owner(event):
        await get_channel_stats(event)
    else:
        await event.respond(Z + "You are not authorized to use this command.")

@client.on(events.NewMessage(pattern='/start'))
async def start(event):
    if is_owner(event):
        await event.respond('Hello! I am your bot. How can I assist you today?')
    else:
        await event.respond(Z + "You are not authorized to use this bot.")

# Run the bot
print("Bot is up and running...")
client.run_until_disconnected()
      
