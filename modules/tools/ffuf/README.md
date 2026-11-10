# FFuF Module

Web content discovery with [ffuf](https://github.com/ffuf/ffuf).

- Endpoint: `POST /back/ffuf/scan?target=http://host[:port]&scan_type=dir|extensions&project=<id>`
- Scan types: `dir` (directory wordlist), `extensions` (same plus `.php,.html,.txt,.bak`).
- Wordlists are baked into the image under `/wordlists/` (`docker/wordlists/`).
- Image `ffuf-tool:latest` is built by `make build` here, or automatically on the first scan.
- Each hit is stored as a `WebPath` node: `Host -[:Runs]-> Service -[:HAS_PATH]-> WebPath`.
