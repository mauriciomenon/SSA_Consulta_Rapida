#!/usr/bin/env bun
/**
 * Local pre/post PR guard runner for derivadas workflows.
 *
 * Examples:
 *   bun scripts/dev_ai_guard.ts --mode pre-pr --db data/ssas.db
 *   bun scripts/dev_ai_guard.ts --mode post-pr --db data/ssas.db
 *   bun scripts/dev_ai_guard.ts --mode pre-pr --skip-tests --skip-health
 */

import { spawnSync } from "node:child_process";
import { mkdirSync, writeFileSync } from "node:fs";
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

function buildSteps(options: Options): Step[] {
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
      cmd: ["python", "-m", "py_compile", ...lintTargets],
    });
    steps.push({
      name: "ruff_check",
      cmd: ["ruff", "check", ...lintTargets],
    });
  }

  if (options.mode === "pre-pr") {
    if (!options.skipTests) {
      steps.push({
        name: "pytest_derivadas_suite",
        cmd: ["pytest", "-q", ...derivadasTests],
      });
    }
    if (!options.skipHealth) {
      steps.push({
        name: "schema_scan",
        cmd: ["python", "scripts/derivadas_cli.py", "--db", options.dbPath, "--output", "json", "schema-scan"],
      });
      steps.push({
        name: "consistency_scan",
        cmd: ["python", "scripts/derivadas_cli.py", "--db", options.dbPath, "--output", "json", "scan"],
      });
      if (!options.skipSyncVerify) {
        steps.push({
          name: "sync_verify_only",
          cmd: ["python", "scripts/derivadas_cli.py", "--db", options.dbPath, "--output", "json", "sync", "--verify-only"],
        });
      }
      steps.push({
        name: "sync_stats",
        cmd: ["python", "scripts/derivadas_cli.py", "--db", options.dbPath, "--output", "json", "stats"],
      });
    }
    return steps;
  }

  if (!options.skipTests) {
    steps.push({
      name: "pytest_post_pr_smoke",
      cmd: ["pytest", "-q", ...postPrTests],
    });
  }
  if (!options.skipHealth) {
    steps.push({
      name: "schema_scan",
      cmd: ["python", "scripts/derivadas_cli.py", "--db", options.dbPath, "--output", "json", "schema-scan"],
    });
    steps.push({
      name: "consistency_scan",
      cmd: ["python", "scripts/derivadas_cli.py", "--db", options.dbPath, "--output", "json", "scan"],
    });
    steps.push({
      name: "maintenance_scan_only",
      cmd: [
        "python",
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
      cmd: ["python", "scripts/derivadas_cli.py", "--db", options.dbPath, "--output", "json", "stats"],
    });
  }
  return steps;
}

function runStep(step: Step): StepResult {
  const startedAt = Date.now();
  const result = spawnSync(step.cmd[0], step.cmd.slice(1), {
    cwd: process.cwd(),
    encoding: "utf8",
  });
  const durationMs = Date.now() - startedAt;
  return {
    name: step.name,
    command: step.cmd.join(" "),
    exitCode: result.status ?? -1,
    durationMs,
    stdout: result.stdout ?? "",
    stderr: result.stderr ?? "",
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
  const steps = buildSteps(options);
  console.log(`Mode: ${options.mode}`);
  console.log(`DB:   ${options.dbPath}`);
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
