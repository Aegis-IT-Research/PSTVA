from pydantic import BaseModel, Field
from pyparsing import Enum


class KerbScanType(str, Enum):
    userenum = "userenum -d {domain} --dc {ip} {wordlist}"
    passwordspray = "passwordspray -d {domain} --dc {ip} {wordlist} {password}"
    bruteuser = "bruteuser -d {domain} --dc {ip} {wordlist} {username}"


class KerbScanDTO(BaseModel):
    project: str = Field(..., description="Project ID to associate the scan results")
    scan_type: KerbScanType
    domain: str = Field(..., description="Active Directory domain (e.g., corp.local)")
    ip: str = Field(..., description="IP address of the target (e.g., 192.168.1.2)")
    username: str | None = Field(
        None, description="Username for authentication (e.g., user)"
    )
    password: str | None = Field(
        None, description="Password for authentication (e.g., password!123)"
    )
    wordlist: str = Field(
        ...,
        description="Path to the wordlist file (USE: opt/wordlists/users.txt or passwords.txt)",
    )
