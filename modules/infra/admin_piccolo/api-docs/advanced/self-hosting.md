Licensed under the MIT. We will not support self hosting or copying our list whatsoever, you are on your own and you MUST additionally give credit and change the branding.

This is the source code for [Fates List](https://fateslist.xyz/)

BTW please add your bots there if you wish to support us or even 

::: warning

Fates List is rather annoying (without knowledge in python/golang/rust) to self host. It requires Fedora (support for Windows will never be happening since we do not use it. MacOS support is upcoming). It also needs a large amount of moving parts including PostgreSQL 14 (older versions *may* work but will never be tested) and Redis. In short: **This page is only meant for people who wish to contribute to Fates List. These docs may be out of date. We are working on it**

:::

## Domain Setup

1. Buy a domain (You will need a domain that can be added to Cloudflare in order to use Fates List. We use namecheap for this)

2. Add the domain to Cloudflare (see [this](https://support.cloudflare.com/hc/en-us/articles/201720164-Creating-a-Cloudflare-account-and-adding-a-website)). Our whole website requires Cloudflare as the DNS in order to work.

3. Buy a Linux VPS (You need a Linux VPS or a Linux home server with a public ip with port 443 open)

4. In Cloudflare, create a record (A/CNAME) called @ that points to your VPS ip/hostname

5. In Cloudflare, go to Speed > Optimization. Enable AMP Real URL

6. In Cloudflare, go to SSL/TLS, set the mode to Full (strict), enable Authenticated Origin Pull, make an origin certificate (in Origin Server) and save the private key as /key.pem on your VPS and the certificate as /cert.pem on your VPS

7. Download [https://support.cloudflare.com/hc/en-us/article_attachments/360044928032/origin-pull-ca.pem](https://support.cloudflare.com/hc/en-us/article_attachments/360044928032/origin-pull-ca.pem) and save it on the VPS as /origin-pull-ca.pem.

## VPS Setup

1. Download the Fates List repo on the VPS using `git clone https://github.com/Fates-List/FatesList`. Make sure the location it is downloaded to is publicly accessible AKA not in a /root folder or anything like that. Make sure you have `xkcdpass, python3.10, *nightly* rust, go 1.18 or newer and docker-compose, gcc-c++, libffi-devel, libxslt-devel, libxml2-devel, libpq-devel packages are installed`.

3. Run `tmux new -s flamepaw-pinger`. Then enter the ``modules/infra/flamepaw`` folder and run `make && make install`. This will build flamepaw for your system.

4. Enter ``FatesList/config/data`` folder and fill in the required information on the JSON files there. 

5. If you have a database backup, copy it to ``/backups/latest.bak`` where ``/`` is the root of your hard disk, then run `flamepaw --cmd db.setup`. Setup venv using `snowtuft venv setup` (you may need to run this multiple times to install all development dependencies

6. Copy the nginx conf in info/nginx to /etc/nginx

7. Restart nginx

8. Run ``python3 pinger.py`` in ``flamepaw-pinger`` tmux session in the ``FatesList/modules/infra/flamepaw-pinger`` folder to start ``flamepaw-pinger`` which will then start ``flamepaw``

9. Enter a tmux session called ``baypaw``. Download baypaw using ``git clone https://github.com/Fates-List/baypaw``, enter the folder, run ``make`` and then run ``target/release/baypaw`` to start baypaw which is a microservice for global API requests across Fates List services.

10. Enter a tmux session called ``next-api``. Download api-v3 using ``git clone https://github.com/Fates-List/api-v3``, enter the folder, run ``make`` and then run ``target/release-lto/fates`` to start api v3.

11. Enter a tmux session called ``widgets``. Run widget API by running ``flamepaw --cmd site.run``.

12. (optional, not done on Fates due to issues) Follow [this](https://stevescargall.com/2020/05/13/how-to-install-prometheus-and-grafana-on-fedora-server/) to set up Prometheus and Grafana for monitoring. Set Grafanas port to 5050. Use a firewall or the digital ocean firewall to block other ports. Do not open prometheus's port in the firewall, only open Grafana's.

Fates List probihits the monetization or resale of coins or any part of Fates List for real money.
