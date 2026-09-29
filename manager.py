from __future__ import annotations

import json
import os
import socket
import subprocess
import sys
import threading
import time
import urllib.request
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Optional


ROOT = Path(__file__).resolve().parent
SITES_DIR = ROOT / "sites"
PYTHON_DIR = SITES_DIR / "python"
STATIC_DIR = SITES_DIR / "static"
DATA_DIR = ROOT / "data"
CONFIG_FILE = DATA_DIR / "config.json"
STATE_FILE = DATA_DIR / "state.json"


@dataclass
class Site:
    name: str
    kind: str                  # "python" or "static"
    local_port: int
    public_port: int
    target: str                # python module/script or static directory
    process_pid: Optional[int] = None
    router_forwarded: bool = False


class RouterForwarder:
    """
    UPnP est optionnel.

    Si miniupnpc est installé :
        pip install miniupnpc

    Le routeur doit accepter les requêtes UPnP IGD.
    """

    def __init__(self):
        self.upnp = None
        try:
            import miniupnpc
            self.miniupnpc = miniupnpc
        except ImportError:
            self.miniupnpc = None

    def setup(self) -> bool:
        if self.miniupnpc is None:
            return False
        try:
            u = self.miniupnpc.UPnP()
            u.discoverdelay = 2000
            u.discover()
            u.selectigd()
            self.upnp = u
            return True
        except Exception as exc:
            print(f"[routeur] UPnP indisponible : {exc}")
            return False

    def add(self, public_port: int, local_port: int, description: str) -> bool:
        if self.upnp is None and not self.setup():
            return False

        local_ip = get_local_ip()
        try:
            # Certains routeurs attendent explicitement TCP.
            self.upnp.addportmapping(
                public_port,
                "TCP",
                local_ip,
                local_port,
                description,
                "",
            )
            return True
        except Exception as exc:
            print(f"[routeur] Impossible de créer {public_port} -> {local_ip}:{local_port}: {exc}")
            return False

    def remove(self, public_port: int) -> bool:
        if self.upnp is None:
            return False
        try:
            return bool(self.upnp.deleteportmapping(public_port, "TCP"))
        except Exception:
            return False

    def external_ip(self) -> Optional[str]:
        if self.upnp is not None:
            try:
                return self.upnp.externalipaddress()
            except Exception:
                pass
        return get_public_ip()


def get_local_ip() -> str:
    """Détermine l'IP LAN utilisée pour sortir vers Internet."""
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(("1.1.1.1", 80))
        return s.getsockname()[0]
    except OSError:
        return "127.0.0.1"
    finally:
        s.close()


def get_public_ip() -> Optional[str]:
    for url in (
        "https://api.ipify.org",
        "https://ifconfig.me/ip",
    ):
        try:
            with urllib.request.urlopen(url, timeout=4) as response:
                return response.read().decode().strip()
        except Exception:
            continue
    return None


def port_is_free(port: int, host: str = "0.0.0.0") -> bool:
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        s.bind((host, port))
        return True
    except OSError:
        return False
    finally:
        s.close()


class SiteManager:
    def __init__(self):
        for directory in (PYTHON_DIR, STATIC_DIR, DATA_DIR):
            directory.mkdir(parents=True, exist_ok=True)

        self.config = self._load_json(CONFIG_FILE, {})
        self.state = self._load_json(STATE_FILE, {})
        self.processes: dict[str, subprocess.Popen] = {}
        self.router = RouterForwarder()

        self.base_port = int(self.config.get("base_port", 5000))
        self.sites: dict[str, Site] = {}
        self._load_sites()

    @staticmethod
    def _load_json(path: Path, default):
        if not path.exists():
            return default
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            return default

    def _save(self):
        DATA_DIR.mkdir(exist_ok=True)
        CONFIG_FILE.write_text(
            json.dumps({"base_port": self.base_port}, indent=2),
            encoding="utf-8",
        )
        STATE_FILE.write_text(
            json.dumps(
                {"sites": {name: asdict(site) for name, site in self.sites.items()}},
                indent=2,
            ),
            encoding="utf-8",
        )

    def _load_sites(self):
        raw = self.state.get("sites", {})
        for name, data in raw.items():
            try:
                self.sites[name] = Site(**data)
            except TypeError:
                continue

    def choose_base_port(self):
        value = input(f"Port de base [{self.base_port}] : ").strip()
        if value:
            try:
                port = int(value)
                if not (1 <= port <= 65535):
                    raise ValueError
                self.base_port = port
                self._save()
            except ValueError:
                print("Port invalide, conservation de la valeur actuelle.")

    def next_port(self) -> int:
        used = {site.public_port for site in self.sites.values()}
        used.update(site.local_port for site in self.sites.values())

        port = self.base_port
        while port <= 65535:
            if port not in used and port_is_free(port):
                return port
            port += 1
        raise RuntimeError("Aucun port libre disponible.")

    def discover_python_sites(self):
        """
        Chaque fichier *.py dans sites/python/ est considéré comme un site.

        Convention recommandée :
            def create_app():
                return une_app_WSGI

        Pour un script plus libre, le fichier peut aussi lancer son propre
        serveur. Dans ce cas, cette version du gestionnaire ne l'enveloppe pas.
        Le mode WSGI/Flask est recommandé pour une gestion de port propre.
        """
        return sorted(
            p for p in PYTHON_DIR.glob("*.py")
            if p.name != "__init__.py"
        )

    def list_static_dirs(self):
        result = []
        for directory in sorted(STATIC_DIR.iterdir()):
            if directory.is_dir() and (directory / "index.html").is_file():
                result.append(directory)
        return result

    def add_python_site(self):
        scripts = self.discover_python_sites()
        if not scripts:
            print(f"Aucun fichier Python dans {PYTHON_DIR}")
            return

        print("\nSites Python disponibles :")
        for i, path in enumerate(scripts, 1):
            print(f"  {i}. {path.name}")

        try:
            choice = int(input("Numéro : "))
            path = scripts[choice - 1]
        except (ValueError, IndexError):
            print("Choix invalide.")
            return

        name = path.stem
        if name in self.sites:
            print("Ce site est déjà enregistré.")
            return

        port = self.next_port()
        site = Site(name, "python", port, port, str(path.relative_to(ROOT)))
        self.sites[name] = site
        self._save()
        print(f"Site ajouté : {name} -> port {port}")

    def add_static_site(self):
        print(f"\nDossiers statiques disponibles dans {STATIC_DIR} :")
        dirs = self.list_static_dirs()
        if dirs:
            for i, directory in enumerate(dirs, 1):
                print(f"  {i}. {directory.name}")
            print("  0. Entrer un nouveau chemin")

            choice = input("Choix : ").strip()
            if choice == "0":
                raw = input("Chemin du dossier contenant index.html : ").strip()
                directory = Path(raw).expanduser().resolve()
            else:
                try:
                    directory = dirs[int(choice) - 1]
                except (ValueError, IndexError):
                    print("Choix invalide.")
                    return
        else:
            raw = input(
                "Chemin du dossier contenant index.html "
                "(ou Entrée pour annuler) : "
            ).strip()
            if not raw:
                return
            directory = Path(raw).expanduser().resolve()

        index = directory / "index.html"
        if not index.is_file():
            print(f"index.html introuvable dans {directory}")
            return

        name = directory.name
        if name in self.sites:
            print("Ce site est déjà enregistré.")
            return

        port = self.next_port()
        site = Site(name, "static", port, port, str(directory))
        self.sites[name] = site
        self._save()
        print(f"Site statique ajouté : {name} -> port {port}")

    def start_site(self, name: str):
        if name not in self.sites:
            print("Site inconnu.")
            return

        site = self.sites[name]
        if name in self.processes and self.processes[name].poll() is None:
            print("Le site tourne déjà.")
            return

        if site.kind == "static":
            cmd = [
                sys.executable, "-m", "http.server",
                str(site.local_port),
                "--bind", "0.0.0.0",
                "--directory", str(Path(site.target).resolve()),
            ]
        else:
            # Convention : un site Python doit exposer create_app().
            # On démarre un petit runner générique basé sur WSGI.
            runner = ROOT / "python_runner.py"
            cmd = [
                sys.executable, str(runner),
                site.target,
                str(site.local_port),
            ]

        print(f"[serveur] Démarrage de {name} sur 0.0.0.0:{site.local_port}")
        try:
            proc = subprocess.Popen(
                cmd,
                cwd=str(ROOT),
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
            )
        except OSError as exc:
            print(f"Erreur de lancement : {exc}")
            return

        self.processes[name] = proc
        site.process_pid = proc.pid

        # Petit délai pour laisser le serveur démarrer avant UPnP.
        time.sleep(0.4)
        forwarded = self.router.add(
            site.public_port,
            site.local_port,
            f"public-site-{name}",
        )
        site.router_forwarded = forwarded
        self._save()

        if forwarded:
            print(f"[routeur] TCP {site.public_port} -> {get_local_ip()}:{site.local_port}")
        else:
            print(
                "[routeur] Redirection automatique non disponible. "
                f"À faire manuellement : TCP {site.public_port} -> "
                f"{get_local_ip()}:{site.local_port}"
            )

        public_ip = self.router.external_ip()
        if public_ip:
            print(f"[web] http://{public_ip}:{site.public_port}")

        threading.Thread(
            target=self._watch_process,
            args=(name, proc),
            daemon=True,
        ).start()

    def _watch_process(self, name: str, proc: subprocess.Popen):
        try:
            output = proc.stdout
            if output:
                for line in output:
                    print(f"[{name}] {line.rstrip()}")
        finally:
            if name in self.sites:
                self.sites[name].process_pid = None
                self.sites[name].router_forwarded = False
                self._save()

    def stop_site(self, name: str):
        proc = self.processes.get(name)
        site = self.sites.get(name)

        if proc is None or proc.poll() is not None:
            print("Le site n'est pas démarré.")
            return

        proc.terminate()
        try:
            proc.wait(timeout=3)
        except subprocess.TimeoutExpired:
            proc.kill()

        if site and site.router_forwarded:
            self.router.remove(site.public_port)
            site.router_forwarded = False
            site.process_pid = None
            self._save()

        print(f"Site arrêté : {name}")

    def remove_site(self):
        self.list_sites()
        name = input("Nom du site à supprimer : ").strip()
        if name not in self.sites:
            print("Site inconnu.")
            return

        self.stop_site(name)
        del self.sites[name]
        self._save()
        print("Site supprimé de la configuration.")


    def auto_discover_sites(self):
        """
        Découvre automatiquement les nouveaux sites présents dans les dossiers
        sites/python/ et sites/static/.

        Les sites déjà connus conservent leur port. Les nouveaux sites reçoivent
        automatiquement le prochain port disponible.
        """
        added = []

        # Applications Python : chaque *.py sauf __init__.py et fichiers README.
        for path in self.discover_python_sites():
            name = path.stem
            if name not in self.sites:
                port = self.next_port()
                self.sites[name] = Site(
                    name=name,
                    kind="python",
                    local_port=port,
                    public_port=port,
                    target=str(path.relative_to(ROOT)),
                )
                added.append(name)

        # Sites statiques : chaque dossier contenant index.html.
        for directory in self.list_static_dirs():
            name = directory.name
            if name not in self.sites:
                port = self.next_port()
                self.sites[name] = Site(
                    name=name,
                    kind="static",
                    local_port=port,
                    public_port=port,
                    target=str(directory.resolve()),
                )
                added.append(name)

        if added:
            self._save()
            print(f"[auto] {len(added)} nouveau(x) site(s) détecté(s) :")
            for name in added:
                site = self.sites[name]
                print(f"       {name} -> port {site.public_port}")

        return added

    def auto_deploy(self):
        """
        Déploie automatiquement tous les sites connus/découverts.

        Chaque site est lancé dans son propre processus : plusieurs sites
        fonctionnent donc simultanément.
        """
        self.auto_discover_sites()

        if not self.sites:
            print("[auto] Aucun site à déployer.")
            return

        print(f"\n[auto] Déploiement de {len(self.sites)} site(s)...")

        # Tous les appels démarrent des processus indépendants ; on ne bloque
        # donc pas sur le premier serveur.
        for name in list(self.sites):
            site = self.sites[name]
            running = (
                name in self.processes
                and self.processes[name].poll() is None
            )
            if running:
                continue

            try:
                self.start_site(name)
            except Exception as exc:
                print(f"[auto] Échec pour {name} : {exc}")

        print("[auto] Déploiement terminé.")
        self.list_sites()

    def list_sites(self):
        if not self.sites:
            print("Aucun site enregistré.")
            return

        public_ip = self.router.external_ip() or "<IP-PUBLIQUE>"
        print("\nSites :")
        for site in self.sites.values():
            running = (
                site.name in self.processes
                and self.processes[site.name].poll() is None
            )
            status = "EN LIGNE" if running else "arrêté"
            print(
                f"  {site.name:20} | {site.kind:6} | "
                f"local {site.local_port} | public {site.public_port} | "
                f"{status}"
            )
            if running:
                print(f"    URL : http://{public_ip}:{site.public_port}")

    def start_all(self):
        for name in list(self.sites):
            self.start_site(name)

    def stop_all(self):
        for name in list(self.sites):
            self.stop_site(name)

    def print_router_help(self):
        local_ip = get_local_ip()
        print(f"""
Configuration manuelle du routeur
---------------------------------
IP LAN de ce PC : {local_ip}

Pour chaque site, créer une redirection :
    protocole : TCP
    port externe : port public affiché
    IP interne : {local_ip}
    port interne : port local affiché

Exemple avec une base à 5000 :
    5000 -> {local_ip}:5000
    5001 -> {local_ip}:5001
    5002 -> {local_ip}:5002

Le routeur doit également autoriser ces ports dans son pare-feu.
Si votre FAI utilise du CGNAT, une redirection IPv4 entrante peut être
impossible sans option/IP publique dédiée.
""")

    def menu(self):
        print("\n=== Public Site Router ===")
        print(f"Port de base : {self.base_port}")
        print("""
1. Lister les sites
2. Ajouter un site Python
3. Ajouter un site statique
4. Démarrer un site
5. Arrêter un site
6. Démarrer tous les sites
7. Arrêter tous les sites
8. Supprimer un site de la configuration
9. Afficher la configuration routeur
10. Re-scanner et déployer tous les sites
0. Quitter
""")

    def run(self):
        print("=== Public Site Router ===")

        if "base_port" not in self.config:
            self.choose_base_port()
        else:
            print(f"Port de base actuel : {self.base_port}")

        # Déploiement automatique dès le lancement.
        self.auto_deploy()

        while True:
            self.menu()
            choice = input("Commande : ").strip()

            if choice == "1":
                self.list_sites()
            elif choice == "2":
                self.add_python_site()
            elif choice == "3":
                self.add_static_site()
            elif choice == "4":
                self.list_sites()
                self.start_site(input("Nom du site : ").strip())
            elif choice == "5":
                self.list_sites()
                self.stop_site(input("Nom du site : ").strip())
            elif choice == "6":
                self.start_all()
            elif choice == "7":
                self.stop_all()
            elif choice == "8":
                self.remove_site()
            elif choice == "9":
                self.print_router_help()
            elif choice == "10":
                self.auto_deploy()
            elif choice == "0":
                self.stop_all()
                print("Au revoir.")
                break
            else:
                print("Commande inconnue.")


if __name__ == "__main__":
    SiteManager().run()
