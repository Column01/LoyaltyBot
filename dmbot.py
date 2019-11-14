# Name: dmbot.py
# Description: A bot that manages roles for users based on their time in the server
# Author: Colin Andress
# Date Created: 11/12/2019

import discord
import asyncio
import pytz
from datetime import datetime
import modules.dmdatabase as db
db.create_tables()

# Discord bot token from disk and init other misc info
token = open("token.txt", "r").read()
prefix = "!"
status = "who's loyal, and who's not!"

client = discord.Client()


@client.event
# When the bot connects to discord
async def on_ready():
    botname = client.user.name
    print(f"{botname} connected to discord!")
    # Setting discord presence
    await client.change_presence(activity=discord.Activity(name=status, type=discord.ActivityType.watching))
    print(f"Setting discord presence to: Watching {status}")
    print(f"{botname} is apart of the following guilds:")
    for guild in client.guilds:
        num = client.guilds.index(guild) + 1
        print(f"\t{num}. {guild.name} (id: {guild.id})")


@client.event
# When a member joins a guild
async def on_member_join(member):
    # Loop over all connected guilds
    for guild in client.guilds:
        # If the guild is the member's guild, send a welcome message to the system channel
        if guild == member.guild:
            await guild.system_channel.send(f"Welcome {member.name} to {guild.name}!")


@client.event
# When a member sends a message
async def on_message(message):
    # and the message is "{prefix}hello", send a welcome message
    command = message.content.split()
    if command[0] == prefix + "dm":
        if command[1] == "create":
            for dm in message.mentions:
                try_add_dm = db.add_dm(dm.id)
                added_roles = []
                for role in message.role_mentions:
                    await dm.add_roles(role)
                    added_roles.append(role.name)
                added_roles = ", ".join(added_roles)
                if try_add_dm:
                    await message.channel.send(f"Added the DM: `{dm.name}` to the database "
                                               f"and assigned them the role(s): `{added_roles}`")
                else:
                    allowed_roles = db.get_allowed_roles(dm.id)
                    role_names = []
                    for roleid in allowed_roles:
                        role_names.append(message.guild.get_role(int(roleid)).name)
                    if allowed_roles is not None:
                        role_names = ", ".join(role_names)
                        await message.channel.send(f"`{dm.name}` is already a DM "
                                                   f"and is allowed to give the following roles:\n `{role_names}`")
        if command[1] == "allow":
            for dm in message.mentions:
                role_ids = []
                role_names = []
                for role in message.role_mentions:
                    role_ids.append(str(role.id))
                    role_names.append(role.name)
                try_add_roles = db.add_allowed_roles(dm.id, role_ids)
                role_names = ", ".join(role_names)
                if try_add_roles is False:
                    await message.channel.send(f"Failed to add roles to the DM: `{dm.name}`. "
                                               f"\nDid you make them a DM using '!dm create'?")
                else:
                    if len(try_add_roles) != 0:
                        try_add_roles = ", ".join(try_add_roles)
                        await message.channel.send(f"Added the roles: `{try_add_roles}` to the DM: `{dm.name}`")
                    else:
                        await message.channel.send(f"`{dm.name}` already has roles: `{role_names}`")


def user_has_role(guild, userid, roleid):
    user_roles = guild.get_member(userid).roles
    for role in user_roles:
        if role.id == roleid:
            return True
    return False


def is_current_time(t):
    # Get time and compare it to the given time.
    ti = datetime.now(pytz.timezone("US/Eastern"))
    ft = datetime.strftime(ti, "%m/%d/%y %H:%M EST")
    return t == ft


# Loop over all users and get their time as members
async def check_users():
    await client.wait_until_ready()
    await asyncio.sleep(1)
    while True:
        # Loop over every guild the bot is a part of
        for guild in client.guilds:
            # Loop over every member in that guild
            for member in guild.members:
                # ignore bots
                if member.bot:
                    continue
                # get their joined time and convert it to datetime format
                joined = datetime.fromisoformat(str(member.joined_at))
                # get the current datetime format
                current = datetime.now()
                # subtract them to get the days they've been a member
                days = abs(current-joined).days
                if days >= 1:
                    # check for a default role
                    default_role = discord.utils.get(guild.roles, name="Default")
                    # if it doesn't exist, make the role
                    if default_role is None:
                        default_role = await guild.create_role(name="Default", reason="Blank Bot Role")
                        print(f"Creating default role for {guild.name}")
                    # if they don't have the default role, give it to them
                    if not user_has_role(guild, member.id, default_role.id):
                        print(f"{member.name} in {guild.name} does not have default role. Adding to user")
                        await member.add_roles(default_role, reason="Playtime Requirements")
        # Run every three seconds
        await asyncio.sleep(3)


async def set_server_time():
    await client.wait_until_ready()
    await asyncio.sleep(1)
    while True:
        # Get current EST time and format it
        t = datetime.now(pytz.timezone("US/Eastern"))
        formatted_time = datetime.strftime(t, "%m/%d/%y %H:%M EST")
        # for all guilds that the bot is connected to
        for guild in client.guilds:
            # set some overwrites to prevent joining
            overwrites = {}
            for role in guild.roles:
                overwrites[role] = discord.PermissionOverwrite(connect=False)
            server_time_category = discord.utils.get(guild.categories, name="Server Time")
            if server_time_category is None:
                server_time_category = await guild.create_category(name="Server Time")
            if len(server_time_category.voice_channels) == 0:
                await server_time_category.create_voice_channel(name=formatted_time, overwrites=overwrites)
            else:
                for vc in server_time_category.voice_channels:
                    await vc.edit(name=formatted_time, overwrites=overwrites)
        await asyncio.sleep(1)

# Register my loop task and run the bot
client.loop.create_task(check_users())
client.loop.create_task(set_server_time())
client.run(token)