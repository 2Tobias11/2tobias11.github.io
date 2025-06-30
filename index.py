# importing

import discord
import asyncio
import os
from discord import Embed
from discord.ext import commands
from discord import Member
from dotenv import load_dotenv
import json
from discord.ext.commands import has_permissions
from discord.utils import get
from discord.ui import Button, View, Modal, TextInput
import random
import re
import time
import datetime
# bot code starts here

load_dotenv()
# hi its me, you must create an external file named .env, in this file write
# DISCORD_TOKEN="the discord token of your bot", otherwise the program wont work
TOKEN = os.getenv("DISCORD_TOKEN")

# Intents
intents = discord.Intents.all()

# Initialize bot
bot = commands.Bot(command_prefix="!", intents=intents)

# Constants
INVITE_FILE = "invites.json"
INVITE_LOG_CHANNEL_ID = 1389143736277139526  # Replace with your actual channel ID
GUILD_ID = 1389093851318452244  # Replace with your actual server ID

# Invite cache
guild_invites = {}

# File setup
if not os.path.exists(INVITE_FILE):
    with open(INVITE_FILE, 'w') as f:
        json.dump({}, f)

def load_data():
    with open(INVITE_FILE, 'r') as f:
        return json.load(f)

def save_data(data):
    with open(INVITE_FILE, 'w') as f:
        json.dump(data, f, indent=4)

# Error handler
@bot.event
async def on_command_error(ctx, error):
    if isinstance(error, commands.CommandNotFound):
        await ctx.send("❌ That command doesn't exist.")
    elif isinstance(error, commands.MissingPermissions):
        await ctx.send("❌ You don't have permission to do that.")
    else:
        await ctx.send(f"⚠️ An error occurred: `{str(error)}`")
        raise error

# Moderation commands
@bot.command()
@commands.has_permissions(kick_members=True)
async def kick(ctx, member: discord.Member, *, reason=None):
    await member.kick(reason=reason)
    await ctx.send(f"{member.mention} has been kicked. Reason: {reason or 'No reason provided'}")

@bot.command()
@commands.has_permissions(ban_members=True)
async def ban(ctx, member: discord.Member, *, reason=None):
    await member.ban(reason=reason)
    await ctx.send(f"{member.mention} has been banned. Reason: {reason or 'No reason provided'}")

@bot.command()
@commands.has_permissions(manage_roles=True)
async def mute(ctx, member: discord.Member, *, reason=None):
    guild = ctx.guild
    mute_role = get(guild.roles, name="Muted")

    if not mute_role:
        mute_role = await guild.create_role(name="Muted")
        for channel in guild.channels:
            await channel.set_permissions(mute_role, speak=False, send_messages=False, read_message_history=True, read_messages=False)

    await member.add_roles(mute_role, reason=reason)
    await ctx.send(f"{member.mention} has been muted. Reason: {reason or 'No reason provided'}")

@bot.command()
@commands.has_permissions(manage_roles=True)
async def unmute(ctx, member: discord.Member):
    mute_role = get(ctx.guild.roles, name="Muted")
    if mute_role:
        await member.remove_roles(mute_role)
        await ctx.send(f"{member.mention} has been unmuted.")
    else:
        await ctx.send("Muted role not found.")

# Invite tracking events
@bot.event
async def on_ready():
    print(f"✅ Bot is online as {bot.user}")
    for guild in bot.guilds:
        invites = await guild.invites()
        guild_invites[guild.id] = invites
    print("✅ Cached invites for all guilds.")

@bot.event
async def on_invite_create(invite):
    invites = await invite.guild.invites()
    guild_invites[invite.guild.id] = invites

@bot.event
async def on_invite_delete(invite):
    invites = await invite.guild.invites()
    guild_invites[invite.guild.id] = invites

@bot.event
async def on_member_join(member):
    guild = member.guild
    before = guild_invites.get(guild.id, [])
    after = await guild.invites()
    guild_invites[guild.id] = after

    inviter = None
    for invite in after:
        old = next((i for i in before if i.code == invite.code), None)
        if old and invite.uses > old.uses:
            inviter = invite.inviter
            break

    data = load_data()
    str_guild_id = str(guild.id)
    if str_guild_id not in data:
        data[str_guild_id] = {}
    if 'invited_users' not in data[str_guild_id]:
        data[str_guild_id]['invited_users'] = {}

    if inviter:
        inviter_id = str(inviter.id)
        member_id = str(member.id)
        data[str_guild_id][inviter_id] = data[str_guild_id].get(inviter_id, 0) + 1
        data[str_guild_id]['invited_users'][member_id] = inviter_id
        save_data(data)

        channel = guild.get_channel(INVITE_LOG_CHANNEL_ID)
        if channel:
            await channel.send(f" {inviter.mention} invited {member.mention} (Total invites: {data[str_guild_id][inviter_id]})")

@bot.event
async def on_member_remove(member):
    guild = member.guild
    data = load_data()
    str_guild_id = str(guild.id)
    member_id = str(member.id)

    if str_guild_id in data and 'invited_users' in data[str_guild_id]:
        invited_users = data[str_guild_id]['invited_users']
        if member_id in invited_users:
            inviter_id = invited_users[member_id]
            if inviter_id in data[str_guild_id]:
                data[str_guild_id][inviter_id] = max(0, data[str_guild_id][inviter_id] - 1)
                save_data(data)
                channel = guild.get_channel(INVITE_LOG_CHANNEL_ID)
                if channel:
                    await channel.send(f" {member.mention} left.")
            del invited_users[member_id]
            save_data(data)

@bot.command()
async def invites(ctx, member: discord.Member = None):
    member = member or ctx.author
    data = load_data()
    count = data.get(str(ctx.guild.id), {}).get(str(member.id), 0)
    await ctx.send(f"{member.mention} has invited **{count}** member(s).")

@bot.command()
@commands.has_permissions(manage_guild=True)
async def resetinvites(ctx, member: discord.Member):
    data = load_data()
    guild_id = str(ctx.guild.id)
    user_id = str(member.id)
    if guild_id in data and user_id in data[guild_id]:
        data[guild_id][user_id] = 0
        save_data(data)
        await ctx.send(f"{member.mention}'s invites have been reset.")
    else:
        await ctx.send(f"{member.mention} has no invite record.")

@bot.command()
async def leaderboard(ctx):
    data = load_data()
    guild_id = str(ctx.guild.id)

    if guild_id not in data:
        await ctx.send("No invite data available.")
        return

    invites = {k: v for k, v in data[guild_id].items() if k != "invited_users"}
    sorted_invites = sorted(invites.items(), key=lambda x: x[1], reverse=True)

    embed = discord.Embed(title="🏆 Invite Leaderboard", color=discord.Color.green())
    for i, (user_id, count) in enumerate(sorted_invites[:10], start=1):
        user = ctx.guild.get_member(int(user_id))
        name = user.mention if user else f"<@{user_id}>"
        embed.add_field(name=f"{i}. {name}", value=f"{count} invite(s)", inline=False)

    await ctx.send(embed=embed)

# Giveaway system

def convert_time(time_str):
    match = re.match(r"^(\d+)([smh])$", time_str)
    if not match:
        return None
    val, unit = match.groups()
    val = int(val)
    return val if unit == "s" else val * 60 if unit == "m" else val * 3600

@bot.command()
@commands.has_permissions(manage_messages=True)
async def giveaway(ctx, time: str, *, prize: str):
    duration = convert_time(time)
    if duration is None:
        await ctx.send("Invalid time format! Use `10s`, `5m`, or `2h`.")
        return

    embed = discord.Embed(
        title="🎉 Giveaway!",
        description=f"Prize: **{prize}**\nReact with 🎉 to enter!\nDuration: {time}",
        color=discord.Color.blue()
    )
    embed.set_footer(text=f"Hosted by {ctx.author}")
    msg = await ctx.send(embed=embed)
    await msg.add_reaction("🎉")

    await asyncio.sleep(duration)

    msg = await ctx.channel.fetch_message(msg.id)
    users = [user async for user in msg.reactions[0].users()]
    users = [u for u in users if not u.bot]

    if not users:
        await ctx.send("No valid entries, no winner selected.")
    else:
        winner = random.choice(users)
        await ctx.send(f"🎊 Congratulations {winner.mention}! You won **{prize}**!")



##############
# middle man
##########


TICKET_CATEGORY_ID = 1389103470048575593
STAFF_ROLE_ID = 1389094404291170365


class ConfirmCancelView(discord.ui.View):
    def __init__(self, user1, user2, staff_role_id, channel):
        super().__init__(timeout=None)
        self.user1 = user1
        self.user2 = user2
        self.staff_role_id = staff_role_id
        self.channel = channel

        self.phase = 1
        self.confirmed_phase1 = set()
        self.canceled_phase1 = set()
        self.confirmed_phase2 = set()
        self.canceled_phase2 = set()
        self.staff_pinged = False

    async def prompt_trade_input(self, user, phase):
        prompt_text = (
            f"{user.mention}, what are you trading?"
            if phase == 1 else
            f"{user.mention}, what are you trading for the second part of the trade?"
        )

        await self.channel.send(embed=discord.Embed(
            description=prompt_text,
            color=discord.Color.green()
        ))

        def check(msg):
            return msg.channel == self.channel and msg.author == user

        msg = await bot.wait_for("message", check=check)

        await self.channel.send(embed=discord.Embed(
            description=f"Confirm that you are trading: `{msg.content}`",
            color=discord.Color.green()
        ), view=self)

    async def check_progress(self):
        if self.phase == 1 and self.canceled_phase1 == {self.user1.id, self.user2.id}:
            await self.channel.send(embed=discord.Embed(
                description="Both parties canceled the trade on phase 1. Closing ticket.",
                color=discord.Color.red()
            ))
            await asyncio.sleep(5)
            await self.channel.delete()
            return

        if self.phase == 2 and self.canceled_phase2 == {self.user1.id, self.user2.id}:
            await self.channel.send(embed=discord.Embed(
                description="Both parties canceled the trade on phase 2. Closing ticket.",
                color=discord.Color.red()
            ))
            await asyncio.sleep(5)
            await self.channel.delete()
            return

        if self.phase == 1 and self.confirmed_phase1 == {self.user1.id, self.user2.id}:
            self.phase = 2
            self.confirmed_phase2.clear()
            self.canceled_phase2.clear()
            await self.prompt_trade_input(self.user2, 2)

        if self.phase == 2 and self.confirmed_phase2 == {self.user1.id, self.user2.id} and not self.staff_pinged:
            self.staff_pinged = True
            staff_mention = f"<@&{self.staff_role_id}>"
            await self.channel.send(embed=discord.Embed(
                description=f"{staff_mention} Both parties have confirmed their second trade. You may proceed.",
                color=discord.Color.green()
            ))

    async def handle_action(self, interaction: discord.Interaction, confirmed_set, canceled_set):
        user_id = interaction.user.id
        if user_id not in (self.user1.id, self.user2.id):
            return await interaction.response.send_message("You are not part of this trade.", ephemeral=True)

        if user_id in confirmed_set:
            return await interaction.response.send_message("You already confirmed.", ephemeral=True)

        if user_id in canceled_set:
            canceled_set.remove(user_id)

        confirmed_set.add(user_id)
        await interaction.response.send_message(embed=discord.Embed(
            description=f"{interaction.user.mention} has confirmed trade.",
            color=discord.Color.green()
        ), ephemeral=False)
        await self.check_progress()

    async def handle_cancel(self, interaction: discord.Interaction, confirmed_set, canceled_set):
        user_id = interaction.user.id
        if user_id not in (self.user1.id, self.user2.id):
            return await interaction.response.send_message("You are not part of this trade.", ephemeral=True)

        if user_id in canceled_set:
            return await interaction.response.send_message("You already canceled.", ephemeral=True)

        if user_id in confirmed_set:
            confirmed_set.remove(user_id)

        canceled_set.add(user_id)
        await interaction.response.send_message(embed=discord.Embed(
            description=f"{interaction.user.mention} has canceled the trade.",
            color=discord.Color.red()
        ))

        if self.phase == 1:
            self.confirmed_phase1.clear()
            self.canceled_phase1.clear()
            await self.prompt_trade_input(self.user1, 1)
        elif self.phase == 2:
            self.confirmed_phase2.clear()
            self.canceled_phase2.clear()
            await self.prompt_trade_input(self.user2, 2)

    @discord.ui.button(label="Confirm", style=discord.ButtonStyle.success)
    async def confirm(self, interaction: discord.Interaction, button: discord.ui.Button):
        if self.phase == 1:
            await self.handle_action(interaction, self.confirmed_phase1, self.canceled_phase1)
        else:
            await self.handle_action(interaction, self.confirmed_phase2, self.canceled_phase2)

    @discord.ui.button(label="Cancel", style=discord.ButtonStyle.danger)
    async def cancel(self, interaction: discord.Interaction, button: discord.ui.Button):
        if self.phase == 1:
            await self.handle_cancel(interaction, self.confirmed_phase1, self.canceled_phase1)
        else:
            await self.handle_cancel(interaction, self.confirmed_phase2, self.canceled_phase2)


@bot.command()
async def middleman(ctx):
    embed = discord.Embed(
        title="Middleman Ticket System",
        description="Select the ticket you'd like to make",
        color=discord.Color.green()
    )
    view = TicketTypeView()
    await ctx.send(embed=embed, view=view)


@bot.command()
@commands.has_permissions(administrator=True)
async def close(ctx):
    if ctx.channel.category_id != TICKET_CATEGORY_ID:
        await ctx.send("This command can only be used in a ticket channel.")
        return
    await ctx.send("Closing ticket in 5 seconds...")
    await asyncio.sleep(5)
    await ctx.channel.delete()


class TicketTypeView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="In-Game Trading", style=discord.ButtonStyle.primary)
    async def in_game_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.start_ticket(interaction, "In-Game Trading")

    @discord.ui.button(label="Fund Related", style=discord.ButtonStyle.primary)
    async def fund_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.start_ticket(interaction, "Fund Related")

    async def start_ticket(self, interaction: discord.Interaction, ticket_type: str):
        category = discord.utils.get(interaction.guild.categories, id=TICKET_CATEGORY_ID)
        type_prefix = ticket_type.lower().replace(' ', '-')

        # Check if user already has a ticket of this type open
        for channel in category.channels:
            perms = channel.permissions_for(interaction.user)
            if perms.read_messages and channel.name.startswith(type_prefix):
                await interaction.response.send_message(
                    f"❌ You already have an open **{ticket_type}** ticket: {channel.mention}",
                    ephemeral=True
                )
                return

        await interaction.response.defer(ephemeral=True)

        overwrites = {
            interaction.guild.default_role: discord.PermissionOverwrite(read_messages=False),
            interaction.user: discord.PermissionOverwrite(read_messages=True, send_messages=True)
        }

        ticket_channel = await interaction.guild.create_text_channel(
            name=f"{type_prefix}-{interaction.user.name}",
            category=category,
            overwrites=overwrites
        )

        await interaction.followup.send(f"Ticket created: {ticket_channel.mention}", ephemeral=True)

        await ticket_channel.send(embed=discord.Embed(
            title="Security Notification",
            description="Our bot and staff team will NEVER direct message you. Ensure all conversations related to the deal are done within this ticket. Failure to do so may put you at risk of being scammed.",
            color=discord.Color.red()
        ))

        target_user = None
        while target_user is None:
            await ticket_channel.send(embed=discord.Embed(
                description=f"{interaction.user.mention}, who are you dealing with? Please enter their **Discord username** or **user ID**.",
                color=discord.Color.green()
            ))

            def check(msg):
                return msg.channel == ticket_channel and msg.author == interaction.user

            msg = await bot.wait_for("message", check=check)

            try:
                if msg.content.isdigit():
                    target_user = await interaction.guild.fetch_member(int(msg.content))
                else:
                    name = msg.content.strip()
                    for member in interaction.guild.members:
                        if member.name.lower() == name.lower():
                            target_user = member
                            break
            except Exception:
                target_user = None

            if target_user is None:
                await ticket_channel.send(embed=discord.Embed(
                    description="Could not find the specified user. Please try again.",
                    color=discord.Color.red()
                ))

        await ticket_channel.set_permissions(target_user, read_messages=True, send_messages=True)

        await ticket_channel.send(embed=discord.Embed(
            description=f"{interaction.user.mention}, what are you trading?",
            color=discord.Color.green()
        ))

        def check_trade1(m):
            return m.channel == ticket_channel and m.author == interaction.user

        trade1 = await bot.wait_for("message", check=check_trade1)

        await ticket_channel.send(embed=discord.Embed(
            description=f"Confirm that you are trading: `{trade1.content}`",
            color=discord.Color.green()
        ), view=ConfirmCancelView(interaction.user, target_user, STAFF_ROLE_ID, ticket_channel))



############
# support and purchase
############


cooldown_tracker2 = {}  # Format: {user_id: {"purchase": timestamp, "support": timestamp}}


class PurchaseModal2(discord.ui.Modal, title="Purchase Form"):
    item = discord.ui.TextInput(label="What are you purchasing?", required=True)
    payment = discord.ui.TextInput(label="Form of payment", required=True)

    def __init__(self, user, guild):
        super().__init__()
        self.user = user
        self.guild = guild

    async def on_submit(self, interaction: discord.Interaction):
        sanitized_name = self.user.name.lower().replace(" ", "-").replace("@", "").replace("#", "")
        channel_name = f"ticket-{sanitized_name}-purchase"

        existing = discord.utils.get(self.guild.text_channels, name=channel_name)
        if existing:
            await interaction.response.send_message(f"❌ You already have an open purchase ticket: {existing.mention}", ephemeral=True)
            return

        overwrites = {
            self.guild.default_role: discord.PermissionOverwrite(read_messages=False),
            self.user: discord.PermissionOverwrite(read_messages=True, send_messages=True),
            self.guild.me: discord.PermissionOverwrite(read_messages=True, send_messages=True)
        }

        category = discord.utils.get(self.guild.categories, id=TICKET_CATEGORY_ID)
        channel = await self.guild.create_text_channel(channel_name, overwrites=overwrites, category=category)

        embed = discord.Embed(title="New Purchase Ticket", color=discord.Color.green())
        embed.add_field(name="User", value=self.user.mention, inline=False)
        embed.add_field(name="Item", value=self.item.value, inline=False)
        embed.add_field(name="Form of Payment", value=self.payment.value, inline=False)
        await channel.send(embed=embed)
        await interaction.response.send_message(f"✅ Ticket created: {channel.mention}", ephemeral=True)

        cooldown_tracker2.setdefault(self.user.id, {})["purchase"] = asyncio.get_event_loop().time()


class SupportModal2(discord.ui.Modal, title="Support Form"):
    issue = discord.ui.TextInput(label="Please state your issue", style=discord.TextStyle.paragraph, required=True)

    def __init__(self, user, guild):
        super().__init__()
        self.user = user
        self.guild = guild

    async def on_submit(self, interaction: discord.Interaction):
        sanitized_name = self.user.name.lower().replace(" ", "-").replace("@", "").replace("#", "")
        channel_name = f"ticket-{sanitized_name}-support"

        existing = discord.utils.get(self.guild.text_channels, name=channel_name)
        if existing:
            await interaction.response.send_message(f"❌ You already have an open support ticket: {existing.mention}", ephemeral=True)
            return

        overwrites = {
            self.guild.default_role: discord.PermissionOverwrite(read_messages=False),
            self.user: discord.PermissionOverwrite(read_messages=True, send_messages=True),
            self.guild.me: discord.PermissionOverwrite(read_messages=True, send_messages=True)
        }

        category = discord.utils.get(self.guild.categories, id=TICKET_CATEGORY_ID)
        channel = await self.guild.create_text_channel(channel_name, overwrites=overwrites, category=category)

        embed = discord.Embed(title="New Support Ticket", color=discord.Color.blue())
        embed.add_field(name="User", value=self.user.mention, inline=False)
        embed.add_field(name="Issue", value=self.issue.value, inline=False)
        await channel.send(embed=embed)
        await interaction.response.send_message(f"✅ Ticket created: {channel.mention}", ephemeral=True)

        cooldown_tracker2.setdefault(self.user.id, {})["support"] = asyncio.get_event_loop().time()


class PurchasePanelView2(discord.ui.View):
    def __init__(self, guild):
        super().__init__(timeout=None)
        self.guild = guild

    @discord.ui.button(label="Purchase", style=discord.ButtonStyle.green)
    async def purchase_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        user = interaction.user
        now = asyncio.get_event_loop().time()
        last_used2 = cooldown_tracker2.get(user.id, {}).get("purchase", 0)

        if now - last_used2 < 300:
            await interaction.response.send_message("⏳ You must wait 5 minutes between creating purchase tickets.", ephemeral=True)
            return

        await interaction.response.send_modal(PurchaseModal2(user, self.guild))


class SupportPanelView2(discord.ui.View):
    def __init__(self, guild):
        super().__init__(timeout=None)
        self.guild = guild

    @discord.ui.button(label="Support", style=discord.ButtonStyle.blurple)
    async def support_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        user = interaction.user
        now = asyncio.get_event_loop().time()
        last_used2 = cooldown_tracker2.get(user.id, {}).get("support", 0)

        if now - last_used2 < 300:
            await interaction.response.send_message("⏳ You must wait 5 minutes between creating support tickets.", ephemeral=True)
            return

        await interaction.response.send_modal(SupportModal2(user, self.guild))


@bot.command()
async def purchasepanel(ctx):
    embed = discord.Embed(
        title="Purchase Ticket Panel",
        description="Click the button below to create a purchase ticket:",
        color=discord.Color.green()
    )
    await ctx.send(embed=embed, view=PurchasePanelView2(ctx.guild))


@bot.command()
async def supportpanel(ctx):
    embed = discord.Embed(
        title="Support Ticket Panel",
        description="Click the button below to create a support ticket:",
        color=discord.Color.blue()
    )
    await ctx.send(embed=embed, view=SupportPanelView2(ctx.guild))


class ConfirmCloseView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=30)

    @discord.ui.button(label="Confirm Close", style=discord.ButtonStyle.danger)
    async def confirm(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message(" Closing ticket in 5 seconds...", ephemeral=True)
        await asyncio.sleep(5)
        await interaction.channel.delete()

    @discord.ui.button(label="Cancel", style=discord.ButtonStyle.secondary)
    async def cancel(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message(" Ticket closure cancelled.", ephemeral=True)
        self.stop()


@bot.command()
@commands.has_permissions(manage_channels=True)
async def closeticket(ctx):
    if not ctx.channel.name.startswith("ticket-"):
        await ctx.send(" This command can only be used in a ticket channel.")
        return

    embed = discord.Embed(
        title="Confirm Close",
        description="Are you sure you want to close this ticket?",
        color=discord.Color.red()
    )
    await ctx.send(embed=embed, view=ConfirmCloseView())
@bot.command(name="ltctobi")
async def ltctobi(ctx):
    """Display Litecoin wallet address for Tobi"""
    await ctx.send("LS7Lk7eVdbu5yimKnaExDxbCvFKVXtyXpp")

@bot.command(name="ltclily")
async def ltclily(ctx):
    """Display Litecoin wallet address for Lily"""
    await ctx.send("LRj6He6Undsh9gjEVD5HLBnQyqEDvAQPpN")

@bot.command(name="pplily")
async def pplily(ctx):
    """Send Lily's PayPal link"""
    await ctx.send("https://www.paypal.me/lkaziiei\nfriends and family only")

@bot.command()
async def ps(ctx):
    """Private server link"""
    await ctx.send("https://www.roblox.com/share?code=b29720a0f12d204dbb3c9d727a917ce2&type=Server")

@bot.command(name="lucas")
async def lucas(ctx):
    await ctx.send("https://paypal.me/luckycxz LagiBRAuHSEqahYEqWB5FrSqJUytheW4xG")


@bot.event
async def on_message(message):
    # Prevent the bot from responding to itself
    if message.author == bot.user:
        return

    # Check if the message is in the specific channel
    if message.channel.id == 1389109307106263120:
        guild = message.guild
        role = guild.get_role(1389110599312474224)

        if role not in message.author.roles:
            try:
                await message.author.add_roles(role)
                print(f"Gave {role.name} to {message.author.display_name}")
            except discord.Forbidden:
                print("Bot lacks permission to assign the role.")
            except Exception as e:
                print(f"Error assigning role: {e}")

    # Important: make sure other commands still work
    await bot.process_commands(message)


@bot.command(name="purge")
@commands.has_permissions(manage_messages=True)
async def purge(ctx, amount: str):
    if amount.lower() == "all":
        deleted = await ctx.channel.purge()
        await ctx.send(f"Deleted {len(deleted)} messages.", delete_after=5)
    else:
        try:
            num = int(amount)
            deleted = await ctx.channel.purge(limit=num+1)  # +1 to include the command message itself
            await ctx.send(f"Deleted {len(deleted)-1} messages.", delete_after=5)
        except ValueError:
            await ctx.send("Invalid argument. Use a number or 'all'.", delete_after=5)


bot.run(TOKEN)