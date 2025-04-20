from app import app
# Importer les routes nécessaires
import app_routes_companies  # Routes pour les sociétés
import app_routes_charges  # Routes pour les charges
import app_routes_tenant_payments  # Routes pour les paiements des locataires
import app_routes_contacts  # Routes pour les contacts
from app_routes_dashboard import dashboard_bp  # Routes pour le tableau de bord

# Enregistrer les blueprints
app.register_blueprint(dashboard_bp)

# IMPORTANT: L'application autonome de gestion des contacts a été COMPLÈTEMENT désactivée
# pour éviter les problèmes de duplication. Une approche standalone est maintenant utilisée
# directement dans app_routes_contacts.py avec un template autonome qui n'utilise pas base.html.

# INTERDIRE explicitement le chargement de tout module "standalone"
import sys
import importlib
for module in list(sys.modules.keys()):
    if 'standalone' in module.lower():
        print(f"WARNING: Module problématique {module} trouvé - DÉCHARGEMENT forcé")
        if module in sys.modules:
            del sys.modules[module]

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)