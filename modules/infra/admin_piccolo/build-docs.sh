source ~/.bashrc
flamepaw --cmd site.enum2html > api-docs/structures/enums-ref.md
flamepaw --cmd site.getdragondocs > api-docs/advanced/flamepaw.md
rm api-docs/endpoints.md
curl https://next.fateslist.xyz/_docs_template > api-docs/endpoints.md
curl http://localhost:10000/_new_doctree