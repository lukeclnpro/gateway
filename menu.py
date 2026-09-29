#!/usr/bin/env python3
"""
Gestionnaire console : déploie automatiquement plusieurs sites locaux.

Fonctionnalités :
- demande un port de base au premier lancement ;
- ajoute automatiquement les sites Python présents dans sites/python/ ;
- ajoute des sites statiques via un dossier contenant index.html ;
- attribue le prochain port libre ;
- démarre les serveurs locaux ;
- tente une redirection de port UPnP/NAT-PMP si miniupnpc est installé et que
  le routeur le permet ;
- affiche l'IP publique et les URLs accessibles.

Important : un routeur ne peut pas être reconfiguré de façon générique sans
un protocole/une API supportée. UPnP est donc optionnel.
"""

from manager import SiteManager


def main():
    manager = SiteManager()
    manager.run()


if __name__ == "__main__":
    main()
