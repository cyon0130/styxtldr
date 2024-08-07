import discord
from discord.ext import commands
import requests
from datetime import datetime
import uuid
import time
import json

# Global variables
TOKEN  = 'MTE3MTM4MDM2MTI4OTI2OTI1OA.GFhqek.zSZWw4YEUIUHmiC05IzApjQ-EA_uCCmfTPqxNM'
BASE_URL = "https://openrouter.ai/api/v1"
API_KEY = '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'
REPORT_CHANNEL_ID = 1269554203253276784  # Replace with your report channel ID
MODEL_NAME = 'openai/gpt-4o'
SYSTEM_PROMPT = '''
You are a casual Discord user in a server that is filled with racing game and sports enthusiasts.
Most of the conversations here include, but are not limited to:
- racing games gameplay, both good plays and guffaws
- memes and jokes
- opinions about the racing industry
- casual talk about how the news in the racing industry

Your task is to provide a TL;DR of what your fellow users were talking about.
Keep it simple as if a person is just casually asking what happened when he was away.
Your output should be like how a Discord user in that server usually chats but in a slightly joking manner. If there are users who are making slurs or NSFW stuff, you can just say "they're doing some research work."
In addition, your fellow users might send images or links with embedded images, your job is to just interpret what is sent.
'''

intents = discord.Intents.default()
intents.messages = True
intents.guilds = True
intents.message_content = True
bot = discord.Bot(intents=intents)  # Use discord.Bot for slash commands

@bot.slash_command(name='tldr_pls', description='Get a TL;DR of a conversation in a channel.')
async def tldr_pls(ctx, from_date: str, from_time: str = '', to_date: str = '', to_time: str = ''):
    start_time = time.time()
    try:
        await ctx.respond("Working on it...", ephemeral=True)

        # Combine date and time
        from_dt = datetime.strptime(f'{from_date} {from_time}', '%Y-%m-%d %H:%M') if from_time else datetime.strptime(from_date, '%Y-%m-%d')
        to_dt = datetime.strptime(f'{to_date} {to_time}', '%Y-%m-%d %H:%M') if to_time else datetime.now()

        # Fetch messages from the channel
        channel = ctx.channel
        messages = [msg async for msg in channel.history(after=from_dt, before=to_dt)]

        # Prepare the conversation for OpenRouter
        conversation = []
        for msg in messages:
            if msg.attachments:
                for attachment in msg.attachments:
                    if attachment.filename.lower().endswith(('png', 'jpg', 'jpeg', 'gif', 'bmp')):
                        # Handle image (interpretation not included here)
                        conversation.append("Image attachment detected.")
            conversation.append(msg.content)

        conversation_text = "\n".join(conversation)
        headers = {
            'Authorization': f'Bearer {API_KEY}',
            'Content-Type': 'application/json'
        }
        data = {
            'model': MODEL_NAME,
            'messages': [{'role': 'system', 'content': SYSTEM_PROMPT}, {'role': 'user', 'content': conversation_text}]
        }

        response = requests.post(BASE_URL, headers=headers, json=data)
        elapsed_time = round(time.time() - start_time, 2)

        if response.status_code != 200:
            detailed_error = f"Status Code {response.status_code}, Response: {response.text}"
            await ctx.send("There was an error processing your request.", ephemeral=True)
            report_channel = bot.get_channel(REPORT_CHANNEL_ID)
            await report_channel.send(f"Error encountered while processing TL;DR command: {detailed_error}")
            return

        tl_dr = response.json().get('choices', [{}])[0].get('message', {}).get('content', 'Failed to generate TL;DR')

        # Send TL;DR to the user in embedded format
        embed = discord.Embed(title="TL;DR Summary", color=discord.Color.blue())
        embed.add_field(name="Username", value=ctx.author.name, inline=False)
        embed.add_field(name="Channel ID", value=channel.id, inline=False)
        embed.add_field(name="Channel Name", value=channel.name, inline=False)
        embed.add_field(name="Date Range", value=f"{from_dt} to {to_dt}", inline=False)
        embed.add_field(name="TL;DR", value=tl_dr, inline=False)
        await ctx.send(embed=embed, ephemeral=True)  # `ephemeral=True` makes it visible only to the user

        # Prepare JSON report
        report_channel = bot.get_channel(REPORT_CHANNEL_ID)
        json_report = {
            "event_uuid": str(uuid.uuid4()),
            "username_of_requester": ctx.author.name,
            "channel_id": channel.id,
            "channel_name": channel.name,
            "date_range": f"{from_dt} to {to_dt}",
            "tldr_summary": tl_dr,
            "tokens_used": response.json().get('usage', {}).get('total_tokens', 'N/A'),
            "elapsed_time": elapsed_time
        }
        await report_channel.send(content=f"```json\n{json.dumps(json_report, indent=4)}\n```")

    except Exception as e:
        detailed_error = f"{str(e)}"
        await ctx.send("An unexpected error occurred.", ephemeral=True)
        report_channel = bot.get_channel(REPORT_CHANNEL_ID)
        await report_channel.send(f"Unexpected error while processing TL;DR command: {detailed_error}")

bot.run(TOKEN)
