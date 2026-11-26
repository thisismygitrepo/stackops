
# a line starting with ::step:: opens a step in the group install view
echo "::step::1/3 Homebrew"
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
# Homebrew on Apple Silicon lives outside the default PATH
if [ -x /opt/homebrew/bin/brew ]; then
    eval "$(/opt/homebrew/bin/brew shellenv)"
fi
echo "::step::2/3 update Homebrew"
brew update || true

echo "::step::3/3 bun"
curl -fsSL https://bun.com/install | bash
# brew install openssl ffmpeg make curl nano git
echo "✅ Essential tools installation complete."
