from __future__ import annotations

from datetime import datetime
from typing import List, Literal, Optional

from pydantic import BaseModel, Field


class RunMeta(BaseModel):
    id: str
    tool: str
    version: Optional[str] = None
    args: Optional[str] = None
    command: Optional[str] = None
    started_at: Optional[datetime] = None
    finished_at: Optional[datetime] = None
    exit_code: Optional[int] = None


class Artifact(BaseModel):
    id: str
    kind: str
    created_at: datetime
    sha256: Optional[str] = None
    raw_text: str
    size_bytes: Optional[int] = None
    truncated: Optional[bool] = None


class FindingTarget(BaseModel):
    type: Literal[
        "host",
        "port",
        "service",
        "url",
        "website",
        "route",
        "inputpoint",
        "unknown",
    ] = "unknown"
    uid: str


class Finding(BaseModel):
    uid: str
    title: str
    severity: str
    category: str
    cve: Optional[str] = None
    cvss: Optional[float] = None
    status: str
    first_seen: datetime
    last_seen: datetime
    target: Optional[FindingTarget] = None


class Evidence(BaseModel):
    id: str
    kind: str
    summary: str
    snippet: Optional[str] = None
    line_start: Optional[int] = None
    line_end: Optional[int] = None
    json_pointer: Optional[str] = None
    created_at: datetime
    finding_uid: Optional[str] = None
    run_id: Optional[str] = None
    artifact_id: Optional[str] = None


class CoreSection(BaseModel):
    version: Literal["core.v1"] = "core.v1"
    artifacts: List[Artifact] = Field(default_factory=list)
    findings: List[Finding] = Field(default_factory=list)
    evidence: List[Evidence] = Field(default_factory=list)


class NetworkCPE(BaseModel):
    uri: str
    first_seen: Optional[datetime] = None
    last_seen: Optional[datetime] = None
    confidence: Optional[float] = None


class NetworkService(BaseModel):
    uid: str
    name: str
    product: Optional[str] = None
    version: Optional[str] = None
    banner_hash: Optional[str] = None
    first_seen: Optional[datetime] = None
    last_seen: Optional[datetime] = None
    protocol: Optional[str] = None
    state: Optional[str] = None
    port: Optional[int] = None
    cpe: List[NetworkCPE] = Field(default_factory=list)


class NetworkPort(BaseModel):
    uid: str
    proto: str
    port: int
    state: str
    first_seen: Optional[datetime] = None
    last_seen: Optional[datetime] = None
    service: Optional[NetworkService] = None


class NetworkHost(BaseModel):
    id: str
    state: Optional[str] = None
    hostname: Optional[str] = None
    domain: Optional[str] = None
    created_at: Optional[datetime] = None
    last_seen: Optional[datetime] = None
    ports: List[NetworkPort] = Field(default_factory=list)


class NetworkSection(BaseModel):
    version: Literal["network.v1"] = "network.v1"
    hosts: List[NetworkHost] = Field(default_factory=list)


class WebSite(BaseModel):
    uid: str
    scheme: str
    first_seen: Optional[datetime] = None
    last_seen: Optional[datetime] = None


class WebSection(BaseModel):
    version: Literal["web.v1"] = "web.v1"
    websites: List[WebSite] = Field(default_factory=list)


class CombinedPayload(BaseModel):
    schema_version: Literal["aegis.v1"] = "aegis.v1"
    project_id: str
    run: RunMeta
    core: Optional[CoreSection] = None
    network: Optional[NetworkSection] = None
    web: Optional[WebSection] = None
    emitted_at: datetime = Field(default_factory=datetime.utcnow)
