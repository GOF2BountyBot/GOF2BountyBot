from typing import List, cast
import aiohttp
from discord import HTTPException, app_commands, Interaction, ButtonStyle
from discord.abc import Snowflake
from discord.ui import View, Button
import os
from os.path import join
import shutil

from .. import client, lib
from ..cfg import cfg, bbData
from ..cfg.cfg import basicAccessLevels
from ..interactions import basedCommand, basedApp
from ..gameObjects.userProfile.medal import Medal

class DevMedalsCog(basedApp.BasedCog):
    @basedCommand.basedCommand(accessLevel=basicAccessLevels.developer, helpSection="medals")
    @app_commands.command(name="create-medal",
                            description="Create a new medal.")
    @app_commands.guilds(*cfg.developmentGuilds)
    async def dev_cmd_create_medal(self, interaction: Interaction, name: str, description: str = "", icon: str = "", wiki: str = "", emoji: str = ""):
        """developer command creating a new medal.
        To include new line characters in the medal description, use the keyword `{NL}`.
        """
        if name.lower() in bbData.medalObjs:
            await interaction.response.send_message(":x: A medal with that name already exists", ephemeral=True)
            return

        if not emoji and not icon:
            await interaction.response.send_message(":x: Please give at least one of `emoji` or `icon`.", ephemeral=True)
            return

        if emoji:
            try:
                parsedEmoji = lib.emojis.BasedEmoji.fromStr(emoji, rejectInvalid=True)
            except lib.exceptions.UnrecognisedEmojiFormat:
                await interaction.response.send_message(f"Invalid emoji: {emoji}", ephemeral=True)
                return
            except lib.exceptions.UnrecognisedCustomEmoji:
                await interaction.response.send_message(f"Unrecognised emoji: {emoji}\nPlease make sure I can access it.", ephemeral=True)
                return
        else:
            parsedEmoji = lib.emojis.BasedEmoji.EMPTY

        if not icon and parsedEmoji is not lib.emojis.BasedEmoji.EMPTY and parsedEmoji.isUnicode:
            await interaction.response.send_message(":x: I can't extract icons from unicode emojis.\nPlease either provide a custom emoji or an icon.",
                                                    ephemeral=True)
            return
          
        if parsedEmoji is lib.emojis.BasedEmoji.EMPTY:
            emojiServer = self.bot.get_guild(cfg.emojisServer) or await self.bot.fetch_guild(cfg.emojisServer)
            if emojiServer is None:
                self.bot.logger.log(type(self).__name__, self.dev_cmd_create_medal.callback.__name__,
                                    "Failed to find cfg.emojisServer", eventType="UKWN_GLD", interaction=interaction)
                await interaction.response.send_message(":x: Failed to connect to the emojisServer", ephemeral=True)
                return
                
            success = False
            async with self.bot.httpClient.get(icon) as resp:
                try:
                    resp.raise_for_status()
                except aiohttp.ClientResponseError as e:
                    await interaction.response.send_message(f"You gave an invalid icon url. Make sure it points directly to an image!\n{e}",
                                                            ephemeral=True)
                else:
                    if not resp.content_type.startswith("image"):
                        await interaction.response.send_message(f":x: The icon URL must point to an image, yours is a '{resp.content_type}'",
                                                                ephemeral=True)
                        success = False
                    else:
                        iconImg = await resp.read()
                        try:
                            newEmoji = await emojiServer.create_custom_emoji(name=name,
                                                                            image=iconImg,
                                                                            reason=self.dev_cmd_create_medal.callback.__name__)
                        except HTTPException as e:
                            await interaction.response.send_message(f":x: Failed to create medal emoji: {e}", ephemeral=True)
                            self.bot.logger.log(type(self).__name__, self.dev_cmd_create_medal.callback.__name__, str(e), exception=e, interaction=interaction)
                            return
                        parsedEmoji = lib.emojis.BasedEmoji(id=newEmoji.id)
            if not success:
                return
        if not icon:
            # When given an emoji but no icon or message attachment, the emoji is ensured earlier to be custom
            dcEmoji = self.bot.get_emoji(parsedEmoji.id)
            if dcEmoji is None:
                await interaction.response.send_message(":x: Failed to get your requested emoji.", ephemeral=True)
                self.bot.logger.log(type(self).__name__, self.dev_cmd_create_medal.callback.__name__, f"Failed to get given emoji: {parsedEmoji.sendable}",
                                    eventType="EMOJI_ERR", interaction=interaction)
                return
            icon = dcEmoji.url
        
        newMedal = Medal(name, description, icon=icon, emoji=parsedEmoji, wiki=wiki)
        bbData.medalsData[name.lower()] = newMedal.serialize()
        bbData.medalObjs[name.lower()] = newMedal

        dirPath = os.path.join(cfg.paths.bbMedalsMETAFolder, name + ".bbMedal")
        if not os.path.isdir(dirPath):
            os.makedirs(dirPath)
        filePath = os.path.join(dirPath, "META.json")
        lib.jsonHandler.writeJSON(filePath,
                                    # TODO: SerializedMedal is incompatible with JsonType?
                                    newMedal.serialize(), # type: ignore[reportGeneralTypeIssues]
                                    prettyPrint=True)

        await interaction.response.send_message(f"{cfg.defaultEmojis.submit.sendable} medal added successfuly: {name}", ephemeral=True)


    @basedCommand.basedCommand(accessLevel=basicAccessLevels.developer, helpSection="medals")
    @app_commands.command(name="delete-medal",
                            description="Delete a medal.")
    @app_commands.guilds(*cfg.developmentGuilds)
    async def dev_cmd_delete_medal(self, interaction: Interaction, name: str):
        """Developer command deleting a medal from the game.  
        """
        if name not in bbData.medalObjs:
            await interaction.response.send_message(f":x: Unknown medal: '{name}'", ephemeral=True)
            return

        medal = bbData.medalObjs[name]
        
        view = View()
        confirmed: List[bool] = []
        nextInteraction: List[Interaction] = []

        async def confirm(interaction: Interaction):
            confirmed.append(True)
            nextInteraction.append(interaction)
            view.stop()

        async def cancel(interaction: Interaction):
            confirmed.clear()
            nextInteraction.append(interaction)
            view.stop()

        confirmButton = Button(style=ButtonStyle.primary, label="Delete")
        confirmButton.callback = confirm
        cancelButton = Button(style=ButtonStyle.red, label="Cancel")
        cancelButton.callback = cancel
        view.add_item(confirmButton).add_item(cancelButton)
        await interaction.response.send_message(f"Are you sure you want to completely remove the {medal.name} " \
                                                + "medal from the game? The medal will be lazily removed from all owning users.",
                                                ephemeral=True, view=view)
        
        if await view.wait(): return

        if confirmed:
            # locate medal META file
            medalFound = False
            for subdir, dirs, _ in lib.jsonHandler.depthLimitedWalk(cfg.paths.bbMedalsMETAFolder, cfg.gameObjectCfgMaxRecursion):
                for dirname in dirs:
                    if dirname.lower().endswith(".bbmedal"):
                        dirpath = join(subdir, dirname)

                        # Read in the medal metadata
                        if lib.jsonHandler.readJSON(join(dirpath, "META.json"))["name"] == medal.name:
                            medalFound = True
                            shutil.rmtree(dirpath)
                
                if medalFound:
                    break
            if medalFound:
                del bbData.medalObjs[name]
                await nextInteraction[0].response.send_message(f"{cfg.defaultEmojis.submit} The {medal.name} medal was removed from the game successfuly." \
                                                            + f"\nThe medal's emoji ({medal.emoji.serialize()}) and icon message (if any) were NOT deleted.")
            else:
                await nextInteraction[0].response.send_message(":x: The medal's META file could not be located. Medal deletion cancelled.", ephemeral=True)
        else:
            await nextInteraction[0].response.send_message("Medal deletion cancelled.", ephemeral=True)


    @basedCommand.basedCommand(accessLevel=basicAccessLevels.developer, helpSection="medals")
    @app_commands.command(name="give-medal",
                            description="Award a medal to a user.")
    @app_commands.guilds(*cfg.developmentGuilds)
    async def dev_cmd_give_medal(self, interaction: Interaction, medal_name: str, user_id: str = ""):
        """Developer command adding a medal to a user's profile
        """
        requestedBUser, _, _, _ = await self.UsersUtilCog.getOrCreateBasedUserOrAuthor(interaction, user_id)
        if requestedBUser is None: return

        dcUser = self.bot.get_user(requestedBUser.id) or await self.bot.tryFetchUser(requestedBUser.id)
        userMention = "<unknown user>" if dcUser is None else dcUser.mention

        if medal_name not in bbData.medalObjs:
            await interaction.response.send_message(f":x: Unknown medal: '{medal_name}'", ephemeral=True)
            return

        medal: Medal = bbData.medalObjs[medal_name]
        if medal in requestedBUser.medals:
            await interaction.response.send_message(f":x: {userMention} already has the {medal.name} medal.",
                                                    ephemeral=True)
            return
        
        requestedBUser.medals.add(medal)
        await interaction.response.send_message(f"{cfg.defaultEmojis.submit} {userMention} was awarded the {medal.name} medal successfuly.",
                                                ephemeral=True)


    @basedCommand.basedCommand(accessLevel=basicAccessLevels.developer, helpSection="medals")
    @app_commands.command(name="take-medal",
                            description="Un-award a medal from a user.")
    @app_commands.guilds(*cfg.developmentGuilds)
    async def dev_cmd_take_medal(self, interaction: Interaction, medal_name: str, user_id: str = ""):
        """Developer command removing a medal from a user's profile
        """
        requestedBUser, _, _ = await self.UsersUtilCog.getBasedUserOrAuthor(interaction, user_id)
        if requestedBUser is None: return
        
        requestedUser = self.bot.get_user(int(user_id)) or await self.bot.tryFetchUser(int(user_id))
        userMention = "<unknown user>" if requestedUser is None else requestedUser.mention

        if medal_name not in bbData.medalObjs:
            await interaction.response.send_message(f":x: Unknown medal: '{medal_name}'", ephemeral=True)
            return

        medal: Medal = bbData.medalObjs[medal_name]
        if medal not in requestedBUser.medals:
            await interaction.response.send_message(f":x: {userMention} already does not have the {medal.name} medal.", ephemeral=True)
            return
        
        requestedBUser.medals.remove(medal)
        await interaction.response.send_message(f"{cfg.defaultEmojis.submit} {userMention} was un-awarded the {medal.name} medal successfuly.", ephemeral=True)


async def setup(bot: client.BasedClient):
    # Casting here because for some reason pyright doesn't think SerializableDiscordObject is a Snowflake,
    # even though it extends discord.Object
    await bot.add_cog(DevMedalsCog(bot), guilds=cast(List[Snowflake], cfg.developmentGuilds))
