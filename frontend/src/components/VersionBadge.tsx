import type { VersionInfo } from "../lib/types";

interface Props {
  version: VersionInfo;
}

export function VersionBadge({ version }: Props) {
  return (
    <span className="version-badge" data-testid="version-badge" title={`Supported: ${version.supported.join(", ")}`}>
      API {version.current}
    </span>
  );
}
