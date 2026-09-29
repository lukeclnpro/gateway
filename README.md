# Public Site Router

Petit gestionnaire Python pour lancer plusieurs sites locaux et leur attribuer
automatiquement des ports.

## Fonctionnement

Le déploiement est automatique au lancement de `menu.py`.

Le programme scanne `sites/python/` et `sites/static/`, détecte les sites,
leur attribue automatiquement un port disponible, puis démarre **tous les
sites simultanément** dans des processus séparés.

Si le port de base est `5000`, le gestionnaire cherche les ports disponibles :

- premier site -> `5000`
- deuxième site -> `5001`
- troisième site -> `5002`
- etc.

Les ports peuvent être différents si un port est déjà occupé.

Il existe deux types de sites :

### Ajouter un nouveau site

Il suffit de déposer le nouveau site dans le bon dossier puis de relancer
`menu.py` (ou d'utiliser la commande `10` dans le menu). Le programme détecte
le nouveau site et lui attribue automatiquement le prochain port disponible.

### 1. Site Python

Dépose une application Python dans :

`sites/python/`

Elle doit exposer une fonction :

```python
def create_app():
    return app
```

Une application Flask est recommandée.

### 2. Site statique

Dépose un dossier dans :

`sites/static/`

avec au minimum :

`index.html`

Les fichiers CSS, JS, images, etc. peuvent rester dans ce dossier.
Le programme utilise ensuite `python -m http.server`.

## Installation

Python 3.10+ recommandé.

```bash
python -m venv .venv
```

Linux/macOS :

```bash
source .venv/bin/activate
pip install -r requirements.txt
python menu.py
```

Windows :

```powershell
.venv\Scripts\activate
pip install -r requirements.txt
python menu.py
```

## Routeur

Le programme tente automatiquement d'utiliser UPnP si :

- `miniupnpc` est installé ;
- le routeur expose UPnP IGD ;
- l'UPnP n'est pas bloqué.

Dans ce cas, par exemple :

`5001 TCP -> 192.168.1.20:5001`

est demandé automatiquement.

Sinon le programme affiche la règle à créer manuellement dans l'interface
du routeur.

### Attention à l'IP publique

Une IP publique affichée par le programme ne garantit pas qu'une connexion
entrante IPv4 soit possible. Avec du CGNAT, l'IPv4 publique peut appartenir
au réseau du FAI et le port forwarding du routeur ne suffira pas.

Dans ce cas, il faut une IPv4 publique/dédiée ou une autre architecture
d'exposition (VPN/tunnel/reverse proxy).

## Pare-feu

Le pare-feu du PC doit autoriser les ports utilisés si nécessaire.

## Sécurité

Ce programme expose volontairement des services sur le réseau.

Avant d'exposer un site sur Internet :

- utilise une authentification si le site est privé ;
- évite d'exposer des interfaces d'administration ;
- garde les dépendances à jour ;
- préfère HTTPS pour un usage réel ;
- ne lance pas des applications non fiables avec des privilèges élevés.

## Commandes du menu

1. Lister les sites
2. Ajouter un site Python
3. Ajouter un site statique
4. Démarrer un site
5. Arrêter un site
6. Démarrer tous les sites
7. Arrêter tous les sites
8. Supprimer un site de la configuration
9. Afficher la configuration routeur
0. Quitter


## Déploiement simultané

Chaque site est lancé dans son propre processus. Par exemple, avec une base
`5000` :

- `blog.py` -> `5000`
- `api.py` -> `5001`
- `portfolio/` -> `5002`

Au démarrage, les trois sont lancés sans attendre que l'un d'eux soit arrêté.
Le menu reste ensuite disponible dans la console.

Pour ajouter un site pendant que le gestionnaire tourne, place-le dans le
dossier correspondant puis utilise la commande `10` pour rescanner et le
déployer automatiquement.
