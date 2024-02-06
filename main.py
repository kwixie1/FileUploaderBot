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
    if not ctx.message.attachments:  # If message hasn't attachments
        await ctx.reply("If you want to upload a file, you need to SEND me a file.")
        return

    if len(ctx.message.attachments) > 1:  # If the message contains more than 1 attachment
        await ctx.reply("Please, send me only ONE file.")
        return

    attachment = ctx.message.attachments[0]  # Get first attachment

    if attachment.size >= 1024 * 1024 * 100:  # Chack attachment size
        await ctx.reply("Your file is too large! Max file size limit is 100 MB.")
        return

    data = aiohttp.FormData()  # Create form-data body for request
    data.add_field("file", await attachment.read(), filename=attachment.filename)  # Add file to the body

    async with ctx.typing():  # Bot typing
        async with aiohttp.ClientSession("https://fu.andcool.ru") as session:  # Create session with the API
            async with session.post(f"/api/upload/private", data=data) as response:  # Send POST request
                response_status = response.status
                response = await response.json()

    if response_status != 200:  # If server answered with error
        errors = {  # List of known errors
            500: "Internal server error",
            502: "API didn't respond.",
            522: "Server didn't respond"
        }
        embed_title = errors.get(response_status, "Unhandled error was occured")

        embed = nextcord.Embed(
            title=embed_title, 
            description=f"Status code: **{response_status}**",
            color=nextcord.Color.from_rgb(170, 63, 68)
        )
        await ctx.reply(embed=embed)
        return

    embed = nextcord.Embed(title="File successfully uploaded!", 
                           color=nextcord.Color.from_rgb(155, 181, 82))
    embed.add_field(name="File link", value=response["file_url_full"])
    embed.add_field(name="File name", value=response["user_filename"])
    embed.set_image(url=response["file_url_full"])

    button = Button(
        label="Delete file",
        style=nextcord.ButtonStyle.red, 
        custom_id=f'del_{response["file_url"]}?key={response["key"]}_{ctx.author.id}'  # Store file info in button custom_id
    )

    view = View()
    view.add_item(button)
    await ctx.reply(embed=embed, view=view)  # Send uploaded file info


@client.event
async def on_interaction(interaction: nextcord.Interaction):
    if interaction.type != nextcord.InteractionType.component:  # If interaction type is not component
        return

    if interaction.data['custom_id'].startswith("del_"):  # If interacted component is delete button
        d_url = interaction.data['custom_id'].replace("del_", "").split("_")  # Get file and owner info

        if str(interaction.user.id) != d_url[1]:  # If the interacted user is not owner
            await interaction.send(content="Hey, this button is not for you!", ephemeral=True)
            return

        async with aiohttp.ClientSession("https://fu.andcool.ru") as session:  # Create session with the API
            async with session.get(f"/api/delete/{d_url[0]}") as response:  # Create a GET request to delete a file
                response_status = response.status
    
        if response_status != 200:  # If deletion not success
            await interaction.response.send_message(f"Oops, something wents wrong. Status code is **{response_status}**")
            return

        del_embed = nextcord.Embed(
            title="File successfully deleted.",
            description="File with link " +
            f"`https://fu.andcool.ru/file/{d_url[0][:10]}` " +
            "has been deleted.",
            color=nextcord.Color.from_rgb(170, 63, 68)
        )
                
        view = View()
        await interaction.message.edit(embed=del_embed, view=view)


@client.event
async def on_command_error(ctx: commands.Context, error):
    if isinstance(error, commands.errors.CommandOnCooldown):
        """Too many files handler"""
        await ctx.reply(
            "Hey, slow down! You can upload only 2 files per 1 minute.\n" +
            f"Try again at {int(error.retry_after)} sec"
        )


if __name__ == "__main__":
    client.run(bot_token)