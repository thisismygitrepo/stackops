#!/bin/bash
set +x

# # Force user to specify variant
# if [ $# -eq 0 ]; then
#     echo "❌ ERROR: Please specify a variant: 'slim' or 'ai'"
#     echo "Usage: $0 <variant>"
#     echo "Example: $0 slim"
#     exit 1
# fi

# VARIANT=$1

# Validate variant
if [ "$VARIANT" != "slim" ] && [ "$VARIANT" != "ai" ]; then
    echo "❌ ERROR: Invalid variant '$VARIANT'. Must be 'slim' or 'ai'"
    exit 1
fi

IMAGE_NAME="stackops-$VARIANT"
DOCKER_IMAGE_NAMESPACE="${DOCKER_IMAGE_NAMESPACE:-${DOCKER_USERNAME:-}}"
DOCKER_IMAGE_REGISTRY="${DOCKER_IMAGE_REGISTRY:-${DOCKER_REGISTRY:-}}"
if [ -z "$DOCKER_IMAGE_NAMESPACE" ]; then
    echo "❌ ERROR: DOCKER_IMAGE_NAMESPACE is not set. Run via 'devops self build-docker' so StackOps can select Docker credentials."
    exit 1
fi
IMAGE_REPOSITORY="$DOCKER_IMAGE_NAMESPACE/$IMAGE_NAME"
if [ -n "$DOCKER_IMAGE_REGISTRY" ]; then
    IMAGE_REPOSITORY="${DOCKER_IMAGE_REGISTRY%/}/$IMAGE_REPOSITORY"
fi
DOCKERFILE_PATH="./jobs/dockers/Dockerfile_$VARIANT"
DATE=$(date +%y-%m)

# Ensure build uses repository root as Docker build context and fail early with useful messages.
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR"/../.. && pwd)"
if [ ! -d "$REPO_ROOT" ]; then
    echo "❌ ERROR: Could not determine repository root (expected $REPO_ROOT)"
    exit 1
fi

if [ ! -f "$DOCKERFILE_PATH" ]; then
    echo "❌ ERROR: Dockerfile not found at $DOCKERFILE_PATH (script was run from $(pwd))."
    echo "           Try running the script from the repository root or run this script via its path."
    exit 1
fi


echo """🚀 STARTING DOCKER BUILD | Building image ${IMAGE_REPOSITORY}:${DATE} """
echo """🧹 CLEANUP | Removing old docker images"""
docker rmi "$IMAGE_REPOSITORY:latest" --force
docker rmi "$IMAGE_REPOSITORY:$DATE" --force

echo """🏗️ BUILD | Creating new docker image"""
docker build --no-cache --file "$DOCKERFILE_PATH" --progress=plain -t "$IMAGE_REPOSITORY:latest" "$REPO_ROOT"
# building with no cache since docker is unaware of changes in code due to dynamic code like curl URL | bash etc.


echo """✨ FINISHED | Try it out using: docker run --rm -it $IMAGE_REPOSITORY:latest
🧰 HELPFUL CLEANUP COMMANDS:
Use this to clean instances: docker ps --all -q | xargs docker rm
Delete images: docker rmi -f \$(docker images -q)
docker ps --all -q | xargs docker rm; docker rmi -f \$(docker images -q)
docker run --rm -it $IMAGE_REPOSITORY:latest /bin/bash hollywood
"""

echo """📝 STATUS | Current docker images"""
docker images

echo """📤 REGISTRY | Push to docker registry"""
printf "❓ Do you want to push to the registry? (y/n): "
read answer
case "$answer" in
    [Yy]* )
        if [ -z "${DOCKER_LOGIN_TOKEN_ENV_VAR:-}" ]; then
            echo "❌ ERROR: DOCKER_LOGIN_TOKEN_ENV_VAR is not set. Run via 'devops self build-docker' so StackOps can select the token env var."
            exit 1
        fi
        if ! printenv "$DOCKER_LOGIN_TOKEN_ENV_VAR" >/dev/null; then
            echo "❌ ERROR: Token env var '$DOCKER_LOGIN_TOKEN_ENV_VAR' is not available."
            exit 1
        fi
        docker_login_command=(docker login --username "$DOCKER_IMAGE_NAMESPACE" --password-stdin)
        if [ -n "$DOCKER_IMAGE_REGISTRY" ]; then
            docker_login_command=(docker login "$DOCKER_IMAGE_REGISTRY" --username "$DOCKER_IMAGE_NAMESPACE" --password-stdin)
        fi
        echo """    🔐 LOGIN | Authenticating Docker as ${DOCKER_IMAGE_NAMESPACE}
    """
        if ! printenv "$DOCKER_LOGIN_TOKEN_ENV_VAR" | "${docker_login_command[@]}"; then
            echo "❌ ERROR: Docker login failed."
            exit 1
        fi
        echo """    ✅ PUSHING IMAGES | Uploading to docker registry
    """
        docker push "$IMAGE_REPOSITORY:latest"
        docker tag "$IMAGE_REPOSITORY:latest" "$IMAGE_REPOSITORY:$DATE"
        docker push "$IMAGE_REPOSITORY:$DATE"
        ;;
    * )
        echo """    ❌ PUSH ABORTED | Registry upload canceled"""
        echo """    You can push later using:
    docker push $IMAGE_REPOSITORY:latest
    docker tag $IMAGE_REPOSITORY:latest $IMAGE_REPOSITORY:$DATE
    docker push $IMAGE_REPOSITORY:$DATE
    """
        ;;
esac
echo """✅ ALL DONE | Docker build and publish script complete."""
