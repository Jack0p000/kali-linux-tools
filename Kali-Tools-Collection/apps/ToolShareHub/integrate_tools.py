#!/usr/bin/env python3
from pathlib import Path
import re
BASE=Path('/home/jack0p000/ToolShareHub')
items={
'/home/jack0p000/Tools/CertificateWatcher/certificate_watcher.py':'Certificate Watcher',
'/home/jack0p000/Tools/CommandCenter/command_center.py':'Command Center',
'/home/jack0p000/Tools/DNSInspector/dns_inspector.py':'DNS Inspector',
'/home/jack0p000/Tools/FileForensics/file_forensics.py':'FileForensics',
'/home/jack0p000/Tools/FileIntegrityMonitor/file_integrity_monitor.py':'File Integrity Monitor',
'/home/jack0p000/Tools/KaliToolboxBuilder/kali_toolbox_builder.py':'Kali Toolbox Builder',
'/home/jack0p000/Tools/PacketVisualizer/packet_visualizer.py':'Packet Visualizer',
'/home/jack0p000/Tools/PortProcessMapper/port_process_mapper.py':'Port Process Mapper',
'/home/jack0p000/Tools/WiFiSignalMapper/wifi_signal_mapper.py':'WiFi Signal Mapper',
'/home/jack0p000/SystemHealthCenter/health_center.py':'System Health Center',
'/home/jack0p000/NetScope/netscope.py':'NetScope',
'/home/jack0p000/NetScope/webapp.py':'NetScope Web',
'/home/jack0p000/RemoteControlHub/remotehub.py':'RemoteControlHub',
'/home/jack0p000/RemoteControlHub/webapp.py':'RemoteControlHub Web',
'/home/jack0p000/Scaricati/osint_self_audit_v2.py':'OSINT Self-Audit',
'/home/jack0p000/Scaricati/osint_gui.py':'OSINT Self-Audit GUI',
'/home/jack0p000/Scaricati/data_breach_scanner/app.py':'BreachFinder',
'/home/jack0p000/Scrivania/matrix_terminal.py':'Matrix Terminal',
'/home/jack0p000/AvviaDesktopCommander.py':'Desktop Remote Commander',
}
BOOT="""\n# --- ToolShare integration ---\nimport sys as _toolshare_sys\nif '/home/jack0p000/ToolShareHub' not in _toolshare_sys.path:\n    _toolshare_sys.path.insert(0, '/home/jack0p000/ToolShareHub')\nfrom toolshare import register as _ts_register, publish as _ts_publish, context as _ts_context\n_TS_NAME = %r\n_ts_register(_TS_NAME)\n_ts_publish(_TS_NAME, 'startup', {'pid': __import__('os').getpid()})\n# --- end ToolShare integration ---\n"""
for fp,name in items.items():
 p=Path(fp)
 if not p.exists(): continue
 s=p.read_text(errors='ignore')
 if '_TS_NAME' in s: continue
 s=BOOT%name+s
 # Add a compact context read immediately before the first interactive menu where one exists.
 s=s.replace('c=menu("'+name+'")', ' _shared = _ts_context(5)\n if _shared.get("events"): print("\\n[ToolShare] Ultimi eventi condivisi:", len(_shared["events"]))\n c=menu("'+name+'")')
 p.write_text(s)
 print('PATCHED',fp)
