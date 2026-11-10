import React from "react";
import ReactJson from "@uiw/react-json-view";
import { githubDarkTheme } from "@uiw/react-json-view/githubDark";

// Dark theme matching the glass panel; bigger monospace text for readability
const JSON_STYLE = {
  ...githubDarkTheme,
  "--w-rjv-background-color": "rgba(13,17,23,0.75)",
  fontFamily: "ui-monospace, SFMono-Regular, Consolas, monospace",
  fontSize: 13,
  lineHeight: 1.6,
  borderRadius: 8,
  padding: 10,
};

export default function SidebarPanel({
  height,
  projectName,
  setProjectName,
  existingProjects,
  newProjectName,
  setNewProjectName,
  onCreateProject,
  onSelectProject,
  target,
  setTarget,
  toolIdx,
  setToolIdx,
  typeIdx,
  setTypeIdx,
  flags,
  setFlags,
  formData,
  setFormData,
  file,
  setFile,
  onRunScan,
  onGenerateReport,
  loading,
  json,
  nodeSelected,
  TOOL_OPTIONS,
}) {
  const tool = TOOL_OPTIONS[toolIdx];
  const scanTypes = tool.scanTypes;
  const mode = tool.mode || "target";

  return (
    <div className="glass-panel" style={{ height: height - 20 }}>
      <div className="panel-scroll">
        <p style={{ fontWeight: 600, marginBottom: 8 }}>
          Assessment:
          <select
            className="panel-select"
            onChange={(e) => {
              const selectedProject = e.target.value;
              if (selectedProject === "New Assessment") {
                setProjectName("");
                setNewProjectName("");
              } else {
                setProjectName(selectedProject);
                onSelectProject(selectedProject);
              }
            }}
            value={projectName || "New Assessment"}
          >
            <option value="New Assessment">-- New Assessment --</option>
            {existingProjects.map((p) => (
              <option key={p.id} value={p.id}>{p.name}</option>
            ))}
          </select>

          {projectName === "" && (
            <div style={{ marginTop: 8 }}>
              <input
                className="panel-input"
                type="text"
                value={newProjectName}
                onChange={(e) => setNewProjectName(e.target.value)}
                placeholder="Enter Assessment Name"
                onKeyDown={(e) => { if (e.key === "Enter") onCreateProject(); }}
              />
            </div>
          )}
        </p>

        {mode === "target" && (
          <label className="panel-label">
            Target
            <input
              className="panel-input"
              value={target}
              onChange={(e) => setTarget(e.target.value)}
              placeholder={tool.placeholder || "Enter target"}
            />
          </label>
        )}

        {mode === "form" &&
          tool.inputs.map((input) => (
            <label key={input.name} className="panel-label">
              {input.label}

              {input.type === "select" ? (
                <select
                  className="panel-select"
                  value={formData[input.name] || ""}
                  onChange={(e) =>
                    setFormData({
                      ...formData,
                      [input.name]: e.target.value,
                    })
                  }
                >
                  <option value="">-- Select --</option>
                  {(tool.scanTypes || []).map((opt) => (
                    <option key={opt.key} value={opt.key}>
                      {opt.label}
                    </option>
                  ))}
                </select>
              ) : (
                <input
                  className="panel-input"
                  type={input.type}
                  placeholder={input.placeholder || ""}
                  value={formData[input.name] || ""}
                  onChange={(e) =>
                    setFormData({
                      ...formData,
                      [input.name]: e.target.value,
                    })
                  }
                />
              )}
            </label>
          ))}

        {mode === "file" && (
          <label className="panel-label">
            Upload ZIP
            <input
              className="panel-input"
              type="file"
              accept=".zip"
              onChange={(e) => setFile(e.target.files[0])}
            />
          </label>
        )}

        <div className="tool-grid">
          {TOOL_OPTIONS.map((t, i) => (
            <button
              key={t.name}
              className="panel-btn"
              style={{
                outline: toolIdx === i ? `3px solid ${t.color}` : undefined,
                filter: toolIdx === i ? undefined : "grayscale(0.3) brightness(0.9)"
              }}
              onClick={() => setToolIdx(i)}
            >
              {t.name}
            </button>
          ))}
        </div>

        {mode === "target" && (
          <label className="panel-label">
            Scan Type
            <select
              className="panel-select"
              value={typeIdx}
              onChange={e => setTypeIdx(Number(e.target.value))}
            >
              {scanTypes.map((t, i) => (
                <option key={t.label} value={i}>{t.label}</option>
              ))}
            </select>
          </label>
        )}

        {mode === "target" && (
          <label className="panel-label">
            Flags
            <input
              className="panel-input"
              value={flags}
              onChange={e => setFlags(e.target.value)}
            />
          </label>
        )}

        <div className="panel-row" style={{ margin: "8px 0" }}>
          <button onClick={onRunScan} disabled={
                                        loading ||
                                        (!projectName && !newProjectName.trim()) ||
                                        (mode === "target" && !target) ||
                                        (mode === "file" && !file) ||
                                        (mode === "form" &&
                                          tool.inputs.some(
                                            (i) => i.required && !formData[i.name]
                                          ))
                                      } className="panel-btn">{mode === "file" ? "Upload & Scan" : "Run Scan"}</button>
          <button onClick={onGenerateReport} disabled={loading || !projectName} className="panel-btn secondary">Generate Report</button>
        </div>

        <div style={{ marginTop: 8 }}>
          <div style={{ fontSize: 12, opacity: 0.8, marginBottom: 4 }}>
            {nodeSelected
              ? "Selected node. Click empty space in the graph to show all data."
              : "All data. Click a node in the graph to see its details."}
          </div>
          <ReactJson
            value={json || { info: "No data loaded yet" }}
            style={JSON_STYLE}
            collapsed={nodeSelected ? false : 2}  /* a single node: show everything */
            displayDataTypes={false}
            shortenTextAfterLength={120}          /* default 30 cuts URLs and CVE titles */
            objectSortKeys
          />
        </div>
      </div>
    </div>
  );
}
