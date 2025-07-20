# 🔧 Quick Fix für Docker Socket Problem

## Problem
API Error 503: "Docker service not available" obwohl docker.sock im Container vorhanden ist.

## Ursache
Docker Socket Berechtigungsproblem - der `webuser` im Container kann nicht auf den Docker Socket zugreifen.

## 🚀 Schnelle Lösung

### Option 1: Automatisches Fix Script (Empfohlen)
```bash
cd web
chmod +x fix_docker_socket.sh
./fix_docker_socket.sh
```

### Option 2: Manuelle Schritte

1. **Docker Socket GID ermitteln:**
   ```bash
   stat -c %g /var/run/docker.sock
   ```

2. **Container mit korrekter GID starten:**
   ```bash
   cd web
   export DOCKER_GID=$(stat -c %g /var/run/docker.sock)
   docker-compose -f docker-compose.web.yml down
   docker-compose -f docker-compose.web.yml build --no-cache
   docker-compose -f docker-compose.web.yml up -d
   ```

3. **Testen:**
   ```bash
   docker exec obs-web-manager python3 debug_docker.py
   ```

### Option 3: Privileged Mode (Nur für Testing)
```yaml
# In docker-compose.web.yml hinzufügen:
privileged: true
```

## 🔍 Diagnose

**Container-Logs prüfen:**
```bash
docker logs obs-web-manager
```

**Debug-Script ausführen:**
```bash
docker exec obs-web-manager python3 debug_docker.py
```

## ✅ Erfolgreich wenn:
- Container-Logs zeigen: "✅ Docker client connected successfully"
- Web-Interface zeigt Instances ohne 503 Fehler
- Debug-Script zeigt: "✅ Docker daemon ping successful"

## 🆘 Falls immer noch Probleme:

1. **Docker Daemon Status prüfen:**
   ```bash
   systemctl status docker
   ```

2. **Socket Berechtigungen prüfen:**
   ```bash
   ls -la /var/run/docker.sock
   ```

3. **Container neu bauen:**
   ```bash
   docker-compose -f docker-compose.web.yml build --no-cache --pull
   ```

4. **Als letzter Ausweg - Root-Modus:**
   ```yaml
   # In docker-compose.web.yml:
   user: "0:0"  # Root user
   ```

Nach dem Fix sollten alle Instance-Operationen funktionieren! 🎉
