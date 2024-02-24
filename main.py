import nextcord
from nextcord.ext import commands
from nextcord.ui import Button, View
import os
from dotenv import load_dotenv
import fileuploader
import json

load_dotenv()
bot_token = os.getenv("TOKEN")
client = commands.Bot(command_prefix="fu ", intents=nextcord.Intents.all())


@client.event
async def on_ready():
    print("online")


@client.event
async def on_interaction(interaction: nextcord.Interaction):
    if interaction.type == nextcord.InteractionType.application_command:
        await client.process_application_commands(interaction)  # Process aplication commands if interaction type is this one

    if interaction.type != nextcord.InteractionType.component:  # If interaction type is not component
        return

    if interaction.data['custom_id'].startswith("del_"):  # If interacted component is delete button
        d_url = interaction.data['custom_id'].replace("del_", "").split("_")  # Get file and owner info

        if str(interaction.user.id) != d_url[2]:  # If the interacted user is not owner
            await interaction.send(content="Hey, this button is not for you!", ephemeral=True)
            return

        try:  
            await fileuploader.delete(  # Delete file from the server
                file_url=d_url[0],
                key=d_url[1]
            )
        except Exception as e:  # If server answered with error
            await interaction.send(e)
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


@commands.cooldown(rate=2, per=60)  # Command cooldown
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

    with open("data.json", "r") as f:
        data = json.load(f)  # load data from .json file

    user = None
    if str(ctx.author.id) in data:  # If user logged in
        userdata = data[str(ctx.author.id)]
        user = await fileuploader.User.loginToken(userdata["accessToken"])  # Get user with login token

    try:
        async with ctx.typing():
            file = await fileuploader.upload(  # Upload file to a server
                bytes=await attachment.read(),
                filename=attachment.filename,
                user=user
            )
    except Exception as e:  # If server answered with error
        embed = nextcord.Embed(
            title=e,
            color=nextcord.Color.from_rgb(170, 63, 68)
        )
        await ctx.reply(embed=embed)
        return

    embed = nextcord.Embed(title="File successfully uploaded!", 
                           color=nextcord.Color.from_rgb(155, 181, 82))
    embed.add_field(name="File link", value=file.file_url_full)
    embed.add_field(name="File name", value=file.user_filename)
    embed.set_image(url=file.file_url_full)
    if user:
        embed.set_author(name=f"logged in as {userdata['username']}")

    button = Button(
        label="Delete file",
        style=nextcord.ButtonStyle.red, 
        custom_id=f'del_{file.file_url}_{file.key}_{ctx.author.id}'  # Store file info in button custom_id
    )

    view = View()
    view.add_item(button)
    await ctx.reply(embed=embed, view=view)  # Send uploaded file info


@client.slash_command()
async def login(interaction: nextcord.Interaction, username: str, password: str):
    message = await interaction.send("Wait a second...", ephemeral=True)

    with open("data.json", "r") as f:
        data = json.load(f)

    if str(interaction.user.id) in data:  # If user in data
        await message.edit(f"You are already logged in as `{data[str(interaction.user.id)]['username']}`.")
        return

    try:
        async with interaction.channel.typing():
            user = await fileuploader.User.login(username, password, True)  # Log in the site
    except Exception as e:
        await message.edit(e)
        return

    data[str(interaction.user.id)] = {  # Add user data
            "accessToken": user.accessToken,
            "username": user.username
        }
    with open("data.json", "w") as f:
        json.dump(data, f, indent=4)  # Update data.json

    await message.edit(f"You are successfully logged in as `{user.username}`.")

    
@client.slash_command()
async def logout(interaction: nextcord.Interaction):
    message = await interaction.send("Wait a second...", ephemeral=True)

    with open("data.json", "r") as f:
        data = json.load(f)  # Load a json file

    if str(interaction.user.id) not in data:  # If user not in data
        await message.edit("You are already logged out!")
        return

    userdata = data[str(interaction.user.id)]
    user = await fileuploader.User.loginToken(userdata["accessToken"])  # Get user with login token

    try:
        async with interaction.channel.typing():
            await user.logout()  # Log out from the account
    except Exception as e:
        await message.edit(e)
        return
    
    del data[str(interaction.user.id)]  # Delete user data
    with open("data.json", "w") as f:
        json.dump(data, f, indent=4)  # Update the json file

    await message.edit("You are successfully logged out.")


@client.slash_command()
async def registration(interaction: nextcord.Interaction, username: str, password: str):
    message = await interaction.send("Wait a second...", ephemeral=True)
    
    with open("data.json", "r") as f:
        data = json.load(f)

    if str(interaction.user.id) in data:  # If user in data
        await message.edit(f"You are already logged in as {data[str(interaction.user.id)]['username']}.")
        return

    try:
        async with interaction.channel.typing():
            user = await fileuploader.User.register(username, password, True)  # Registrating a new account
    except Exception as e:
        await message.edit(e)
        return
    
    data[str(interaction.user.id)] = {  # Add user data
            "accessToken": user.accessToken,
            "username": user.username
        }
    with open("data.json", "w") as f:
        json.dump(data, f, indent=4)  # Update the json file

    await message.edit(f"You are successfully created an account and logged in as `{user.username}`.")


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