import discord
import spoilers

with open(f"token_botanada.txt", "r") as f:
    TOKEN = f.read()

whitelist = {
    # ("Test Server", "general"),
    ("Hollow Knight Things", "hk-help"),
    ("Hollow Knight", "hk-help"),
}

intents = discord.Intents.default()
intents.message_content = True

client = discord.Client(intents=intents)

@client.event
async def on_ready():
    print(f'Logged in as {client.user}')

@client.event
async def on_message(message):
    if message.author == client.user: return
    if (message.guild.name, message.channel.name) not in whitelist: return
    await spoilers.handle_spoilers(message)

client.run(TOKEN)
