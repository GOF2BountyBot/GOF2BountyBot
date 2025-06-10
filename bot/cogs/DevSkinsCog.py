from typing import List, cast

from discord import HTTPException, app_commands, Interaction, Colour
from discord.abc import Snowflake

from .. import client, lib
from bot.cfg import cfg, bbData
from bot.cfg.cfg import basicAccessLevels
from ..interactions import basedCommand
from ..interactions.basedApp import BasedCog
from .util.CommonAutocomplete import shipAutoComplete, ShipKey, \
                                    shipSkinAutoComplete, ShipSkinKey
from ..shipRenderer import shipRenderer

PAINTBRUSH_ICON = "https://emojipedia-us.s3.dualstack.us-west-1.amazonaws.com/thumbs/120/twitter/282/paintbrush_1f58c-fe0f.png"

class DevSkinsCog(BasedCog):
    @shipAutoComplete()
    @shipSkinAutoComplete()
    @basedCommand.basedCommand(accessLevel=basicAccessLevels.developer, helpSection="skins")
    @app_commands.command(name="add-skin",
                            description="Make the specified ship compatible with the specified skin")
    @app_commands.guilds(*cfg.developmentGuilds)
    async def dev_cmd_addSkin(self, interaction: Interaction, ship: ShipKey, skin: ShipSkinKey):
        """Make the specified ship compatible with the specified skin.
        """
        shipData = bbData.builtInShipData[ship]

        if skin in shipData.get("compatibleSkins", []):
            await interaction.response.send_message(f":x: That skin is already compatible with the **{shipData['name']}**!", ephemeral=True)

        else:
            await interaction.response.defer(thinking=True, ephemeral=True)
            await bbData.builtInShipSkins[skin].addShip(shipData['name'], self.bot.skinStorageChannel)
            await interaction.followup.send("Done!", ephemeral=True)


    @shipAutoComplete()
    @shipSkinAutoComplete()
    @basedCommand.basedCommand(accessLevel=basicAccessLevels.developer, helpSection="skins")
    @app_commands.command(name="del-skin",
                            description="Remove the specified ship's compatibility with the specified skin")
    @app_commands.guilds(*cfg.developmentGuilds)
    async def dev_cmd_delSkin(self, interaction: Interaction, ship: ShipKey, skin: ShipSkinKey):
        """Remove the specified ship's compatibility with the specified skin.
        """
        shipData = bbData.builtInShipData[ship]

        if skin not in shipData.get("compatibleSkins", []):
            await interaction.response.send_message(f":x: That skin is already incompatible with the **{shipData['name']}**!", ephemeral=True)

        else:
            await interaction.response.defer(thinking=True, ephemeral=True)
            await bbData.builtInShipSkins[skin].removeShip(shipData['name'], self.bot.skinStorageChannel)
            await interaction.followup.send("Done!", ephemeral=True)


    @shipSkinAutoComplete()
    @basedCommand.basedCommand(accessLevel=basicAccessLevels.developer, helpSection="skins")
    @app_commands.command(name="apply-skin",
                            description="Apply the specified ship skin to the equipped ship")
    @app_commands.guilds(*cfg.developmentGuilds)
    async def dev_cmd_applySkin(self, interaction: Interaction, skin: ShipSkinKey):
        """Remove the specified ship's compatibility with the specified skin.
        """
        activeShip = self.bot.usersDB.getOrAddID(interaction.user.id).activeShip
        if activeShip.isSkinned:
            await interaction.response.send_message(":x: Your ship already has a skin applied!", ephemeral=True)
            return

        shipData = bbData.builtInShipData[activeShip.name]

        if not shipData["skinnable"]:
            await interaction.response.send_message(":x: Your ship is not skinnable!", ephemeral=True)
            return

        if skin not in shipData.get("compatibleSkins", []):
            await interaction.response.send_message(f":x: That skin is incompatible with your active ship! ({activeShip.name})", ephemeral=True)

        else:
            activeShip.applySkin(bbData.builtInShipSkins[skin])
            await interaction.response.send_message("Done!", ephemeral=True)


    @basedCommand.basedCommand(accessLevel=basicAccessLevels.developer, helpSection="skins")
    @app_commands.command(name="unapply-skin",
                            description="Remove the applied skin from the active ship")
    @app_commands.guilds(*cfg.developmentGuilds)
    async def dev_cmd_unapplySkin(self, interaction: Interaction):
        """Remove the applied skin from the active ship.
        """
        activeShip = self.bot.usersDB.getOrAddID(interaction.user.id).activeShip
        if not activeShip.isSkinned:
            await interaction.response.send_message(":x: Your ship has no skin applied!", ephemeral=True)
            return
        elif not activeShip.builtIn:
            await interaction.response.send_message(":x: Your ship is not built in, so the original icon cannot be recovered.", ephemeral=True)
        else:
            activeShip.icon = bbData.builtInShipData[activeShip.name]["icon"]
            activeShip.skin = None
            activeShip.isSkinned = False
            await interaction.response.send_message("Done!", ephemeral=True)

    
    @shipSkinAutoComplete()
    @basedCommand.basedCommand(accessLevel=basicAccessLevels.developer, helpSection="skins")
    @app_commands.command(name="add-skin-to-all-ships",
                            description="Make all builtIn ships in the game compatible with the specified skin")
    @app_commands.guilds(*cfg.developmentGuilds)
    async def dev_cmd_add_skin_to_all_ships(self, interaction: Interaction, skin: ShipSkinKey):
        """Make all builtIn ships in the game compatible with the specified skin.
        """
        await interaction.response.defer(thinking=True, ephemeral=True)

        succeededShips = 0
        failedShips = 0
        for shipName, shipData in bbData.builtInShipData.items():
            if shipData["skinnable"] and skin not in shipData.get("compatibleSkins", []):
                try:
                    await bbData.builtInShipSkins[skin].addShip(shipName, self.bot.skinStorageChannel)
                except shipRenderer.RenderFailed as e:
                    self.bot.logger.log(DevSkinsCog.__name__, DevSkinsCog.dev_cmd_add_skin_to_all_ships.callback.__name__,
                                        f"Failed to render ship '{shipName}' with skin '{skin}'", exception=e, interaction=interaction)
                    failedShips += 1
                else:
                    succeededShips += 1

        await interaction.response.send_message(f"Ship renders complete, with {succeededShips} successful renders and {failedShips} failed renders. See logs for details.")


    @shipSkinAutoComplete()
    @basedCommand.basedCommand(accessLevel=basicAccessLevels.developer, helpSection="skins")
    @app_commands.command(name="del-skin-from-all-ships",
                            description="Make all builtIn ships in the game incompatible with the specified skin")
    @app_commands.guilds(*cfg.developmentGuilds)
    async def dev_cmd_del_skin_from_all_ships(self, interaction: Interaction, skin: ShipSkinKey):
        """Make all builtIn ships in the game incompatible with the specified skin.
        """
        await interaction.response.defer(thinking=True, ephemeral=True)

        for shipName, shipData in bbData.builtInShipData.items():
            if shipData["skinnable"] and skin in shipData.get("compatibleSkins", []):
                await bbData.builtInShipSkins[skin].removeShip(shipName, self.bot.skinStorageChannel)

        await interaction.followup.send("Done!", ephemeral=True)


    @shipAutoComplete()
    @shipSkinAutoComplete()
    @basedCommand.basedCommand(accessLevel=basicAccessLevels.developer, helpSection="skins")
    @app_commands.command(name="show-incompatible-skin",
                            description="Render any ship with any skin, ignoring compatibility")
    @app_commands.guilds(*cfg.developmentGuilds)
    async def dev_cmd_show_incompatible_skin(self, interaction: Interaction, ship: ShipKey, skin: ShipSkinKey):
        """Render any ship with any skin, ignoring compatibility
        """
        shipData = bbData.builtInShipData[ship]

        if not shipData["skinnable"]:
            await interaction.response.send_message(":x: That ship is not skinnable!", ephemeral=True)
            return
        else:
            if skin in shipData.get("compatibleSkins", []):
                itemEmbed = lib.discordUtil.makeEmbed(col=Colour.random(),
                                                        img=bbData.builtInShipSkins[skin].shipRenders[shipData["name"]][0],
                                                        titleTxt=shipData["name"], footerTxt="Custom skin: " + skin.capitalize())
                await interaction.response.send_message(embed=itemEmbed, ephemeral=True)

            else:
                await interaction.response.defer(thinking=True, ephemeral=True)
                await bbData.builtInShipSkins[skin].addShip(shipData["name"], self.bot.showmeRendersChannel)
                itemEmbed = lib.discordUtil.makeEmbed(col=Colour.random(),
                                                        img=bbData.builtInShipSkins[skin].shipRenders[shipData["name"]][0],
                                                        titleTxt=shipData["name"], footerTxt="Custom skin: " + skin.capitalize())
                await interaction.followup.send(embed=itemEmbed, ephemeral=True)
                await bbData.builtInShipSkins[skin].removeShip(shipData["name"], self.bot.showmeRendersChannel)


    @shipAutoComplete()
    @basedCommand.basedCommand(accessLevel=basicAccessLevels.developer, helpSection="skins")
    @app_commands.command(name="try-all-skins",
                            description="Render all skins onto the specified ship")
    @app_commands.guilds(*cfg.developmentGuilds)
    async def dev_cmd_try_all_skins(self, interaction: Interaction, ship: ShipKey):
        """Render all skins onto the specified ship
        """
        shipData = bbData.builtInShipData[ship]

        if not shipData["skinnable"]:
            await interaction.response.send_message(":x: That ship is not skinnable!", ephemeral=True)
            return
        else:
            compatibleSkins = shipData.get("compatibleSkins", [])

            try:
                await interaction.user.send("Sending renders for ship " + shipData["name"] + "...")
            except HTTPException:
                await interaction.response.send_message(":x: I can't DM you!")
                return
            
            await interaction.response.defer(thinking=True, ephemeral=True)

            for skin in bbData.builtInShipSkins:
                if skin not in bbData.builtInShipSkins:
                    await interaction.user.send("Ignoring unrecognised skin: " + skin)

                elif skin in compatibleSkins:
                    itemEmbed = lib.discordUtil.makeEmbed(col=Colour.random(),
                                                            img=bbData.builtInShipSkins[skin].shipRenders[shipData["name"]][0],
                                                            titleTxt=shipData["name"], footerTxt="Custom skin: " + skin.capitalize())
                    await interaction.user.send(embed=itemEmbed)

                else:
                    await bbData.builtInShipSkins[skin].addShip(shipData["name"], self.bot.showmeRendersChannel)
                    itemEmbed = lib.discordUtil.makeEmbed(col=Colour.random(),
                                                            img=bbData.builtInShipSkins[skin].shipRenders[shipData["name"]][0],
                                                            titleTxt=shipData["name"], footerTxt="Custom skin: " + skin.capitalize())
                    await interaction.user.send(embed=itemEmbed)
                    await bbData.builtInShipSkins[skin].removeShip(shipData["name"], self.bot.showmeRendersChannel)

        await interaction.user.send("All skins sent for ship " + shipData["name"] + ".")
        await interaction.followup.send("All skins sent.", ephemeral=True)


    @basedCommand.basedCommand(accessLevel=basicAccessLevels.developer, helpSection="skins")
    @app_commands.command(name="set-showme-res",
                            description="Configure the resolution that cmd_showme_ship will render to")
    @app_commands.guilds(*cfg.developmentGuilds)
    async def dev_cmd_set_autoskin_resolution(self, interaction: Interaction, width: int, height: int):
        """Configure the resolution that cmd_showme_ship will render to.
        """
        cfg.skinRenderShowmeResolution = [width, height]
        await interaction.response.send_message(f"✅ Done!", ephemeral=True)


    @basedCommand.basedCommand(accessLevel=basicAccessLevels.developer, helpSection="skins")
    @app_commands.command(name="set-showme-samples",
                            description="Configure the samples that cmd_showme_ship will render to")
    @app_commands.guilds(*cfg.developmentGuilds)
    async def dev_cmd_set_autoskin_samples(self, interaction: Interaction, samples: int):
        """Configure the samples that cmd_showme_ship will render to.
        """
        cfg.skinRenderShowmeSamples = samples
        await interaction.response.send_message(f"✅ Done!", ephemeral=True)


    @basedCommand.basedCommand(accessLevel=basicAccessLevels.developer, helpSection="skins")
    @app_commands.command(name="showme-config",
                            description="Get the current configuration for rendering with cmd_showme_ship")
    @app_commands.guilds(*cfg.developmentGuilds)
    async def dev_cmd_get_autoskin_configuration(self, interaction: Interaction):
        """Get the current configuration for rendering with cmd_showme_ship
        """
        e = lib.discordUtil.makeEmbed(authorName="Ship Renderer Configuration",
                                        icon=PAINTBRUSH_ICON, desc="For command: `$showme ship`",
                                        col=Colour.random())
        e.add_field(name="Samples", value=str(cfg.skinRenderShowmeSamples))
        e.add_field(name="Resolution", value=f"x: {cfg.skinRenderShowmeResolution[0]}\ny: {cfg.skinRenderShowmeResolution[1]}")
        await interaction.response.send_message(embed=e, ephemeral=True)
    

async def setup(bot: client.BasedClient):
    # Casting here because for some reason pyright doesn't think SerializableDiscordObject is a Snowflake,
    # even though it extends discord.Object
    await bot.add_cog(DevSkinsCog(bot), guilds=cast(List[Snowflake], cfg.developmentGuilds))
