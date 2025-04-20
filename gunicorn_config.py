# Configuration de Gunicorn
bind = "0.0.0.0:5000"
reload = True
workers = 1
worker_class = "sync"
timeout = 300  # Timeout plus long pour gérer les téléchargements longs (5 minutes)
graceful_timeout = 60  # Délai pour terminer les requêtes en cours
keepalive = 5  # Maintenir les connexions actives
max_requests = 1000  # Redémarrer les workers après X requêtes pour éviter les fuites mémoire
max_requests_jitter = 50  # Ajouter un peu d'aléatoire pour éviter les redémarrages simultanés
limit_request_line = 0  # Pas de limite, utilise la valeur de l'OS
limit_request_field_size = 0  # Pas de limite, utilise la valeur de l'OS
limit_request_fields = 0  # Pas de limite sur le nombre de champs

# Gérer les erreurs de manière silencieuse
capture_output = True
loglevel = "info"
errorlog = "-"
accesslog = "-"