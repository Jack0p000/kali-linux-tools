# Kali Tools Collection

Raccolta di utility e applicazioni sviluppate per Kali Linux, con interfacce da terminale e dashboard web dove previste.

Progetto personale per apprendimento, amministrazione e verifiche su sistemi e reti propri o per i quali si dispone di autorizzazione.

## Struttura

### tools/
- FileForensics
- CertificateWatcher
- DNSInspector
- PortProcessMapper
- WiFiSignalMapper
- FileIntegrityMonitor
- PacketVisualizer
- KaliToolboxBuilder
- CommandCenter

### apps/
- NetScope
- RemoteControlHub
- SystemHealthCenter
- ToolShareHub
- OSINT-Self-Audit
- MatrixTerminal
- AvviaDesktopCommander
- ToolAuth (senza credenziali personali)

### assets/
Icone dei tool incluse nella raccolta.

## Requisiti

I requisiti cambiano in base al singolo progetto. Consultare il README o i file di dipendenze presenti nella relativa cartella prima dell'avvio.

## Sicurezza e privacy

- Non sono inclusi database locali, report generati, sessioni, ambienti virtuali o dipendenze scaricate.
- Le credenziali personali sono escluse: configurare le proprie credenziali localmente e non caricarle su GitHub.
- Usare gli strumenti esclusivamente su dispositivi, account e reti propri o con autorizzazione esplicita.

## Stato

Copia sorgente preparata per la pubblicazione. Verificare e completare le configurazioni specifiche di ciascun tool prima del rilascio pubblico.

## Avviatori desktop

La cartella `launchers/` contiene i file `.desktop` dei tool inclusi (escluso BreachFinder). Sono conservati come riferimento per l'installazione originale su Kali; i percorsi assoluti del computer di sviluppo potrebbero dover essere adattati su un'altra macchina.

## Esclusioni intenzionali

BreachFinder è escluso su richiesta. Non sono inclusi repository di terze parti installati sul sistema (ad esempio PhoneSploit, THC-Hydra, Skipfish o OWASP Dependency-Check), né backup, report, log e dati runtime.
