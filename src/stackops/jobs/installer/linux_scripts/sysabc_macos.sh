

/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
# Homebrew on Apple Silicon lives outside the default PATH
if [ -x /opt/homebrew/bin/brew ]; then
    eval "$(/opt/homebrew/bin/brew shellenv)"
fi
echo "🔄 Updating Homebrew..."
brew update || true

curl -fsSL https://bun.com/install | bash
# brew install openssl ffmpeg make curl nano git
echo "✅ Essential tools installation complete."
