Licensed under the MIT. We officially support self hosting of our list and you can request for help on our [support server](https://fateslist.xyz/servers/789934742128558080).

This is the source code for [Fates List](https://fateslist.xyz/)

BTW please add your bots there if you wish to support us. It would mean a lot!

::: warning

Fates List is a bit difficult (without basic knowledge in python/golang/rust) to self-host. 

It requires a Linux distribution (such as what we officially use: Fedora) at this time. 

Fates List also uses quite a few moving parts including PostgreSQL 14 (older versions *may* work but will never be tested) and Redis. 

**We welcome all contributors and self hosters to Fates List**

:::

## Domain Setup

1. Buy a domain (You will need a domain that can be added to Cloudflare in order to use Fates List. We use namecheap for this)

2. Add the domain to Cloudflare (see [this](https://support.cloudflare.com/hc/en-us/articles/201720164-Creating-a-Cloudflare-account-and-adding-a-website)). Our whole website requires Cloudflare as the DNS in order to work.

3. Buy a Linux VPS (You need a Linux VPS or a Linux home server with a public ip with port 443 open)

4. In Cloudflare, create a record (A/CNAME) called @ that points to your VPS ip/hostname

5. In Cloudflare, go to Speed > Optimization. Enable AMP Real URL

6. In Cloudflare, go to SSL/TLS, set the mode to Full (strict), enable Authenticated Origin Pull, make an origin certificate (in Origin Server) and save the private key as /key.pem on your VPS and the certificate as /cert.pem on your VPS

7. Download [https://support.cloudflare.com/hc/en-us/article_attachments/360044928032/origin-pull-ca.pem](https://support.cloudflare.com/hc/en-us/article_attachments/360044928032/origin-pull-ca.pem) and save it on the VPS as /origin-pull-ca.pem.

8. Repeat step for 4 with a A/CNAME record called lynx pointing to the same ip/hostname.

## VPS Initial Setup

- Run ``cd ~/FatesList`` between every step

0. Install the below dependencies:

- python 3.10 or newer
- *nightly* rust, 
- go 1.18 or newer
- gcc-c++ (required for cython)
- libffi-devel (required for cython)
- libxslt-devel (required by some python dependencies we use such as lxml)
- libxml2-devel (required by some python dependencies we use such as lxml)- libpq-devel (required by some python dependencies we use such as asyncpg)
- tmux

The two below dependencies can also be replaced by having a PostgreSQL 14+ server listening at port 1000 and a Redis 6.2+ server listening at port 1001.

- docker
- docker-compose

1. Create a user account named ``meow``. This is the username that Fates List currently requires.

2. Download the Fates List infra repo on the VPS using `git clone https://github.com/Fates-List/infra FatesList`. Make sure the location it is downloaded to is publicly accessible AKA not in a /root folder or anything like that.

3. Enter the ``modules/infra/flamepaw`` folder and run `make && make install`. This will build and install flamepaw on your system.

4. Enter the ``FatesList/config/data`` folder and fill in the required information in the JSON files there. This should be self-explanatory but feel free to ask for help on our support server.

5. (optional) If you have a database backup, copy it to ``/backups/latest.bak`` where ``/`` is the root of your hard disk

6. Run ``flamepaw --cmd db.setup`` to setup your database. This may fail, if so, report it on our support server and/or try manually creating the schema (if postgres docker setup succeeds) using the below commands:

```bash

cd data/sql

psql # If this fails then postgres docker setup failed and you should report this

\i schema.sql
```

7. Install the lynx python dependencies with ``pip install -r modules/infra/admin_piccolo/deps.txt``

8. Install ``git+https://github.com/Rapptz/discord.py`` manually (due to python 3.11 and aiohttp issues)

9. Copy the nginx conf in data/nginx to /etc/nginx

10. Restart nginx using ``systemctl restart nginx``

### Compiling actual site 

- Do all steps below apart from ``make`` and ``git`` commands on server reboot/full site restart/``tmux`` server kill as well

1. Clone baypaw using ``git clone https://github.com/Fates-List/baypaw``, enter the folder, run ``make`` to compile baypaw which is a microservice for global API requests across Fates List services.

2. Clone api-v3 using ``git clone https://github.com/Fates-List/api-v3``, enter the folder, run ``make`` to compile the api.

3. Clone squirrelflight using ``git clone https://github.com/Fates-List/squirrelflight``, enter the folder, run ``make`` to compile squirrelflight, our vote reminders bot.

4. (optional, not done on Fates due to issues) Follow [this](https://stevescargall.com/2020/05/13/how-to-install-prometheus-and-grafana-on-fedora-server/) to set up Prometheus and Grafana for monitoring. Set Grafanas port to 5050. Use a firewall or the digital ocean firewall to block other ports. Do not open prometheus's port in the firewall, only open Grafana's.

### Running the site

Run ``FatesList/data/start_tmux.sh`` to start Fates List