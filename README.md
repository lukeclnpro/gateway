# Gateway

Gestionnaire permettant d'exposer et de lancer facilement plusieurs sites **HTML statiques** ou **applications Python** depuis une machine Linux.

Le script détecte automatiquement les sites présents dans `sites/static/` et `sites/python/`, leur attribue un port disponible à partir du port `5000`, puis les lance.

> ⚠️ Ce projet permet d'exposer des services de votre PC sur Internet. Assurez-vous de comprendre les implications de sécurité avant d'ouvrir des ports.

---

## Fonctionnement

Gateway recherche automatiquement les sites présents dans :

```text
sites/
├── static/
│   └── ...
└── python/
    └── ...
```

Les sites détectés sont associés automatiquement à des ports disponibles.

Exemple :

```text
Site 1 → port 5000
Site 2 → port 5001
Site 3 → port 5002
```

---

# Installation sur Linux

## 1. Cloner le projet

```bash
git clone https://github.com/lukeclnpro/gateway.git
cd gateway
```

## 2. Créer l'environnement virtuel

```bash
python -m venv .venv
```

## 3. Activer l'environnement virtuel

Pour **Fish** :

```fish
source .venv/bin/activate.fish
```

Pour **Bash/Zsh** :

```bash
source .venv/bin/activate
```

## 4. Installer les dépendances

```bash
pip install -r requirements.txt
```

## 5. Lancer Gateway

```bash
python menu.py
```

---

# Ajouter un site

Gateway prend en charge deux types de sites :

- les sites HTML/CSS/JavaScript statiques ;
- les applications Python.

## Site HTML statique

Pour ajouter un site HTML statique, copiez **le dossier entier du site** dans :

```text
sites/static/
```

Exemple :

```text
sites/
└── static/
    └── mon-site/
        ├── index.html
        ├── style.css
        ├── script.js
        └── images/
```

Gateway détecte automatiquement le site et le lance.

## Site Python

Pour ajouter une application Python, copiez **le fichier Python d'initialisation de votre site** dans :

```text
sites/python/
```

Exemple :

```text
sites/
└── python/
    └── mon_site.py
```

Votre application doit obligatoirement définir une fonction :

```python
def create_app():
    return app
```

Exemple minimal avec Flask :

```python
from flask import Flask

app = Flask(__name__)

def create_app():
    return app
```

Gateway détecte automatiquement le fichier et lance l'application.

---

# Attribution des ports

Par défaut, Gateway commence à utiliser le port :

```text
5000
```

Exemple :

```text
mon-site-html → 5000
blog.py       → 5001
portfolio     → 5002
api.py        → 5003
```

Si un port est déjà utilisé, Gateway recherche un autre port disponible.

---

# ⚠️ Configuration du pare-feu Linux

Il est nécessaire d'autoriser votre PC à recevoir les connexions sur les ports utilisés.

Avec **UFW**, pour autoriser les ports `5000` à `5100` :

```bash
sudo ufw allow 5000:5100/tcp
```

Vérifiez les règles avec :

```bash
sudo ufw status
```

> Si vous utilisez un autre pare-feu que UFW, configurez-le afin d'autoriser les ports utilisés par Gateway.

---

# 🌐 Configuration du routeur

Pour rendre les sites accessibles depuis Internet, il faut également effectuer une **redirection de ports (NAT / Port Forwarding)** sur votre routeur.

Pour les ports `5000` à `5100`, créez une règle similaire à :

```text
Port externe : 5000:5100
Port interne  : 5000:5100
Protocole     : TCP
Équipement    : votre PC
Adresse IP    : IP locale de votre PC
```

Par exemple, si l'adresse IP locale de votre PC est `192.168.1.42` :

```text
5000:5100 TCP
      ↓
192.168.1.42:5000:5100
```

> ⚠️ L'interface et la terminologie peuvent varier selon le fabricant de votre routeur.

---

# 🔒 Sécurité

Gateway permet d'exposer des services de votre ordinateur sur le réseau et potentiellement sur Internet.

Avant d'exposer un site publiquement :

- n'exposez pas d'interfaces d'administration sans protection ;
- utilisez une authentification pour les sites privés ;
- maintenez Python et les dépendances à jour ;
- évitez d'exécuter des applications non fiables ;
- n'utilisez pas de privilèges élevés inutilement ;
- utilisez HTTPS pour un usage public ;
- vérifiez attentivement les ports ouverts sur votre routeur.

**N'exécutez pas Gateway avec `sudo` sauf si vous savez exactement pourquoi vous en avez besoin.**

---

# ⚠️ CGNAT

La redirection de ports nécessite que votre connexion Internet permette les connexions entrantes.

Si votre fournisseur d'accès utilise du **CGNAT**, une simple redirection de ports peut ne pas fonctionner.

Il peut alors être nécessaire d'utiliser :

- une IPv4 publique ;
- une IPv4 dédiée ;
- un VPN ;
- un tunnel ;
- un reverse proxy.

---

# Exemple complet

```bash
git clone https://github.com/lukeclnpro/gateway.git
cd gateway

python -m venv .venv
source .venv/bin/activate.fish

pip install -r requirements.txt

python menu.py
```

Ajoutez ensuite vos sites :

```text
sites/
├── static/
│   ├── portfolio/
│   │   └── index.html
│   └── blog/
│       └── index.html
│
└── python/
    └── api.py
```

Gateway détectera automatiquement les sites.

---

# Dépannage

## Le site n'est pas accessible depuis Internet

Vérifiez :

1. que Gateway est bien lancé ;
2. que le site est détecté par Gateway ;
3. que le port utilisé est correct ;
4. que le pare-feu Linux autorise le port ;
5. que le port est redirigé sur le routeur ;
6. que l'adresse IP locale du PC est correcte dans la règle du routeur ;
7. que votre connexion Internet n'utilise pas de CGNAT.

## Le port est déjà utilisé

Vous pouvez vérifier les ports utilisés avec :

```bash
ss -ltnp
```

---

# Structure du projet

```text
gateway/
├── sites/
│   ├── python/
│   └── static/
├── manager.py
├── menu.py
├── python_runner.py
├── requirements.txt
└── README.md
```

---

# Prérequis

- Linux
- Python 3.10+
- `pip`
- `venv`
- accès à la configuration du routeur pour une exposition Internet
- configuration du pare-feu permettant les ports utilisés

---

# GitHub

Projet disponible sur :

https://github.com/lukeclnpro/gateway
