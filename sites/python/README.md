# Sites Python

Place tes applications Python ici.

## Convention

Chaque fichier `.py` sélectionnable par le menu doit définir :

```python
def create_app():
    return app
```

L'objet retourné doit être une application WSGI, par exemple une application Flask.

Exemple :

```python
from flask import Flask

app = Flask(__name__)

@app.get("/")
def index():
    return "Bonjour"

def create_app():
    return app
```

Le gestionnaire lui attribue automatiquement un port libre.
