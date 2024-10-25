# RangerAi
# Exemples d'utilisation de l'API

# 1. Obtenir les sites touristiques
GET /api/sites/

# 2. Obtenir les services près d'un site
GET /api/sites/{site_id}/nearby_services/?radius=5

# 3. Compléter une action écologique
POST /api/profiles/{profile_id}/complete_action/
{
    "action_id": 1
}

# 4. Obtenir les statistiques utilisateur
GET /api/profiles/{profile_id}/statistics/

# 4. Obtenir les statistiques utilisateur
GET /api/profiles/{profile_id}/history

# 5. Obtenir les services par type
GET /api/services/by_type/