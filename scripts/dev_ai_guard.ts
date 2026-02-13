#!/usr/bin/env bun
/**
 * Local pre/post PR guard runner for derivadas workflows.
 * ACTIVE runner: keep this TypeScript/Bun version as the primary one.
 * Python equivalent exists as fallback at `scripts/dev_ai_guard.py`.
 *
 * Examples:
 *   bun scripts/dev_ai_guard.ts --mode pre-pr --db data/ssas.db
 *   bun scripts/dev_ai_guard.ts --mode post-pr --db data/ssas.db
 *   bun scripts/dev_ai_guard.ts --mode pre-pr --skip-tests --skip-health
 */

import { spawnSync } from "node:child_process";
import { existsSync, mkdirSync, writeFileSync } from "node:fs";
import { resolve } from "node:path";

type Mode = "pre-pr" | "post-pr";

type Step = {
  name: string;
  cmd: string[];
};

type StepResult = {
  name: string;
  command: string;
  exitCode: number;
  durationMs: number;
  stdout: string;
  stderr: string;
};

type Options = {
  mode: Mode;
  dbPath: string;
  skipTests: boolean;
  skipHealth: boolean;
  skipLint: boolean;
  skipSyncVerify: boolean;
  outputDir: string;
};

type TablePresence = "present" | "absent" | "unknown";

function guardPythonExecutable(): string {
  const override = (process.env.SSA_DEV_GUARD_PYTHON ?? "").trim();
  if (override) {
    return override;
  }

  const venvPosix = resolve(process.cwd(), ".venv", "bin", "python");
  if (existsSync(venvPosix)) {
    return venvPosix;
  }

  const venvWindows = resolve(process.cwd(), ".venv", "Scripts", "python.exe");
  if (existsSync(venvWindows)) {
    return venvWindows;
  }

  if (spawnSync("python3", ["-c", "print('ok')"], { encoding: "utf8" }).status === 0) {
    return "python3";
  }

  return "python";
}

function usage(): string {
  return [
    "Usage: bun scripts/dev_ai_guard.ts [options]",
    "",
    "Options:",
    "  --mode pre-pr|post-pr   Guard mode (default: pre-pr)",
    "  --db <path>             SQLite DB path (default: data/ssas.db)",
    "  --skip-tests            Skip pytest steps",
    "  --skip-health           Skip schema/scan/sync-health steps",
    "  --skip-lint             Skip py_compile and ruff",
    "  --skip-sync-verify      Skip 'sync --verify-only' health step",
    "  --output-dir <path>     Report directory (default: local_ai_private)",
    "  --help                  Show this help",
  ].join("\n");
}

function parseArgs(argv: string[]): Options {
  const options: Options = {
    mode: "pre-pr",
    dbPath: "data/ssas.db",
    skipTests: false,
    skipHealth: false,
    skipLint: false,
    skipSyncVerify: false,
    outputDir: "local_ai_private",
  };

  for (let index = 0; index < argv.length; index += 1) {
    const arg = argv[index];
    if (arg === "--help" || arg === "-h") {
      console.log(usage());
      process.exit(0);
    }
    if (arg === "--mode") {
      const next = argv[index + 1];
      if (next !== "pre-pr" && next !== "post-pr") {
        throw new Error("--mode must be 'pre-pr' or 'post-pr'");
      }
      options.mode = next;
      index += 1;
      continue;
    }
    if (arg === "--db") {
      const next = argv[index + 1];
      if (!next) {
        throw new Error("--db requires a file path");
      }
      options.dbPath = next;
      index += 1;
      continue;
    }
    if (arg === "--output-dir") {
      const next = argv[index + 1];
      if (!next) {
        throw new Error("--output-dir requires a directory path");
      }
      options.outputDir = next;
      index += 1;
      continue;
    }
    if (arg === "--skip-tests") {
      options.skipTests = true;
      continue;
    }
    if (arg === "--skip-health") {
      options.skipHealth = true;
      continue;
    }
    if (arg === "--skip-lint") {
      options.skipLint = true;
      continue;
    }
    if (arg === "--skip-sync-verify") {
      options.skipSyncVerify = true;
      continue;
    }
    throw new Error(`Unknown argument: ${arg}`);
  }

  return options;
}

function sqliteTablePresence(pythonExe: string, dbPath: string, tableName: string): TablePresence {
  if (!dbPath || !tableName) {
    return "unknown";
  }
  if (!existsSync(dbPath)) {
    return "unknown";
  }
  const probeScript = [
    "import os, sqlite3, sys",
    "db_path = sys.argv[1]",
    "table_name = sys.argv[2]",
    "if not db_path or not table_name or not os.path.exists(db_path):",
    "    print('absent')",
    "    raise SystemExit(0)",
    "try:",
    "    with sqlite3.connect(db_path) as conn:",
    "        row = conn.execute(",
    "            \"SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = ? LIMIT 1\",",
    "            (table_name,),",
    "        ).fetchone()",
    "    print('present' if row is not None else 'absent')",
    "except sqlite3.Error as exc:",
    "    print('unknown')",
    "    print(str(exc), file=sys.stderr)",
  ].join("\n");

  const probe = spawnSync(pythonExe, ["-c", probeScript, dbPath, tableName], {
    cwd: process.cwd(),
    encoding: "utf8",
  });
  const value = (probe.stdout ?? "").trim().split(/\s+/)[0];
  if (probe.status === 0 && (value === "present" || value === "absent" || value === "unknown")) {
    return value;
  }
  const stderr = (probe.stderr ?? "").trim();
  if (stderr) {
    console.error(`Warning: unable to verify table presence (${tableName}) in ${dbPath}: ${stderr}`);
  } else {
    console.error(`Warning: unable to verify table presence (${tableName}) in ${dbPath}: probe failed`);
  }
  return "unknown";
}

function guardStepTimeoutMs(): number {
  const raw = (process.env.SSA_DEV_GUARD_STEP_TIMEOUT_SECONDS ?? "900").trim();
  const parsed = Number(raw);
  if (!Number.isFinite(parsed) || parsed <= 0) {
    return 900_000;
  }
  return Math.min(Math.floor(parsed * 1000), 3_600_000);
}

function buildSteps(pythonExe: string, options: Options, includeSyncVerifyStep: boolean): Step[] {
  const lintTargets = [
    "armazenamento/derivadas_schema.py",
    "armazenamento/derivadas_queries.py",
    "armazenamento/derivadas_sync.py",
    "scripts/derivadas_cli.py",
    "tests/test_derivadas_schema.py",
    "tests/test_derivadas_sync.py",
    "tests/test_derivadas_queries.py",
    "tests/test_derivadas_cli.py",
    "tests/test_derivadas_maintenance.py",
  ];

  const derivadasTests = [
    "tests/test_derivadas_schema.py",
    "tests/test_derivadas_sync.py",
    "tests/test_derivadas_queries.py",
    "tests/test_derivadas_cli.py",
    "tests/test_derivadas_maintenance.py",
  ];

  const postPrTests = [
    "tests/test_derivadas_sync.py",
    "tests/test_derivadas_queries.py",
    "tests/test_derivadas_maintenance.py",
  ];

  const steps: Step[] = [];

  if (!options.skipLint) {
    steps.push({
      name: "py_compile",
      cmd: [pythonExe, "-m", "py_compile", ...lintTargets],
    });
    steps.push({
      name: "ruff_check",
      cmd: [pythonExe, "-m", "ruff", "check", ...lintTargets],
    });
  }

  if (options.mode === "pre-pr") {
    if (!options.skipTests) {
      steps.push({
        name: "pytest_derivadas_suite",
        cmd: [pythonExe, "-m", "pytest", "-q", ...derivadasTests],
      });
    }
    if (!options.skipHealth) {
      steps.push({
        name: "schema_scan",
        cmd: [pythonExe, "scripts/derivadas_cli.py", "--db", options.dbPath, "--output", "json", "schema-scan"],
      });
      steps.push({
        name: "consistency_scan",
        cmd: [pythonExe, "scripts/derivadas_cli.py", "--db", options.dbPath, "--output", "json", "scan"],
      });
      if (includeSyncVerifyStep) {
        steps.push({
          name: "sync_verify_only",
          cmd: [pythonExe, "scripts/derivadas_cli.py", "--db", options.dbPath, "--output", "json", "sync", "--verify-only"],
        });
      }
      steps.push({
        name: "sync_stats",
        cmd: [pythonExe, "scripts/derivadas_cli.py", "--db", options.dbPath, "--output", "json", "stats"],
      });
    }
    return steps;
  }

  if (!options.skipTests) {
    steps.push({
      name: "pytest_post_pr_smoke",
      cmd: [pythonExe, "-m", "pytest", "-q", ...postPrTests],
    });
  }
  if (!options.skipHealth) {
    steps.push({
      name: "schema_scan",
      cmd: [pythonExe, "scripts/derivadas_cli.py", "--db", options.dbPath, "--output", "json", "schema-scan"],
    });
    steps.push({
      name: "consistency_scan",
      cmd: [pythonExe, "scripts/derivadas_cli.py", "--db", options.dbPath, "--output", "json", "scan"],
    });
    steps.push({
      name: "maintenance_scan_only",
      cmd: [
        pythonExe,
        "scripts/derivadas_cli.py",
        "--db",
        options.dbPath,
        "--output",
        "json",
        "maintenance",
        "--min-interval-seconds",
        "0",
        "--no-auto-heal",
      ],
    });
    steps.push({
      name: "sync_stats",
      cmd: [pythonExe, "scripts/derivadas_cli.py", "--db", options.dbPath, "--output", "json", "stats"],
    });
  }
  return steps;
}

function runStep(step: Step): StepResult {
  const startedAt = Date.now();
  const result = spawnSync(step.cmd[0], step.cmd.slice(1), {
    cwd: process.cwd(),
    encoding: "utf8",
    timeout: guardStepTimeoutMs(),
  });
  const durationMs = Date.now() - startedAt;
  const maybeError = result.error as NodeJS.ErrnoException | undefined;
  const timedOut = maybeError?.code === "ETIMEDOUT";
  const stderr = [result.stderr ?? "", maybeError ? String(maybeError) : ""].filter(Boolean).join("\n");
  return {
    name: step.name,
    command: step.cmd.join(" "),
    exitCode: timedOut ? 124 : (result.status ?? -1),
    durationMs,
    stdout: result.stdout ?? "",
    stderr,
  };
}

function writeReport(options: Options, results: StepResult[]): string {
  const reportDir = resolve(process.cwd(), options.outputDir);
  mkdirSync(reportDir, { recursive: true });

  const timestamp = new Date().toISOString().replace(/[:.]/g, "-");
  const reportPath = resolve(reportDir, `dev_ai_guard_${options.mode}_${timestamp}.json`);
  const summary = {
    mode: options.mode,
    dbPath: options.dbPath,
    success: results.every((item) => item.exitCode === 0),
    generatedAt: new Date().toISOString(),
    steps: results,
  };
  writeFileSync(reportPath, JSON.stringify(summary, null, 2), "utf8");
  return reportPath;
}

function main(): number {
  const options = parseArgs(process.argv.slice(2));
  const pythonExe = guardPythonExecutable();
  const tablePresence = sqliteTablePresence(pythonExe, options.dbPath, "ssa_table");
  const autoSkippedSyncVerify =
    options.mode === "pre-pr" &&
    !options.skipHealth &&
    !options.skipSyncVerify &&
    tablePresence === "absent";
  if (autoSkippedSyncVerify) {
    console.log("Notice: skipping sync_verify_only because table 'ssa_table' is missing in DB.");
  }
  if (
    options.mode === "pre-pr" &&
    !options.skipHealth &&
    !options.skipSyncVerify &&
    tablePresence === "unknown"
  ) {
    console.log("Notice: table presence check returned unknown; keeping sync_verify_only enabled.");
  }
  const includeSyncVerifyStep = !autoSkippedSyncVerify && !options.skipSyncVerify;
  const steps = buildSteps(pythonExe, options, includeSyncVerifyStep);
  console.log(`Mode: ${options.mode}`);
  console.log(`DB:   ${options.dbPath}`);
  console.log(`Python: ${pythonExe}`);
  console.log(`Steps planned: ${steps.length}`);

  const results: StepResult[] = [];
  for (const step of steps) {
    console.log(`\n==> ${step.name}`);
    console.log(`$ ${step.cmd.join(" ")}`);
    const result = runStep(step);
    results.push(result);
    if (result.stdout.trim()) {
      console.log(result.stdout.trim());
    }
    if (result.stderr.trim()) {
      console.error(result.stderr.trim());
    }
    if (result.exitCode !== 0) {
      const reportPath = writeReport(options, results);
      console.error(`\nFAILED at step '${step.name}'. Report: ${reportPath}`);
      return 1;
    }
  }

  const reportPath = writeReport(options, results);
  console.log(`\nAll steps passed. Report: ${reportPath}`);
  return 0;
}

try {
  process.exit(main());
} catch (error) {
  const message = error instanceof Error ? error.message : String(error);
  console.error(`Error: ${message}`);
  console.error(usage());
  process.exit(2);
}
