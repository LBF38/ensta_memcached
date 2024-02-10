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

## Organisation du projet

Le projet est organisé de la façon suivante:

```txt
src/
├── utils/
│   ├── *contient les fichiers pour les différents stockages implémentés dans le TP*
├── main.py
tests/
├── *contient les tests pour les différents stockages implémentés dans le TP*
```

Avant de lancer les tests ou le programme principal, il faut installer les dépendances:

```bash
python3 -m venv venv
pip install -r requirements.txt
```

Et il faut aussi définir les variables d'environnement suivantes:

```bash
ak=AWS_ACCESS_KEY
sk=AWS_SECRET_KEY
```

> [!TIP]
> Vous pouvez trouver ces informations dans la console AWS.
>
> Ensuite, vous pouvez les renseigner dans le fichier `.env` à la racine du projet.
> Pour cela, vous pouvez copier le fichier `.env.example` et le renommer en `.env` avec :
>
> ```bash
> cp .env.example .env
> ```

Le fichier `main.py` contient les premiers programmes du TP qui permettent de tester l'implémentation des stockages de base (FS, AWS S3, Memcached).

Ensuite, vous trouverez les différents tests d'utilisation des stockages plus complexes dans le dossier `tests/`.

Les tests de stockage sont concentrés dans le fichier `test_storage.py`.

## Remarques

- Les tests automatisés sont effectués avec `pytest`.
- Ils effectuent des requêtes réelles vers AWS S3, Memcached et le système de fichiers.
- Ainsi, il est nécessaire d'avoir une connexion internet pour les exécuter.

Enjoy! 🚀
