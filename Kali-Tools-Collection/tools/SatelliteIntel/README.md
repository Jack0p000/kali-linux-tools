# SatelliteIntel

Tool di analisi Earth Observation basato su dati pubblici.

Funzioni:
- catalogo satelliti e TLE pubblici da CelesTrak;
- posizione orbitale calcolata localmente con SGP4;
- ricerca passaggi sopra coordinate inserite dall'utente;
- ricerca acquisizioni Sentinel nel catalogo Copernicus Data Space;
- filtri temporali e cloud cover quando disponibili;
- mappa web locale con tracce e risultati;
- export JSON dei risultati.

Il tool non localizza persone, telefoni o dispositivi. Analizza esclusivamente satelliti e dati pubblici di osservazione della Terra.

## Avvio

```bash
./run_tool.sh
```

Se mancano le dipendenze:

```bash
python3 -m pip install -r requirements.txt
```

La GUI usa localhost e apre automaticamente Chrome.
