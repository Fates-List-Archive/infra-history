# Fates List

Licensed under the [MIT](LICENSE). We support self hosting and you may ask for help in doing so on our discord server!

This is the source code for [Fates List](https://fateslist.xyz).

BTW please add your bots there if you want to support us :)

## Deploying/Setup instructions

Run ```dragon --cmd site.venv``` to setup a venv for Fates List

Then run ``dragon --cmd db.setup`` after activating the created venv to setup the databases

To create the slash commands: ``dragon --register-only``

**Automatic**
Run ``data/start_tmux.sh`` to automate site startup and setup tmux for you!

**Manual**
To start the dragon (must be started before the main site): ``dragon --cmd dragon.server``

To start the main site (must be started after dragon): ``dragon --cmd site.run``

To start the misc manager bot (must be started after dragon): ``dragon --cmd site.manager``

**Make sure /home/meow exists and you are logged in as meow while running Fates List. fates.sock is the main site socket and fatesws.sock is websocket socket**

PYTHON 3.11: Compile yarl, frozendict and aiohttp from github manually. Compile asyncpg/uvloop from github manually after patching setup.py to remove the cython version check
