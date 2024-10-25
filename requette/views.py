# views.py

from rest_framework import viewsets, status, filters
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, IsAuthenticatedOrReadOnly
from django.db.models import Q, Count
from django.utils import timezone
from datetime import timedelta
from .models import TouristicSite, Service, EcoAction, UserProfile, UserAction
from .serializer import *

class TouristicSiteViewSet(viewsets.ModelViewSet):
    """
    ViewSet pour gérer les sites touristiques.
    Permet le CRUD complet sur les sites touristiques avec des fonctionnalités additionnelles.
    """
    queryset = TouristicSite.objects.all()
    serializer_class = TouristicSiteSerializer
    permission_classes = [IsAuthenticatedOrReadOnly]
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['name', 'description', 'type']
    ordering_fields = ['name', 'eco_score', 'created_at']

    @action(detail=True, methods=['get'])
    def nearby_services(self, request, pk=None):
        """
        Retourne les services à proximité d'un site touristique.
        
        Parameters:
            radius (float): Rayon de recherche en kilomètres (optionnel, défaut: 5)
        """
        site = self.get_object()
        radius = float(request.query_params.get('radius', 5.0))
        
        # Utilise la formule de Haversine pour calculer la distance
        services = Service.objects.raw('''
            SELECT *, 
                   6371 * acos(cos(radians(%s)) * cos(radians(latitude)) *
                   cos(radians(longitude) - radians(%s)) + 
                   sin(radians(%s)) * sin(radians(latitude))) AS distance
            FROM requette_service
            GROUP BY distance
            HAVING distance < %s
            ORDER BY distance
        ''', [site.latitude, site.longitude, site.latitude, radius])

        serializer = ServiceSerializer(services, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['get'])
    def eco_friendly(self, request):
        """
        Retourne les sites avec un eco_score élevé (>= 4).
        """
        eco_sites = self.queryset.filter(eco_score__gte=4)
        serializer = self.serializer_class(eco_sites, many=True)
        return Response(serializer.data)

class ServiceViewSet(viewsets.ModelViewSet):
    """
    ViewSet pour gérer les services (hôtels, restaurants, etc.).
    """
    queryset = Service.objects.all()
    serializer_class = ServiceSerializer
    permission_classes = [IsAuthenticatedOrReadOnly]
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['name', 'description', 'type']
    ordering_fields = ['name', 'type']

    @action(detail=False, methods=['get'])
    def by_type(self, request):
        """
        Retourne les services groupés par type avec leur compte.
        """
        services_by_type = (
            Service.objects
            .values('type')
            .annotate(count=Count('id'))
            .order_by('type')
        )
        return Response(services_by_type)

class EcoActionViewSet(viewsets.ModelViewSet):
    """
    ViewSet pour gérer les actions écologiques.
    """
    queryset = EcoAction.objects.all()
    serializer_class = EcoActionSerializer
    permission_classes = [IsAuthenticatedOrReadOnly]

    @action(detail=False, methods=['get'])
    def popular_actions(self, request):
        """
        Retourne les actions les plus complétées cette semaine.
        """
        week_ago = timezone.now() - timedelta(days=7)
        popular_actions = (
            EcoAction.objects
            .annotate(
                completion_count=Count(
                    'useraction',
                    filter=Q(useraction__completed_at__gte=week_ago)
                )
            )
            .order_by('-completion_count')
        )
        serializer = self.serializer_class(popular_actions, many=True)
        return Response(serializer.data)

class UserProfileViewSet(viewsets.ModelViewSet):
    """
    ViewSet pour gérer les profils utilisateurs.
    """
    queryset = UserProfile.objects.all()
    serializer_class = UserProfileSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        """
        Filtre les profils pour que l'utilisateur ne voie que le sien,
        sauf pour les administrateurs qui peuvent voir tous les profils.
        """
        if self.request.user.is_staff:
            return self.queryset
        return self.queryset.filter(user=self.request.user)

    @action(detail=True, methods=['post'])
    def complete_action(self, request, pk=None):
        """
        Endpoint pour compléter une action écologique.
        
        Parameters:
            action_id (int): ID de l'action à compléter
        """
        profile = self.get_object()
        action_id = request.data.get('action_id')
        
        try:
            action = EcoAction.objects.get(id=action_id)
            
            # Vérifie si l'action n'a pas déjà été complétée aujourd'hui
            if not UserAction.objects.filter(
                user_profile=profile,
                action=action,
                completed_at__date=timezone.now().date()
            ).exists():
                # Crée l'action et met à jour les points
                UserAction.objects.create(
                    user_profile=profile,
                    action=action
                )
                profile.eco_points += action.points
                profile.save()
                
                return Response({
                    'status': 'success',
                    'points_earned': action.points,
                    'total_points': profile.eco_points
                })
            else:
                return Response({
                    'status': 'error',
                    'message': 'Action déjà complétée aujourd\'hui'
                }, status=status.HTTP_400_BAD_REQUEST)
                
        except EcoAction.DoesNotExist:
            return Response({
                'status': 'error',
                'message': 'Action non trouvée'
            }, status=status.HTTP_404_NOT_FOUND)

    @action(detail=True, methods=['get'])
    def action_history(self, request, pk=None):
        """
        Retourne l'historique des actions de l'utilisateur.
        """
        profile = self.get_object()
        actions = UserAction.objects.filter(user_profile=profile)
        serializer = UserActionSerializer(actions, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=['get'])
    def statistics(self, request, pk=None):
        """
        Retourne des statistiques sur les actions de l'utilisateur.
        """
        profile = self.get_object()
        week_ago = timezone.now() - timedelta(days=7)
        
        stats = {
            'total_points': profile.eco_points,
            'level': profile.level,
            'total_actions': UserAction.objects.filter(user_profile=profile).count(),
            'actions_this_week': UserAction.objects.filter(
                user_profile=profile,
                completed_at__gte=week_ago
            ).count(),
            'most_common_action': UserAction.objects.filter(user_profile=profile)
                .values('action__name')
                .annotate(count=Count('id'))
                .order_by('-count')
                .first()
        }
        
        return Response(stats)