export const API = {
  generate: "/api/generate",
  edit: "/api/edit",
  receipt: (versionId: string) => `/api/receipt/${encodeURIComponent(versionId)}`,
  perfLatest: "/api/perf/latest",
  langReport: "/api/lang/report",
  artifacts: (path: string) => `/api/artifacts?path=${encodeURIComponent(path)}`
};
