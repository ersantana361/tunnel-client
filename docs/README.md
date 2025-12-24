# Tunnel Client Documentation

Welcome to the Tunnel Client documentation. This guide will help you set up, configure, and use the tunnel client to expose your local services to the internet.

---

## Quick Navigation

| Section | Description |
|---------|-------------|
| [Getting Started](./getting-started/) | Installation and first steps |
| [Configuration](./configuration/) | YAML config file reference |
| [Usage](./usage/) | Web UI, CLI, and service management |
| [API Reference](./api/) | REST API endpoints |
| [Examples](./examples/) | Common use cases and recipes |
| [Troubleshooting](./troubleshooting/) | Common issues and solutions |
| [Architecture](./architecture/) | How it works internally |

---

## What is Tunnel Client?

Tunnel Client is a web-based interface for managing [FRP (Fast Reverse Proxy)](https://github.com/fatedier/frp) tunnels. It allows you to:

- Expose local web servers, APIs, and databases to the internet
- Define tunnels in a simple YAML configuration file
- Monitor tunnel status through a web UI
- Control the frpc service (start/stop/restart)

### Key Features

- **YAML Configuration** - Define all tunnels in `tunnels.yaml`
- **Web Dashboard** - Monitor status at `http://127.0.0.1:3000`
- **Hot Reload** - Update tunnels without restarting
- **Secure by Default** - Listens on localhost only
- **Systemd Integration** - Run as a background service

---

## Quick Links

### New Users
1. [Installation Guide](./getting-started/#installation)
2. [Quick Start](./getting-started/#quick-start)
3. [Your First Tunnel](./examples/#example-1-expose-a-web-server)

### Configuration
- [Config File Format](./configuration/#config-file-format)
- [Tunnel Types](./configuration/#tunnel-types)
- [Server Settings](./configuration/#server-settings)

### Daily Usage
- [Web UI Guide](./usage/#web-ui)
- [CLI Options](./usage/#cli-options)
- [Managing Tunnels](./usage/#managing-tunnels)

### Reference
- [API Endpoints](./api/#endpoints)
- [File Locations](./architecture/#files)
- [Troubleshooting](./troubleshooting/)

---

## Documentation Structure

```
docs/
├── README.md                 # This file (main index)
├── getting-started/
│   └── README.md             # Installation & quick start
├── configuration/
│   └── README.md             # YAML config reference
├── usage/
│   └── README.md             # Web UI, CLI, service management
├── api/
│   └── README.md             # REST API reference
├── examples/
│   └── README.md             # Use cases & recipes
├── troubleshooting/
│   └── README.md             # Common issues & solutions
└── architecture/
    └── README.md             # Internals & how it works
```

---

## Support

- **Issues**: [GitHub Issues](https://github.com/your-repo/tunnel-client/issues)
- **Main README**: [../README.md](../README.md)
- **Example Config**: [../tunnels.example.yaml](../tunnels.example.yaml)

---

## Version

This documentation is for Tunnel Client v1.0 with YAML-based configuration.

---

[Back to Project Root](../) | [Getting Started](./getting-started/) | [Configuration](./configuration/)
