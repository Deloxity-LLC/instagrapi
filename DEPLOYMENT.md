# Instagrapi REST API - Deployment Anleitung

## Deployment über Dokploy

### Voraussetzungen
- Dokploy Installation
- GitHub Account verbunden mit Dokploy
- Geforktes Repository: `Deloxity-LLC/instagrapi`

### Schritt-für-Schritt Anleitung

#### 1. In Dokploy einloggen
Gehe zu deiner Dokploy-Instanz

#### 2. Neues Application erstellen
- Klicke auf "New Application"
- Wähle **GitHub** als Provider

#### 3. Repository konfigurieren
- **GitHub Account**: Wähle deinen Account (`Dokploy-2025-12-31-6d688e`)
- **Repository**: Wähle `instagrapi`
- **Branch**: `master`
- **Build Path**: `/` (Root)

#### 4. Build-Einstellungen
- **Dockerfile**: `Dockerfile` (wird automatisch erkannt)
- **Port**: `8000`

#### 5. Environment Variables (Optional)
Keine zwingend erforderlich für den Start.

#### 6. Deploy
- Klicke auf **Save**
- Dann auf **Deploy**

### Nach dem Deployment

Die API wird verfügbar sein unter:
- **API Docs (Swagger)**: `http://deine-domain:8000/docs`
- **Health Check**: `http://deine-domain:8000/health`

### API Endpoints

#### Authentifizierung
```bash
POST /auth/login
{
  "username": "dein_instagram_username",
  "password": "dein_passwort"
}
```

Antwort:
```json
{
  "status": "success",
  "session_id": "session_1",
  "user_id": "123456789",
  "message": "Login successful"
}
```

#### User Informationen abrufen
```bash
POST /user/info
{
  "session_id": "session_1",
  "username": "target_username"
}
```

#### User Medias abrufen
```bash
POST /user/target_username/medias?session_id=session_1&amount=20
```

#### Foto hochladen
```bash
POST /photo/upload?session_id=session_1
Content-Type: multipart/form-data

file: [photo.jpg]
caption: "Mein neues Foto"
```

#### Media liken
```bash
POST /media/{media_id}/like?session_id=session_1
```

#### Media kommentieren
```bash
POST /media/{media_id}/comment?session_id=session_1&text=Nice post!
```

#### Logout
```bash
DELETE /session/{session_id}
```

### Lokales Testen (vor dem Deployment)

```bash
# Docker Build
docker build -t instagrapi-api .

# Docker Run
docker run -p 8000:8000 instagrapi-api

# Oder mit Docker Compose
docker-compose -f docker-compose.prod.yml up
```

### Wichtige Hinweise

1. **Session Management**: Die aktuelle Implementation speichert Sessions im Speicher. Für Production solltest du Redis oder eine Datenbank verwenden.

2. **Rate Limits**: Instagram hat strikte Rate Limits. Nutze die API verantwortungsvoll.

3. **2FA**: Falls dein Instagram-Account 2FA aktiviert hat, musst du den Code beim Login angeben.

4. **Proxies**: Für Production-Nutzung wird empfohlen, Proxies zu verwenden (siehe instagrapi Dokumentation).

5. **Account-Sicherheit**: Nutze am besten einen Test-Account, nicht deinen Haupt-Account.

### Troubleshooting

#### Build schlägt fehl
- Prüfe ob das Dockerfile im Root-Verzeichnis liegt
- Prüfe die Logs in Dokploy

#### API startet nicht
- Prüfe den Health Check: `curl http://localhost:8000/health`
- Schaue in die Container-Logs

#### Login funktioniert nicht
- Prüfe Instagram-Credentials
- Möglicherweise Challenge erforderlich
- 2FA Code notwendig

### Support

- [Instagrapi Dokumentation](https://subzeroid.github.io/instagrapi/)
- [Instagrapi GitHub Issues](https://github.com/subzeroid/instagrapi/issues)
- [Telegram Support Chat](https://t.me/instagrapi)
