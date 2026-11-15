# BreachFinder

Interfaccia locale per consultare metadati pubblici relativi a violazioni di dati tramite XposedOrNot. Non scarica né mostra dump di credenziali.

## Avvio

```bash
python3 -m pip install -r requirements.txt
cp .env.example .env
# Modifica .env con credenziali personali non riutilizzate altrove
chmod +x run.sh run_tool.sh
./run.sh
```

Apri `http://127.0.0.1:3010`.

- `TOOL_AUTH_USER` e `TOOL_AUTH_PASS` sono obbligatori per il login web.
- `BREACH_HOST` usa `127.0.0.1` per impostazione predefinita.
- Database SQLite e report PDF sono dati locali generati durante l'uso e non vanno versionati.
- Le richieste di verifica inviano l'identificativo inserito al provider XposedOrNot.