# NetScope

Network inventory tool for authorized networks.

## V1
- automatic local IPv4 target detection
- host discovery with Nmap
- MAC collection when available
- SQLite scan history
- CLI table output
- JSON output

## Usage
```bash
cd ~/NetScope
python3 netscope.py
python3 netscope.py 192.168.1.0/24
python3 netscope.py --json
```

Use only on networks you own or are explicitly authorized to assess.
