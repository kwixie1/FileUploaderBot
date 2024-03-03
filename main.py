import nextcord
from nextcord.ext import commands
from nextcord.ui import Button, View
import os
from dotenv import load_dotenv
import fileuploader
import json
import cooldowns

load_dotenv()
bot_token = os.getenv("TOKEN")
client = commands.Bot(intents=nextcord.Intents.all())


@client.event
async def on_ready():
    print("online")


@client.event
async def on_interaction(interaction: nextcord.Interaction):
    if interaction.type == nextcord.InteractionType.application_command:
        await client.process_application_commands(interaction)  # Process aplication commands if interaction type is this one

    if interaction.type != nextcord.InteractionType.component:  # If interaction type is not component
        return

    await interaction.message.edit(content="Wait a second...")  # Without it Discord can answer with an error for long waiting
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
            await interaction.message.edit(content=None)
            await interaction.send(e, ephemeral=True)
            return

        del_embed = nextcord.Embed(
            title="File successfully deleted.",
            description="File with link " +
            f"`https://fu.andcool.ru/file/{d_url[0][:10]}` " +
            "has been deleted.",
            color=nextcord.Color.from_rgb(170, 63, 68)
        )
                    
        view = View()
        await interaction.message.edit(content=None, embed=del_embed, view=view)


@client.slash_command(description="Bot and commands info")
async def help(interaction: nextcord.Interaction):
    description = """This bot - simple discord provider for fu.andcool.ru
    Using bot you can:
    — Upload and delete files to/from the server.
    — Working with accounts: login, logout or register a new one."""
    embed = nextcord.Embed(title="File uploader bot", description=description, color=nextcord.Color.from_rgb(155, 181, 82))
    embed.add_field(
        name="Commands", 
        value="**Main**\n`/upload` `/help`\n**Accounts**\n`/login` `/logout` `/registration`"
    )
    embed.add_field(name="Credits", value="**Bot creator**\n<@826589820528230450>\n**Fu creator**\n<@812990469482610729>")
    embed.set_thumbnail("https://fu.andcool.ru/file/OVuFMwonbD")

    await interaction.send(embed=embed)


@client.slash_command(description="Upload a file to the server")
@cooldowns.cooldown(2, 60, bucket=cooldowns.SlashBucket.author)  # Command cooldown
async def upload(interaction: nextcord.Interaction, attachment: nextcord.Attachment):
    await interaction.response.defer()

    if attachment.size >= 1024 * 1024 * 100:  # Chack attachment size
        await interaction.followup.send("Your file is too large! Max file size limit is 100 MB.")
        return

    with open("data.json", "r") as f:
        data = json.load(f)  # load data from .json file

    user = None
    if str(interaction.user.id) in data:  # If user logged in
        userdata = data[str(interaction.user.id)]
        try:
            user = await fileuploader.User.loginToken(userdata["accessToken"])  # Get user with login token

        except fileuploader.exceptions.NotAuthorized:  # If access token is invalid
            del data[str(interaction.user.id)]  # Delete user data
            with open("data.json", "w") as f:
                json.dump(data, f, indent=4)  # Update the json file

        except Exception as e:
            await interaction.followup.send(e)
            return
        
    try:
        file = await fileuploader.upload(  # Upload file to the server
            bytes=await attachment.read(),
            filename=attachment.filename,
            user=user
        )
    except Exception as e:  # If server answered with error
        await interaction.followup.send(e)
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
        custom_id=f'del_{file.file_url}_{file.key}_{interaction.user.id}'  # Store file info in button custom_id
    )

    view = View()
    view.add_item(button)
    await interaction.followup.send(embed=embed, view=view)  # Send uploaded file info


@client.slash_command(description="log in the fu account")
async def login(interaction: nextcord.Interaction, username: str, password: str):
    await interaction.response.defer(ephemeral=True)

    with open("data.json", "r") as f:
        data = json.load(f)

    try:
        user = await fileuploader.User.login(username, password, True)  # Log in the site
    except Exception as e:
        await interaction.followup.send(e)
        return

    if str(interaction.user.id) in data:
        del data[str(interaction.user.id)]

    data[str(interaction.user.id)] = {  # Add user data
            "accessToken": user.accessToken,
            "username": user.username
        }
    with open("data.json", "w") as f:
        json.dump(data, f, indent=4)  # Update data.json

    await interaction.followup.send(f"You are successfully logged in as `{user.username}`.")

    
@client.slash_command(description="log out from the fu account")
async def logout(interaction: nextcord.Interaction):
    await interaction.response.defer(ephemeral=True)

    with open("data.json", "r") as f:
        data = json.load(f)  # Load data from .json file

    if str(interaction.user.id) not in data:  # If user not in data
        await interaction.followup.send("You are already logged out!")
        return

    userdata = data[str(interaction.user.id)]

    try:
        user = await fileuploader.User.loginToken(userdata["accessToken"])  # Get user with token

    except fileuploader.exceptions.NotAuthorized:
        user = None
    except Exception as e:
        await interaction.followup.send(e)
        return

    del data[str(interaction.user.id)]  # Delete user data
    with open("data.json", "w") as f:
        json.dump(data, f, indent=4)  # Update the json file

    if user:
        try:
                await user.logout()  # Log out from the account
        except Exception as e:
            await interaction.followup.send(e)
            return

    await interaction.followup.send("You are successfully logged out.")


@client.slash_command(description="register the new fu account")
async def registration(interaction: nextcord.Interaction, username: str, password: str):
    await interaction.response.defer(ephemeral=True)
    
    with open("data.json", "r") as f:
        data = json.load(f)

    try:
        user = await fileuploader.User.register(username, password, True)  # Registrating a new account
    except Exception as e:
        await interaction.followup.send(e)
        return
    
    if str(interaction.user.id) in data:
        del data[str(interaction.user.id)]

    data[str(interaction.user.id)] = {  # Add user data
            "accessToken": user.accessToken,
            "username": user.username
        }
    with open("data.json", "w") as f:
        json.dump(data, f, indent=4)  # Update the json file

    await interaction.followup.send(f"You are successfully created an account and logged in as `{user.username}`.")


@client.event
async def on_application_command_error(interaction: nextcord.Interaction, error):
    error = getattr(error, "original", error)  # Get original error if avaible
    if isinstance(error, cooldowns.CallableOnCooldown):  # If command on cooldown
        await interaction.send(
            "Hey, slow down! You can upload only 2 files per 1 minute.\n" +
            f"Try again at {int(error.retry_after)} sec",
            ephemeral=True
        )
    else:
        raise error


if __name__ == "__main__":
    client.run(bot_token)