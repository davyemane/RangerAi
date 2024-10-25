# consumers.py

import json
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from django.utils import timezone
from .models import TouristicSite, Service, UserProfile, EcoAction, UserAction
from django.db.models import F
import math

class TourismConsumer(AsyncWebsocketConsumer):
    """
    Consumer WebSocket pour gérer les interactions en temps réel de l'application de tourisme.
    Gère la recherche de services, la validation d'actions écologiques et les mises à jour des profils utilisateurs.
    """

    async def connect(self):
        """
        Gère la connexion d'un client au WebSocket.
        - Vérifie l'authentification
        - Stocke l'ID utilisateur si authentifié
        - Accepte la connexion
        - Envoie un message de bienvenue
        """
        # Vérifie si l'utilisateur est authentifié et stocke son ID
        if self.scope["user"].is_authenticated:
            self.user_id = self.scope["user"].id
        else:
            self.user_id = None

        # Accepte la connexion WebSocket
        await self.accept()
        
        # Envoie un message de bienvenue
        await self.send(text_data=json.dumps({
            'type': 'welcome',
            'message': 'Connecté au service de tourisme écologique',
            'user_id': self.user_id
        }))

    async def disconnect(self, close_code):
        """
        Gère la déconnexion d'un client.
        Peut être utilisé pour nettoyer les ressources ou sauvegarder l'état.
        """
        pass

    @database_sync_to_async
    def get_nearby_services(self, latitude, longitude, radius=5):
        """
        Récupère les services à proximité d'une position donnée.
        
        Args:
            latitude (float): Latitude de la position
            longitude (float): Longitude de la position
            radius (int): Rayon de recherche en kilomètres (défaut: 5km)
        
        Returns:
            list: Liste des services trouvés avec leurs informations et distances
        """
        # Utilise la formule de Haversine pour calculer les distances
        services = Service.objects.raw('''
            SELECT *, 
                   6371 * acos(cos(radians(%s)) * cos(radians(latitude)) *
                   cos(radians(longitude) - radians(%s)) + 
                   sin(radians(%s)) * sin(radians(latitude))) AS distance
            FROM tourism_service
            HAVING distance < %s
            ORDER BY distance
        ''', [latitude, longitude, latitude, radius])
        
        # Formate les résultats pour le retour
        return [{
            'id': service.id,
            'name': service.name,
            'type': service.type,
            'description': service.description,
            'distance': round(service.distance, 2),
            'eco_friendly': service.eco_friendly,
            'latitude': float(service.latitude),
            'longitude': float(service.longitude)
        } for service in services]

    @database_sync_to_async
    def get_site_details(self, site_id):
        """
        Récupère les détails d'un site touristique.
        
        Args:
            site_id (int): ID du site touristique
            
        Returns:
            dict: Détails du site ou message d'erreur
        """
        try:
            site = TouristicSite.objects.get(id=site_id)
            return {
                'id': site.id,
                'name': site.name,
                'description': site.description,
                'type': site.type,
                'eco_score': site.eco_score,
                'latitude': float(site.latitude),
                'longitude': float(site.longitude),
                'image_url': site.image.url if site.image else None
            }
        except TouristicSite.DoesNotExist:
            return None

    @database_sync_to_async
    def complete_eco_action(self, user_id, action_id):
        """
        Valide une action écologique pour un utilisateur.
        Met à jour les points et vérifie la progression de niveau.
        
        Args:
            user_id (int): ID de l'utilisateur
            action_id (int): ID de l'action écologique
            
        Returns:
            dict: Résultat de l'action avec les points mis à jour
        """
        try:
            # Récupère le profil utilisateur et l'action
            user_profile = UserProfile.objects.get(user_id=user_id)
            action = EcoAction.objects.get(id=action_id)
            
            # Vérifie si l'action n'a pas déjà été complétée aujourd'hui
            if not UserAction.objects.filter(
                user_profile=user_profile,
                action=action,
                completed_at__date=timezone.now().date()
            ).exists():
                # Ajoute les points
                user_profile.eco_points = F('eco_points') + action.points
                user_profile.save()
                user_profile.refresh_from_db()  # Recharge pour avoir les points à jour
                
                # Crée l'entrée dans UserAction
                UserAction.objects.create(
                    user_profile=user_profile,
                    action=action
                )
                
                # Vérifie la montée de niveau
                old_level = user_profile.level
                level_up = self.check_level_up(user_profile)
                
                return {
                    'status': 'success',
                    'points': user_profile.eco_points,
                    'level': user_profile.level,
                    'level_up': level_up,
                    'points_earned': action.points,
                    'action_name': action.name
                }
            else:
                return {
                    'status': 'error',
                    'message': 'Action déjà complétée aujourd\'hui'
                }
                
        except UserProfile.DoesNotExist:
            return {
                'status': 'error',
                'message': 'Profil utilisateur non trouvé'
            }
        except EcoAction.DoesNotExist:
            return {
                'status': 'error',
                'message': 'Action non trouvée'
            }

    @database_sync_to_async
    def check_level_up(self, user_profile):
        """
        Vérifie et met à jour le niveau de l'utilisateur.
        
        Args:
            user_profile (UserProfile): Profil de l'utilisateur
            
        Returns:
            bool: True si l'utilisateur a monté de niveau
        """
        # Calcule le nouveau niveau basé sur les points
        # Formule: niveau = sqrt(points/100)
        new_level = int(math.sqrt(user_profile.eco_points / 100))
        
        if new_level > user_profile.level:
            user_profile.level = new_level
            user_profile.save()
            return True
        return False

    async def receive(self, text_data):
        """
        Gère les messages reçus des clients.
        Parse le JSON et dispatche vers les bonnes actions.
        
        Args:
            text_data (str): Données JSON reçues du client
        """
        try:
            data = json.loads(text_data)
            action = data.get('action')

            # Gestion des différentes actions
            if action == 'get_services':
                # Récupération des services à proximité
                latitude = data.get('latitude')
                longitude = data.get('longitude')
                radius = data.get('radius', 5)
                
                if latitude is not None and longitude is not None:
                    services = await self.get_nearby_services(latitude, longitude, radius)
                    await self.send(text_data=json.dumps({
                        'type': 'services_list',
                        'services': services
                    }))
                else:
                    await self.send(text_data=json.dumps({
                        'type': 'error',
                        'message': 'Latitude et longitude requises'
                    }))

            elif action == 'complete_action':
                # Validation d'une action écologique
                if self.user_id:
                    action_id = data.get('action_id')
                    result = await self.complete_eco_action(self.user_id, action_id)
                    await self.send(text_data=json.dumps({
                        'type': 'action_result',
                        'data': result
                    }))
                else:
                    await self.send(text_data=json.dumps({
                        'type': 'error',
                        'message': 'Utilisateur non authentifié'
                    }))

            elif action == 'get_site_details':
                # Récupération des détails d'un site
                site_id = data.get('site_id')
                site_details = await self.get_site_details(site_id)
                
                if site_details:
                    await self.send(text_data=json.dumps({
                        'type': 'site_details',
                        'data': site_details
                    }))
                else:
                    await self.send(text_data=json.dumps({
                        'type': 'error',
                        'message': 'Site non trouvé'
                    }))

        except json.JSONDecodeError:
            await self.send(text_data=json.dumps({
                'type': 'error',
                'message': 'Format de données invalide'
            }))
        except Exception as e:
            await self.send(text_data=json.dumps({
                'type': 'error',
                'message': f'Erreur: {str(e)}'
            }))