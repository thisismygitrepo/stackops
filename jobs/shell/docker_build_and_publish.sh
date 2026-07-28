#!/usr/bin/env bash
set -euo pipefail
set +x

# Validate variant
if [ "$VARIANT" != "slim" ] && [ "$VARIANT" != "ai" ]; then
    echo "❌ ERROR: Invalid variant '$VARIANT'. Must be 'slim' or 'ai'"
    exit 1
fi

LOCAL_IMAGE_REPOSITORY="stackops-$VARIANT"
DOCKERFILE_PATH="./jobs/dockers/Dockerfile_$VARIANT"

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

case "${STACKOPS_DOCKER_ACTION:-}" in
    build)
        echo "🚀 STARTING DOCKER BUILD | Building image ${LOCAL_IMAGE_REPOSITORY}:latest"
        echo "🧹 CLEANUP | Removing old docker image"
        docker image rm "$LOCAL_IMAGE_REPOSITORY:latest" --force >/dev/null 2>&1 || true

        echo "🏗️ BUILD | Creating new docker image"
        docker build --no-cache --file "$DOCKERFILE_PATH" --progress=plain -t "$LOCAL_IMAGE_REPOSITORY:latest" "$REPO_ROOT"

        echo "✨ FINISHED | Try it out using: docker run --rm -it $LOCAL_IMAGE_REPOSITORY:latest /bin/bash hollywood"
        echo "📝 STATUS | Current docker images"
        docker images
        ;;
    publish)
        DOCKER_IMAGE_NAMESPACE="${DOCKER_IMAGE_NAMESPACE:-}"
        DOCKER_IMAGE_REGISTRY="${DOCKER_IMAGE_REGISTRY:-${DOCKER_REGISTRY:-}}"
        if [ -z "$DOCKER_IMAGE_NAMESPACE" ]; then
            echo "❌ ERROR: DOCKER_IMAGE_NAMESPACE is not set."
            exit 1
        fi
        if [ -z "${DOCKER_LOGIN_TOKEN_ENV_VAR:-}" ]; then
            echo "❌ ERROR: DOCKER_LOGIN_TOKEN_ENV_VAR is not set."
            exit 1
        fi
        if ! printenv "$DOCKER_LOGIN_TOKEN_ENV_VAR" >/dev/null; then
            echo "❌ ERROR: Token env var '$DOCKER_LOGIN_TOKEN_ENV_VAR' is not available."
            exit 1
        fi
        if ! docker image inspect "$LOCAL_IMAGE_REPOSITORY:latest" >/dev/null 2>&1; then
            echo "❌ ERROR: Local image '$LOCAL_IMAGE_REPOSITORY:latest' does not exist."
            exit 1
        fi

        IMAGE_REPOSITORY="$DOCKER_IMAGE_NAMESPACE/$LOCAL_IMAGE_REPOSITORY"
        if [ -n "$DOCKER_IMAGE_REGISTRY" ]; then
            IMAGE_REPOSITORY="${DOCKER_IMAGE_REGISTRY%/}/$IMAGE_REPOSITORY"
        fi
        DATE=$(date +%y-%m)
        docker_login_command=(docker login --username "$DOCKER_IMAGE_NAMESPACE" --password-stdin)
        if [ -n "$DOCKER_IMAGE_REGISTRY" ]; then
            docker_login_command=(docker login "$DOCKER_IMAGE_REGISTRY" --username "$DOCKER_IMAGE_NAMESPACE" --password-stdin)
        fi
        echo "🔐 LOGIN | Authenticating Docker as ${DOCKER_IMAGE_NAMESPACE}"
        if ! printenv "$DOCKER_LOGIN_TOKEN_ENV_VAR" | "${docker_login_command[@]}"; then
            echo "❌ ERROR: Docker login failed."
            exit 1
        fi
        echo "✅ PUSHING IMAGES | Uploading to docker registry"
        docker tag "$LOCAL_IMAGE_REPOSITORY:latest" "$IMAGE_REPOSITORY:latest"
        docker push "$IMAGE_REPOSITORY:latest"
        docker tag "$LOCAL_IMAGE_REPOSITORY:latest" "$IMAGE_REPOSITORY:$DATE"
        docker push "$IMAGE_REPOSITORY:$DATE"
        echo "✅ ALL DONE | Docker publish complete."
        ;;
    *)
        echo "❌ ERROR: STACKOPS_DOCKER_ACTION must be 'build' or 'publish'."
        exit 1
        ;;
esac
