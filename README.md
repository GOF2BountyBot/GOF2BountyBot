This repository is a work-in-progress port of [BountyBot](https://github.com/Trimatix/GOF2BountyBot) onto the [BASED](https://github.com/Trimatix/BASED) platform. The game's code has only partially been copied over, but is in a state of basic functionality.

---

<p align="center">
  <img
    width="256"
    src="https://i.imgur.com/mt0eL8l.png"
    alt="BountyBot Logo"
  />
</p>
<h1 align="center">BountyBot - A GOF2 Fan Project</h1>
<p align="center">
  <a href="https://github.com/GOF2BountyBot/GOF2BountyBot/actions"
    ><img
      src="https://img.shields.io/github/workflow/status/GOF2BountyBot/GOF2BountyBot/BASED"
      alt="GitHub Actions workflow status"
  /></a>
  <a href="https://github.com/GOF2BountyBot/GOF2BountyBot/projects/1?card_filter_query=label%3Abug"
    ><img
      src="https://img.shields.io/github/issues-search?color=eb4034&label=bugs&query=repo%3AGOF2BountyBot%2FGOF2BountyBot%20is%3Aopen%20label%3Abug"
      alt="GitHub open bug reports"
  /></a>
  <a href="https://github.com/GOF2BountyBot/GOF2BountyBot/projects/1?card_filter_query=label%3Agame%20balance"
    ><img
      src='https://img.shields.io/github/issues-search?color=46d2e8&label=balance%20issues&query=repo%3AGOF2BountyBot%2FGOF2BountyBot%20is%3Aopen%20label%3A"game+balance"'
      alt="GitHub open game balance issues"
  /></a>
  <a href="https://github.com/GOF2BountyBot/GOF2BountyBot/projects/1?card_filter_query=label%3Aenhancement"
    ><img
      src="https://img.shields.io/github/issues-search?color=edd626&label=upcoming%20features&query=repo%3AGOF2BountyBot%2FGOF2BountyBot%20is%3Aopen%20label%3Aenhancement"
      alt="GitHub open enhancement issues"
  /></a>
</p>
<p align="center">
  <a href="https://sonarcloud.io/dashboard?id=GOF2BountyBot_GOF2BountyBot"
    ><img
      src="https://sonarcloud.io/api/project_badges/measure?project=GOF2BountyBot_GOF2BountyBot&metric=bugs"
      alt="SonarCloud bugs analysis"
  /></a>
  <a href="https://sonarcloud.io/dashboard?id=GOF2BountyBot_GOF2BountyBot"
    ><img
      src="https://sonarcloud.io/api/project_badges/measure?project=GOF2BountyBot_GOF2BountyBot&metric=code_smells"
      alt="SonarCloud code smells analysis"
  /></a>
  <a href="https://sonarcloud.io/dashboard?id=GOF2BountyBot_GOF2BountyBot"
    ><img
      src="https://sonarcloud.io/api/project_badges/measure?project=GOF2BountyBot_GOF2BountyBot&metric=alert_status"
      alt="SonarCloud quality gate status"
  /></a>
</p>

# GOF2BountyBot
An ambitious discord bot written in python, recreating some of the features of Galaxy on Fire 2. Currently, the standout features are the bounty hunting system, and the items/loadout/trading/dueling system.

# Architecture
The 'main' file is `bot.bot`, which defines regular behaviour with `discord.Client.event`s.
Command definitions are located in the various modules of the `commands` package.

## cfg
This package configures the game's behaviour with BASED's automatic TOML config file generation, and a custom gameConfigurator script that parses a set of JSON game object descriptions.

## gameObjects
Contains definitions for all *game objects* - representing items useable by the players (items, inventories) and playing functionality of the game itself (shops, bounties, duels).

## shipRenderer
At its base, `_render.py `implements calls to [blender](https://www.blender.org/) to render a named model with a named texture file. `shipRenderer.py` makes use of this, passing renderer arguments to blender through the `render_args` plaintext file. `shipRenderer` is capable of compositing multiple textures according to image masks,using the `Pillow` library. All of this behaviour can be called asynchronously to render a given `Ship` with a series of texture files according to the ship's textureRegion masks, by using the `shipRenderer.renderShip` coroutine.

## userAlerts
Defines the versitile `UABase` class, which can be used to assign boolean alert subscriptions to alert behaviour, to be called upon certain events. For example, a guild may define a `UA_Shop_Refresh` alert, corresponding to a role within the guild. Users may then subscribe to this alert, granting them the role. The shop refreshing `TimedTask` expiry function is directed to check for the existence of such an alert in guilds, and ping the alerting role.

