export const API = {
  health: "/api/health",
  generate: "/api/generate",
  edit: "/api/edit",
  projects: "/api/projects",
  project: (projectId: string) => `/api/projects/${encodeURIComponent(projectId)}`,
  receipt: (projectId: string, versionId: string) =>
    `/api/receipt/${encodeURIComponent(projectId)}/${encodeURIComponent(versionId)}`,
  perfLatest: "/api/perf/latest",
  langReport: "/api/lang/report",
  artifacts: (path: string) => `/api/artifacts?path=${encodeURIComponent(path)}`,
};
