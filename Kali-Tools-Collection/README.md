# Kali Tools Collection

Raccolta di utility e applicazioni personalizzate per Kali Linux, sviluppate per apprendimento, amministrazione, monitoraggio e verifiche su sistemi e reti propri o per i quali si dispone di autorizzazione.

## Struttura

### tools/
- AutoSecFlow
- CertificateWatcher
- CommandCenter
- DNSInspector
- FileForensics
- FileIntegrityMonitor
- KaliToolboxBuilder
- PacketVisualizer
- PortProcessMapper
- SatelliteIntel
- WiFiSignalMapper

### apps/
- BreachFinder
- DesktopRemoteCommander
- MatrixTerminal
- NetScope
- OSINT-Self-Audit
- RemoteControlHub
- SystemHealthCenter
- ToolAuth
- ToolShareHub

**Totale: 20 progetti** (11 tool e 9 applicazioni).

## SatelliteIntel

SatelliteIntel aggiunge una GUI per analizzare dati orbitali pubblici e cataloghi di osservazione della Terra. Usa TLE pubblici di CelesTrak, propagazione orbitale SGP4 locale e metadati Sentinel-2 del Copernicus Data Space. Permette di inserire coordinate, calcolare posizioni orbitali e individuare passaggi vicini al target, oltre a interrogare il catalogo Sentinel. Consultare [tools/SatelliteIntel/README.md](tools/SatelliteIntel/README.md) per requisiti e avvio.

## AutoSecFlow

AutoSecFlow aggiunge un workflow builder visuale per concatenare controlli difensivi locali: snapshot del sistema, inventario SHA-256 di una directory, verifica della scadenza di certificati TLS e registrazione di eventi. I workflow sono salvati localmente; l'interfaccia è limitata a localhost e non accetta comandi shell arbitrari. Consultare [tools/AutoSecFlow/README.md](tools/AutoSecFlow/README.md) per requisiti e avvio.

## Requisiti e avvio

I requisiti variano in base al progetto. Consultare il README e il file `requirements.txt`, se presente, nella cartella dello strumento. Gli script `run.sh` e `run_tool.sh` sono disponibili dove previsti.

## Sicurezza e privacy

- Non sono inclusi database locali, report generati, sessioni, ambienti virtuali o dipendenze scaricate.
- Le credenziali personali non sono incluse. Configurare le proprie credenziali localmente e non caricarle su GitHub.
- BreachFinder interroga metadati pubblici tramite XposedOrNot; non scarica dump di credenziali.
- SatelliteIntel analizza satelliti e dati pubblici di osservazione della Terra; non è progettato per localizzare persone o dispositivi.
- Usare gli strumenti esclusivamente su dispositivi, account e reti propri o con autorizzazione esplicita.
- Verificare le impostazioni di rete e autenticazione prima di esporre un'interfaccia web.

## Note

Questa repository raccoglie i progetti sviluppati per Kali Linux. Non include software di terze parti semplicemente installato sul sistema, backup, log, report o dati runtime.
