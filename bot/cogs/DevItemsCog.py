import json
from typing import List, cast

from bot.cfg import bbData

from .. import client, lib
from ..lib.discordUtil import ZWSP
from discord import app_commands, Interaction, Embed
from discord.abc import GuildChannel, Snowflake
from discord.utils import utcnow, MISSING
from discord.app_commands import Range
from ..cfg import cfg
from ..cfg.cfg import basicAccessLevels
from ..interactions import basedCommand
from ..interactions.basedApp import BasedCog
from ..gameObjects.items import gameItem, shipItem
from .util.transformers import ItemCategory
from typing import List, cast


class DevItemsCog(BasedCog):
    def __init__(self, bot: client.BasedClient, *args, **kwargs):
        self.bot = bot
        super().__init__(*args, **kwargs)

#region commands

    @basedCommand.basedCommand(accessLevel=basicAccessLevels.developer)
    @app_commands.command(name="give-item",
                            description="Spawn in an item and give it to a user.")
    @app_commands.guilds(*cfg.developmentGuilds)
    async def dev_cmd_give(self, interaction: Interaction, item_json: str, user_id: str = ""):
        """developer command giving the provided user the provided item of the provided type.
        user must be either an ID or empty (to give the item to the calling user).
        item must be a json format description in line with the item's to and deserialize functions.
        """
        requestedUser = await self.UsersUtilCog.getBasedUserOrAuthor(interaction, user_id, sendError=False)
        if requestedUser is None:
            intId = int(user_id)
            dcUser = self.bot.get_user(intId) or await self.bot.fetch_user(intId)
            if dcUser is None:
                await interaction.response.send_message(":x: Unknown user.", ephemeral=True)
                return
            requestedUser = self.bot.usersDB.getOrAddID(intId)
        else:
            dcUser = self.bot.get_user(requestedUser.id) or await self.bot.fetch_user(requestedUser.id)

        try:
            itemDict = json.loads(item_json)
        except json.JSONDecodeError as e:
            await interaction.response.send_message(f":x: Your `item_json` is not valid json: {e}", ephemeral=True)
            return

        if "type" not in itemDict:
            await interaction.response.send_message(f":x: Failed to deserialize your `item_json`: Missing 'type' property", ephemeral=True)
            return

        if itemDict["type"] not in gameItem.subClassNames:
            await interaction.response.send_message(f":x: Failed to deserialize your `item_json`: Unknown gameItem subclass '{itemDict['type']}'", ephemeral=True)
            return

        newItem = gameItem.spawnItem(itemDict)
        requestedUser.getInventoryForItem(newItem).addItem(newItem)

        await interaction.response.send_message(f":white_check_mark: Given one '{newItem.name}' to **" \
                                                + dcUser.mention + "**!", ephemeral=True)


    @basedCommand.basedCommand(accessLevel=basicAccessLevels.developer)
    @app_commands.command(name="delete-item",
                            description="Delete one of an item in a user's inventory. If they have more several, the other are not affected.")
    @app_commands.guilds(*cfg.developmentGuilds)
    async def dev_cmd_del_item(self, interaction: Interaction, item_type: ItemCategory, item_number: Range[int, 1, ...], user_id: str = ""):
        """Delete an item in a requested user's inventory.
        """
        requestedBBUser = await self.UsersUtilCog.getBasedUserOrAuthor(interaction, user_id)
        if requestedBBUser is None: return

        userItemInactives = requestedBBUser.getInactivesByName(item_type.value)
        if item_number > userItemInactives.numKeys:
            await interaction.response.send_message(f":x: Invalid item number! The user only has {userItemInactives.numKeys} {item_type.value}s.",
                                                    ephemeral=True)
            return

        requestedItem = userItemInactives.itemAtIndex(item_number - 1)
        itemName = ""
        itemEmbed = None

        if item_type == ItemCategory.ship:
            requestedItem = cast(shipItem.Ship, requestedItem)
            itemName = requestedItem.getNameAndNick()
            itemEmbed = lib.discordUtil.makeEmbed(col=bbData.factionColours.get(requestedItem.manufacturer, bbData.factionColours["neutral"]),
                                                    thumb=requestedItem.icon if requestedItem.hasIcon else "")

            if requestedItem is None:
                itemEmbed.add_field(name="Item:",
                                    value="None", inline=False)
            else:
                itemEmbed.add_field(name="Item:", inline=False,
                                    value=requestedItem.getNameAndNick() + "\n" + requestedItem.statsStringNoItems())
                
                for name, inv, max in ( ("Weapons", requestedItem.weapons, requestedItem.getMaxPrimaries()),
                                        ("Modules", requestedItem.modules, requestedItem.getMaxPrimaries()),
                                        ("Turrets", requestedItem.turrets, requestedItem.getMaxPrimaries())):
                    if max == 0: continue
                    itemEmbed.add_field(name=ZWSP, value=f"__**Equipped {name}**__ *{len(inv)}/{max}*", inline=False)
                    for i in range(1, len(inv) + 1):
                        current = inv[i - 1]
                        emoji = f"{current.emoji} " if current.hasEmoji else ""
                        itemEmbed.add_field(name=f"{i}. {emoji} {current.name}", value=current.statsStringShort(), inline=True)

        else:
            itemName = requestedItem.name + "\n" + requestedItem.statsStringShort()

        # Ignoring here because requestedItem is guaranteed to match userItemInactives's contained type, because it was retrieved from userItemInactives
        userItemInactives.removeItem(requestedItem) # type: ignore[reportGeneralTypeIssues]

        userName = str(self.bot.get_user(requestedBBUser.id) or "<unknown user>")
        await interaction.response.send_message(f":white_check_mark: One item deleted from {userName}'s inventory: {itemName}",
                                                embed=itemEmbed or MISSING)

#endregion

async def setup(bot: client.BasedClient):
    # Casting here because for some reason pyright doesn't think SerializableDiscordObject is a Snowflake,
    # even though it extends discord.Object
    await bot.add_cog(DevItemsCog(bot), guilds=cast(List[Snowflake], cfg.developmentGuilds))
