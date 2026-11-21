const REPOSITORY_TONES = { Clean: "good", Changed: "warn", Missing: "warn", "Not a Git repo": "bad", Bare: "info" };
const SYSTEM_LABELS = {
  system: "System", distro: "Distribution", release: "Release", version: "Kernel version", machine: "Architecture",
  processor: "Processor", hostname: "Hostname", user: "User", home_dir: "Home directory", python_version: "Python",
};

function renderRepos(details) {
  const rows = details.repositories.map((repository) => {
    const changes = el("span", "", repository.local.changes || "—");
    changes.title = "m modified · n new · d deleted · r renamed · u unmerged";
    let commit = "—";
    if (repository.local.committed_at) {
      const committed = new Date(repository.local.committed_at);
      const days = Math.floor((Date.now() - committed.getTime()) / 86400000);
      commit = stack(
        el("span", "", committed.toLocaleDateString(undefined, { year: "numeric", month: "short", day: "numeric" })),
        el("span", "meta", days <= 0 ? "today" : days === 1 ? "1 day ago" : `${days} days ago`),
      );
    }
    return [
      stack(el("span", "name", repository.name), pathCode(repository.local.path)),
      statusLabel(REPOSITORY_TONES[repository.local.state], repository.local.state),
      changes,
      repository.local.branch ?? "—",
      commit,
      stack(el("span", "", `${repository.sync.mode} · ${repository.sync.cloud ?? "no cloud"}`), el("code", "", repository.sync.remotePath ?? "")),
    ];
  });
  return [
    simpleTable(["Repository", "State", "Changes", "Branch", "Last commit", "Sync"], rows, "No repositories registered"),
    factGrid([["Repository spec", pathCode(details.spec_path)]]),
  ];
}

function renderBackup(details) {
  const rows = Object.entries(details.backup_items).flatMap(([group, items]) =>
    Object.entries(items).map(([name, item]) => {
      const tags = el("span", "tags");
      if (item.zip) tags.append(el("span", "tag", "zip"));
      if (item.encryption) tags.append(el("span", "tag", `${item.encryption} encryption`));
      if (item.rel2home) tags.append(el("span", "tag", "relative to home"));
      let share = "—";
      if (/^https?:\/\//.test(item.share_url ?? "")) {
        share = el("a", "", "open");
        share.href = item.share_url;
        share.rel = "noreferrer";
      }
      return [
        stack(el("span", "name", name), el("span", "meta", group)),
        pathCode(item.path_local),
        el("code", "", item.path_cloud ?? "—"),
        tags,
        (item.os ?? []).join(", "),
        share,
        item.note ?? "—",
      ];
    }),
  );
  return [
    factGrid([
      ["Cloud config", details.cloud_config ?? "not set"],
      ["Cloud selection", details.cloud_selection_required ? statusLabel("warn", "required") : statusLabel("good", "not required")],
      ["Backup spec", pathCode(details.source_path)],
    ]),
    simpleTable(["Item", "Local path", "Cloud path", "Options", "Systems", "Share link", "Note"], rows, "No registered backup items"),
  ];
}

function renderSystem(details) {
  return [factGrid(Object.entries(details).map(([key, value]) => [SYSTEM_LABELS[key] ?? key, String(value)]))];
}

function renderShell(details) {
  return [
    checklist([
      { label: "Shell profile", ok: details.exists, present: "exists", absent: "missing", absentTone: "warn", detail: pathCode(details.profile_path) },
      { label: "Init script", ok: details.init_script_exists, present: "exists", absent: "missing", absentTone: "warn", detail: pathCode(details.init_script_path) },
      { label: "Source line in profile", ok: details.source_line_present, present: "present", absent: "missing", absentTone: "warn" },
      { label: "Shell integration", ok: details.configured, present: "configured", absent: "not configured", absentTone: "warn" },
    ]),
  ];
}

function renderSsh(details) {
  const rows = details.keys.map((key) => [
    el("span", "name", key.name),
    stack(key.public_exists ? statusLabel("good", "present") : statusLabel("warn", "missing"), pathCode(key.public_path)),
    stack(key.private_exists ? statusLabel("good", "present") : statusLabel("warn", "missing"), pathCode(key.private_path)),
  ]);
  return [
    checklist([
      { label: "SSH directory", ok: details.ssh_dir_exists, present: "exists", absent: "missing", absentTone: "warn", detail: pathCode(details.ssh_dir_path) },
      { label: "config", ok: details.config_exists, present: "found", absent: "not found", absentTone: "warn" },
      { label: "authorized_keys", ok: details.authorized_keys_exists, present: "found", absent: "not found", absentTone: "muted" },
      { label: "known_hosts", ok: details.known_hosts_exists, present: "found", absent: "not found", absentTone: "muted" },
    ]),
    simpleTable(["Key", "Public key", "Private key"], rows, "No public keys found"),
  ];
}
