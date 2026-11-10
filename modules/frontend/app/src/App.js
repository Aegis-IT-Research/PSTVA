import React, { useState, useEffect, useCallback } from "react";
import GraphViewer from "./GraphViewer";
import Login from "./Login";
import { isAuthenticated, clearToken } from "./auth";
import { apiFetch, authFetchRaw } from "./api";
import { TOOL_OPTIONS } from "./constants";
import { useDebounce } from "./hooks";
import TopBar from "./components/TopBar";
import SidebarPanel from "./components/SidebarPanel";
import ReportEditor from "./components/ReportEditor";

// Sidebar card: 10px offset + 420px width (Theme.css .glass-panel) + 10px gap
const SIDEBAR_SPACE = 440;

// Layout fields added by the graph library; hidden from the node details view
const GRAPH_LAYOUT_KEYS = ["x", "y", "vx", "vy", "fx", "fy", "index", "__indexColor", "color"];
const nodeDetails = (node) =>
  Object.fromEntries(Object.entries(node).filter(([k]) => !GRAPH_LAYOUT_KEYS.includes(k)));

export default function App() {
  const [authed, setAuthed] = useState(isAuthenticated());
  const [toolIdx, setToolIdx] = useState(0);
  const [typeIdx, setTypeIdx] = useState(0);
  const [target, setTarget] = useState("");
  const [flags, setFlags] = useState(TOOL_OPTIONS[0].scanTypes[0].flags);
  const [loading, setLoading] = useState(false);
  const [json, setJson] = useState(null);
  const [selectedNode, setSelectedNode] = useState(null);
  const clearSelectedNode = useCallback(() => setSelectedNode(null), []);
  const [graphKey, setGraphKey] = useState(0);
  const [isEditingReport, setIsEditingReport] = useState(false);
  const [reportMd, setReportMd] = useState("");
  const [formData, setFormData] = useState({});
  const [file, setFile] = useState(null);

  const [projectName, setProjectName] = useState("");
  const [newProjectName, setNewProjectName] = useState("");
  const [existingProjects, setExistingProjects] = useState([]);

  const [{ width, height }, setWin] = useState({
    width: window.innerWidth,
    height: window.innerHeight
  });

  useEffect(() => {
    const onResize = () => setWin({ width: window.innerWidth, height: window.innerHeight });
    window.addEventListener("resize", onResize);
    return () => window.removeEventListener("resize", onResize);
  }, []);

  useEffect(() => {
    if (!authed) return;
    apiFetch("/back/projects")
      .then(data => {
        if (Array.isArray(data)) setExistingProjects(data);
        else if (data.projects && Array.isArray(data.projects)) setExistingProjects(data.projects);
        else setExistingProjects([]);
      })
      .catch((e) => {
        // Token missing/expired/invalid: force re-login
        if (e && (e.status === 401 || e.status === 422)) {
          clearToken();
          setAuthed(false);
        }
        setExistingProjects([]);
      });
  }, [authed]);

  const tool = TOOL_OPTIONS[toolIdx];
  const mode = tool.mode || "target"; 

  const handleScan = async () => {
    setLoading(true);
    try {
      
      let effectiveProjectId = projectName;

      if (!effectiveProjectId) {
        if (!newProjectName.trim()) {
          alert("Please enter a project name");
          return;
        }

        const data = await apiFetch(`/back/create_project`, {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
          },
          body: JSON.stringify({ name: newProjectName }),
        });

        const createdProjectId = data?.id || data?.project?.id;

        if (!createdProjectId) {
          console.error("Unexpected create_project response:", data);
          throw new Error("Project creation failed");
        }

        effectiveProjectId = createdProjectId;
        setProjectName(createdProjectId);
        setExistingProjects(prev => [
          ...prev,
          { id: createdProjectId, name: newProjectName }
        ]);
        setNewProjectName("");

      }


      if (mode === "target") {
        const selected = tool.scanTypes[typeIdx];
        const scanKey = selected.key;

        const url = `/back/${tool.endpoint}?` +
          `project=${encodeURIComponent(effectiveProjectId)}` +
          `&target=${encodeURIComponent(target)}` +
          `&scan_type=${encodeURIComponent(scanKey)}`;

        await apiFetch(url, { method: "POST" });
      }

      if (mode === "form") {
        const params = new URLSearchParams({
          project: effectiveProjectId,
          ...formData,
        });

        await apiFetch(`/back/${tool.endpoint}?${params.toString()}`, {
          method: "POST",
        });
      }

      if (mode === "file") {
        const form = new FormData();
        form.append("file", file);

        const res = await authFetchRaw(
          `/back/${tool.endpoint}?project=${encodeURIComponent(effectiveProjectId)}`,
          {
            method: "POST",
            body: form,
          }
        );

        if (!res.ok) {
          throw new Error(await res.text());
        }
      }

      await fetchGraph(effectiveProjectId);
    } catch (err) {
      console.error("Scan failed:", err);
      alert("Scan failed: " + err.message);
    } finally {
      setLoading(false);
    }
  };

  const handleNewProject = async () => {
    if (!newProjectName.trim()) return;
    setLoading(true);
    try {
      const data = await apiFetch(`/back/create_project`, {
        method: "POST",
        body: JSON.stringify({ name: newProjectName }),
      });
      if (data.status === "Project created successfully") {
        // Note: backend returns { project: {...} } – adapt if needed
        setExistingProjects(prev => [...prev, { id: data.id, name: newProjectName }]);
        setProjectName(data.id);
        setNewProjectName("");
        await fetchGraph(data.id);
      } else {
        console.error("Failed to create project:", data.error || "Unknown error");
      }
    } catch (err) {
      console.error("Error creating project:", err);
    } finally {
      setLoading(false);
    }
  };

  // Removed Fetch Report handler (no longer used)

  const handleGenerateReport = async () => {
    if (!projectName) {
      alert("Please select a project first.");
      return;
    }
    setLoading(true);
    try {
      const md = await apiFetch(`/back/get_findings?project=${encodeURIComponent(projectName)}`);
      setReportMd(typeof md === "string" ? md : String(md || ""));
      setIsEditingReport(true);
    } catch (e) {
      alert("Generate report failed – " + (e.message || "unknown error"));
    } finally {
      setLoading(false);
    }
  };

  const fetchGraph = async (proj) => {
    if (!proj || proj === "New Project") return;
    setLoading(true);
    try {
      const data = await apiFetch(`/back/graph?project=${encodeURIComponent(proj)}`);
      setJson(data);
      setSelectedNode(null);
      setGraphKey(k => k + 1);
    } catch (err) {
      console.error("Failed to fetch graph data:", err);
      setJson({ error: "Failed to fetch graph data" });
    } finally {
      setLoading(false);
    }
  };

  const debouncedTarget = useDebounce(target, 300);
  useEffect(() => {
    void debouncedTarget;
  }, [debouncedTarget]);

  if (!authed) return <Login onLogin={() => setAuthed(true)} />;

  return (
    <>
      <TopBar onLogout={() => { clearToken(); setAuthed(false); }} />

      {isEditingReport ? (
        <ReportEditor
          width={width}
          height={height}
          value={reportMd}
          onChange={setReportMd}
          onClose={() => setIsEditingReport(false)}
          onGeneratePdf={async (md) => {
            try {
              setLoading(true);
              const blob = new Blob([md || ""], { type: "text/markdown" });
              const form = new FormData();
              form.append("file", blob, "report.md");

              const res = await authFetchRaw("/back/report/upload_md_to_pdf", {
                method: "POST",
                body: form,
              });

              if (!res.ok) {
                const txt = await res.text().catch(() => "");
                throw new Error(txt || res.statusText || "Upload failed");
              }

              const ct = (res.headers.get("content-type") || "").toLowerCase();
              if (!ct.includes("application/pdf")) {
                const txt = await res.text().catch(() => "");
                throw new Error(txt || "Unexpected response type (not PDF)");
              }

              const pdfBlob = await res.blob();
              const url = window.URL.createObjectURL(pdfBlob);
              const a = document.createElement("a");

              // Try to honor filename from Content-Disposition
              const cd = res.headers.get("content-disposition") || "";
              let fname = `report_${projectName || "download"}.pdf`;
              const m = /filename\*=UTF-8''([^;]+)|filename="?([^";]+)"?/i.exec(cd);
              if (m) {
                try { fname = decodeURIComponent(m[1] || m[2] || fname); } catch (_) {}
              }

              a.href = url;
              a.download = fname;
              document.body.appendChild(a);
              a.click();
              setTimeout(() => {
                document.body.removeChild(a);
                window.URL.revokeObjectURL(url);
              }, 0);
            } catch (e) {
              alert("PDF generation failed: " + (e.message || String(e)));
            } finally {
              setLoading(false);
            }
          }}
        />
      ) : (
        // Graph lives right of the fixed sidebar card, so no node can hide under it
        <div style={{ marginLeft: SIDEBAR_SPACE }}>
          <GraphViewer
            key={graphKey}
            data={projectName ? json : null}
            onSelect={setSelectedNode}
            onBackgroundClick={clearSelectedNode}
            width={Math.max(width - SIDEBAR_SPACE, 300)}
            height={height}
          />
        </div>
      )}

      {!isEditingReport && (
        <SidebarPanel
          height={height}
          projectName={projectName}
          setProjectName={setProjectName}
          existingProjects={existingProjects}
          newProjectName={newProjectName}
          setNewProjectName={setNewProjectName}
          onCreateProject={handleNewProject}
          onSelectProject={fetchGraph}
          target={target}
          setTarget={setTarget}
          toolIdx={toolIdx}
          setToolIdx={(i) => {
            setToolIdx(i);
            setTypeIdx(0);

            const nextTool = TOOL_OPTIONS[i];
            if (nextTool.scanTypes && nextTool.scanTypes.length > 0) {
              setFlags(nextTool.scanTypes[0].flags || "");
            } else {
              setFlags("");
            }

            setFormData({});
            setFile(null);
          }}

          typeIdx={typeIdx}
          setTypeIdx={(i) => { setTypeIdx(i); setFlags(TOOL_OPTIONS[toolIdx].scanTypes[i].flags); }}
          flags={flags}
          setFlags={setFlags}
          formData={formData}
          setFormData={setFormData}
          file={file}
          setFile={setFile}
          onRunScan={handleScan}
          onGenerateReport={handleGenerateReport}
          loading={loading}
          json={selectedNode ? nodeDetails(selectedNode) : json}
          nodeSelected={!!selectedNode}
          TOOL_OPTIONS={TOOL_OPTIONS}
        />
      )}
    </>
  );
}
