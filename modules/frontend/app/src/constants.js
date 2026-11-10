export const TOOL_OPTIONS = [
  {
    name: "Nmap",
    scanTypes: [
      { label: "Quick", key: "quick", flags: "-T4 -F" },
      { label: "Service/Version", key: "service_version", flags: "-sV" },
      { label: "Vulnerability", key: "vulnerability", flags: "-sV --script vulners" },
      { label: "OS Detection", key: "os_detection", flags: "-O" },
      { label: "Top Ports", key: "top_ports", flags: "--top-ports 1000" }
    ],
    placeholder: "Host/IP e.g. 192.168.1.1",
    endpoint: "nmap/scan",
    targetParam: "target",
    color: "#3869f6",
  },
  {
    name: "Nikto",
    scanTypes: [
      { label: "Default", key: "default", flags: "-h" },
      { label: "Plugins", key: "Plugins", flags: "--list-plugins" },
      { label: "SSL", key: "SSL", flags: "--ssl" }
    ],
    placeholder: "IP/host, with http[s]:// or just hostname",
    endpoint: "nikto/scan",
    targetParam: "target",
    color: "#2ecc71",
  },
  {
    name: "FFuF",
    scanTypes: [
      { label: "Directories", key: "dir", flags: "-w directory-list.txt" },
      { label: "Dirs + Extensions", key: "extensions", flags: "-e .php,.html,.txt,.bak" }
    ],
    placeholder: "Base URL e.g. http://192.168.1.1",
    endpoint: "ffuf/scan",
    targetParam: "target",
    color: "#e67e22",
  },
  {
    name: "ADenum",
    mode: "form",
    endpoint: "adenum/scan",
    color: "#f1c40f",

    inputs: [
      { name: "domain", label: "Domain", type: "text", placeholder: "Active directory domain", required: true },
      { name: "ip", label: "IP Address", type: "text", placeholder: "e.g.192.168.1.10", required: true },
      { name: "username", label: "Username", type: "text", placeholder: "username", required: true },
      { name: "password", label: "Password", type: "password", placeholder: "password", required: true },
    ],
  },
  {
    name: "Kerbrute",
    mode: "form",
    endpoint: "kerbrute/scan",
    color: "#f70a0a",

    inputs: [
      { name: "ip", label: "Domain Controller IP", type: "text", placeholder: "e.g. 192.168.1.10", required: true },
      { name: "domain", label: "Domain", type: "text", placeholder: "Active directory domain", required: true },
      { name: "wordlist", label: "Wordlist Path", type: "text", placeholder: "Use /opt/wordlists/users.txt or passwords.txt", required: true },
      { name: "scan_type", label: "Scan Type", type: "select", required: true },
    ],

    scanTypes: [
      { label: "User Enum", key: "userenum" },
      { label: "Password Spray", key: "passwordspray" },
      { label: "Bruteforce", key: "bruteforce" },
    ],
  },
  {
    name: "Horusec",
    mode: "file",
    endpoint: "horusec/scan",
    color: "#685dbc",

    inputs: [
      { name: "file", label: "Upload ZIP", type: "file", accept: ".zip", required: true },
    ],
  },
];