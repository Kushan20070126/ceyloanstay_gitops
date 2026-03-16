#!/usr/bin/env bash
set -euo pipefail

cd /home/kushan/Documents/ceyloanstay_gitops/services

REGISTRY="${REGISTRY:-docker.io}"
NAMESPACE="${NAMESPACE:-kushanrandika}"
TAG="${TAG:-v1.0.2}"

echo "Building images with: $REGISTRY/$NAMESPACE:*:$TAG"

docker build -t "$REGISTRY/$NAMESPACE/ads-service:$TAG" ads_service
docker build -t "$REGISTRY/$NAMESPACE/user-service:$TAG" user_service
docker build -t "$REGISTRY/$NAMESPACE/notification-service:$TAG" notification_service
docker build -t "$REGISTRY/$NAMESPACE/ai-service:$TAG" ai_service
docker build -t "$REGISTRY/$NAMESPACE/search-service:$TAG" search_service
docker build -t "$REGISTRY/$NAMESPACE/admin-service:$TAG" admin_service
docker build -t "$REGISTRY/$NAMESPACE/super-admin-service:$TAG" super_admin_service

docker push "$REGISTRY/$NAMESPACE/ads-service:$TAG"
docker push "$REGISTRY/$NAMESPACE/user-service:$TAG"
docker push "$REGISTRY/$NAMESPACE/notification-service:$TAG"
docker push "$REGISTRY/$NAMESPACE/ai-service:$TAG"
docker push "$REGISTRY/$NAMESPACE/search-service:$TAG"
docker push "$REGISTRY/$NAMESPACE/admin-service:$TAG"
docker push "$REGISTRY/$NAMESPACE/super-admin-service:$TAG"

echo "Done."
