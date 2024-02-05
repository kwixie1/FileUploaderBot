import nextcord
from nextcord.ext import commands
import aiohttp
from nextcord.ui import Button, View
import os
from dotenv import load_dotenv

load_dotenv()
bot_token = os.getenv("TOKEN")

client = commands.Bot(command_prefix="fu ", intents=nextcord.Intents.all())

@client.event
async def on_ready():
    print("online")


@commands.cooldown(rate=2, per=60)
@client.command()
async def upload(ctx: commands.Context):

    if not ctx.message.attachments:
        await ctx.reply("If you want to upload a file, you need to SEND me a file.")
        return

    if len(ctx.message.attachments) > 1:
        await ctx.reply("Please, send me only ONE file.")
        return

    attachment = ctx.message.attachments[0]

    if attachment.size >= 104857600:
        await ctx.reply("Your file is too large! Max file size limit is 100 MB.")
        return

    if attachment.content_type == None:
        await ctx.reply("Wait-wait, what is it? Non-extension file? Interesting, but no. Please, find file with any extension")
        return

    data = aiohttp.FormData()
    data.add_field("file", await attachment.read(), filename=attachment.filename)

    async with ctx.typing():
        async with aiohttp.ClientSession("https://fu.andcool.ru") as session:
            async with session.post(f"/api/upload/private", data=data) as response:
                response = await response.json()

    embed = nextcord.Embed(title="File successfully uploaded!", color=nextcord.Color.from_rgb(155, 181, 82))
    embed.add_field(name="File link", value=response["file_url_full"])
    embed.add_field(name="File name", value=response["user_filename"])
    embed.set_image(url=response["file_url_full"])

    button = Button(
        label="Delete file",
        style=nextcord.ButtonStyle.red, 
        custom_id=f'del;{response["file_url"]}?key={response["key"]}_{ctx.author.id}'
    )

    view = View()
    view.add_item(button)

    await ctx.reply(embed=embed, view=view)


@client.event
async def on_interaction(interaction: nextcord.Interaction):
    if interaction.type == nextcord.InteractionType.component:

        if interaction.data['custom_id'].startswith("del;"):
            d_url = interaction.data['custom_id'].replace("del;", "").split("_")

            if str(interaction.user.id) != d_url[1]:
                    await interaction.send(content="Hey, this button is not for you!", ephemeral=True)
                    return

            async with aiohttp.ClientSession("https://fu.andcool.ru") as session:
                async with session.get(f"/api/delete/{d_url[0]}") as response:
                    response_status = response.status
        
            if response_status != 200:
                await interaction.response.send_message(f"Oops, something wents wrong. Status code is **{response_status}**")
                return

            del_embed = nextcord.Embed(
                title="File successfully deleted.",
                description="File with link " +
                f"`https://fu.andcool.ru/file/{d_url[0][:d_url[0].index('?')]}`" +
                " has been deleted.",
                color=nextcord.Color.from_rgb(170, 63, 68)
                )
                    
            view = View()
            await interaction.message.edit(embed=del_embed, view=view)

@client.event
async def on_command_error(ctx: commands.Context, error):
    if isinstance(error, commands.errors.CommandOnCooldown):
        await ctx.reply(
            "Hey, slow down! You can upload only 2 files per 1 minute.\n" +
            f"Try again at {int(error.retry_after)} sec"
        )


if __name__ == "__main__":
    client.run(bot_token)