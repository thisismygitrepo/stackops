## Quick Reference

```bash
# === Package Installation ===
devops i btop                    # Install single package
devops i btop,fd,bat             # Install multiple packages
devops i termabc -g              # Install package group
devops i -i                      # Interactive mode
devops i https://github.com/...  # From GitHub

# === Group Installation (Recommended Order) ===
devops i sysabc -g               # 1. System essentials
devops i termabc -g              # 2. Terminal tools
devops i agents -g               # 3. AI assistants (optional)

# === Script Execution ===
devops e -l                      # List scripts
devops e my_script               # Run script
devops e -i                      # Interactive

# === Help ===
devops --help
devops install --help
```

---

## Platform Support

| Feature | Linux | macOS | Windows |
|---------|-------|-------|---------|
| Package Manager Install | `apt`, `nala`, `snap` | `brew` | `winget`, `scoop` |
| GitHub Release Install | ✅ | ✅ | ✅ |
| Custom Python Installers | ✅ | ✅ | ✅ |
| Shell Script Installers | ✅ | ✅ | ❌ |
| PowerShell Installers | ❌ | ❌ | ✅ |
| Binary Path | `~/.local/bin` | `/usr/local/bin` | `%LOCALAPPDATA%\\Microsoft\\WindowsApps` |

---

## See Also

- [Installer Module API](../api/jobs/installer.md) - Detailed API documentation
- [Package Groups](../api/jobs/installer.md#package-groups) - Full package group contents
- [Custom Installers](../api/jobs/installer.md#custom-python-installers) - Creating custom installers
