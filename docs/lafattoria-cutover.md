# Pizzeria La Fattoria: Umzug auf Dokploy (Stand 2026-09-12, Cutover geplant Dienstag 2026-09-15)

## Ist-Zustand

| | Alt | Neu |
| --- | --- | --- |
| Backend | https://shopware.veliu.net (Strato/Easypanel, 194.164.61.70, MySQL 8.4) | https://backend.pizzeria-lafattoria.de (Dokploy 46.224.172.150, MariaDB 11.8) |
| Dokploy | – | Projekt "Pizzeria La Fattoria", Compose `shopware`, composeId `DK2K6r_rK_3GfgxQhB3-j`, appName `lafattoria-shopware-odg4uf`, **autoDeploy aus** |
| Version | Shopware 6.7.13.1, ShopBitePlugin 1.4.7 | identisch, zusätzlich MolliePayments + SwagPayPal aus dem Repo (Zahlungsarten inaktiv) |
| Dateien | Hetzner Object Storage nbg1, `lafattoria-public` + `lafattoria-private` | dieselben Buckets, Cache-Control auf allen Objekten gesetzt |
| Storefront | pizzeria-lafattoria.de (alter Host) | Dokploy-App `storefront` (applicationId `GS8bbKBWgiVkNhG6y7NNM`, appName `pizzeria-la-fattoria-storefront-o5ur5z`, Repo veliu/pizzerialafattoria), bisher nur sslip.io-Testdomain |
| Backup | – | Dokploy-Backup `f51Q9ZkATwf3hmHuMgqkz`, täglich 03:00 nach "Strato Minio Backups", 14 Stände |
| Order-Printer | `SHOPWARE_HOST=https://shopware.veliu.net` | noch umzustellen |

Erster Import vom 2026-09-12 ist drin und verifiziert (Admin-Login, Store API mit altem Access Key
`SWSCWK03ELNBQ043VERHB3U3UA`, Admin API mit Order-Printer-Integration, Medien-URLs). Seitdem laufen
Bestellungen weiter im alten Shop, daher am Cutover-Tag ein finaler Abgleich.

Host-Hinweise: 7.7 GB RAM, 4 GB Swapfile (seit 2026-09-12), 2 Cores. Storefront-Builds brauchen
kurzzeitig ~5 GB, mit Swap ok. Zugang: `ssh root@46.224.172.150`. Dokploy-API-Key in
`~/workspace/shopbite/.env.local`, Hetzner-Bucket-Zugang in `~/workspace/shopbite/bucket.txt`.

## Ablauf am Cutover-Tag (ruhige Zeit, z. B. vormittags vor Öffnung)

1. **Alten Shop schreibschützen** (optional, verhindert Bestellungen zwischen Dump und Umstellung):
   im alten Admin Wartungsmodus oder Checkout im ShopBite-Plugin deaktivieren. Bestellungen, die
   danach noch im alten Shop landen, wären verloren.
2. **Dump ziehen** (auf dem Strato-Server, Datenbank heißt dort `pizzeria`):

   ```bash
   mysqldump --single-transaction --quick --routines --triggers --hex-blob \
     --default-character-set=utf8mb4 -u <user> -p pizzeria | gzip > lafattoria-final.sql.gz
   ```

3. **Import** in die neue Instanz (vom Rechner mit dem Dump; Web/Worker dürfen laufen):

   ```bash
   gzip -dc lafattoria-final.sql.gz | ssh root@46.224.172.150 'docker exec -i lafattoria-shopware-odg4uf-database-1 sh -c '"'"'mariadb -uroot -p"$MARIADB_ROOT_PASSWORD" -e "DROP DATABASE shopware; CREATE DATABASE shopware CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci" && mariadb -uroot -p"$MARIADB_ROOT_PASSWORD" shopware'"'"''
   ```

4. **Valkey leeren** (sonst Fremdschlüsselfehler beim Plugin-Install, siehe production-docker.md):

   ```bash
   ssh root@46.224.172.150 'docker exec lafattoria-shopware-odg4uf-valkey-1 valkey-cli FLUSHALL'
   ```

5. **Redeploy** in Dokploy (Button oder API):

   ```bash
   curl -X POST https://panel.shopbite.de/api/compose.redeploy -H "x-api-key: $DOKPLOY_API_KEY" \
     -H 'Content-Type: application/json' -d '{"composeId":"DK2K6r_rK_3GfgxQhB3-j","title":"Final import"}'
   ```

   Warten bis `init` mit Exit 0 durch ist und `web` healthy meldet.
6. **Prüfen**: `https://backend.pizzeria-lafattoria.de/api/_info/health-check` 200, Admin-Login, letzte
   Bestellnummer im neuen Admin = letzte im alten, Store API:
   `curl -H 'sw-access-key: SWSCWK03ELNBQ043VERHB3U3UA' https://backend.pizzeria-lafattoria.de/store-api/shopbite/config`.
7. **Storefront umstellen**: in der Dokploy-App `storefront` die Umgebungsvariablen
   `NUXT_PUBLIC_SHOPWARE_ENDPOINT=https://backend.pizzeria-lafattoria.de` (bzw. `/store-api`, je nach
   bisherigem Wert) setzen, echte Domain `www.pizzeria-lafattoria.de` (+ Redirect von der Apex-Domain)
   im Domains-Tab anlegen, DNS von 194.164.61.70 auf 46.224.172.150 drehen, deployen. Der Build dauert
   etwa drei Minuten und belegt kurz den Swap.
8. **Order-Printer** im Restaurant: `SHOPWARE_HOST=https://backend.pizzeria-lafattoria.de` in
   `.env.local`, Dienst neu starten, Testbestellung drucken lassen. Client-ID/Secret bleiben gleich.
9. **Alten Stack** noch eine Woche stehen lassen (Rückweg), dann in Easypanel stoppen. MinIO auf dem
   Strato-Server bleibt für den Demo-Shop in Betrieb.
10. **Nacharbeiten**: manuelles Backup auslösen (`backup.manualBackupCompose`), Hetzner-Bucket `shopbite`
    für das Dokploy-Backup-Ziel anlegen und Backup dorthin umstellen, Builds mittelfristig vom Host
    nehmen (GitHub Actions oder Build-Server).

## Rückweg

Solange der alte Stack läuft: DNS und Storefront-Variable zurückdrehen, Order-Printer zurück auf
`shopware.veliu.net`. Bestellungen, die inzwischen im neuen Shop eingegangen sind, müssten manuell
nachgetragen werden.
