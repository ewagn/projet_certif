# projet_certif
versionning du projet de certification pour la formation Dev IA

Le projet est composé de portions de codes placés dans des containers Docker. Le déploiement est géré par le fichier docker-compose.prod.yml. Ce fichier lances les containers avec les scripts d'automatisation permettant aux recources de fonctionner.
ce fichier utilise un fichier d'envrionnement .env qu'il faut créer. Vous pouvez le créer à partir du fichier template_env.txt, en rempalçant les valeurs par vos propres valeurs.
Pour lancer le script d'initialisation, il faut se palcer à la racine du projet et lancer la commande : docker compose -f docker-compose.prod.yml up
Vous pouvez interroger l'API sur le port 8000
Vous pouvez accéder à la web-app sur le port 5000