# TP stockage et mode d'accès

## Memcached

> [!IMPORTANT]
> La taille de memcached est limité (c'est un cache après tout).
> Il faut donc utiliser des images de taille raisonnable.

En inspectant le server Memcached, on peut voir que la taille maximale du cache est de `STAT limit_maxbytes 67108864`, soit 68MB.

Commandes utilisées pour inspecter Memcached:

```bash
telnet localhost 11211
stats
quit
```
