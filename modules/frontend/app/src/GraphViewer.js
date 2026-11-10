/* ----------------------------------------------------------
 *  GraphViewer – every node clickable, no link interference
 *  • Vulnerability nodes are highlighted in red and display the CVE (node.vuln)
 * -------------------------------------------------------- */
import React, { useRef } from "react";
import ForceGraph2D from "react-force-graph-2d";

const horusec_severity_color = {
  CRITICAL: "#e53935", 
  HIGH: "#fb8c00",     
  MEDIUM: "#fdd835",   
  LOW: "#43a047",      
};

const formatDateTime = (iso) => {
  if (!iso) return "—";
  const d = new Date(iso);
  return d.toLocaleString();
};


const GraphViewer = React.memo(function GraphViewer({ onSelect, onBackgroundClick, width, height, data }) {
  const fgRef = useRef(null);
  const fitted = useRef(false);

  /* fit all nodes into view once the first layout settles (keeps drifting nodes clickable) */
  const handleEngineStop = () => {
    if (fitted.current) return;
    fitted.current = true;
    fgRef.current?.zoomToFit(400, 40);
  };

  /* change cursor */
  const handleHover = (node) => {
    const canvas = fgRef.current?.canvas?.() || fgRef.current?.canvas;
    if (canvas) canvas.style.cursor = node ? "pointer" : "crosshair";
  };

  if (!data) return null;

  /* ----------- Filter and Limit Vulnerabilities ---------------- */
  const processGraphData = (data) => {
    const { nodes, links } = data;

    // Group vulnerabilities by service
    const serviceToVulns = {};
    links.forEach((link) => {
      if (link.type === "HAS_VULN") {
        if (!serviceToVulns[link.source]) {
          serviceToVulns[link.source] = [];
        }
        serviceToVulns[link.source].push(link);
      }
    });

    // Limit vulnerabilities to a maximum of 25 per service
    const filteredLinks = links.filter((link) => {
      if (link.type === "FOUND") return true; 
      if (link.type !== "HAS_VULN") return true; // Keep non-vulnerability links
      const vulns = serviceToVulns[link.source] || [];
      return vulns.indexOf(link) < 25; // Keep only the first 25 vulnerabilities
    });

    // Ensure all nodes are included
    const filteredNodes = nodes.filter((node) => {
      if (node.group === "Project" || node.group === "Scan"|| node.group === "CodeVulnerability") return true;
      if (node.group === "Vulnerability" ) {
        // Check if the vulnerability is linked to a service
        return filteredLinks.some((link) => link.target === node.id);
      }
      // if (node.group === "Log") return false;
      //if (node.group === "Scan") return false;

      return true; // Keep all other nodes
    });

    return { nodes: filteredNodes, links: filteredLinks };
  };

  const filteredData = processGraphData(data);

  /* ----------- drawing helpers ---------------- */
  const R = (n) => (n.group === "Host" ? 16 : 12); /* visible radius */

  const drawNode = (node, ctx, scale, isShadow) => {
    const r = R(node);
    const isVuln = node.group === "Vulnerability";
    const isCodeVuln = node.group === "CodeVulnerability";

    let fillColor = node.color;

    if (isVuln) {
      fillColor = "#ff4d4f"; 
    }

    if (isCodeVuln) {
      let sev = node.severity?.toUpperCase();

      if (!sev && node.rule) {
        if (node.rule.includes("LEAK")) sev = "HIGH";
        else if (node.rule.includes("SECRET")) sev = "CRITICAL";
        else if (node.rule.includes("JAVASCRIPT")) sev = "MEDIUM";
      }

      fillColor = horusec_severity_color[sev] || "#69c0ff";
    }


    /* circle */
    ctx.beginPath();
    ctx.arc(node.x, node.y, r, 0, 2 * Math.PI);
    ctx.fillStyle = fillColor;

    ctx.fill();
    ctx.strokeStyle = "#333";
    ctx.lineWidth = 1;
    ctx.stroke();

    /* label (only on visible canvas) */
    if (!isShadow) {
      let label;
      if (node.group === "Host") {
        label = node.ip;
      } else if (isVuln) {
        label = node.vuln ?? "Unknown Vulnerability";
      } else if (node.group === "CodeVulnerability") {
        label = node.rule ?? node.severity ?? "CODE";
      } else if (node.group === "Project") {
        label = node.name ?? "Project";
      } else if (node.group === "Log") {
        label = node.action ?? "Log";
      } else if (node.group === "Scan") {     
        label = node.tool ?? "Scan";
      } else if (node.group === "File") {
        label = node.path ?? "File";
      } else if (node.group === "WebPath") {
        label = node.url ? new URL(node.url).pathname : "Path";
      } else {
        label = node.portid ?? node.name;
      }
      ctx.font = `bold ${14 / scale}px sans-serif`;
      ctx.fillStyle = "#000";
      ctx.textAlign = "center";
      ctx.textBaseline = "middle";
      ctx.fillText(label, node.x, node.y);
    }
  };

  /* large invisible circle for hit‑testing */
  const drawPickArea = (node, color, ctx) => {
    ctx.fillStyle = color;
    ctx.beginPath();
    ctx.arc(node.x, node.y, R(node) + 8, 0, 2 * Math.PI);
    ctx.fill();
  };

  /* tooltip text */
  const tooltip = (n) => {
    if (n.group === "Host") {
      return `Host: ${n.hostname || "unknown"}\nIP: ${n.ip}`;
    }
    if (n.group === "Vulnerability") {
      return `Vulnerability: ${n.vuln}\nPort: ${n.portid}`;
    }
    if (n.group === "Scan") {
      return `Scan Tool: ${n.tool}\nStarted: ${formatDateTime(n.started_at)}\nCompleted: ${formatDateTime(n.finished_at)}`;
    }
    if (n.group === "CodeVulnerability") {
      return (
        `Code Vulnerability\n` +
        `Severity: ${n.severity || "unknown"}\n` +
        `File: ${n.file || "unknown"}:${n.line ?? "?"}\n` +
        `Rule: ${n.rule || "unknown"}`
      );
    }
    if (n.group === "Log") {
      return `Log Entry\nAction: ${n.action}`;
    }
    if (n.group === "File") {
      return `File: ${n.path}`;
    }
    if (n.group === "WebPath") {
      return `Path: ${n.url}\nStatus: ${n.status}\nSize: ${n.length} bytes`;
    }
    return `Service: ${n.name || "unknown"}\nPort: ${n.portid}\nState: ${n.state}`;
  };

  /* ----------- render graph ------------------- */
  return (
    <>
      <ForceGraph2D
        ref={fgRef}
        graphData={filteredData}
        width={width}
        height={height}
        backgroundColor="rgba(0,0,0,0)"
        nodeAutoColorBy="group"
        linkColor={() => "#b3b3b3"}
        linkDirectionalArrowLength={3}
        linkDirectionalArrowRelPos={1}
        cooldownTicks={60}
        /* painters */
        nodeCanvasObject={drawNode}
        nodePointerAreaPaint={drawPickArea}
        linkPointerAreaPaint={() => {}} /* disable link clicks */
        nodeLabel={tooltip}
        onNodeHover={handleHover}
        onNodeClick={onSelect}
        onBackgroundClick={onBackgroundClick}
        onEngineStop={handleEngineStop}
      />
      {data.loading && (
        <div
          style={{
            position: "absolute",
            top: 0,
            left: 0,
            width: "100%",
            height: "100%",
            background: "rgba(255, 255, 255, 0.8)",
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            zIndex: 10,
          }}
        >
          <span>Loading...</span>
        </div>
      )}
    </>
  );
});

export default GraphViewer;