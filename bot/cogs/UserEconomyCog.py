from typing import Dict, Literal, Optional, Union, cast

from discord import Guild, Member, User, app_commands, Interaction
from discord.app_commands import Range

from bot.gameObjects.items.shipItem import Ship

from .. import client
from ..lib.stringTyping import isInt, commaSplitNum
from ..lib.discordUtil import makeEmbed, ZWSP
from ..lib.gameMaths import calculateUserBountyHuntingLevel
from ..cfg import cfg
from ..cfg.cfg import basicAccessLevels
from ..cfg.bbData import ItemCategory
from ..interactions import basedCommand
from ..interactions.basedApp import BasedCog
from ..users import basedUser
from .util.CommonAutocomplete import divisionAutoComplete, anyUserHangerItemAutoComplete, anyUserHangerItemAutoComplete_decodeValue
from .util.transformers import BoolYesNo
from ..interactions.commandChecks import guildOnly
from ..gameObjects.guildShop import TechLeveledShop
from ..logging import LogCategory
from ..views.confirmView import ConfirmView


class UserEconomyCog(BasedCog):
#region util

    async def targetUser(self, interaction: Interaction, user: Optional[Union[User, Member]], user_id: Optional[str]) -> Optional[Union[User, Member]]:
        if (user_id is not None and user is not None) or (user is None and user_id is None):
            await interaction.response.send_message(":x: Please give exactly one of `user` or `user_id`!", ephemeral=True)
            return None

        if user_id is not None:    
            if not isInt(user_id):
                await interaction.response.send_message(":x: Invalid `user_id` - must be a number.", ephemeral=True)
                return None

            user = self.bot.get_user(int(user_id))
            
        if user is None:
            await interaction.response.send_message(":x: Unknown user!", ephemeral=True)
            return None

        return user


    async def targetUserOrAuthor(self, interaction: Interaction, user: Optional[Union[User, Member]], user_id: Optional[str]) -> Optional[Union[User, Member]]:
        if user_id is not None:
            if user is not None:
                await interaction.response.send_message(":x: Please only give at most one of `user` or `user_id`!", ephemeral=True)
                return None
            if not isInt(user_id):
                await interaction.response.send_message(":x: Invalid `user_id` - must be a number.", ephemeral=True)
                return None

            user = self.bot.get_user(int(user_id))
            if user is None:
                await interaction.response.send_message(":x: Unknown user!", ephemeral=True)
                return None

        if user is None:
            user = interaction.user

        return user

#endregion

    @basedCommand.basedCommand(accessLevel=basicAccessLevels.user, helpSection="economy")
    @app_commands.describe(user="The user whose balance to check.",
                            user_id="The ID of the user whose balance to check. Useful if they are in another server.")
    @app_commands.command(name="balance",
                            description="Give no arguments to check your credits balance, give a user to check their balance.")
    async def cmd_balance(self, interaction: Interaction, user: Optional[Union[User, Member]] = None, user_id: str = ""):
        """print the balance of the specified user, using the calling user if no user is specified.
        """
        if not (user := await self.targetUserOrAuthor(interaction, user, user_id)): return

        if self.bot.usersDB.idExists(user.id):
            bal = self.bot.usersDB.getUser(user.id).credits
        else:
            bal = basedUser.defaultUserDict.get("credits", 0)

        await interaction.response.send_message(f":moneybag: {'You have' if user == interaction.user else f'{user} has'} **{commaSplitNum(bal)} credits.**")

    
    @guildOnly(shopsEnabled=True)
    @divisionAutoComplete(allowAllDivisions=False)
    @basedCommand.basedCommand(accessLevel=basicAccessLevels.user, helpSection="economy",
                                formattedDesc="Display all items currently for sale. Shop stock is refreshed every six hours, with items" \
                                            + f" based on its tech level. Give an item type ({'/'.join(i.value for i in ItemCategory)}) to only" \
                                            + " list items of that type. To shop the shop for a division other than your own, " \
                                            + "specify the division name.")
    @app_commands.describe(item_type="The type of items to view. Default: All items",
                            division="The shop to view. Default: Your division's shop")
    @app_commands.command(name="shop",
                            description="View the current stock of this server's shop. Give no arguments to view all items in your division.")
    async def cmd_shop(self, interaction: Interaction, item_type: Union[Literal['all'], ItemCategory] = "all", division: Optional[str] = None):
        """list the current stock of the guildShop owned by the guild containing the sent message.
        Can specify an item type to list.
        """
        # Casting because this command has @guildOnly(shopsEnabled=True), so it can only be called from a guild with shops enabled.
        guild = cast(Guild, interaction.guild)
        bGuild = self.bot.guildsDB.getGuild(guild.id)
        divShops = cast(Dict[str, TechLeveledShop], bGuild.divisionShops)

        bUser = self.bot.usersDB.getUser(interaction.user.id) if self.bot.usersDB.idExists(interaction.user.id) else None
        isClassicMode = bUser is not None and bUser.classicModeEnabled

        if division is None:
            userLevel = cfg.minTechLevel if bUser is None or bUser.classicModeEnabled else calculateUserBountyHuntingLevel(bUser.bountyHuntingXP)
            userDivisionName = cfg.divisionNameForPlayerLevel(userLevel)
            division = userDivisionName

        shop = divShops[division]

        classicModeDesc = ("You are playing in classic mode. " \
                        + "You can access any shop by giving its division name in shop commands.\n") \
                        if isClassicMode else ""

        shopEmbed = makeEmbed(titleTxt=f"{division} Shop",
                                desc=f"__{guild.name}__\n" \
                                    + classicModeDesc \
                                    + f"`Current Tech Level: {shop.currentTechLevel}`",
                                footerTxt="All items" if item_type == "all" else (item_type.value + "s").title(),
                                thumb="" if guild.icon is None else guild.icon.with_size(64).url)

        for currentItemType in [ItemCategory.ship, ItemCategory.weapon, ItemCategory.module, ItemCategory.turret, ItemCategory.tool]:
            if item_type in ["all", currentItemType]:
                currentStock = shop.getStock(currentItemType)

                for itemNum in range(1, currentStock.numKeys + 1):
                    if itemNum == 1:
                        shopEmbed.add_field(name=ZWSP, value=f"__**{currentItemType.value.title()}s**__", inline=False)

                    try:
                        currentItem = currentStock.itemAtIndex(itemNum - 1)
                    except KeyError:
                        try:
                            self.bot.logger.log("Main", "cmd_shop",
                                                f"Requested {currentItemType.value} '{currentStock.keys[itemNum-1].name}' " \
                                                    + f"(index {itemNum-1}), which was not found in the shop stock",
                                                category=LogCategory.shop, eventType="UNKWN_KEY")
                        except IndexError:
                            break
                        except AttributeError:
                            keysStr = ", ".join(str(i) for i in currentStock.items)
                            self.bot.logger.log("Main", "cmd_shop",
                                                f"Unexpected type in {currentItemType.value}sStock KEYS, index " \
                                                    + f"{itemNum-1}. Got {type(currentStock.keys[itemNum-1]).__name__}" \
                                                    + f".\nInventory keys: {keysStr}",
                                                category=LogCategory.shop, eventType="INVTY_KEY_TYPE")
                            shopEmbed.add_field(name=f"{itemNum}. **⚠ #INVALID-ITEM# '{currentStock.keys[itemNum-1]}'",
                                                value="Do not attempt to buy. Could cause issues.", inline=True)
                            continue
                        shopEmbed.add_field(name=f"{itemNum}. **⚠ #INVALID-ITEM# '{currentStock.keys[itemNum-1].name}'",
                                            value="Do not attempt to buy. Could cause issues.", inline=True)
                        
                        continue


                    currentItemCount = currentStock.items[currentItem].count

                    itemEmoji = f"{currentItem.emoji.sendable} " if currentItem.hasEmoji else ""
                    itemCountStr = f"`({currentItemCount})` " if currentItemCount > 1 else ""
                    shopEmbed.add_field(name=f"{itemNum}. {itemEmoji}{itemCountStr}**{currentItem.name}**",
                                        value=commaSplitNum(currentItem.value) + " Credits\n" \
                                            + currentItem.statsStringShort(), inline=True)

        await interaction.response.send_message(embed=shopEmbed, ephemeral=True)


    @guildOnly(shopsEnabled=True)
    @divisionAutoComplete(allowAllDivisions=False)
    @basedCommand.basedCommand(accessLevel=basicAccessLevels.user, helpSection="economy",
                                formattedDesc="Buy the requested item from the shop. Item numbers are shown next to items in the `shop`." \
                                            + "\nWhen buying from a division other than your own, specify the division name." \
                                            + "\nWhen buying a ship, specify `sell_old_ship` to sell your active ship, and/or `move_equipped_items` to " \
                                            + "move your active items to the new ship. I.e, *to sell your active ship without " \
                                            + "selling the items on the ship, use:* `/buy item_type:ship <ship number> sell_old_ship:Yes move_equipped_items:Yes`.*" \
                                            + "\n🌎 This command must be used in your **home server**.")
    @app_commands.describe(item_type="The type of item to buy.",
                            item_number="The number of the item to buy, as shown in `/shop`.",
                            sell_old_ship="When buying a ship, sell your currently equipped ship first. Default: No",
                            move_equipped_items="When buying a ship, move your currently equipped items to the new one. Default: No",
                            division="The shop to buy from. You can only buy from your division or lower. Default: Your division's shop")
    @app_commands.command(name="buy",
                            description="🌎 Buy the requested item from the shop. Item numbers can be seen in the `/shop`")
    async def cmd_shop_buy(self, interaction: Interaction, item_type: ItemCategory, item_number: Range[int, 1], sell_old_ship: BoolYesNo = BoolYesNo.No, move_equipped_items: BoolYesNo = BoolYesNo.No, division: Optional[str] = None):
        """Buy the item of the given item type, at the given index, from the guild's shop.
        if "transfer" is specified, the new ship's items are unequipped, and the old ship's items attempt to fill the new ship.
        any items left unequipped are added to the user's inactive items lists.
        if "sell" is specified, the user's old activeShip is stripped of items and sold to the shop.
        "transfer" and "sell" are only valid when buying a ship.
        """
        sellOldShip = bool(sell_old_ship)
        moveEquippedItems = bool(move_equipped_items)

        # Casting because this command has @guildOnly(shopsEnabled=True), so it can only be called from a guild with shops enabled.
        guild = cast(Guild, interaction.guild)
        bGuild = self.bot.guildsDB.getGuild(guild.id)
        divShops = cast(Dict[str, TechLeveledShop], bGuild.divisionShops)

        bUser = self.bot.usersDB.getUser(interaction.user.id) if self.bot.usersDB.idExists(interaction.user.id) else None
        isClassicMode = bUser is not None and bUser.classicModeEnabled
        userLevel = cfg.minTechLevel if bUser is None or bUser.classicModeEnabled else calculateUserBountyHuntingLevel(bUser.bountyHuntingXP)
        userDivisionName = cfg.divisionNameForPlayerLevel(userLevel)

        if division is None:
            division = userDivisionName

        if not isClassicMode and cfg.bountyDivisionNames.index(userDivisionName) < cfg.bountyDivisionNames.index(division):
            await interaction.response.send_message(f":x: You are not high enough level to use the {division} shop!", ephemeral=True)
            return

        shop = divShops[division]

        # verify this is the calling user's home guild. If no home guild is set, transfer here.
        if bUser is not None and bUser.hasHomeGuild() and bUser.homeGuildID != guild.id:
            await interaction.response.send_message(":x: This command can only be used from your home server!", ephemeral=True)
            return

        shopItemStock = shop.getStock(item_type)
        if item_number > shopItemStock.numKeys:
            if shopItemStock.numKeys == 0:
                await interaction.response.send_message(f":x: This shop has no {item_type.value}s in stock!", ephemeral=True)
            else:
                await interaction.response.send_message(f":x: Invalid item number! This shop has {shopItemStock.numKeys} {item_type.value}(s).", ephemeral=True)
            return

        requestedItem = shopItemStock.itemAtIndex(item_number - 1)
        userBalance = basedUser.defaultUserDict.get("credits", 0) if bUser is None else bUser.credits

        if item_type is ItemCategory.ship:
            if not isinstance(requestedItem, Ship): raise TypeError(f"Expected item of type {Ship.__name__}, received {type(requestedItem).__name__}")

            newShipValue = requestedItem.getValue()
            activeShip = Ship.deserialize(basedUser.defaultShipLoadoutDict) if bUser is None else bUser.activeShip

            # Check the item can be afforded
            effectiveCredits = userBalance
            if sellOldShip:
                effectiveCredits += activeShip.getValue(shipUpgradesOnly=moveEquippedItems)

            if effectiveCredits < newShipValue:
                await interaction.response.send_message(f":x: You can't afford that item! You need {newShipValue - effectiveCredits} more credits.", ephemeral=True)
                return

            if bUser is None:
                bUser = self.bot.usersDB.addID(interaction.user.id)

            bUser.inactiveShips.addItem(requestedItem)

            if moveEquippedItems:
                bUser.unequipAll(requestedItem)
                activeShip.transferItemsTo(requestedItem)
                itemsNotTransferred = bUser.unequipAll(activeShip)
            else:
                itemsNotTransferred = 0

            if sellOldShip:
                # TODO: move to a separate sellActiveShip function
                oldShipValue = activeShip.getValue(shipUpgradesOnly=moveEquippedItems)
                bUser.credits += oldShipValue
                shopItemStock.addItem(activeShip)
            else:
                oldShipValue = None

            bUser.equipShipObj(requestedItem, noSaveActive=sellOldShip)
            bUser.credits -= newShipValue
            shopItemStock.removeItem(requestedItem)
            
            outStr = ""
            if not bUser.hasHomeGuild():
                await bUser.transferGuild(guild)
                outStr += ":airplane_arriving: Your home server has been set.\n\n"
            
            outStr += f":moneybag: Congratulations on your new **{requestedItem.name}**!"
            if sellOldShip:
                outStr += f"\nYou received **{oldShipValue} credits** for your old **{activeShip.name}**."
            else:
                outStr += f" Your old **{activeShip.name}** can be found in the hangar."
            if moveEquippedItems:
                if itemsNotTransferred:
                    outStr += f"\n**{itemsNotTransferred}** equipped items could not fit in your new ship, and can be found in the hangar."
                else:
                    outStr += f"\nAll equipped items were moved to your new ship."
            outStr += f"\n\nYour balance is now: **{bUser.credits} credits**."

            await interaction.response.send_message(outStr)

        elif item_type in [ItemCategory.weapon, ItemCategory.module, ItemCategory.turret, ItemCategory.tool]:
            newItemValue = requestedItem.getValue()
            if userBalance < newItemValue:
                await interaction.response.send_message(f":x: You can't afford that item! You need {newItemValue - userBalance} more credits.", ephemeral=True)
                return

            if bUser is None:
                bUser = self.bot.usersDB.addID(interaction.user.id)

            bUser.credits -= requestedItem.value
            # Ignoring here because I can't statically hint that getInventory will match the requested item type
            bUser.getInventory(item_type).addItem(requestedItem) # type: ignore[reportGeneralTypeIssues]
            shopItemStock.removeItem(requestedItem)

            outStr = ""
            if not bUser.hasHomeGuild():
                await bUser.transferGuild(guild)
                outStr += ":airplane_arriving: Your home server has been set.\n\n"

            await interaction.response.send_message(f"{outStr}:moneybag: Congratulations on your new **{requestedItem.name}" \
                                                + f"**! \n\nYour balance is now: **{bUser.credits} credits**.")
        else:
            raise NotImplementedError("Valid but unsupported item name: " + item_type.value)


    @guildOnly(shopsEnabled=True)
    @anyUserHangerItemAutoComplete()
    @basedCommand.basedCommand(accessLevel=basicAccessLevels.user, helpSection="economy",
                                formattedDesc="Sell the requested item from your hangar to the shop in your division.\n" \
                                            + "When selling a ship, specify `unequip_items` to first remove all " \
                                            + "items from the ship. See `help buy` for how to sell your active ship.\n" \
                                            + "🌎 This command must be used in your **home server**.")
    @app_commands.describe(item="The item from your hangar to sell.",
                            unequip_items="When selling a ship, automatically unequip all items on the ship, and keep them. Default: Yes")
    @app_commands.command(name="sell",
                            description="🌎 Sell the requested item from your hangar, to your division's shop.")
    async def cmd_shop_sell(self, interaction: Interaction, item: str, unequip_items: BoolYesNo = BoolYesNo.Yes):
        """Sell the item of the given item type, at the given index, from the user's inactive items, to the guild's shop.
        if "clear" is specified, the ship's items are unequipped before selling.
        "clear" is only valid when selling a ship.
        """
        itemType, itemNum = anyUserHangerItemAutoComplete_decodeValue(item)
        
        # Casting because this command has @guildOnly(shopsEnabled=True), so it can only be called from a guild with shops enabled.
        guild = cast(Guild, interaction.guild)
        bGuild = self.bot.guildsDB.getGuild(guild.id)
        divShops = cast(Dict[str, TechLeveledShop], bGuild.divisionShops)

        bUser = self.bot.usersDB.getOrAddID(interaction.user.id)
        userLevel = cfg.minTechLevel if bUser.classicModeEnabled else calculateUserBountyHuntingLevel(bUser.bountyHuntingXP)
        userDivisionName = cfg.divisionNameForPlayerLevel(userLevel)

        # verify this is the calling user's home guild. If no home guild is set, transfer here.
        if not bUser.hasHomeGuild():
            await bUser.transferGuild(guild)
            await interaction.response.send_message(":airplane_arriving: Your home server has been set.", ephemeral=True)
        elif bUser.homeGuildID != guild.id:
            await interaction.response.send_message(":x: This command can only be used from your home server!", ephemeral=True)
            return
        
        clearItems = bool(unequip_items)
        shop = divShops[userDivisionName]

        shopItemStock = shop.getStock(itemType)
        userItemInactives = bUser.getInventory(itemType)
        requestedItem = userItemInactives.itemAtIndex(itemNum - 1)

        if item is ItemCategory.ship:
            if not isinstance(requestedItem, Ship):
                raise TypeError(f"item type is {itemType.value}, but referenced item is {type(requestedItem).__name__} instead of {Ship.__name__}")

            unequippedItems = bUser.unequipAll(requestedItem) if clearItems else 0

            bUser.credits += requestedItem.getValue()
            # Ignoring here because I verified the item type above
            userItemInactives.removeItem(requestedItem) # type: ignore[reportGeneralTypeIssues]
            shopItemStock.addItem(requestedItem)

            outStr = f":moneybag: You sold your **{requestedItem.getNameOrNick()}** for **" \
                        + f"{requestedItem.getValue()} credits**!"
            if clearItems:
                outStr += f"\n{unequippedItems} items were removed from the ship, and can be found in your hangar."

            await interaction.response.send_message(outStr)

        else:
            shop.userSellItem(bUser, requestedItem)
            await interaction.response.send_message(f":moneybag: You sold your **{requestedItem.name}** for **{requestedItem.getValue()} credits**!")
    

    @basedCommand.basedCommand(accessLevel=basicAccessLevels.user, helpSection="economy",
                                formattedDesc="Pay the given user an amount of credits from your balance.\n" \
                                            + "\n🌎 You can only pay users who share your **home server**.")
    @app_commands.describe(user="The user to pay.",
                            user_id="The ID of the user to pay. Useful if they are in another server.")
    @app_commands.command(name="pay",
                            description="Pay the given user an amount of credits from your balance.")
    async def cmd_pay(self, interaction: Interaction, amount: Range[int, 0], user: Optional[Union[User, Member]] = None, user_id: str = ""):
        """Pay a given user the given number of credits from your balance.
        """
        if not (user := await self.targetUser(interaction, user, user_id)): return
        bUser = self.bot.usersDB.getUser(interaction.user.id) if self.bot.usersDB.idExists(interaction.user.id) else None

        if bUser is None or bUser.credits < amount:
            await interaction.response.send_message(":x: You don't have that many credits!", ephemeral=True)
            return
            
        targetBUser = self.bot.usersDB.getUser(interaction.user.id) if self.bot.usersDB.idExists(interaction.user.id) else None
        if targetBUser is None or not targetBUser.hasHomeGuild():
            await interaction.response.send_message(f"You must have the same home server as {user.display_name} in order to pay them, and they do not have a home server.", ephemeral=True)
            return

        if not bUser.hasHomeGuild():
            if interaction.guild is None:
                await interaction.response.send_message("You must have a home server set in order to use this command.", ephemeral=True)
                return

            timeout = int(cfg.timeouts.homeGuildTransferCooldown.total_seconds())
            view = ConfirmView(timeout=timeout)
            await interaction.response.send_message("You must have a home server set in order to use this command.\n" \
                                                    + f"Set your home server to '{interaction.guild.name}' now?",
                                                    view=view, ephemeral=True)
            
            if await view.wait() or not view.confirmed:
                return

            await bUser.transferGuild(interaction.guild)

        if targetBUser.homeGuildID != bUser.homeGuildID:
            await interaction.response.send_message(":x: You can only pay players with the same home server as you!", ephemeral=True)
            return
        
        bUser.credits -= amount
        targetBUser.credits += amount

        await interaction.response.send_message(f":moneybag: You paid {user.display_name} **{amount}** credits!")
        await targetBUser.individualNotify(self.bot, f":moneybag: {interaction.user.mention} paid you **{amount}** credits!")


    @basedCommand.basedCommand(accessLevel=basicAccessLevels.user, helpSection="economy",
                                formattedDesc="Get the total value of all of your items, including your credits balance. " \
                                            + "Give a user to check someone else's total inventory value.")
    @app_commands.describe(user="The user to pay.",
                            user_id="The ID of the user to pay. Useful if they are in another server.")
    @app_commands.command(name="total_value",
                            description="Get the total value of all of your items, including your credits balance, or that of another user.")
    async def cmd_total_value(self, interaction: Interaction, user: Optional[Union[User, Member]] = None, user_id: str = ""):
        """⚠ WARNING: MARKED FOR CHANGE ⚠
        The following function is provisional and marked as planned for overhaul.
        Details: The command output is finalised. However, the inner workings of the command are to be replaced with attribute
        getters. It is inefficient to calculate total value measurements on every call, so current totals should be cached in
        object attributes whenever modified.

        print the total value of the specified user, use the calling user if no user is specified.
        """
        if not (user := await self.targetUserOrAuthor(interaction, user, user_id)): return

        bUser = self.bot.usersDB.getUser(interaction.user.id) if self.bot.usersDB.idExists(interaction.user.id) else None
        userValue = basedUser.defaultUserValue if bUser is None else bUser.getTotalValue()

        isAuthor = user is None and user_id == ""
        userHas = "Your" if isAuthor else f"**{user}'s**"

        await interaction.response.send_message(f":moneybag: {userHas} your items and balance are worth a total of **{userValue}** credits.")


async def setup(bot: client.BasedClient):
    await bot.add_cog(UserEconomyCog(bot))
